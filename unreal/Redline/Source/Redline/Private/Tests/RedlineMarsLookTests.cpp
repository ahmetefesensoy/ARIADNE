#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Tests/AutomationCommon.h"
#include "RedlineFootprints.h"
#include "RedlineAmbientDust.h"
#include "RedlineSettings.h"
#include "Engine/World.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineFootprintStrideTest,"Redline.MarsLook.FootprintStride",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineFootprintStrideTest::RunTest(const FString& Parameters)
{
    // One print per step: a suited walk at ~1 m/s steps ~0.7 m; faster gaits lengthen the step, bounded.
    TestEqual(TEXT("standing still leaves no prints"),ARedlineFootprints::StrideMetres(0.f),0.f);
    TestTrue(TEXT("walking step is about 0.7 m"),FMath::IsNearlyEqual(ARedlineFootprints::StrideMetres(1.f),.7f,.05f));
    TestTrue(TEXT("a faster gait lengthens the step"),ARedlineFootprints::StrideMetres(2.5f)>ARedlineFootprints::StrideMetres(1.f));
    TestTrue(TEXT("the step stays bounded"),ARedlineFootprints::StrideMetres(10.f)<=1.4f);
    TestEqual(TEXT("non-finite speed leaves no prints"),ARedlineFootprints::StrideMetres(NAN),0.f);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineFootprintPoolTest,"Redline.MarsLook.FootprintPoolAndAlternation",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineFootprintPoolTest::RunTest(const FString& Parameters)
{
    TGuardValue<bool> NoConnection(GetMutableDefault<URedlineSettings>()->bAutoConnect,false);FTestWorldWrapper Fixture;
    if(!Fixture.CreateTestWorld(EWorldType::Game)){Fixture.ForwardErrorMessages(this);return false;}
    auto* Prints=Fixture.GetTestWorld()->SpawnActor<ARedlineFootprints>();
    Prints->MaxPrints=4;
    for(int32 I=0;I<10;++I)Prints->StampForTest(FVector(I*70.,0,0),FRotator::ZeroRotator);
    TestEqual(TEXT("the decal pool is bounded"),Prints->GetPrintCount(),4);
    TestTrue(TEXT("left and right feet alternate"),Prints->LastFootWasLeft()!=Prints->PreviousFootWasLeft());
    Fixture.ForwardErrorMessages(this);return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineAmbientDustTest,"Redline.MarsLook.AmbientDustStaysNearTheViewer",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineAmbientDustTest::RunTest(const FString& Parameters)
{
    // Wisps drift with the authored wind and are recycled around the viewer; opacity stays faint.
    const FVector Viewer(1000,2000,300);
    FVector Wisp=Viewer+FVector(5000,0,0);
    TestTrue(TEXT("a wisp beyond the radius is recycled"),ARedlineAmbientDust::NeedsRecycle(Wisp,Viewer,2500.f));
    TestFalse(TEXT("a nearby wisp is kept"),ARedlineAmbientDust::NeedsRecycle(Viewer+FVector(800,0,0),Viewer,2500.f));
    TestTrue(TEXT("opacity is faint"),ARedlineAmbientDust::WispOpacity(.5f)<=.09f && ARedlineAmbientDust::WispOpacity(.5f)>0.f);
    TestEqual(TEXT("opacity fades to zero at the ends of life"),ARedlineAmbientDust::WispOpacity(0.f),0.f);
    return true;
}
#endif
