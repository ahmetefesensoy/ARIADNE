#include "RedlineAmbientDust.h"
#include "RedlineSurfaceDust.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Materials/MaterialInstanceDynamic.h"

DEFINE_LOG_CATEGORY_STATIC(LogRedlineAmbientDust,Log,All);

ARedlineAmbientDust::ARedlineAmbientDust()
{
    PrimaryActorTick.bCanEverTick=true;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}
bool ARedlineAmbientDust::NeedsRecycle(const FVector& Wisp,const FVector& Viewer,float RadiusCm)
{
    return Wisp.ContainsNaN() || FVector::Dist2D(Wisp,Viewer)>RadiusCm || FMath::Abs(Wisp.Z-Viewer.Z)>RadiusCm*.4f;
}
float ARedlineAmbientDust::WispOpacity(float F)
{
    if(!FMath::IsFinite(F) || F<=0.f || F>=1.f)return 0.f;
    return .08f*FMath::Sin(PI*F);
}
void ARedlineAmbientDust::BeginPlay()
{
    Super::BeginPlay();
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Plane.Plane"));
    auto* Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Campaign/Materials/M_SurfaceDust.M_SurfaceDust"));
    if(!Mesh || !Material){UE_LOG(LogRedlineAmbientDust,Warning,TEXT("Ambient dust disabled: plane or M_SurfaceDust missing"));return;}
    for(int32 I=0;I<WispCount;++I)
    {
        auto* Plane=NewObject<UStaticMeshComponent>(this);Plane->SetupAttachment(RootComponent);Plane->SetStaticMesh(Mesh);
        Plane->SetCollisionEnabled(ECollisionEnabled::NoCollision);Plane->SetCastShadow(false);Plane->RegisterComponent();
        auto* Dynamic=UMaterialInstanceDynamic::Create(Material,this);Plane->SetMaterial(0,Dynamic);
        Dynamic->SetScalarParameterValue(TEXT("PuffOpacity"),0);Planes.Add(Plane);Materials.Add(Dynamic);
    }
    Wisps.SetNum(WispCount);
    UE_LOG(LogRedlineAmbientDust,Display,TEXT("SCENARIO ambient dust: %d faint wisps within %.0f m, authored wind"),WispCount,RadiusCm/100.f);
}
bool ARedlineAmbientDust::Outdoors(const FVector& Viewer) const
{
    // Inside the habitat there is a roof; outdoors nothing blocks a short trace upward.
    FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(RedlineAmbientDust),false);Query.AddIgnoredActor(this);
    return !GetWorld()->LineTraceSingleByChannel(Hit,Viewer,Viewer+FVector(0,0,3000),ECC_Visibility,Query);
}
void ARedlineAmbientDust::Respawn(int32 I,const FVector& Viewer,bool bAnywhere)
{
    FWisp& W=Wisps[I];
    const float Angle=FMath::FRandRange(0.f,2*PI),Distance=bAnywhere ? FMath::Sqrt(FMath::FRand())*RadiusCm : RadiusCm*FMath::FRandRange(.7f,1.f);
    // Upwind of the viewer when recycled, so wisps drift into view instead of popping.
    const FVector Upwind=-ScenarioWindCmS.GetSafeNormal2D();
    const FVector Offset=bAnywhere ? FVector(FMath::Cos(Angle),FMath::Sin(Angle),0)*Distance : (Upwind*.8f+FVector(FMath::Cos(Angle),FMath::Sin(Angle),0)*.6f).GetSafeNormal2D()*Distance;
    W.Position=Viewer+Offset+FVector(0,0,FMath::FRandRange(-120.f,80.f));
    W.Age=bAnywhere ? FMath::FRandRange(0.f,20.f) : 0.f;W.Life=FMath::FRandRange(18.f,40.f);W.Size=FMath::FRandRange(120.f,320.f);
}
void ARedlineAmbientDust::Tick(float Delta)
{
    Super::Tick(Delta);
    if(Planes.IsEmpty())return;
    auto* PC=GetWorld()->GetFirstPlayerController();if(!PC || !PC->PlayerCameraManager)return;
    const FVector Viewer=PC->PlayerCameraManager->GetCameraLocation();
    const FRotator Facing=PC->PlayerCameraManager->GetCameraRotation();
    const bool bOutside=Outdoors(Viewer);
    for(int32 I=0;I<Wisps.Num();++I)
    {
        FWisp& W=Wisps[I];
        if(!bSeeded || W.Age>=W.Life || NeedsRecycle(W.Position,Viewer,RadiusCm))Respawn(I,Viewer,!bSeeded);
        W.Age+=Delta;W.Position+=ScenarioWindCmS*Delta;
        const float Opacity=bOutside ? WispOpacity(W.Age/W.Life) : 0.f;
        Materials[I]->SetScalarParameterValue(TEXT("PuffOpacity"),Opacity);
        Planes[I]->SetVisibility(Opacity>.001f);
        // Plane faces +Z; turn it to face the camera (billboard) and scale to the wisp size.
        Planes[I]->SetWorldLocationAndRotation(W.Position,FRotator(Facing.Pitch+90.f,Facing.Yaw,0.f));
        Planes[I]->SetWorldScale3D(FVector(W.Size/100.f));
    }
    bSeeded=true;
}
