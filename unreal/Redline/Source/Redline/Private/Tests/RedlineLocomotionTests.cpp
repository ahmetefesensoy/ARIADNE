#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "RedlineAstronautCharacter.h"
#include "Tests/AutomationCommon.h"
#include "Components/SkeletalMeshComponent.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Engine/World.h"
#include "RedlineSettings.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineSprint,"Redline.EVA.SprintBounds",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineSprint::RunTest(const FString& Parameters)
{
    auto Speed=[](double Walk,bool Run){return ARedlineAstronautCharacter::RequestedSpeed(Walk,Run,3.6,3.);};
    TestEqual(TEXT("walking remains the core table value"),Speed(.6,false),.6);
    TestTrue(TEXT("Shift accelerates a traversable flat cell"),FMath::IsNearlyEqual(Speed(.6,true),2.16));
    TestEqual(TEXT("sprint cannot bypass a forbidden cell"),Speed(0,true),0.);
    TestEqual(TEXT("sprint speed is bounded"),Speed(1.2,true),3.);
    TestTrue(TEXT("slower terrain remains slower when sprinting"),Speed(.25,true)<Speed(.6,true));
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineViewModes,"Redline.EVA.FirstAndThirdPerson",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineViewModes::RunTest(const FString& Parameters)
{
    TGuardValue<bool> Offline(GetMutableDefault<URedlineSettings>()->bAutoConnect,false);
    FTestWorldWrapper World;if(!World.CreateTestWorld(EWorldType::Game))return false;
    auto* Pawn=World.GetTestWorld()->SpawnActor<ARedlineAstronautCharacter>();if(!Pawn)return false;
    Pawn->SetFirstPersonView(true);
    TestTrue(TEXT("first-person camera active"),Pawn->FirstPersonCamera->IsActive());
    TestFalse(TEXT("third-person camera inactive"),Pawn->FollowCamera->IsActive());
    TestTrue(TEXT("helmet cannot obscure first-person camera"),Pawn->GetMesh()->bOwnerNoSee);
    Pawn->SetFirstPersonView(false);
    TestTrue(TEXT("third-person camera restored"),Pawn->FollowCamera->IsActive());
    TestFalse(TEXT("body restored in third person"),Pawn->GetMesh()->bOwnerNoSee);
    TestTrue(TEXT("camera boom uses collision"),Pawn->CameraArm->bDoCollisionTest);
    TestTrue(TEXT("indoor camera boom is at most 2.2 m"),Pawn->CameraArm->TargetArmLength<=220);
    return true;
}
#endif
