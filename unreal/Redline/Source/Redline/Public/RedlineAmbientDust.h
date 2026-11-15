#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineAmbientDust.generated.h"
class UStaticMeshComponent;
class UMaterialInstanceDynamic;

/** SCENARIO presentation: faint, slow dust wisps drifting near the ground around the viewer outdoors.
 *  Authored wind, not measured Mars weather; no ROS input or output. */
UCLASS()
class REDLINE_API ARedlineAmbientDust : public AActor
{
    GENERATED_BODY()
public:
    ARedlineAmbientDust();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    static bool NeedsRecycle(const FVector& Wisp,const FVector& Viewer,float RadiusCm);
    /** Opacity over a wisp's life fraction (0..1): faint, zero at both ends. */
    static float WispOpacity(float LifeFraction);
    UPROPERTY(EditAnywhere,Category="REDLINE|Ambient Dust") int32 WispCount=48;
    UPROPERTY(EditAnywhere,Category="REDLINE|Ambient Dust") float RadiusCm=2500.f;
    /** Authored drift in UE cm/s; explicitly not measured Mars wind. */
    UPROPERTY(EditAnywhere,Category="REDLINE|Ambient Dust") FVector ScenarioWindCmS=FVector(60,22,0);
private:
    struct FWisp {FVector Position=FVector::ZeroVector;float Age=0,Life=1,Size=100;};
    TArray<FWisp> Wisps;
    bool bSeeded=false;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Planes;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
    void Respawn(int32 Index,const FVector& Viewer,bool bAnywhere);
    bool Outdoors(const FVector& Viewer) const;
};
