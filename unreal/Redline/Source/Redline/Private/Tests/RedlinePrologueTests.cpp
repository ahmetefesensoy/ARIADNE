#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Tests/AutomationCommon.h"
#include "RedlinePrologueDirector.h"
#include "RedlineAstronautCharacter.h"
#include "RedlineSettings.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlinePrologueSkip,"Redline.Prologue.SkipRestoresControl",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlinePrologueSkip::RunTest(const FString& Parameters)
{
    TGuardValue<bool> NoConnection(GetMutableDefault<URedlineSettings>()->bAutoConnect,false);
    FTestWorldWrapper Fixture;
    if(!Fixture.CreateTestWorld(EWorldType::Game) || !Fixture.BeginPlayInTestWorld()){Fixture.ForwardErrorMessages(this);return false;}
    UWorld* World=Fixture.GetTestWorld();
    auto* Pawn=World->SpawnActor<ARedlineAstronautCharacter>();auto* PC=World->SpawnActor<APlayerController>();
    auto* Director=World->SpawnActor<ARedlinePrologueDirector>();
    if(!Pawn || !PC || !Director)return false;
    PC->Possess(Pawn);Director->Astronaut=Pawn;Director->Player=PC;
    Pawn->SetActorLocation(FVector(300,200,150));Pawn->MissionPhase=0;
    const FTransform Before=Pawn->GetActorTransform();const int32 Published=Pawn->PublishedPoses;
    Pawn->bPresentationLocked=true;Pawn->SetActorHiddenInGame(true);Director->bPlaying=true;
    Director->NarrativeBody->SetHiddenInGame(false);PC->SetViewTarget(Director);
    auto* Lander=World->SpawnActor<AStaticMeshActor>();auto* Target=World->SpawnActor<AStaticMeshActor>();
    Lander->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
    Target->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
    Target->SetActorLocation(FVector(500,300,20));Lander->SetActorLocation(FVector(500,300,2000));
    Director->Lander=Lander;Director->LandingTarget=Target;
    TestFalse(TEXT("incomplete scene cannot acquire optional rest"),Director->CanRest());
    Director->SkipAll();
    TestFalse(TEXT("skip releases presentation lock"),Pawn->bPresentationLocked);
    TestFalse(TEXT("skip restores actual pawn visibility"),Pawn->IsHidden());
    TestFalse(TEXT("skip hides duplicate narrative body"),Director->NarrativeBody->IsVisible());
    TestTrue(TEXT("skip restores original view target"),PC->GetViewTarget()==Pawn);
    TestFalse(TEXT("all sequence/rest states end"),Director->IsCinematic());
    TestTrue(TEXT("landing visual finishes at the surface"),Lander->GetActorLocation().Equals(Target->GetActorLocation()));
    for(auto* Audio:{Director->Narrator.Get(),Director->Jazz.Get(),Director->Foley.Get()})TestFalse(TEXT("skip stops presentation audio"),Audio->IsPlaying());
    Director->SkipAll();Director->SkipCurrent();
    TestTrue(TEXT("repeated skips leave physical human transform untouched"),Pawn->GetActorTransform().Equals(Before));
    TestEqual(TEXT("no synthetic pose published by skipping"),Pawn->PublishedPoses,Published);
    TestEqual(TEXT("no mission phase advanced by skipping"),Pawn->MissionPhase,0);
    Director->bPlaying=true;Director->bPhaseClip=true;Pawn->bPresentationLocked=true;
    Director->SkipCurrent();
    TestFalse(TEXT("skipping a mission intro finishes just that clip"),Director->IsCinematic());
    TestFalse(TEXT("mission intro skip releases movement"),Pawn->bPresentationLocked);
    TestEqual(TEXT("mission intro skip sends no phase advance"),Pawn->MissionPhase,0);
    Fixture.ForwardErrorMessages(this);return true;
}
#endif
