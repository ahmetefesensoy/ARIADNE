#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "RedlineFieldWork.h"

namespace FieldWorkTests
{
using B=ERedlineFieldWorkButtons;
void Hold(FRedlineFieldWork& Work,B Button,int32 Ticks)
{for(int32 I=0;I<Ticks;++I)Work.Tick(.1,Button,true);}
void Release(FRedlineFieldWork& Work){Work.Tick(.1,B::None,true);}
void Confirm(FRedlineFieldWork& Work)
{Release(Work);Work.Tick(.1,B::Interact,true,true,true);}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineFieldWorkInputTest,"Redline.FieldWork.InputFocusAndTimeGates",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineFieldWorkInputTest::RunTest(const FString&)
{
    using namespace FieldWorkTests;FRedlineFieldWork Work;
    TestFalse(TEXT("unknown work cannot begin"),Work.Begin(TEXT("drill")));TestEqual(TEXT("invalid kind leaves idle"),int32(Work.State()),int32(ERedlineFieldWorkState::Idle));
    TestTrue(TEXT("supported work begins"),Work.Begin(TEXT("collect")));
    for(int32 I=0;I<1000;++I)Work.Tick(.1,B::None,true);
    TestEqual(TEXT("elapsed time alone does not perform work"),Work.Progress(),0.);
    Hold(Work,B::Right,50);TestEqual(TEXT("wrong button cannot scoop"),Work.Progress(),0.);
    Hold(Work,B::Left|B::Right|B::Interact,50);TestEqual(TEXT("all buttons cannot skip work"),Work.Progress(),0.);
    Work.Tick(.1,uint8(128),true);TestEqual(TEXT("unknown input bits ignored"),Work.Progress(),0.);
    for(double Dt:{0.,-.1,.1001,1.,double(NAN),double(INFINITY)})Work.Tick(Dt,B::Left,true);
    TestEqual(TEXT("invalid/large deltas never catch up"),Work.Progress(),0.);
    Hold(Work,B::Left,5);const double Partial=Work.Progress();TestTrue(TEXT("correct hold adds progress"),Partial>0);
    TestFalse(TEXT("repeated Begin cannot reset active work"),Work.Begin(TEXT("cache")));TestEqual(TEXT("progress survives rejected Begin"),Work.Progress(),Partial);
    for(int32 I=0;I<50;++I){Work.Tick(.1,B::Left,false);Work.Tick(.1,B::Left,true,false);}
    TestEqual(TEXT("misalignment and missing focus pause progress"),Work.Progress(),Partial);
    TestTrue(TEXT("focus message visible"),Work.Prompt().Contains(TEXT("oyuna dön")));
    Release(Work);TestEqual(TEXT("releasing preserves partial hold"),Work.Progress(),Partial);
    Hold(Work,B::Left,10);TestEqual(TEXT("only scoop advances"),Work.StageIndex(),1);
    Work.Cancel();TestEqual(TEXT("cancelled state"),int32(Work.State()),int32(ERedlineFieldWorkState::Cancelled));
    TestFalse(TEXT("cancelled preparation cannot dispatch"),Work.ConsumePrepared());Hold(Work,B::Right,100);TestEqual(TEXT("cancelled input does not resume"),Work.Progress(),0.);
    TestTrue(TEXT("explicit new attempt can start after cancel"),Work.Begin(TEXT("cache")));TestEqual(TEXT("new attempt starts at first phase"),Work.StageIndex(),0);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineFieldWorkSequenceTest,"Redline.FieldWork.ManualSequencesAndSinglePreparation",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineFieldWorkSequenceTest::RunTest(const FString&)
{
    using namespace FieldWorkTests;
    for(const FString Kind:{FString(TEXT("collect")),FString(TEXT("xrf")),FString(TEXT("weather")),FString(TEXT("cache"))})
    {
        FRedlineFieldWork Work;TestTrue(TEXT("kind supported: ")+Kind,Work.Begin(Kind));
        Work.Tick(.1,B::Interact,true,true,true);TestEqual(TEXT("activation E cannot start a preparation stage"),Work.Progress(),0.);
        const int32 FirstTicks=Kind==TEXT("collect") ? 15 : Kind==TEXT("weather") ? 12 : 10;
        Hold(Work,B::Left,FirstTicks-1);TestEqual(TEXT("hold threshold not rounded early: ")+Kind,Work.StageIndex(),0);
        Hold(Work,B::Left,1);TestEqual(TEXT("first manual phase completed: ")+Kind,Work.StageIndex(),1);
        TestFalse(TEXT("first phase does not prepare complete operation"),Work.IsPrepared());
        if(Kind!=TEXT("xrf"))
        {
            Hold(Work,B::Left,50);TestEqual(TEXT("previous button cannot advance transfer/extension"),Work.StageIndex(),1);
            Hold(Work,B::Right,Kind==TEXT("collect") ? 12 : Kind==TEXT("weather") ? 10 : 8);
            TestEqual(TEXT("second distinct manual phase completed"),Work.StageIndex(),2);
        }
        // Even a held activation/previous E is ignored until a release at the
        // final stage. A stage transition never reuses a button or spare dt.
        for(int32 I=0;I<30;++I)Work.Tick(.1,B::Interact,true,true,true);
        TestFalse(TEXT("E must be released after final stage opens"),Work.IsPrepared());
        Release(Work);
        if(Kind==TEXT("collect"))
        {
            Hold(Work,B::Interact,7);TestFalse(TEXT("seal needs its full hold"),Work.IsPrepared());
            Hold(Work,B::Interact,1);
        }
        else
        {
            Hold(Work,B::Interact,30);TestFalse(TEXT("confirmation requires press edge, not held time"),Work.IsPrepared());
            Confirm(Work);
        }
        TestTrue(TEXT("complete manual sequence prepares exactly once: ")+Kind,Work.IsPrepared());
        TestEqual(TEXT("prepared progress bounded at one"),Work.Progress(),1.);
        TestTrue(TEXT("ROS remains separate from manual preparation"),Work.Prompt().Contains(TEXT("görev sonucu değildir")));
        TestTrue(TEXT("first dispatch consumes readiness"),Work.ConsumePrepared());
        TestFalse(TEXT("second dispatch cannot consume it again"),Work.ConsumePrepared());
        TestFalse(TEXT("repeated Begin cannot reset prepared work"),Work.Begin(Kind));
        Hold(Work,B::Left|B::Right|B::Interact,50);TestTrue(TEXT("more input keeps prepared state"),Work.IsPrepared());TestFalse(TEXT("more input cannot rearm a dispatch"),Work.ConsumePrepared());
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineFieldWorkReentryTest,"Redline.FieldWork.ConfirmFocusAndAlignmentReentry",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineFieldWorkReentryTest::RunTest(const FString&)
{
    using namespace FieldWorkTests;FRedlineFieldWork Work;Work.Begin(TEXT("xrf"));Hold(Work,B::Left,10);Release(Work);
    Work.Tick(.1,B::Interact,true,false,true);TestFalse(TEXT("unfocused confirm ignored"),Work.IsPrepared());
    Work.Tick(.1,B::Interact,true,true,true);TestFalse(TEXT("focus restoration requires release again"),Work.IsPrepared());
    Release(Work);Work.Tick(.1,B::Interact,false,true,true);TestFalse(TEXT("misaligned confirm ignored"),Work.IsPrepared());
    Work.Tick(.1,B::Interact,true,true,true);TestFalse(TEXT("alignment restoration requires release again"),Work.IsPrepared());
    Confirm(Work);TestTrue(TEXT("fresh deliberate confirmation succeeds"),Work.IsPrepared());
    Work.Cancel();TestFalse(TEXT("cancelled undispatched preparation cannot later dispatch"),Work.ConsumePrepared());
    TestTrue(TEXT("new cancelled attempt can be prepared"),Work.Begin(TEXT("xrf")));Hold(Work,B::Left,10);Confirm(Work);TestTrue(TEXT("new attempt has one readiness event"),Work.ConsumePrepared());TestFalse(TEXT("new event still one-shot"),Work.ConsumePrepared());
    return true;
}
#endif
