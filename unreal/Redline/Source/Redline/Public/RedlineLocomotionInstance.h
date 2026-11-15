#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "RedlineLocomotionInstance.generated.h"

class UAnimSequence;
struct FRedlineLocomotionProxy;

/** Presentation state only. The existing walk clip is not a captured run. */
struct REDLINE_API FRedlineLocomotionState
{
    float WalkWeight=0;
    float Cadence=0;
    double IdleTime=0,WalkTime=0;
    void Advance(float MeasuredSpeedCmS,float DeltaSeconds,double IdleLength,double WalkLength);
};

/** Runtime two-pose blend without editor-generated assets or root-motion authority. */
UCLASS(Transient,NotBlueprintable)
class REDLINE_API URedlineLocomotionInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    URedlineLocomotionInstance();
    bool Configure(UAnimSequence* InIdle,UAnimSequence* InWalk);
    void SetMeasuredSpeed(float SpeedCmS);
    float GetWalkWeight() const;
    float GetCadence() const;
    double GetWalkTime() const;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override;
private:
    friend struct FRedlineLocomotionProxy;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Idle;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Walk;
    float MeasuredSpeed=0;
};
