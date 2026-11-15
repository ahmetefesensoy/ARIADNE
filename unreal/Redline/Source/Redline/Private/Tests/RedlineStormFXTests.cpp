#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "RedlineStormFX.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineStormFXTest,"Redline.MarsLook.StormFX",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineStormFXTest::RunTest(const FString& Parameters)
{
    // Storm level follows the alert: up over ~6 s, down over ~12 s, always 0..1.
    TestTrue(TEXT("an alert raises the storm gradually"),FMath::IsNearlyEqual(ARedlineStormFX::ApproachStorm(0.f,1.f,3.f),.5f,.01f));
    TestEqual(TEXT("the storm reaches full after 6 s"),ARedlineStormFX::ApproachStorm(0.f,1.f,6.f),1.f);
    TestTrue(TEXT("it settles slower than it rises"),FMath::IsNearlyEqual(ARedlineStormFX::ApproachStorm(1.f,0.f,6.f),.5f,.01f));
    TestEqual(TEXT("non-finite input keeps a valid level"),ARedlineStormFX::ApproachStorm(NAN,1.f,1.f),1.f/6.f);
    // Camera speckles: none without a storm, more with a higher replayed dose ratio, bounded.
    TestEqual(TEXT("no storm, no speckles"),ARedlineStormFX::SpeckleCount(0.f,60.),0);
    TestTrue(TEXT("a higher dose ratio gives more speckles"),ARedlineStormFX::SpeckleCount(1.f,60.)>ARedlineStormFX::SpeckleCount(1.f,1.8));
    TestTrue(TEXT("speckles stay bounded"),ARedlineStormFX::SpeckleCount(1.f,1e9)<=90);
    TestEqual(TEXT("non-finite dose gives none"),ARedlineStormFX::SpeckleCount(1.f,NAN),0);
    // Sand streaks: a calm baseline and the full pool in a storm.
    TestEqual(TEXT("calm baseline"),ARedlineStormFX::ActiveStreaks(0.f),70);
    TestEqual(TEXT("full storm uses the pool"),ARedlineStormFX::ActiveStreaks(1.f),ARedlineStormFX::MaxStreaks);
    return true;
}
#endif
