#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineSurfaceDust.generated.h"

class URedlineBridgeSubsystem;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class UPrimitiveComponent;

enum class ERedlineDustSource : uint8 { Boot, Rover, Rotor };

/** Bounded SCENARIO dust presentation. No soil physics, weather measurement or ROS commands. */
UCLASS()
class REDLINE_API ARedlineSurfaceDust : public AActor
{
    GENERATED_BODY()
public:
    ARedlineSurfaceDust();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    static bool CanEmit(ERedlineDustSource Kind,double SpeedCmS,double GroundClearanceCm,bool Fresh,bool Grounded);
    static bool IsTerrainComponent(const UPrimitiveComponent* Component);
    static float OpacityAt(float Age,float Life,float Strength);
    int32 GetActiveParticleCount() const;
    int32 GetTotalEmitted() const {return TotalEmitted;}
    static constexpr int32 PoolCapacity=96;
    /** Authored visual drift in UE cm/s; explicitly not measured Mars wind. */
    UPROPERTY(EditAnywhere,Category="REDLINE|Scenario Dust") FVector ScenarioWindCmS=FVector(24,9,0);
private:
    friend class FRedlineSurfaceDustPoolTest;
    struct FPuff
    {
        FVector Position=FVector::ZeroVector,Velocity=FVector::ZeroVector;
        float Age=0,Life=0,Diameter=0,Strength=0;
        bool Active=false;
    };
    struct FSource
    {
        TWeakObjectPtr<AActor> Actor;
        FVector LastPosition=FVector::ZeroVector;
        double LastSample=-1,LastEmission=-1,LastAcceptedPoseAt=-1;
        float Speed=0;
        int32 ContactIndex=0,LastAppliedPoseCount=0;
    };
    UPROPERTY(Transient) TObjectPtr<URedlineBridgeSubsystem> Bridge;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Planes;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
    TArray<FPuff> Puffs;
    TArray<FSource> Sources;
    FRandomStream Random;
    double NextDiscovery=0;
    int32 NextPuff=0,TotalEmitted=0;
    bool bReady=false;
    void DiscoverSources();
    bool TraceSurface(AActor* Source,FVector Near,FVector& Surface,double& Clearance)const;
    void UpdateSource(FSource& Source,double Now);
    void SpawnPuff(FVector Surface,FVector InheritedVelocity,ERedlineDustSource Kind,float Strength);
    void AdvanceParticles(float Delta,FVector Camera);
};
