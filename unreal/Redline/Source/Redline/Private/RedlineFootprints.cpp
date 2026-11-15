#include "RedlineFootprints.h"
#include "RedlineAstronautCharacter.h"
#include "RedlineSurfaceDust.h"
#include "Components/DecalComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInterface.h"

DEFINE_LOG_CATEGORY_STATIC(LogRedlineFootprints,Log,All);

ARedlineFootprints::ARedlineFootprints()
{
    PrimaryActorTick.bCanEverTick=true;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}
void ARedlineFootprints::BeginPlay()
{
    Super::BeginPlay();
    Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/MarsLook/M_Footprint.M_Footprint"));
    UE_LOG(LogRedlineFootprints,Display,TEXT("SCENARIO footprints: %s, pool %d, fade %.0f s, terrain only"),
        Material ? TEXT("decal material ready") : TEXT("material missing, prints off"),MaxPrints,FadeSeconds);
}
float ARedlineFootprints::StrideMetres(float SpeedMps)
{
    if(!FMath::IsFinite(SpeedMps) || SpeedMps<.2f)return 0.f;
    // Step length grows with speed and saturates (suited gait); one print per step.
    return FMath::Clamp(.55f+.15f*SpeedMps,.6f,1.4f);
}
void ARedlineFootprints::Stamp(const FVector& Ground,const FRotator& Facing)
{
    if(MaxPrints<=0)return;
    UDecalComponent* Decal=nullptr;
    if(Prints.Num()<MaxPrints)
    {
        Decal=NewObject<UDecalComponent>(this);Decal->SetupAttachment(RootComponent);Decal->RegisterComponent();
        Prints.Add(Decal);
    }
    else{Decal=Prints[Next];Next=(Next+1)%MaxPrints;}
    bPreviousLeft=bLastLeft;bLastLeft=!bLastLeft;
    const FVector Side=FRotationMatrix(FRotator(0,Facing.Yaw,0)).GetUnitAxis(EAxis::Y)*(bLastLeft ? -11.f : 11.f);
    if(Material)Decal->SetDecalMaterial(Material);
    // A decal projects along its X axis: pitch -90 points it at the ground, yaw follows the walk.
    Decal->DecalSize=FVector(8.f,6.f,15.f);
    Decal->SetWorldLocationAndRotation(Ground+Side,FRotator(-90.f,Facing.Yaw,0.f));
    Decal->SetFadeOut(FadeSeconds,30.f,false);
    Decal->SetFadeScreenSize(.002f);
    Decal->SetHiddenInGame(Material==nullptr);
}
void ARedlineFootprints::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(!Material)return;
    ARedlineAstronautCharacter* Walker=nullptr;
    for(TActorIterator<ARedlineAstronautCharacter> It(GetWorld());It;++It){Walker=*It;break;}
    if(!Walker || Walker->IsHidden())return;
    const FVector Here=Walker->GetActorLocation();
    if(!bHasLast){LastPosition=Here;bHasLast=true;return;}
    Travel+=FVector::Dist2D(Here,LastPosition)/100.;LastPosition=Here;
    const float Stride=StrideMetres(Walker->GetVelocity().Size2D()/100.f);
    if(Stride<=0.f || Travel<Stride)return;
    Travel=0;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(RedlineFootprints),true);Query.AddIgnoredActor(Walker);Query.AddIgnoredActor(this);
    FHitResult Hit;
    // Only on the terrain mesh: roofs, floors and ramps of the habitat never get prints.
    if(!GetWorld()->LineTraceSingleByChannel(Hit,Here,Here-FVector(0,0,400),ECC_Visibility,Query) || !Hit.bBlockingHit
        || !ARedlineSurfaceDust::IsTerrainComponent(Hit.GetComponent()) || Hit.ImpactNormal.Z<.6)return;
    Stamp(Hit.ImpactPoint,Walker->GetVelocity().Rotation());
}
