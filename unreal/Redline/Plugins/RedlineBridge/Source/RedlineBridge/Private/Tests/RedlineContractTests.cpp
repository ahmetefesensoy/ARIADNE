#include "Misc/AutomationTest.h"
#include "RedlineCoords.h"
#include "RedlineTypes.h"
#include "RedlineRoverActor.h"
#include "RedlineStaleMonitor.h"
#include "RedlineBridgeSubsystem.h"
#include "RedlineSettings.h"
#include "Subsystems/SubsystemCollection.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Components/StaticMeshComponent.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineWheelVisuals,"Redline.Contracts.PhysicalWheelVisuals",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineWheelVisuals::RunTest(const FString& Parameters)
{
    UWorld::InitializationValues Values;
    Values.AllowAudioPlayback(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Values);
    auto* Rover=World->SpawnActor<ARedlineRoverActor>();
    const TArray<FString> Names={TEXT("wheel_fl_link"),TEXT("wheel_ml_link"),TEXT("wheel_rl_link"),TEXT("wheel_fr_link"),TEXT("wheel_mr_link"),TEXT("wheel_rr_link")};
    TSharedRef<FJsonObject> Scene=MakeShared<FJsonObject>();Scene->SetNumberField(TEXT("physics_stamp_s"),12);
    TArray<TSharedPtr<FJsonValue>> Wheels;
    for(const FString& Name:Names)
    {
        auto* Visual=World->SpawnActor<ARedlineRoverActor>();Visual->AttachToActor(Rover,FAttachmentTransformRules::KeepRelativeTransform);
        Rover->WheelVisuals.Add(Name,Visual);
        TSharedRef<FJsonObject> W=MakeShared<FJsonObject>();W->SetStringField(TEXT("name"),Name);
        W->SetObjectField(TEXT("position"),FRedlineJson::Parse(TEXT(R"({"x":1,"y":0.8,"z":-0.6})")));
        W->SetObjectField(TEXT("orientation"),FRedlineJson::Parse(TEXT(R"({"x":0,"y":0.7071067811865475,"z":0,"w":0.7071067811865476})")));
        Wheels.Add(MakeShared<FJsonValueObject>(W));
    }
    Scene->SetArrayField(TEXT("wheels"),Wheels);
    TSharedRef<FJsonObject> Packet=MakeShared<FJsonObject>();Packet->SetStringField(TEXT("data"),FRedlineJson::Write(Scene));
    Rover->ApplyWheelScene(Packet);
    TestEqual(TEXT("six actual relative poses applied atomically"),Rover->AppliedWheelSceneCount,1);
    for(const auto& Wheel:Rover->WheelVisuals)
    {
        TestTrue(TEXT("metre/handedness conversion preserves suspension position"),Wheel.Value->GetRootComponent()->GetRelativeTransform().GetTranslation().Equals(FVector(100,-80,-60),1e-6));
        TestTrue(TEXT("wheel rotation applied"),Wheel.Value->GetRootComponent()->GetRelativeTransform().GetRotation().Equals(FQuat(0,0.7071067811865475,0,0.7071067811865476),1e-6));
    }
    Rover->ApplyWheelScene(Packet);TestEqual(TEXT("replayed/stale scene ignored"),Rover->AppliedWheelSceneCount,1);
    Scene->SetNumberField(TEXT("physics_stamp_s"),13);Scene->SetArrayField(TEXT("wheels"),TArray<TSharedPtr<FJsonValue>>());
    Packet->SetStringField(TEXT("data"),FRedlineJson::Write(Scene));Rover->ApplyWheelScene(Packet);
    TestEqual(TEXT("incomplete wheel array cannot partially overwrite"),Rover->AppliedWheelSceneCount,1);
    World->DestroyWorld(false);return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlinePresentationSource,"Redline.Contracts.PhysicalPresentationSource",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlinePresentationSource::RunTest(const FString& Parameters)
{
    auto* Settings=GetMutableDefault<URedlineSettings>(); const bool Auto=Settings->bAutoConnect; Settings->bAutoConnect=false;
    auto* Instance=NewObject<UGameInstance>(); auto* Bridge=NewObject<URedlineBridgeSubsystem>(Instance); Bridge->AddToRoot(); FSubsystemCollection<UGameInstanceSubsystem> Collection; Bridge->Initialize(Collection); Settings->bAutoConnect=Auto;
    const FString Topic=TEXT("/redline/presentation/rover_1/odom"); Bridge->Subscribe(Topic,TEXT("nav_msgs/msg/Odometry"));
    FString Raw=TEXT(R"({"op":"publish","topic":"/redline/presentation/rover_1/odom","msg":{"header":{"frame_id":"map","stamp":{"sec":12,"nanosec":500000000}},"child_frame_id":"rover_1/base_link","pose":{"pose":{"position":{"x":145,"y":-325,"z":-3597.4},"orientation":{"x":0,"y":0,"z":0,"w":1}}}}})");
    Bridge->HandleEnvelope(Raw); TestEqual(TEXT("namespaced display source accepts only explicit rover map pose"),Bridge->ReceivedCount,1);
    FString Wrong=Raw.Replace(TEXT("\"frame_id\":\"map\""),TEXT("\"frame_id\":\"rover_1/odom\""));
    Bridge->HandleEnvelope(Wrong); TestEqual(TEXT("physical display requires map frame"),Bridge->ReceivedCount,1);
    Wrong=Raw.Replace(TEXT("rover_1/base_link"),TEXT("rover_2/base_link")); Bridge->HandleEnvelope(Wrong);
    TestEqual(TEXT("other robot rejected"),Bridge->ReceivedCount,1);
    Bridge->Deinitialize(); Bridge->RemoveFromRoot(); return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineManualIntent,"Redline.Manual.KeyboardIntent",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineManualIntent::RunTest(const FString& Parameters)
{
    TestTrue(TEXT("forward is ROS +X"),ARedlineRoverActor::ManualIntent(true,true,false,false,false,false).Equals(FVector2D(.3,0)));
    TestTrue(TEXT("backward is ROS -X"),ARedlineRoverActor::ManualIntent(true,false,true,false,false,false).Equals(FVector2D(-.3,0)));
    TestTrue(TEXT("left is ROS +yaw"),ARedlineRoverActor::ManualIntent(true,false,false,true,false,false).Equals(FVector2D(0,.3)));
    TestTrue(TEXT("right is ROS -yaw"),ARedlineRoverActor::ManualIntent(true,false,false,false,true,false).Equals(FVector2D(0,-.3)));
    TestTrue(TEXT("brake overrides keys"),ARedlineRoverActor::ManualIntent(true,true,false,true,false,true).IsNearlyZero());
    TestTrue(TEXT("focus loss overrides keys"),ARedlineRoverActor::ManualIntent(false,true,false,true,false,false).IsNearlyZero());
    TestTrue(TEXT("opposing keys cancel"),ARedlineRoverActor::ManualIntent(true,true,true,true,true,false).IsNearlyZero());
    TestTrue(TEXT("release stops"),ARedlineRoverActor::ManualIntent(true,false,false,false,false,false).IsNearlyZero());
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineCoordsRoundTrip,"Redline.Coords.RoundTrip",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineCoordsRoundTrip::RunTest(const FString& Parameters)
{
    FRandomStream Random(7714);
    for (int32 I=0;I<1000;++I)
    {
        FVector P(Random.FRandRange(-1e5,1e5),Random.FRandRange(-1e5,1e5),Random.FRandRange(-1e5,1e5));
        const FQuat Q=FRotator(Random.FRandRange(-180,180),Random.FRandRange(-180,180),Random.FRandRange(-180,180)).Quaternion();
        TestTrue(TEXT("metre/cm position round trip <1e-4m"),P.Equals(URedlineCoords::UeToRosLocation(URedlineCoords::RosToUeLocation(P)),1e-4));
        const FQuat Round=URedlineCoords::UeToRosRotation(URedlineCoords::RosToUeRotation(Q));
        TestTrue(TEXT("full 3D quaternion round trip incl sign-equivalent q/-q"),FMath::Abs(Q|Round)>1.0-1e-12 && Round.IsNormalized());
        const FQuat Negative(-Q.X,-Q.Y,-Q.Z,-Q.W);
        TestTrue(TEXT("q/-q have identical basis rotations"),URedlineCoords::RosToUeRotation(Q).RotateVector(FVector(0.2,-0.3,0.7)).Equals(URedlineCoords::RosToUeRotation(Negative).RotateVector(FVector(0.2,-0.3,0.7)),1e-10));
    }
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineAxes,"Redline.Coords.Axes",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineAxes::RunTest(const FString& Parameters)
{
    TestEqual(TEXT("ROS +x -> UE +X centimetres"),URedlineCoords::RosToUeLocation(FVector(1,0,0)),FVector(100,0,0));
    TestEqual(TEXT("ROS +y -> UE -Y"),URedlineCoords::RosToUeLocation(FVector(0,1,0)),FVector(0,-100,0));
    TestEqual(TEXT("ROS +z -> UE +Z"),URedlineCoords::RosToUeLocation(FVector(0,0,1)),FVector(0,0,100));
    TestTrue(TEXT("yaw +90 -> yaw -90"),FMath::IsNearlyEqual(URedlineCoords::RosToUeRotation(FQuat(FVector::UpVector,UE_DOUBLE_PI/2)).Rotator().Yaw,-90.0,1e-8));
    TestEqual(TEXT("row-major grid"),URedlineCoords::MapToCellIndex(FVector(3,5,0),FVector::ZeroVector,2,10,10),21);
    TestEqual(TEXT("half-open max edge rejected"),URedlineCoords::MapToCellIndex(FVector(20,0,0),FVector::ZeroVector,2,10,10),INDEX_NONE);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineComposition,"Redline.Coords.MapOdomComposition",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineComposition::RunTest(const FString& Parameters)
{
    FTransform T(FQuat(FVector::UpVector,UE_DOUBLE_PI/2),FVector(10,20,-3500));
    FTransform Result=ARedlineRoverActor::ComposeRosPose(T,FVector(2,3,4),FQuat::Identity);
    TestTrue(TEXT("nonzero origin and ROS yaw90 translate before conversion"),Result.GetTranslation().Equals(FVector(7,22,-3496),1e-8));
    TestTrue(TEXT("composition basis"),Result.GetRotation().RotateVector(FVector::ForwardVector).Equals(FVector::RightVector,1e-8));
    FRandomStream Random(77);
    for (int32 I=0;I<100;++I)
    {
        FQuat A=FRotator(Random.FRandRange(-180,180),Random.FRandRange(-180,180),Random.FRandRange(-180,180)).Quaternion();
        FQuat B=FRotator(Random.FRandRange(-180,180),Random.FRandRange(-180,180),Random.FRandRange(-180,180)).Quaternion();
        FVector P(1,2,3),Origin(100,-30,-3598),Basis(.3,.8,-.2);
        Result=ARedlineRoverActor::ComposeRosPose(FTransform(A,Origin),P,B);
        TestTrue(TEXT("3D ROS rotation composition"),Result.GetRotation().RotateVector(Basis).Equals(A.RotateVector(B.RotateVector(Basis)),1e-8));
        TestTrue(TEXT("3D point composition"),Result.GetTranslation().Equals(Origin+A.RotateVector(P),1e-8));
    }
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineParser,"Redline.Contracts.StrictOdometry",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineParser::RunTest(const FString& Parameters)
{
    FString Raw=TEXT(R"({"header":{"frame_id":"rover_1/odom","stamp":{"sec":12,"nanosec":500000000}},"child_frame_id":"rover_1/base_link","pose":{"pose":{"position":{"x":1,"y":2,"z":3},"orientation":{"x":0,"y":0,"z":0,"w":1}}}})");
    FRedlineOdometry O; FString Error; TestTrue(TEXT("valid odometry parsed"),FRedlineOdometry::Parse(FRedlineJson::Parse(Raw),O,Error));
    TestEqual(TEXT("source physics stamp retained"),O.PhysicsStampSec,12.5);
    Raw.ReplaceInline(TEXT("\"w\":1"),TEXT("\"w\":0"));
    TestFalse(TEXT("zero quaternion rejected"),FRedlineOdometry::Parse(FRedlineJson::Parse(Raw),O,Error));
    TestFalse(TEXT("missing fields rejected"),FRedlineOdometry::Parse(FRedlineJson::Parse(TEXT("{}")),O,Error)); return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineClocks,"Redline.Contracts.ClocksAndFreshness",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineClocks::RunTest(const FString& Parameters)
{
    auto* Settings=GetMutableDefault<URedlineSettings>(); const bool Auto=Settings->bAutoConnect; Settings->bAutoConnect=false;
    auto* Instance=NewObject<UGameInstance>();
    auto* Bridge=NewObject<URedlineBridgeSubsystem>(Instance); Bridge->AddToRoot(); FSubsystemCollection<UGameInstanceSubsystem> Collection; Bridge->Initialize(Collection); Settings->bAutoConnect=Auto;
    Bridge->HandleEnvelope(TEXT(R"({"op":"publish","topic":"/clock","msg":{"clock":{"sec":-1,"nanosec":0}}})"));
    TestFalse(TEXT("malformed clock never marks fresh"),Bridge->StaleMonitor->IsFresh(TEXT("/clock"),FPlatformTime::Seconds()));
    Bridge->Subscribe(TEXT("/rover_1/odom"),TEXT("nav_msgs/msg/Odometry"));
    Bridge->HandleEnvelope(TEXT(R"({"op":"publish","topic":"/rover_1/odom","msg":{}})"));
    TestFalse(TEXT("malformed odometry never marks fresh"),Bridge->StaleMonitor->IsFresh(TEXT("/rover_1/odom"),FPlatformTime::Seconds()));
    Bridge->HandleEnvelope(TEXT(R"({"op":"publish","topic":"/clock","msg":{"clock":{"sec":10,"nanosec":0}}})"));
    Bridge->HandleEnvelope(TEXT(R"({"op":"publish","topic":"/redline/mission/clock","msg":{"clock":{"sec":14400,"nanosec":0}}})"));
    TestEqual(TEXT("physics clock"),Bridge->PhysicsClockSec,10.0); TestEqual(TEXT("PET seek does not move physics clock"),Bridge->MissionClockSec,14400.0);
    auto* Monitor=NewObject<URedlineStaleMonitor>(); Monitor->Watch(TEXT("/odom"),2,100); Monitor->Received(TEXT("/odom"),100);
    TestTrue(TEXT("fresh by monotonic receive time"),Monitor->IsFresh(TEXT("/odom"),101)); TestFalse(TEXT("stale regardless of PET"),Monitor->IsFresh(TEXT("/odom"),103)); Monitor->Disconnected(); TestFalse(TEXT("disconnect invalidates freshness"),Monitor->IsFresh(TEXT("/odom"),100));
    Bridge->Deinitialize(); Bridge->RemoveFromRoot(); return true;
}

class FRedlineReconnectCommand final : public IAutomationLatentCommand
{
    FAutomationTestBase* Test; URedlineBridgeSubsystem* Bridge; double Started=FPlatformTime::Seconds(); bool bFresh=false,bStaleAfterFresh=false,bService=false,bCommandChecked=false,bStaleRejected=false;
public:
    explicit FRedlineReconnectCommand(FAutomationTestBase* InTest):Test(InTest)
    {
        auto* Settings=GetMutableDefault<URedlineSettings>(); const bool Auto=Settings->bAutoConnect; Settings->bAutoConnect=false;
        auto* Instance=NewObject<UGameInstance>();
        Bridge=NewObject<URedlineBridgeSubsystem>(Instance); Bridge->AddToRoot(); FSubsystemCollection<UGameInstanceSubsystem> Collection; Bridge->Initialize(Collection); Settings->bAutoConnect=Auto;
        Bridge->Subscribe(TEXT("/rover_1/odom"),TEXT("nav_msgs/msg/Odometry"),50,1.0); Bridge->Connect();
    }
    virtual bool Update() override
    {
        const double Now=FPlatformTime::Seconds(); const bool Fresh=Bridge->StaleMonitor->IsFresh(TEXT("/rover_1/odom"),Now);
        if (Fresh) bFresh=true; if (bFresh && !Fresh) bStaleAfterFresh=true;
        if (Fresh && !bCommandChecked)
        {
            bCommandChecked=true; FString Error;
            Test->TestTrue(TEXT("fresh command dispatched once"),Bridge->DispatchMissionCommand(TEXT("cmd-test"),TEXT("/t4/echo"),TEXT("std_srvs/srv/Trigger"),MakeShared<FJsonObject>(),{TEXT("/rover_1/odom")},[this](bool Success,const TSharedPtr<FJsonObject>& Reply,const FString& Message){bService=Success && Reply.IsValid();},Error));
            Test->TestFalse(TEXT("duplicate command rejected"),Bridge->DispatchMissionCommand(TEXT("cmd-test"),TEXT("/t4/echo"),TEXT("std_srvs/srv/Trigger"),MakeShared<FJsonObject>(),{},nullptr,Error));
        }
        if (bStaleAfterFresh && !bStaleRejected)
        { FString Error; bStaleRejected=!Bridge->DispatchMissionCommand(TEXT("cmd-stale"),TEXT("/t4/echo"),TEXT("std_srvs/srv/Trigger"),MakeShared<FJsonObject>(),{TEXT("/rover_1/odom")},nullptr,Error); }
        if ((Bridge->ConnectionCount>=2 && Fresh && bStaleAfterFresh && bService) || Now-Started>25)
        {
            Test->TestTrue(TEXT("initial topic received"),bFresh); Test->TestTrue(TEXT("server closure becomes stale"),bStaleAfterFresh); Test->TestTrue(TEXT("stale command rejected"),bStaleRejected); Test->TestTrue(TEXT("reconnected and resubscribed receives topic"),Bridge->ConnectionCount>=2 && Fresh); Test->TestTrue(TEXT("service correlated response"),bService);
            Bridge->Deinitialize(); Bridge->RemoveFromRoot(); return true;
        }
        return false;
    }
};
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineReconnect,"Redline.Bridge.Reconnect",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineReconnect::RunTest(const FString& Parameters)
{
    FString Url; if (!FParse::Value(FCommandLine::Get(),TEXT("RedlineRosbridgeUrl="),Url)) { AddError(TEXT("Start scripts/t4_mock_rosbridge.py on9091 and supply -RedlineRosbridgeUrl=ws://localhost:9091")); return false; }
    ADD_LATENT_AUTOMATION_COMMAND(FRedlineReconnectCommand(this)); return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineServiceReentrancy,"Redline.Contracts.ServiceTimeoutReentrancy",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineServiceReentrancy::RunTest(const FString& Parameters)
{
    auto* Settings=GetMutableDefault<URedlineSettings>(); const bool Auto=Settings->bAutoConnect; Settings->bAutoConnect=false;
    auto* Instance=NewObject<UGameInstance>(); auto* Bridge=NewObject<URedlineBridgeSubsystem>(Instance); Bridge->AddToRoot(); FSubsystemCollection<UGameInstanceSubsystem> Collection; Bridge->Initialize(Collection); Settings->bAutoConnect=Auto;
    int32 ExpiredCount=0,DisconnectedCount=0,ReentryCount=0;
    for (int32 I=0;I<2;++I)
    {
        URedlineBridgeSubsystem::FPending P; P.Deadline=0;
        P.Callback=[&](bool Success,const TSharedPtr<FJsonObject>& Reply,const FString& Reason){++ExpiredCount; Bridge->Disconnect(); Bridge->CallService(TEXT("/unavailable"),TEXT("std_srvs/srv/Trigger"),MakeShared<FJsonObject>(),[&](bool Ok,const TSharedPtr<FJsonObject>& Value,const FString& Why){if (!Ok) ++ReentryCount;});};
        Bridge->PendingServices.Add(FString::FromInt(I),MoveTemp(P));
    }
    URedlineBridgeSubsystem::FPending NonExpired; NonExpired.Deadline=FPlatformTime::Seconds()+100;
    NonExpired.Callback=[&](bool Success,const TSharedPtr<FJsonObject>& Reply,const FString& Reason){++DisconnectedCount;}; Bridge->PendingServices.Add(TEXT("later"),MoveTemp(NonExpired));
    Bridge->Tick(0);
    TestEqual(TEXT("each expired callback exactly once"),ExpiredCount,2); TestEqual(TEXT("disconnect fails other pending once"),DisconnectedCount,1); TestEqual(TEXT("safe synchronous service reentry"),ReentryCount,2); TestEqual(TEXT("pending map empty"),Bridge->PendingServices.Num(),0);
    Bridge->Deinitialize(); Bridge->RemoveFromRoot(); return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineFrameGuards,"Redline.Contracts.PresentationFrameGuards",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineFrameGuards::RunTest(const FString& Parameters)
{
    UWorld::InitializationValues Values;
    Values.AllowAudioPlayback(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Values);
    ARedlineRoverActor* Actor=World->SpawnActor<ARedlineRoverActor>();
    auto Odom=FRedlineJson::Parse(TEXT(R"({"header":{"frame_id":"rover_1/odom","stamp":{"sec":12,"nanosec":0}},"child_frame_id":"rover_1/base_link","pose":{"pose":{"position":{"x":2,"y":3,"z":4},"orientation":{"x":0,"y":0,"z":0,"w":1}}}})"));
    Actor->OnMessage(TEXT("/rover_1/odom"),Odom); TestEqual(TEXT("missing map TF freezes proxy"),Actor->AppliedPoseCount,0);
    auto Static=FRedlineJson::Parse(TEXT(R"({"transforms":[{"header":{"frame_id":"map","stamp":{"sec":0,"nanosec":0}},"child_frame_id":"rover_1/odom","transform":{"translation":{"x":10,"y":20,"z":-3500},"rotation":{"x":0,"y":0,"z":0.7071067811865475,"w":0.7071067811865476}}}]})"));
    Actor->OnMessage(TEXT("/tf_static"),Static); Actor->OnMessage(TEXT("/rover_1/odom"),Odom);
    TestEqual(TEXT("static TF permits pose"),Actor->AppliedPoseCount,1); TestTrue(TEXT("actual actor pose transformed to cm"),Actor->GetActorLocation().Equals(FVector(700,-2200,-349600),1e-7));
    Odom->GetObjectField(TEXT("header"))->SetStringField(TEXT("frame_id"),TEXT("unexpected")); Actor->OnMessage(TEXT("/rover_1/odom"),Odom); TestEqual(TEXT("wrong frame rejected"),Actor->AppliedPoseCount,1);
    Odom->GetObjectField(TEXT("header"))->SetStringField(TEXT("frame_id"),TEXT("rover_1/odom"));
    Actor->OnMessage(TEXT("/tf"),Static); Actor->OnMessage(TEXT("/rover_1/odom"),Odom); TestEqual(TEXT("dynamic TF older than0.5s rejected"),Actor->AppliedPoseCount,1);
    Actor->ConnectionChanged(false); Actor->OnMessage(TEXT("/rover_1/odom"),Odom); TestEqual(TEXT("reconnect cannot reuse old static TF"),Actor->AppliedPoseCount,1);
    Actor->OnMessage(TEXT("/redline/bridge/tf_static_snapshot"),Static);
    AddExpectedError(TEXT("Static TF snapshot invalid; presentation frozen"),EAutomationExpectedErrorFlags::Contains,1);
    Actor->OnMessage(TEXT("/redline/bridge/tf_static_snapshot_status"),FRedlineJson::Parse(TEXT(R"({"data":"{\"valid\":false}"})")));
    Actor->OnMessage(TEXT("/rover_1/odom"),Odom); TestEqual(TEXT("invalid snapshot freezes otherwise fresh odometry"),Actor->AppliedPoseCount,1);
    Actor->OnMessage(TEXT("/redline/bridge/tf_static_snapshot"),Static);
    Actor->OnMessage(TEXT("/redline/bridge/tf_static_snapshot_status"),FRedlineJson::Parse(TEXT(R"({"data":"{\"valid\":true}"})")));
    Actor->OnMessage(TEXT("/rover_1/odom"),Odom); TestEqual(TEXT("late valid history cannot clear quarantined session"),Actor->AppliedPoseCount,1);
    Actor->ConnectionChanged(false); Actor->OnMessage(TEXT("/redline/bridge/tf_static_snapshot"),Static);
    Actor->OnMessage(TEXT("/rover_1/odom"),Odom); TestEqual(TEXT("new connection requires new valid transform"),Actor->AppliedPoseCount,2);
    TestFalse(TEXT("proxy does not simulate physics"),Actor->PresentationMesh->IsSimulatingPhysics());
    World->DestroyWorld(false); return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineOfflineReplay,"Redline.Bridge.OfflineReplay",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineOfflineReplay::RunTest(const FString& Parameters)
{
    auto* Settings=GetMutableDefault<URedlineSettings>(); const bool Auto=Settings->bAutoConnect; Settings->bAutoConnect=false;
    auto* Instance=NewObject<UGameInstance>(); auto* Bridge=NewObject<URedlineBridgeSubsystem>(Instance); Bridge->AddToRoot(); FSubsystemCollection<UGameInstanceSubsystem> Collection; Bridge->Initialize(Collection); Settings->bAutoConnect=Auto;
    FString Path=FPaths::CreateTempFilename(*FPaths::ProjectSavedDir(),TEXT("t4-feed"),TEXT(".jsonl"));
    FString Feed=TEXT("{\"op\":\"publish\",\"topic\":\"/clock\",\"_redline_elapsed_sec\":0,\"msg\":{\"clock\":{\"sec\":10,\"nanosec\":0}}}\n{\"op\":\"publish\",\"topic\":\"/redline/mission/clock\",\"_redline_elapsed_sec\":0,\"msg\":{\"clock\":{\"sec\":3600,\"nanosec\":0}}}\n");
    FFileHelper::SaveStringToFile(Feed,*Path); FString Error; TArray<FString> Topics;
    Bridge->OnTopic.AddLambda([&](const FString& Topic,const TSharedPtr<FJsonObject>& Msg){Topics.Add(Topic);});
    TestTrue(TEXT("ordered offline feed accepted"),Bridge->StartOfflineFeed(Path,Error)); Bridge->Tick(0);
    TestEqual(TEXT("identical envelope event count"),Topics.Num(),2); TestEqual(TEXT("stable event order"),Topics[0],FString(TEXT("/clock"))); TestEqual(TEXT("physics unchanged by replay PET"),Bridge->PhysicsClockSec,10.0); TestEqual(TEXT("mission independent"),Bridge->MissionClockSec,3600.0);
    TestFalse(TEXT("offline feed cannot issue real command"),Bridge->DispatchMissionCommand(TEXT("offline-command"),TEXT("/t4/echo"),TEXT("std_srvs/srv/Trigger"),MakeShared<FJsonObject>(),{},nullptr,Error));
    Bridge->Deinitialize(); Bridge->RemoveFromRoot(); return true;
}
#endif
