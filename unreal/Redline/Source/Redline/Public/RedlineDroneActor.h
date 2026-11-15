#pragma once
#include "CoreMinimal.h"
#include "RedlineRoverActor.h"
#include "RedlineDroneActor.generated.h"
class USceneComponent;
class UStaticMeshComponent;

/** Actual ROS scout pose; visual rotor spin has no motor/physics authority. */
UCLASS()
class REDLINE_API ARedlineDroneActor : public ARedlineRoverActor
{
    GENERATED_BODY()
public:
    ARedlineDroneActor();
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<USceneComponent>> RotorPivots;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> VisualParts;
    bool bAirborne=false;
    double HomeAltitude=-DBL_MAX;
};
