#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineFootprints.generated.h"
class UDecalComponent;
class UMaterialInterface;

/** SCENARIO presentation: boot prints decals behind EV1 on terrain only. Not soil mechanics; the pose
 *  sent to ROS and the human movement are unchanged. Prints fade after FadeSeconds; the pool is bounded. */
UCLASS()
class REDLINE_API ARedlineFootprints : public AActor
{
    GENERATED_BODY()
public:
    ARedlineFootprints();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    /** Ground distance between successive prints for a walking speed (m/s); 0 when standing. */
    static float StrideMetres(float SpeedMps);
    int32 GetPrintCount() const {return Prints.Num();}
    bool LastFootWasLeft() const {return bLastLeft;}
    bool PreviousFootWasLeft() const {return bPreviousLeft;}
    void StampForTest(const FVector& Ground,const FRotator& Facing){Stamp(Ground,Facing);}
    UPROPERTY(EditAnywhere,Category="REDLINE|Footprints") int32 MaxPrints=600;
    UPROPERTY(EditAnywhere,Category="REDLINE|Footprints") float FadeSeconds=1200.f;
private:
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> Material;
    UPROPERTY(Transient) TArray<TObjectPtr<UDecalComponent>> Prints;
    int32 Next=0;
    bool bLastLeft=false,bPreviousLeft=true,bHasLast=false;
    FVector LastPosition=FVector::ZeroVector;
    double Travel=0;
    void Stamp(const FVector& Ground,const FRotator& Facing);
};
