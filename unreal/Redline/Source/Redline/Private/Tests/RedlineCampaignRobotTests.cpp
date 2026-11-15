#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Tests/AutomationCommon.h"
#include "RedlineCampaignConsole.h"
#include "RedlineTypes.h"
#include "RedlineSettings.h"
#include "Engine/World.h"
#include "Dom/JsonObject.h"

namespace
{
TSharedRef<FJsonObject> RobotStamp(double Seconds)
{
    auto Stamp=MakeShared<FJsonObject>();const double Whole=FMath::FloorToDouble(Seconds);
    Stamp->SetNumberField(TEXT("sec"),Whole);Stamp->SetNumberField(TEXT("nanosec"),FMath::RoundToDouble((Seconds-Whole)*1e9));return Stamp;
}
TSharedRef<FJsonObject> RobotHeader(double Seconds,const FString& Frame=TEXT("map"))
{
    auto Header=MakeShared<FJsonObject>();Header->SetStringField(TEXT("frame_id"),Frame);Header->SetObjectField(TEXT("stamp"),RobotStamp(Seconds));return Header;
}
TSharedRef<FJsonObject> RobotPose(FVector Point)
{
    auto Pose=MakeShared<FJsonObject>(),P=MakeShared<FJsonObject>(),Q=MakeShared<FJsonObject>();
    P->SetNumberField(TEXT("x"),Point.X);P->SetNumberField(TEXT("y"),Point.Y);P->SetNumberField(TEXT("z"),Point.Z);
    Q->SetNumberField(TEXT("x"),0);Q->SetNumberField(TEXT("y"),0);Q->SetNumberField(TEXT("z"),0);Q->SetNumberField(TEXT("w"),1);
    Pose->SetObjectField(TEXT("position"),P);Pose->SetObjectField(TEXT("orientation"),Q);return Pose;
}
TSharedRef<FJsonObject> RobotOdometry(double Seconds,FVector Point,const FString& Frame=TEXT("map"))
{
    auto Odom=MakeShared<FJsonObject>(),Pose=MakeShared<FJsonObject>();
    Odom->SetObjectField(TEXT("header"),RobotHeader(Seconds,Frame));Odom->SetStringField(TEXT("child_frame_id"),TEXT("rover_1/base_link"));
    Pose->SetObjectField(TEXT("pose"),RobotPose(Point));Odom->SetObjectField(TEXT("pose"),Pose);return Odom;
}
TSharedRef<FJsonObject> RobotPlan(double Seconds,int32 Count)
{
    auto Plan=MakeShared<FJsonObject>();Plan->SetObjectField(TEXT("header"),RobotHeader(Seconds));
    TArray<TSharedPtr<FJsonValue>> Poses;
    for(int32 I=0;I<Count;++I)
    {
        auto P=MakeShared<FJsonObject>();P->SetObjectField(TEXT("header"),RobotHeader(Seconds));
        P->SetObjectField(TEXT("pose"),RobotPose(FVector(-40+I*.1,-382+I*.2,0)));
        Poses.Add(MakeShared<FJsonValueObject>(P));
    }
    Plan->SetArrayField(TEXT("poses"),Poses);return Plan;
}
TSharedRef<FJsonObject> GoalStatus(double Stamp,int32 Status,int32 FirstByte=1)
{
    auto S=MakeShared<FJsonObject>(),Info=MakeShared<FJsonObject>(),Id=MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> Uuid;for(int32 I=0;I<16;++I)Uuid.Add(MakeShared<FJsonValueNumber>(I==0 ? FirstByte : 0));
    Id->SetArrayField(TEXT("uuid"),Uuid);Info->SetObjectField(TEXT("goal_id"),Id);Info->SetObjectField(TEXT("stamp"),RobotStamp(Stamp));
    S->SetObjectField(TEXT("goal_info"),Info);S->SetNumberField(TEXT("status"),Status);return S;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineCampaignRobotTelemetryTest,"Redline.Campaign.RobotTelemetryBoundsAndFreshness",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineCampaignRobotTelemetryTest::RunTest(const FString& Parameters)
{
    TGuardValue<bool> NoConnection(GetMutableDefault<URedlineSettings>()->bAutoConnect,false);FTestWorldWrapper Fixture;
    if(!Fixture.CreateTestWorld(EWorldType::Game)){Fixture.ForwardErrorMessages(this);return false;}
    auto* Screen=Fixture.GetTestWorld()->SpawnActor<ARedlineCampaignConsole>();
    Screen->CaptureRoverPose(RobotOdometry(1,FVector(-40,-382,-3596)),10);
    TestEqual(TEXT("map metres retained without UE handedness conversion"),Screen->RoverMap,FVector(-40,-382,-3596));
    TestFalse(TEXT("one source sample does not invent speed"),Screen->bHasRoverSpeed);
    Screen->CaptureRoverPose(RobotOdometry(2,FVector(-39,-382,-3596)),10.5);
    TestTrue(TEXT("consecutive physics stamps provide speed"),Screen->bHasRoverSpeed);
    TestEqual(TEXT("speed uses physics seconds, not wall interval"),Screen->RoverSpeedMps,1.);
    Screen->CaptureRoverPose(RobotOdometry(2,FVector(-38,-382,-3596)),20);
    TestEqual(TEXT("duplicate source time cannot refresh receipt"),Screen->RoverReceipt,10.5);
    TestEqual(TEXT("duplicate source cannot move the trace"),Screen->RoverMap.X,-39.);
    Screen->CaptureRoverPose(RobotOdometry(3,FVector(-38,-382,-3596),TEXT("rover_1/odom")),12);
    TestEqual(TEXT("local odom cannot be drawn as map"),Screen->RoverReceipt,10.5);
    auto Invalid=RobotOdometry(3,FVector(-38,-382,-3596));
    Invalid->GetObjectField(TEXT("pose"))->GetObjectField(TEXT("pose"))->GetObjectField(TEXT("orientation"))->SetNumberField(TEXT("w"),0);
    Screen->CaptureRoverPose(Invalid,12);TestEqual(TEXT("invalid quaternion cannot freshen display"),Screen->RoverReceipt,10.5);
    Screen->CaptureRoverPose(RobotOdometry(3,FVector(50,-382,-3596)),12);
    TestFalse(TEXT("position jump is not a measured travel speed"),Screen->bHasRoverSpeed);
    TestEqual(TEXT("position jump starts a new trace"),Screen->RoverTrack.Num(),1);
    Screen->CaptureRobotPath(RobotPlan(3,5),12);TestEqual(TEXT("pre-reset path present"),Screen->RobotPath.Num(),5);
    Screen->CaptureRoverPose(RobotOdometry(.5,FVector(-40,-382,-3596)),13);
    TestEqual(TEXT("physics reset clears old plan"),Screen->RobotPath.Num(),0);
    for(int32 I=1;I<=700;++I)Screen->CaptureRoverPose(RobotOdometry(.5+I*.2,FVector(-40+I*.02,-382,-3596)),13+I*.2);
    TestEqual(TEXT("trajectory memory bounded"),Screen->RoverTrack.Num(),Screen->RoverTrackCapacity);
    Screen->ConnectionChanged(false);TestEqual(TEXT("disconnect cannot leave a live trace"),Screen->RoverReceipt,-1.);
    TestEqual(TEXT("disconnect clears trajectory"),Screen->RoverTrack.Num(),0);
    Fixture.ForwardErrorMessages(this);return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineCampaignRobotPathTest,"Redline.Campaign.RobotPlanStatusAndMetricMap",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineCampaignRobotPathTest::RunTest(const FString& Parameters)
{
    TGuardValue<bool> NoConnection(GetMutableDefault<URedlineSettings>()->bAutoConnect,false);FTestWorldWrapper Fixture;
    if(!Fixture.CreateTestWorld(EWorldType::Game)){Fixture.ForwardErrorMessages(this);return false;}
    auto* Screen=Fixture.GetTestWorld()->SpawnActor<ARedlineCampaignConsole>();
    Screen->CaptureRobotPath(RobotPlan(1,600),10);
    TestEqual(TEXT("path decimated to bounded display memory"),Screen->RobotPath.Num(),Screen->RobotPathCapacity);
    TestTrue(TEXT("start/end retained in metres"),Screen->RobotPath[0].Equals(FVector2D(-40,-382),1e-6) && Screen->RobotPath.Last().Equals(FVector2D(19.9,-262.2),1e-6));
    auto Invalid=RobotPlan(2,4);
    Invalid->GetArrayField(TEXT("poses"))[2]->AsObject()->GetObjectField(TEXT("header"))->SetStringField(TEXT("frame_id"),TEXT("odom"));
    Screen->CaptureRobotPath(Invalid,11);TestEqual(TEXT("mixed-frame path preserves last accepted value"),Screen->RobotPathReceipt,10.);
    Screen->CaptureRobotPath(RobotPlan(0,5),12);TestEqual(TEXT("older path cannot replace latest"),Screen->RobotPathReceipt,10.);
    Screen->CaptureRobotPath(RobotPlan(2,4097),13);TestEqual(TEXT("oversized message rejected before drawing"),Screen->RobotPathReceipt,10.);
    Screen->CaptureRobotPath(RobotPlan(3,0),14);TestEqual(TEXT("explicit empty plan clears line"),Screen->RobotPath.Num(),0);
    auto Status=MakeShared<FJsonObject>();Status->SetArrayField(TEXT("status_list"),{
        MakeShared<FJsonValueObject>(GoalStatus(7,2,2)),MakeShared<FJsonValueObject>(GoalStatus(4,4))});
    Screen->CaptureNavStatus(Status,15);TestEqual(TEXT("newest goal wins instead of array position"),Screen->NavStatus,2);
    Status->SetArrayField(TEXT("status_list"),{MakeShared<FJsonValueObject>(GoalStatus(6,4))});
    Screen->CaptureNavStatus(Status,16);TestEqual(TEXT("older succeeded goal cannot override executing goal"),Screen->NavStatus,2);
    Status->SetArrayField(TEXT("status_list"),{MakeShared<FJsonValueObject>(GoalStatus(7,4,2))});
    Screen->CaptureNavStatus(Status,17);TestEqual(TEXT("same goal result advances"),Screen->NavStatus,4);
    Status->SetArrayField(TEXT("status_list"),{MakeShared<FJsonValueObject>(GoalStatus(8,9))});
    Screen->CaptureNavStatus(Status,18);TestEqual(TEXT("malformed status cannot freshen latest result"),Screen->NavStatusReceipt,17.);
    FVector2D Minimum,Maximum;const FVector2D Pixels(548,208);
    TestTrue(TEXT("metric auto-fit available"),Screen->FitRobotMap({FVector2D(-40,-382),FVector2D(30,-300)},Pixels,Minimum,Maximum));
    TestTrue(TEXT("equal metres use equal pixels on both axes"),FMath::IsNearlyEqual((Maximum.X-Minimum.X)/Pixels.X,(Maximum.Y-Minimum.Y)/Pixels.Y,1e-9));
    TestTrue(TEXT("all points fit with padding"),Minimum.X<-40 && Maximum.X>30 && Minimum.Y<-382 && Maximum.Y>-300);
    TestFalse(TEXT("empty telemetry does not invent a map position"),Screen->FitRobotMap({},Pixels,Minimum,Maximum));
    Fixture.ForwardErrorMessages(this);return true;
}
#endif
