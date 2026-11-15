#include "RedlineSurfaceDust.h"
#include "RedlineAstronautCharacter.h"
#include "RedlineDroneActor.h"
#include "RedlineRoverActor.h"
#include "RedlineBridgeSubsystem.h"
#include "RedlineStaleMonitor.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Math/RotationMatrix.h"

DEFINE_LOG_CATEGORY_STATIC(LogRedlineDust,Log,All);

ARedlineSurfaceDust::ARedlineSurfaceDust():Random(20261115)
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickGroup=TG_PostUpdateWork;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("DustPresentationRoot"));
    SetActorEnableCollision(false);
}
void ARedlineSurfaceDust::BeginPlay()
{
    Super::BeginPlay();
    if(auto* GI=GetGameInstance())Bridge=GI->GetSubsystem<URedlineBridgeSubsystem>();
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Plane.Plane"));
    auto* Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Campaign/Materials/M_SurfaceDust.M_SurfaceDust"));
    if(!Mesh || !Material){UE_LOG(LogRedlineDust,Warning,TEXT("Surface dust disabled: prepare_surface_dust.py asset is missing"));return;}
    Planes.Reserve(PoolCapacity);Materials.Reserve(PoolCapacity);Puffs.SetNum(PoolCapacity);
    for(int32 I=0;I<PoolCapacity;++I)
    {
        auto* Plane=NewObject<UStaticMeshComponent>(this);
        Plane->SetupAttachment(RootComponent);Plane->SetMobility(EComponentMobility::Movable);Plane->SetStaticMesh(Mesh);
        Plane->SetCollisionEnabled(ECollisionEnabled::NoCollision);Plane->SetSimulatePhysics(false);Plane->SetCanEverAffectNavigation(false);
        Plane->SetCastShadow(false);Plane->SetReceivesDecals(false);Plane->bAffectDistanceFieldLighting=false;
        Plane->bAffectDynamicIndirectLighting=false;Plane->SetHiddenInGame(true);Plane->RegisterComponent();
        auto* Dynamic=UMaterialInstanceDynamic::Create(Material,this);Plane->SetMaterial(0,Dynamic);
        Dynamic->SetScalarParameterValue(TEXT("PuffOpacity"),0);Planes.Add(Plane);Materials.Add(Dynamic);
    }
    bReady=true;DiscoverSources();
    UE_LOG(LogRedlineDust,Display,TEXT("SCENARIO surface dust: pooled %d soft planes, local terrain contact only; no soil or weather physics"),PoolCapacity);
}
bool ARedlineSurfaceDust::CanEmit(ERedlineDustSource Kind,double Speed,double Clearance,bool Fresh,bool Grounded)
{
    if(!Fresh || !FMath::IsFinite(Speed) || !FMath::IsFinite(Clearance) || Speed<0 || Speed>800 || Clearance<0)return false;
    if(Kind==ERedlineDustSource::Rotor)return Clearance>=35 && Clearance<=500;
    if(Kind==ERedlineDustSource::Boot)return Grounded && Speed>=18 && Clearance<=120;
    return Speed>=8 && Clearance<=170;
}
float ARedlineSurfaceDust::OpacityAt(float Age,float Life,float Strength)
{
    if(!FMath::IsFinite(Age) || !FMath::IsFinite(Life) || !FMath::IsFinite(Strength) || Age<0 || Life<=0 || Age>=Life)return 0;
    const float Alpha=Age/Life;
    return FMath::Clamp(Strength,0.f,1.f)*.14f*FMath::Min(1.f,Alpha*8.f)*FMath::Square(1.f-Alpha);
}
bool ARedlineSurfaceDust::IsTerrainComponent(const UPrimitiveComponent* Component)
{
    const auto* Mesh=Cast<UStaticMeshComponent>(Component);
    if(!Mesh || !Mesh->GetStaticMesh())return false;
    // Asset identity is stable in runtime builds; actor labels are editor-only.
    return Mesh->GetStaticMesh()->GetPathName().StartsWith(TEXT("/Game/T4Fixtures/Terrain/"));
}
void ARedlineSurfaceDust::DiscoverSources()
{
    Sources.RemoveAll([](const FSource& S){return !S.Actor.IsValid();});
    for(TActorIterator<AActor> It(GetWorld());It;++It)
    {
        if(!It->IsA<ARedlineRoverActor>() && !It->IsA<ARedlineAstronautCharacter>())continue;
        bool Known=false;for(const FSource& Existing:Sources)if(Existing.Actor.Get()==*It){Known=true;break;}
        if(!Known && Sources.Num()<8){FSource Source;Source.Actor=*It;Sources.Add(Source);}
    }
}
bool ARedlineSurfaceDust::TraceSurface(AActor* Source,FVector Near,FVector& Surface,double& Clearance)const
{
    if(!Source || Near.ContainsNaN())return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(RedlineSurfaceDust),true);Query.AddIgnoredActor(Source);Query.AddIgnoredActor(this);
    FHitResult Hit;
    // First blocker must be the terrain mesh itself. Roofs/floors/interiors
    // suppress emission instead of tracing through a habitat to hidden ground.
    if(!GetWorld()->LineTraceSingleByChannel(Hit,Near+FVector(0,0,35),Near-FVector(0,0,1200),ECC_Visibility,Query) ||
        !Hit.bBlockingHit || !IsTerrainComponent(Hit.GetComponent()) || Hit.ImpactNormal.Z<.55)return false;
    Surface=Hit.ImpactPoint;Clearance=Near.Z-Surface.Z;
    return FMath::IsFinite(Clearance) && Clearance>=0;
}
void ARedlineSurfaceDust::UpdateSource(FSource& S,double Now)
{
    auto* Actor=S.Actor.Get();if(!Actor || Actor->IsHidden())return;
    auto* Human=Cast<ARedlineAstronautCharacter>(Actor);auto* Robot=Cast<ARedlineRoverActor>(Actor);
    const bool Rotor=Actor->IsA<ARedlineDroneActor>();
    if(Robot && Robot->AppliedPoseCount>S.LastAppliedPoseCount)
    {S.LastAppliedPoseCount=Robot->AppliedPoseCount;S.LastAcceptedPoseAt=Now;}
    const FVector Position=Actor->GetActorLocation();
    if(S.LastSample<0){S.LastPosition=Position;S.LastSample=Now;return;}
    const double Dt=Now-S.LastSample;if(Dt<.1)return;
    const FVector Delta=Position-S.LastPosition;S.LastPosition=Position;S.LastSample=Now;
    // Reset after a stall/seek/teleport, and never leave an emission trail
    // between discontinuous presentation poses.
    if(Dt>.5 || Delta.Size()>400){S.Speed=0;return;}
    S.Speed=Delta.Size2D()/Dt;
    const bool Fresh=Bridge && !Bridge->IsOfflineReplay() && Bridge->IsConnected() && Bridge->StaleMonitor &&
        (Human ? Human->bMissionStateFresh : Robot && S.LastAcceptedPoseAt>=0 && Now-S.LastAcceptedPoseAt<=.4 && Bridge->StaleMonitor->IsFresh(Robot->OdometryTopic,Now));
    if(Human && (Human->bPresentationLocked || !Human->GetCharacterMovement()->IsMovingOnGround()))return;
    FVector Surface;double Clearance;
    if(!TraceSurface(Actor,Position,Surface,Clearance))return;
    const auto Kind=Rotor ? ERedlineDustSource::Rotor : Human ? ERedlineDustSource::Boot : ERedlineDustSource::Rover;
    if(!CanEmit(Kind,S.Speed,Clearance,Fresh,Human && Human->GetCharacterMovement()->IsMovingOnGround()))return;
    const double Period=Rotor ? .10 : Human ? (Human->bSprinting ? .16 : .26) : .12;
    if(Now-S.LastEmission<Period)return;S.LastEmission=Now;
    FVector Contact=Surface;
    if(Human)Contact+=Actor->GetActorRightVector()*(S.ContactIndex++%2 ? 13 : -13);
    else if(!Rotor)
    {
        const int32 Wheel=S.ContactIndex++%6;
        const FVector Offset=Actor->GetActorForwardVector()*((Wheel/2-1)*90)+Actor->GetActorRightVector()*(Wheel%2 ? 90 : -90);
        FVector Checked;double Unused;
        if(!TraceSurface(Actor,Position+Offset,Checked,Unused))return;Contact=Checked;
    }
    const float Strength=Rotor ? FMath::Clamp(float(1-Clearance/600.),.1f,.7f) : FMath::Clamp(S.Speed/200.f,.2f,.75f);
    SpawnPuff(Contact,Delta/Dt,Kind,Strength);
}
void ARedlineSurfaceDust::SpawnPuff(FVector Surface,FVector InheritedVelocity,ERedlineDustSource Kind,float Strength)
{
    if(Puffs.Num()!=PoolCapacity || Surface.ContainsNaN() || InheritedVelocity.ContainsNaN() || !FMath::IsFinite(Strength))return;
    FPuff& P=Puffs[NextPuff];const int32 Index=NextPuff;NextPuff=(NextPuff+1)%PoolCapacity;
    const bool Rotor=Kind==ERedlineDustSource::Rotor;
    const float Angle=Random.FRandRange(0,2*PI);const FVector Radial(FMath::Cos(Angle),FMath::Sin(Angle),0);
    P.Position=Surface+FVector(0,0,Rotor ? 10 : 5)+Radial*(Rotor ? Random.FRandRange(20,60) : 8);
    const FVector Wind=ScenarioWindCmS.GetClampedToMaxSize(60);
    P.Velocity=Wind+InheritedVelocity.GetClampedToMaxSize(200)*.12+Radial*(Rotor ? 65 : 16)+FVector(0,0,Rotor ? 20 : 31);
    P.Age=0;P.Life=Random.FRandRange(.7f,1.25f);P.Diameter=Rotor ? 70 : Kind==ERedlineDustSource::Rover ? 45 : 29;
    P.Strength=FMath::Clamp(Strength,0.f,1.f);P.Active=true;++TotalEmitted;
    if(Planes.IsValidIndex(Index))Planes[Index]->SetHiddenInGame(false);
}
void ARedlineSurfaceDust::AdvanceParticles(float Dt,FVector Camera)
{
    if(!FMath::IsFinite(Dt) || Dt<=0)return;
    for(int32 I=0;I<Puffs.Num();++I)
    {
        FPuff& P=Puffs[I];if(!P.Active)continue;P.Age+=Dt;
        if(P.Age>=P.Life){P.Active=false;if(Planes.IsValidIndex(I))Planes[I]->SetHiddenInGame(true);continue;}
        P.Velocity.Z-=18*Dt;P.Position+=P.Velocity*Dt;
        if(!Planes.IsValidIndex(I) || !Materials.IsValidIndex(I))continue;
        const float Alpha=P.Age/P.Life;
        const FVector Facing=(Camera-P.Position).GetSafeNormal();
        Planes[I]->SetWorldLocationAndRotation(P.Position,FRotationMatrix::MakeFromZ(Facing.IsNearlyZero() ? FVector::UpVector : Facing).Rotator());
        Planes[I]->SetWorldScale3D(FVector(P.Diameter/100.f*(1+Alpha*.8f),P.Diameter/100.f*(1+Alpha*.8f),1));
        Materials[I]->SetScalarParameterValue(TEXT("PuffOpacity"),OpacityAt(P.Age,P.Life,P.Strength));
    }
}
int32 ARedlineSurfaceDust::GetActiveParticleCount()const
{int32 Count=0;for(const FPuff& P:Puffs)if(P.Active)++Count;return Count;}
void ARedlineSurfaceDust::Tick(float Delta)
{
    Super::Tick(Delta);if(!bReady)return;
    const double Now=FPlatformTime::Seconds();
    if(Now>=NextDiscovery){DiscoverSources();NextDiscovery=Now+1;}
    for(FSource& S:Sources)UpdateSource(S,Now);
    FVector Camera=FVector::ZeroVector;if(auto* PC=GetWorld()->GetFirstPlayerController())if(PC->PlayerCameraManager)Camera=PC->PlayerCameraManager->GetCameraLocation();
    AdvanceParticles(FMath::Min(Delta,.1f),Camera);
}
