#include "RedlineDroneActor.h"
#include "RedlineTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/StaticMesh.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"

ARedlineDroneActor::ARedlineDroneActor()
{
    OdometryTopic=TEXT("/scout_1/odom");OdomFrame=TEXT("scout_1/odom");BaseFrame=TEXT("scout_1/base_link");
    PrimaryActorTick.bStartWithTickEnabled=true;
}
void ARedlineDroneActor::BeginPlay()
{
    Super::BeginPlay();SetActorTickEnabled(true);PresentationMesh->SetVisibility(false,false);
    FString Text;if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("Campaign/scout.json"))) || Text.Len()>32768)return;
    auto Manifest=FRedlineJson::Parse(Text);const TArray<TSharedPtr<FJsonValue>>* Parts=nullptr;
    if(!Manifest || !Manifest->TryGetArrayField(TEXT("parts"),Parts) || Parts->Num()>8)return;
    for(const auto& Value:*Parts)
    {
        if(!Value || Value->Type!=EJson::Object)continue;auto Part=Value->AsObject();FString Path;const TArray<TSharedPtr<FJsonValue>>* Pivot=nullptr;
        if(!Part->TryGetStringField(TEXT("mesh"),Path) || !Path.StartsWith(TEXT("/Game/Campaign/")) || !Part->TryGetArrayField(TEXT("pivot_cm"),Pivot) || Pivot->Num()!=3)continue;
        UStaticMesh* Mesh=LoadObject<UStaticMesh>(nullptr,*Path);if(!Mesh)continue;
        const FVector Position((*Pivot)[0]->AsNumber(),(*Pivot)[1]->AsNumber(),(*Pivot)[2]->AsNumber());if(Position.ContainsNaN())continue;
        auto* Joint=NewObject<USceneComponent>(this);Joint->SetupAttachment(RootComponent);Joint->SetRelativeLocation(Position);Joint->RegisterComponent();
        auto* Visual=NewObject<UStaticMeshComponent>(this);Visual->SetupAttachment(Joint);Visual->SetStaticMesh(Mesh);Visual->SetRelativeLocation(-Position);
        Visual->SetSimulatePhysics(false);Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);Visual->SetReceivesDecals(false);Visual->RegisterComponent();
        VisualParts.Add(Visual);bool Rotor=false;Part->TryGetBoolField(TEXT("rotor"),Rotor);if(Rotor)RotorPivots.Add(Joint);
    }
    SetActorHiddenInGame(true);
}
void ARedlineDroneActor::Tick(float Delta)
{
    Super::Tick(Delta);SetActorHiddenInGame(AppliedPoseCount==0);
    if(AppliedPoseCount>0)
    {
        // Cosmetic only. The physics publishes pose; this never commands motors.
        if(HomeAltitude==-DBL_MAX)HomeAltitude=LastMapPositionMetres.Z;
        bAirborne=LastMapPositionMetres.Z>HomeAltitude+.35;
        for(int32 I=0;I<RotorPivots.Num();++I)RotorPivots[I]->AddLocalRotation(FRotator(0,(I%2 ? -1 : 1)*Delta*(bAirborne ? 2400 : 0),0));
    }
}
