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
TSharedPtr<FJsonObject> CampaignPacket()
{
    return FRedlineJson::Parse(TEXT(R"({"schema":"redline.campaign.v1","revision":0,"progress":0,"task_count":1,"task_index":0,"pet_s":0,"run_id":"campaign-test","message":"","operation_phase":"","operation_id":"","state":"ready","evidence_ids":[],"products":[],"samples":[],"task":{"id":"collect","title":"Collect","instruction":"Pick sample","kind":"collect","actor":"EV1","target_id":"BXW_RIDGE_A","xy":[306,-454],"phase":2},"tasks":[{"id":"collect","title":"Collect","instruction":"Pick sample","kind":"collect","actor":"EV1","target_id":"BXW_RIDGE_A","xy":[306,-454],"phase":2}]})"));
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineCampaignSnapshotTest,"Redline.Campaign.BoundedSnapshot",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineCampaignSnapshotTest::RunTest(const FString& Parameters)
{
    auto J=CampaignPacket();TestTrue(TEXT("valid campaign packet"),ARedlineCampaignConsole::ValidateSnapshot(J));
    J->SetArrayField(TEXT("products"),{MakeShared<FJsonValueNull>()});TestFalse(TEXT("null product cannot crash chart"),ARedlineCampaignConsole::ValidateSnapshot(J));
    J=CampaignPacket();J->SetNumberField(TEXT("progress"),1.1);TestFalse(TEXT("bounded progress"),ARedlineCampaignConsole::ValidateSnapshot(J));
    J=CampaignPacket();J->SetStringField(TEXT("state"),TEXT("running"));TestFalse(TEXT("running operation needs request id"),ARedlineCampaignConsole::ValidateSnapshot(J));
    J=CampaignPacket();J->SetNumberField(TEXT("task_index"),2);TestFalse(TEXT("invalid index rejected"),ARedlineCampaignConsole::ValidateSnapshot(J));
    J=CampaignPacket();J->SetArrayField(TEXT("route_xy_m"),{MakeShared<FJsonValueNull>()});TestFalse(TEXT("bad waypoint cannot crash the navigation pin"),ARedlineCampaignConsole::ValidateSnapshot(J));
    J=CampaignPacket();auto P=FRedlineJson::Parse(TEXT(R"({"product_id":"sim-product","instrument":"LIBS","target_id":"BXW_RIDGE_A","summary":{"values":[40,20],"sigma":[1],"labels":["SiO2","FeO"],"unit":"mass_percent_SCENARIO"}})"));
    J->SetArrayField(TEXT("products"),{MakeShared<FJsonValueObject>(P)});TestFalse(TEXT("error bars must match observations"),ARedlineCampaignConsole::ValidateSnapshot(J));
    P->GetObjectField(TEXT("summary"))->SetArrayField(TEXT("sigma"),{MakeShared<FJsonValueNumber>(1.),MakeShared<FJsonValueNumber>(2.)});
    TestTrue(TEXT("matched observations and errors accepted"),ARedlineCampaignConsole::ValidateSnapshot(J));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineCampaignChartTest,"Redline.Campaign.RADRingAndDetector",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineCampaignChartTest::RunTest(const FString& Parameters)
{
    TGuardValue<bool> NoConnection(GetMutableDefault<URedlineSettings>()->bAutoConnect,false);FTestWorldWrapper Fixture;
    if(!Fixture.CreateTestWorld(EWorldType::Game)){Fixture.ForwardErrorMessages(this);return false;}
    auto* Screen=Fixture.GetTestWorld()->SpawnActor<ARedlineCampaignConsole>();
    auto J=FRedlineJson::Parse(TEXT(R"({"header":{"frame_id":"map","stamp":{"sec":1,"nanosec":0}},"dose_rate_b_ugy_h":2.5,"background_b_ugy_h":1,"dose_rate_e_ugy_h":8.3,"background_e_ugy_h":6,"source_sol":4190,"source_file":"test.tab","alert":true,"alert_detector":"E"})"));
    Screen->CaptureRad(J);TestEqual(TEXT("selected detector E used"),Screen->RadAt(0).Rate,8.3);TestEqual(TEXT("selected E background"),Screen->RadAt(0).Background,6.);
    for(int32 I=1;I<400;++I){J->SetNumberField(TEXT("dose_rate_e_ugy_h"),I);Screen->CaptureRad(J);}
    TestEqual(TEXT("bounded ring"),Screen->RadHistory.Num(),360);TestEqual(TEXT("newest item preserved"),Screen->RadAt(359).Rate,399.);
    J->SetStringField(TEXT("alert_detector"),TEXT("B"));Screen->CaptureRad(J);TestEqual(TEXT("detector switch starts separate series"),Screen->RadHistory.Num(),1);TestEqual(TEXT("B never reuses E axis values"),Screen->RadAt(0).Rate,2.5);
    J->SetNumberField(TEXT("dose_rate_b_ugy_h"),-1);Screen->CaptureRad(J);TestEqual(TEXT("invalid value cannot overwrite last accepted"),Screen->RadAt(0).Rate,2.5);
    Fixture.ForwardErrorMessages(this);return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineCampaignCommandFeedbackTest,"Redline.Campaign.CommandFeedbackIsVisible",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineCampaignCommandFeedbackTest::RunTest(const FString& Parameters)
{
    // Playtest 2026-11-15: E at a task "did nothing". Every refused or lost command must leave a visible,
    // recent message for the HUD instead of returning silently.
    TGuardValue<bool> NoConnection(GetMutableDefault<URedlineSettings>()->bAutoConnect,false);FTestWorldWrapper Fixture;
    if(!Fixture.CreateTestWorld(EWorldType::Game)){Fixture.ForwardErrorMessages(this);return false;}
    auto* Screen=Fixture.GetTestWorld()->SpawnActor<ARedlineCampaignConsole>();
    Screen->SendCommand(TEXT("START"));
    TestFalse(TEXT("offline START leaves a message"),Screen->Message().IsEmpty());
    TestTrue(TEXT("the message is recent"),Screen->MessageAgeSec()<1.);
    Screen->bPendingCommand=true;Screen->LastCommand=FPlatformTime::Seconds()-6.;Screen->LastCommandMessage.Empty();
    Screen->ExpirePendingCommand(FPlatformTime::Seconds());
    TestFalse(TEXT("a command without an answer for 5 s unlocks"),Screen->bPendingCommand);
    TestFalse(TEXT("and says so"),Screen->Message().IsEmpty());
    Fixture.ForwardErrorMessages(this);return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineCampaignScoutMapTest,"Redline.Tablet.ScoutSnapshotReplay",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineCampaignScoutMapTest::RunTest(const FString&)
{
    TGuardValue<bool> NoConnection(GetMutableDefault<URedlineSettings>()->bAutoConnect,false);FTestWorldWrapper Fixture;
    if(!Fixture.CreateTestWorld(EWorldType::Game)){Fixture.ForwardErrorMessages(this);return false;}
    auto* Screen=Fixture.GetTestWorld()->SpawnActor<ARedlineCampaignConsole>();
    auto Observation=FRedlineJson::Parse(TEXT(R"({"header":{"frame_id":"map"},"source":"scout_1_truth_adapter","evidence_id":"actual-evidence-1","pose":{"pose":{"position":{"x":538,"y":-174,"z":-3599}}},"provenance":{"status":2},"summary_json":"{\"passability\":0}"})"));
    auto Packet=CampaignPacket();Packet->SetArrayField(TEXT("scout_observations"),{MakeShared<FJsonValueObject>(Observation)});
    auto Message=MakeShared<FJsonObject>();Message->SetStringField(TEXT("data"),FRedlineJson::Write(Packet.ToSharedRef()));
    Screen->Receive(TEXT("/redline/campaign/state"),Message);
    TestEqual(TEXT("late subscriber gets actual retained observation"),Screen->ScoutObservations.Num(),1);
    Screen->Receive(TEXT("/redline/campaign/state"),Message);TestEqual(TEXT("snapshot does not duplicate evidence"),Screen->ScoutObservations.Num(),1);
    TestEqual(TEXT("blocked observation preserved"),Screen->ScoutObservations[0].Passability,0);
    Observation->GetObjectField(TEXT("header"))->SetStringField(TEXT("frame_id"),TEXT("odom"));Observation->SetStringField(TEXT("evidence_id"),TEXT("wrong-frame"));Screen->CaptureScoutEvidence(Observation,1.);
    TestEqual(TEXT("wrong-frame evidence cannot pollute atlas"),Screen->ScoutObservations.Num(),1);
    TArray<TSharedPtr<FJsonValue>> TooMany;for(int32 I=0;I<129;++I)TooMany.Add(MakeShared<FJsonValueObject>(Observation));Packet->SetArrayField(TEXT("scout_observations"),TooMany);
    TestFalse(TEXT("unbounded history rejected"),Screen->ValidateSnapshot(Packet));
    Fixture.ForwardErrorMessages(this);return true;
}
#endif
