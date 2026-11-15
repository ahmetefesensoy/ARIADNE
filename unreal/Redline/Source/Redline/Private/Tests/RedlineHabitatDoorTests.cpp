#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Tests/AutomationCommon.h"
#include "RedlineHabitatDoor.h"
#include "RedlineSettings.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "Engine/StaticMeshActor.h"
#include "GameFramework/Character.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineDoorAnimation,"Redline.EVA.DoorUnlockSlideLatch",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineDoorAnimation::RunTest(const FString& Parameters)
{
    TGuardValue<bool> NoConnection(GetMutableDefault<URedlineSettings>()->bAutoConnect,false);
    FTestWorldWrapper Fixture;
    if(!Fixture.CreateTestWorld(EWorldType::Game) || !Fixture.BeginPlayInTestWorld()){Fixture.ForwardErrorMessages(this);return false;}
    auto* Door=Fixture.GetTestWorld()->SpawnActor<ARedlineHabitatDoor>();if(!TestNotNull(TEXT("runtime presentation door"),Door))return false;
    TestTrue(TEXT("valid real-size opening"),Door->ConfigureOpening(FTransform(FRotator(0,0,0),FVector(0,0,130)),FVector(10,210,240)));
    TestFalse(TEXT("undersize opening rejected"),Door->ConfigureOpening(FTransform::Identity,FVector(10,50,240)));
    Door->DoorAudio->SetVolumeMultiplier(0);
    Door->AdvanceAnimation(.1,true,false);Door->AdvanceAnimation(.1,true,false);
    TestTrue(TEXT("latch unlocks before slide"),Door->GetDoorState()==ERedlineHabitatDoorState::Unlocking && Door->GetUnlockProgress()>0);
    TestEqual(TEXT("panels stay sealed during unlocking"),Door->GetOpenness(),0.);
    for(int32 I=0;I<80;++I)Door->AdvanceAnimation(.025,true,false);
    TestTrue(TEXT("opening completes"),Door->GetDoorState()==ERedlineHabitatDoorState::Open && FMath::IsNearlyEqual(Door->GetOpenness(),1.));
    const FVector L=Door->LeftPanel->GetRelativeLocation(),R=Door->RightPanel->GetRelativeLocation();
    TestTrue(TEXT("two separate panels slide in opposite directions"),L.Y< -105 && R.Y>105 && FMath::IsNearlyEqual(L.Y,-R.Y));
    TestTrue(TEXT("panels do not rise or change depth"),FMath::IsNearlyZero(L.X) && FMath::IsNearlyZero(L.Z) && FMath::IsNearlyZero(R.X) && FMath::IsNearlyZero(R.Z));
    TestFalse(TEXT("open center seal hidden"),Door->CenterSeal->IsVisible());
    for(auto* Panel:{Door->LeftPanel.Get(),Door->RightPanel.Get()})
    {
        TestTrue(TEXT("only query collision"),Panel->GetCollisionEnabled()==ECollisionEnabled::QueryOnly);
        TestFalse(TEXT("no independent rigid body physics"),Panel->IsSimulatingPhysics());
        TestTrue(TEXT("human collision blocks"),Panel->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block);
    }
    for(int32 I=0;I<150;++I)Door->AdvanceAnimation(.025,false,false);
    TestTrue(TEXT("close then relatch completes"),Door->GetDoorState()==ERedlineHabitatDoorState::Closed && FMath::IsNearlyZero(Door->GetOpenness()) && FMath::IsNearlyZero(Door->GetUnlockProgress()));
    TestTrue(TEXT("closed center seal restored"),Door->CenterSeal->IsVisible());
    Fixture.ForwardErrorMessages(this);return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineDoorSafety,"Redline.EVA.DoorCapsuleAndObstacleReopen",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineDoorSafety::RunTest(const FString& Parameters)
{
    TGuardValue<bool> NoConnection(GetMutableDefault<URedlineSettings>()->bAutoConnect,false);
    FTestWorldWrapper Fixture;
    if(!Fixture.CreateTestWorld(EWorldType::Game) || !Fixture.BeginPlayInTestWorld()){Fixture.ForwardErrorMessages(this);return false;}
    auto* World=Fixture.GetTestWorld();auto* Door=World->SpawnActor<ARedlineHabitatDoor>();
    if(!Door || !Door->ConfigureOpening(FTransform(FRotator(0,0,0),FVector(0,0,130)),FVector(10,210,240)))return false;
    Door->DoorAudio->SetVolumeMultiplier(0);Door->SetAutomaticOpen(false);Door->RequestPresentationOpen(true);
    for(int32 I=0;I<100;++I)Door->Tick(.025);
    TestTrue(TEXT("initial passage open"),FMath::IsNearlyEqual(Door->GetOpenness(),1.));
    Door->RequestPresentationOpen(false);
    for(int32 I=0;I<40;++I)Door->Tick(.025);
    TestTrue(TEXT("door is closing after clear hold"),Door->GetDoorState()==ERedlineHabitatDoorState::Closing && Door->GetOpenness()<1 && Door->GetOpenness()>0);
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Human=World->SpawnActor<ACharacter>(ACharacter::StaticClass(),FVector(0,0,130),FRotator::ZeroRotator,Spawn);
    if(!TestNotNull(TEXT("actual capsule in passage"),Human))return false;
    TestTrue(TEXT("capsule overlap detected independent of cinematic/proximity"),Door->IsPassageBlocked());
    const double Before=Door->GetOpenness();Door->Tick(.025);
    TestTrue(TEXT("closing immediately reverses without reducing gap"),Door->GetDoorState()==ERedlineHabitatDoorState::Opening && Door->GetOpenness()>=Before);
    TestEqual(TEXT("one measured safety reopen"),Door->GetSafetyReopenCount(),1);
    for(int32 I=0;I<120;++I)Door->Tick(.025);
    TestTrue(TEXT("cannot close around the stationary human"),Door->GetDoorState()==ERedlineHabitatDoorState::Open && FMath::IsNearlyEqual(Door->GetOpenness(),1.));
    Human->SetActorLocation(FVector(600,0,130));
    for(int32 I=0;I<40;++I)Door->Tick(.025);
    TestTrue(TEXT("clear passage may close again"),Door->GetDoorState()==ERedlineHabitatDoorState::Closing);
    auto* Obstacle=World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(),FVector(0,0,130),FRotator::ZeroRotator,Spawn);
    if(!Obstacle)return false;auto* Mesh=Obstacle->GetStaticMeshComponent();Mesh->SetMobility(EComponentMobility::Movable);
    Mesh->SetStaticMesh(Door->LeftPanel->GetStaticMesh());Mesh->SetWorldScale3D(FVector(.3,.3,.3));
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Mesh->SetCollisionObjectType(ECC_WorldDynamic);Mesh->SetCollisionResponseToAllChannels(ECR_Ignore);Mesh->SetCollisionResponseToChannel(ECC_Pawn,ECR_Block);
    TestTrue(TEXT("query-only blocking object detected"),Door->IsPassageBlocked());
    Door->Tick(.025);TestTrue(TEXT("object obstruction reopens"),Door->GetDoorState()==ERedlineHabitatDoorState::Opening);
    TestEqual(TEXT("second safety reopen counted"),Door->GetSafetyReopenCount(),2);
    Fixture.ForwardErrorMessages(this);return true;
}
#endif
