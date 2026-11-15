#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Tests/AutomationCommon.h"
#include "RedlineSampleInteraction.h"
#include "RedlineAstronautCharacter.h"
#include "RedlineSettings.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineSamplePresentation,"Redline.EVA.SampleFeedbackPresentation",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineSamplePresentation::RunTest(const FString& Parameters)
{
    TGuardValue<bool> NoConnection(GetMutableDefault<URedlineSettings>()->bAutoConnect,false);
    FTestWorldWrapper Fixture;
    // Pre-BeginPlay world isolates pose geometry from ROS/profile setup. The
    // real character and poseable component are registered native objects.
    if(!Fixture.CreateTestWorld(EWorldType::Game)){Fixture.ForwardErrorMessages(this);return false;}
    auto* World=Fixture.GetTestWorld();auto* Human=World->SpawnActor<ARedlineAstronautCharacter>();auto* Performance=World->SpawnActor<ARedlineSampleInteraction>();
    auto* Asset=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/EVAFixtures/Astronaut/SK_Astronaut.SK_Astronaut"));
    if(!TestNotNull(TEXT("actual imported astronaut"),Asset) || !Human || !Performance)return false;
    Human->GetMesh()->SetSkeletalMeshAsset(Asset);Human->GetMesh()->RefreshBoneTransforms();
    Human->SetActorLocation(FVector(1000,2000,500));Human->MissionPhase=3;Human->PublishedPoses=17;
    Human->GetMesh()->SetHiddenInGame(false);Human->GetMesh()->SetVisibility(true);Human->GetMesh()->SetOwnerNoSee(true);
    const FTransform Original=Human->GetActorTransform();const auto OriginalSourcePose=Human->GetMesh()->GetBoneSpaceTransforms();
    Performance->bUseInspectionCamera=false;
    TestTrue(TEXT("presentation accepts real rig"),Performance->BeginInteraction(Human,FVector(11,-20,4),TEXT("COLLECT")));
    TestTrue(TEXT("movement lock belongs only to presentation"),Human->bPresentationLocked);
    TestTrue(TEXT("original mesh hidden during duplicate performance"),Human->GetMesh()->bHiddenInGame);
    const FVector StandingHand=Performance->PerformanceBody->GetBoneLocationByName(TEXT("hand_r"),EBoneSpaces::ComponentSpace);
    const FVector StandingFoot=Performance->PerformanceBody->GetBoneLocationByName(TEXT("foot_l"),EBoneSpaces::ComponentSpace);
    Performance->SetProgress(.45f,TEXT("COLLECTING"));
    const FVector CrouchedHand=Performance->PerformanceBody->GetBoneLocationByName(TEXT("hand_r"),EBoneSpaces::ComponentSpace);
    const FVector CrouchedFoot=Performance->PerformanceBody->GetBoneLocationByName(TEXT("foot_l"),EBoneSpaces::ComponentSpace);
    TestTrue(TEXT("native hand bones actually move in the poseable body"),FVector::Distance(StandingHand,CrouchedHand)>10);
    TestTrue(TEXT("crouch retains foot planting"),FVector::Distance(StandingFoot,CrouchedFoot)<2);
    TestTrue(TEXT("hand and foot transforms are finite"),!CrouchedHand.ContainsNaN() && !CrouchedFoot.ContainsNaN());
    Performance->SetProgress(.75f,TEXT("SEALING"));TestTrue(TEXT("sample tube transfers visually during feedback"),Performance->WasSampleTransferredVisually());
    const FVector HandWorld=Performance->PerformanceBody->GetBoneLocationByName(TEXT("hand_r"),EBoneSpaces::WorldSpace);
    TestTrue(TEXT("tube stays within centimetres of the hand despite imported bind scale"),FVector::Distance(HandWorld,Performance->SampleVisual->GetComponentLocation())<15);
    Performance->SetProgress(.2f,TEXT("OLD_FEEDBACK"));TestTrue(TEXT("late feedback cannot rewind performance"),FMath::IsNearlyEqual(Performance->GetProgress(),.75f));
    Performance->SetProgress(1.f,TEXT("WAITING_FOR_RESULT"));
    TestTrue(TEXT("feedback 100 percent does not synthesize action completion"),Performance->IsInteracting() && Human->bPresentationLocked);
    Performance->Tick(30.f);TestTrue(TEXT("wall-time ticking cannot complete the action"),Performance->IsInteracting());
    TestTrue(TEXT("actual capsule transform never changes"),Human->GetActorTransform().Equals(Original));
    TestEqual(TEXT("no synthetic crew pose is emitted by animation"),Human->PublishedPoses,17);
    TestEqual(TEXT("no mission transition is emitted by animation"),Human->MissionPhase,3);
    const auto& SourceAfter=Human->GetMesh()->GetBoneSpaceTransforms();bool SourceUnchanged=SourceAfter.Num()==OriginalSourcePose.Num();
    for(int32 I=0;SourceUnchanged && I<SourceAfter.Num();++I)SourceUnchanged=SourceAfter[I].Equals(OriginalSourcePose[I],1e-6);
    TestTrue(TEXT("source rig pose unchanged"),SourceUnchanged);
    Performance->EndInteraction(true);
    TestFalse(TEXT("explicit result ends presentation"),Performance->IsInteracting());
    TestFalse(TEXT("movement restored"),Human->bPresentationLocked);
    TestTrue(TEXT("original mesh visibility/owner-no-see preserved"),!Human->GetMesh()->bHiddenInGame && Human->GetMesh()->IsVisible() && Human->GetMesh()->bOwnerNoSee);
    TestTrue(TEXT("first-person selection remains intact"),Human->bFirstPersonView);
    TestTrue(TEXT("presentation tube hidden after result"),Performance->SampleVisual->bHiddenInGame);
    TestTrue(TEXT("second interaction can begin"),Performance->BeginInteraction(Human,FVector(11,-20,4),TEXT("COLLECT")));
    Performance->EndInteraction(false);Performance->EndInteraction(false);
    TestFalse(TEXT("cancel/repeated end does not retain control lock"),Human->bPresentationLocked);
    Performance->bUseActualWorkPoint=true;
    TestTrue(TEXT("laboratory accepts a tabletop work point"),Performance->BeginInteraction(Human,FVector(10.5,-20,5),TEXT("lab")));
    const FVector BenchRoot=Performance->PerformanceBody->BoneSpaceTransforms[0].GetTranslation();
    Performance->SetProgress(.45f,TEXT("SAMPLE_PREPARATION"));
    TestTrue(TEXT("bench work stays standing instead of ground crouching"),Performance->PerformanceBody->BoneSpaceTransforms[0].GetTranslation().Equals(BenchRoot,.01));
    TestFalse(TEXT("bench work hides outdoor scoop"),Performance->HandTool->IsVisible() && !Performance->HandTool->bHiddenInGame);
    TestTrue(TEXT("laboratory hands remain finite"),!Performance->PerformanceBody->GetBoneLocationByName(TEXT("hand_r"),EBoneSpaces::WorldSpace).ContainsNaN());
    TestTrue(TEXT("lab animation does not move real human"),Human->GetActorTransform().Equals(Original));
    Performance->EndInteraction(false);TestFalse(TEXT("bench cancel restores control"),Human->bPresentationLocked);
    for(auto* Visual:{Performance->SampleVisual.Get(),Performance->HandTool.Get(),Performance->ToolHead.Get()})
    {TestFalse(TEXT("props never simulate physics"),Visual->IsSimulatingPhysics());TestTrue(TEXT("props do not enter robot or human collision"),Visual->GetCollisionEnabled()==ECollisionEnabled::NoCollision);}
    Fixture.ForwardErrorMessages(this);return true;
}
#endif
