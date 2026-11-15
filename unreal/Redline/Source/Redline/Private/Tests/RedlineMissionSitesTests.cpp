#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Tests/AutomationCommon.h"
#include "RedlineMissionSites.h"
#include "RedlineSettings.h"
#include "RedlineCoords.h"
#include "Engine/World.h"
#include "Dom/JsonObject.h"

namespace MissionSitesTests
{
TSharedPtr<FJsonObject> Packet(int32 Active=0)
{
    auto J=MakeShared<FJsonObject>();J->SetStringField(TEXT("schema"),TEXT("redline.campaign.v1"));J->SetStringField(TEXT("run_id"),TEXT("test-sites"));
    J->SetNumberField(TEXT("revision"),Active);J->SetNumberField(TEXT("task_count"),12);J->SetNumberField(TEXT("task_index"),Active);J->SetNumberField(TEXT("progress"),0);J->SetStringField(TEXT("state"),Active==12 ? TEXT("complete") : TEXT("ready"));J->SetBoolField(TEXT("done"),Active==12);
    const TCHAR* Kinds[]={TEXT("briefing"),TEXT("scout"),TEXT("decision"),TEXT("collect"),TEXT("xrf"),TEXT("weather"),TEXT("libs"),TEXT("dan"),TEXT("drill"),TEXT("cache"),TEXT("assessment"),TEXT("debrief")};
    const TCHAR* Endpoints[]={TEXT("/redline/campaign/command"),TEXT("/scout_1/execute_scout"),TEXT("/redline/campaign/command"),TEXT("/redline/science/collect_sample"),TEXT("/rover_1/contact_science"),TEXT("/redline/science/deploy_station"),TEXT("/rover_1/remote_libs"),TEXT("/rover_1/neutron_survey"),TEXT("/rover_1/drill"),TEXT("/redline/science/cache_sample"),TEXT("/redline/campaign/command"),TEXT("/redline/campaign/command")};
    TArray<TSharedPtr<FJsonValue>> Tasks,Completed;
    for(int32 I=0;I<12;++I)
    {
        const bool Robot=I>=6 && I<=8;const FString Actor=Robot ? TEXT("rover_1") : I==1 ? TEXT("scout_1") : TEXT("EV1");
        auto T=MakeShared<FJsonObject>();T->SetStringField(TEXT("id"),FString::Printf(TEXT("task-%d"),I));T->SetStringField(TEXT("kind"),Kinds[I]);T->SetStringField(TEXT("title"),FString::Printf(TEXT("%02d / İşlem"),I+1));T->SetStringField(TEXT("actor"),Actor);T->SetNumberField(TEXT("radius_m"),4);
        const bool Field=I>=3 && I<=8;const double X=Field ? 570 : 285.1,Y=Field ? -454 : I==9 ? -468 : -456;
        TArray<TSharedPtr<FJsonValue>> XY={MakeShared<FJsonValueNumber>(X),MakeShared<FJsonValueNumber>(Y)};T->SetArrayField(TEXT("xy"),XY);
        auto P=MakeShared<FJsonObject>();P->SetStringField(TEXT("state"),I<Active ? TEXT("complete") : I==Active ? TEXT("active") : TEXT("locked"));P->SetArrayField(TEXT("site_xy_m"),XY);P->SetStringField(TEXT("actor"),Actor);P->SetStringField(TEXT("endpoint"),Endpoints[I]);P->SetStringField(TEXT("command_endpoint"),TEXT("/redline/campaign/command"));P->SetStringField(TEXT("interaction_mode"),Robot ? TEXT("remote") : TEXT("local"));P->SetBoolField(TEXT("requires_proximity"),!Robot);P->SetBoolField(TEXT("enabled"),I==Active);T->SetObjectField(TEXT("presentation"),P);
        Tasks.Add(MakeShared<FJsonValueObject>(T));if(I<Active)Completed.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("task-%d"),I)));
    }
    J->SetArrayField(TEXT("tasks"),Tasks);J->SetArrayField(TEXT("completed"),Completed);J->SetObjectField(TEXT("task"),Tasks[FMath::Min(Active,11)]->AsObject());return J;
}
TSharedPtr<FJsonObject> Task(const TSharedPtr<FJsonObject>& J,int32 I){return J->GetArrayField(TEXT("tasks"))[I]->AsObject();}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineMissionSitesPacketTest,"Redline.MissionSites.SequentialPacketsAndFrames",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineMissionSitesPacketTest::RunTest(const FString&)
{
    using namespace MissionSitesTests;FRedlineMissionSitesState State;
    TestTrue(TEXT("bounded real chain contract accepted"),ARedlineMissionSites::ParseSnapshot(Packet(),State));
    TestEqual(TEXT("one active task"),State.ActiveIndex,0);TestEqual(TEXT("future sites locked"),State.Sites[3].State,FString(TEXT("locked")));
    TestTrue(TEXT("successful prior tasks reveal remote work"),ARedlineMissionSites::ParseSnapshot(Packet(6),State));
    TestTrue(TEXT("remote task stays at actual registered field point"),State.Sites[6].bRemote && State.Sites[6].Map.Equals(FVector(570,-454,0)));
    auto J=Packet();Task(J,3)->GetObjectField(TEXT("presentation"))->SetStringField(TEXT("state"),TEXT("active"));TestFalse(TEXT("future task cannot become active out of sequence"),ARedlineMissionSites::ParseSnapshot(J,State));
    J=Packet();J->SetStringField(TEXT("frame"),TEXT("odom"));TestFalse(TEXT("wrong parent frame rejected"),ARedlineMissionSites::ParseSnapshot(J,State));
    J=Packet();Task(J,0)->SetStringField(TEXT("frame"),TEXT("EPSG:4326"));TestFalse(TEXT("planetary degrees cannot enter metre marker"),ARedlineMissionSites::ParseSnapshot(J,State));
    J=Packet();Task(J,0)->GetObjectField(TEXT("presentation"))->SetArrayField(TEXT("site_xy_m"),{MakeShared<FJsonValueNumber>(999),MakeShared<FJsonValueNumber>(0)});TestFalse(TEXT("presentation cannot move authoritative XY"),ARedlineMissionSites::ParseSnapshot(J,State));
    J=Packet();Task(J,0)->SetArrayField(TEXT("xy"),{MakeShared<FJsonValueNumber>(NAN),MakeShared<FJsonValueNumber>(0)});TestFalse(TEXT("nonfinite coordinate rejected"),ARedlineMissionSites::ParseSnapshot(J,State));
    J=Packet();J->SetNumberField(TEXT("task_count"),33);TestFalse(TEXT("pool capacity enforced"),ARedlineMissionSites::ParseSnapshot(J,State));
    J=Packet(2);J->SetArrayField(TEXT("completed"),{});TestFalse(TEXT("unrecorded prerequisites do not unlock sites"),ARedlineMissionSites::ParseSnapshot(J,State));
    J=Packet(6);Task(J,6)->GetObjectField(TEXT("presentation"))->SetStringField(TEXT("endpoint"),TEXT("/robot/unsafe_override"));TestFalse(TEXT("unexpected endpoint rejected even by passive view"),ARedlineMissionSites::ParseSnapshot(J,State));
    TestTrue(TEXT("completed chain accepted"),ARedlineMissionSites::ParseSnapshot(Packet(12),State));TestTrue(TEXT("no active site after final result"),State.bDone && State.ActiveIndex==INDEX_NONE);
    TestEqual(TEXT("ENU metres flip Y into UE cm"),ARedlineMissionSites::SiteWorldPosition(FVector(3,-4,-3500),110),FVector(300,400,-349890));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineMissionSitesAuthorityTest,"Redline.MissionSites.PassiveDeduplicationAndFreshness",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineMissionSitesAuthorityTest::RunTest(const FString&)
{
    using namespace MissionSitesTests;TGuardValue<bool> NoConnection(GetMutableDefault<URedlineSettings>()->bAutoConnect,false);FTestWorldWrapper Fixture;
    if(!Fixture.CreateTestWorld(EWorldType::Game)){Fixture.ForwardErrorMessages(this);return false;}
    auto* Actor=Fixture.GetTestWorld()->SpawnActor<ARedlineMissionSites>();if(!Actor)return false;
    const FTransform Before=Actor->GetActorTransform();TestTrue(TEXT("initial snapshot accepted"),Actor->AcceptSnapshot(Packet(3),100));
    TestEqual(TEXT("12 steps share only three physical sites"),Actor->VisualTasks.Num(),3);
    int32 ActiveMarkers=0;for(int32 Index:Actor->VisualTasks)if(Index==Actor->State.ActiveIndex)++ActiveMarkers;
    TestEqual(TEXT("active site takes precedence over locked steps at same rock"),ActiveMarkers,1);
    TestTrue(TEXT("fresh receipt with connection is visible"),Actor->FreshAt(101,true));TestFalse(TEXT("old receipt cannot remain live"),Actor->FreshAt(103,true));TestFalse(TEXT("disconnected receipt hidden"),Actor->FreshAt(101,false));
    const int32 Initial=Actor->State.ActiveIndex;
    for(int32 I=0;I<20;++I)Actor->UpdateVisuals(100+I*.1);
    TestEqual(TEXT("rendering/arrival never advances a task"),Actor->State.ActiveIndex,Initial);TestTrue(TEXT("rendering does not move physics or actor root"),Actor->GetActorTransform().Equals(Before));
    TestFalse(TEXT("old revision cannot rewind active site"),Actor->AcceptSnapshot(Packet(2),101));TestEqual(TEXT("rejected packet preserves received state"),Actor->State.ActiveIndex,3);
    TestFalse(TEXT("invalid timestamp cannot refresh state"),Actor->AcceptSnapshot(Packet(4),NAN));TestEqual(TEXT("receipt preserved"),Actor->Receipt,100.);
    FVector Ground;TestFalse(TEXT("missing connection/terrain cannot invent a site height"),Actor->GetActiveSiteMap(Ground));TestEqual(TEXT("unknown distance stays unknown"),Actor->DistanceMetres(),-1.);
    Fixture.ForwardErrorMessages(this);return true;
}
#endif
