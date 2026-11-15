#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "RedlineLocomotionInstance.h"
#include "Animation/AnimSequence.h"
#include "Engine/SkeletalMesh.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Tests/AutomationCommon.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineGaitTransitionTest,"Redline.EVA.GaitTransitionAndCadence",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineGaitTransitionTest::RunTest(const FString& Parameters)
{
    FRedlineLocomotionState State;
    State.Advance(65.f,1.f/60.f,8,8);
    TestTrue(TEXT("movement blends in rather than replacing the whole pose"),State.WalkWeight>0 && State.WalkWeight<.3f);
    for(int32 I=0;I<120;++I)State.Advance(65.f,1.f/60.f,8,8);
    TestTrue(TEXT("steady walk reaches its authored cadence"),FMath::IsNearlyEqual(State.Cadence,1.f,.001f));
    const double Cycle=State.WalkTime;
    State.Advance(0.f,1.f/60.f,8,8);
    TestTrue(TEXT("stopping blends out without snapping to idle"),State.WalkWeight>.5f && State.WalkWeight<1.f);
    TestTrue(TEXT("stop does not reset the walk cycle"),State.WalkTime>=Cycle);
    for(int32 I=0;I<120;++I)State.Advance(0.f,1.f/60.f,8,8);
    TestTrue(TEXT("stopped cadence settles to zero instead of pedalling at a minimum rate"),State.Cadence<.001f && State.WalkWeight<.001f);
    const double Resume=State.WalkTime;
    State.Advance(130.f,1.f/60.f,8,8);
    TestTrue(TEXT("restart resumes the previous cycle"),State.WalkTime>=Resume);
    for(int32 I=0;I<120;++I)State.Advance(130.f,1.f/60.f,8,8);
    TestTrue(TEXT("twice measured speed produces twice visual cadence"),FMath::IsNearlyEqual(State.Cadence,2.f,.001f));
    FRedlineLocomotionState SlowFrame,FastFrame;
    for(int32 I=0;I<30;++I)SlowFrame.Advance(65.f,1.f/30.f,8,8);
    for(int32 I=0;I<120;++I)FastFrame.Advance(65.f,1.f/120.f,8,8);
    TestTrue(TEXT("blend envelope is independent of render rate"),FMath::IsNearlyEqual(SlowFrame.WalkWeight,FastFrame.WalkWeight,.0001f));
    const double Before=State.WalkTime;
    State.Advance(65.f,std::numeric_limits<float>::quiet_NaN(),8,8);
    TestEqual(TEXT("invalid frame delta cannot corrupt cycle time"),State.WalkTime,Before);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineGaitPoseTest,"Redline.EVA.GaitUsesApprovedAssetsWithoutMovingActor",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineGaitPoseTest::RunTest(const FString& Parameters)
{
    auto* Asset=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/EVAFixtures/Astronaut/SK_Astronaut.SK_Astronaut"));
    auto* Idle=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/EVAFixtures/Astronaut/AN_Idle.AN_Idle"));
    auto* Walk=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/EVAFixtures/Astronaut/AN_Walk.AN_Walk"));
    if(!Asset || !Idle || !Walk){AddError(TEXT("Approved astronaut assets unavailable"));return false;}
    FTestWorldWrapper World;
    if(!World.CreateTestWorld(EWorldType::Game)){World.ForwardErrorMessages(this);return false;}
    auto* Actor=World.GetTestWorld()->SpawnActor<AActor>();
    auto* Mesh=NewObject<USkeletalMeshComponent>(Actor);Actor->AddInstanceComponent(Mesh);Actor->SetRootComponent(Mesh);
    Mesh->SetSkeletalMeshAsset(Asset);Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Mesh->RegisterComponent();Mesh->SetAnimInstanceClass(URedlineLocomotionInstance::StaticClass());
    auto* Anim=Cast<URedlineLocomotionInstance>(Mesh->GetAnimInstance());
    if(!TestNotNull(TEXT("native runtime locomotion instance"),Anim))return false;
    if(!TestTrue(TEXT("matching non-additive clips accepted"),Anim->Configure(Idle,Walk)))return false;
    TestEqual(TEXT("gait has no root-motion authority"),Anim->RootMotionMode.GetValue(),ERootMotionMode::NoRootMotionExtraction);
    const FTransform Start=Actor->GetActorTransform();
    auto Tick=[&](float Speed){Anim->SetMeasuredSpeed(Speed);Mesh->TickAnimation(1.f/60.f,false);Mesh->RefreshBoneTransforms();};
    Tick(0);const FVector IdleFoot=Mesh->GetBoneLocation(TEXT("foot_l"),EBoneSpaces::ComponentSpace);
    Tick(65);
    TestTrue(TEXT("actual proxy uses a partial weight on first moving frame"),Anim->GetWalkWeight()>0 && Anim->GetWalkWeight()<.3f);
    const FVector FirstFoot=Mesh->GetBoneLocation(TEXT("foot_l"),EBoneSpaces::ComponentSpace);
    TestTrue(TEXT("first-frame foot shift remains under 5 cm"),FVector::Distance(FirstFoot,IdleFoot)<5.);
    for(int32 I=0;I<60;++I)Tick(65);
    TestTrue(TEXT("actual evaluated clip progresses"),Anim->GetWalkTime()>.25);
    TestTrue(TEXT("bone pose remains finite at human scale"),!Mesh->GetBoneLocation(TEXT("head"),EBoneSpaces::ComponentSpace).ContainsNaN() &&
        FVector::Distance(Mesh->GetBoneLocation(TEXT("head"),EBoneSpaces::ComponentSpace),Mesh->GetBoneLocation(TEXT("foot_l"),EBoneSpaces::ComponentSpace))>100);
    TestTrue(TEXT("animation never moves authoritative actor transform"),Actor->GetActorTransform().Equals(Start));
    World.ForwardErrorMessages(this);return true;
}
#endif
