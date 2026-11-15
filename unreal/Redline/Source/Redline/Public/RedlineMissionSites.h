#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineMissionSites.generated.h"

class URedlineBridgeSubsystem;
class UTextRenderComponent;
class UStaticMeshComponent;
class UStaticMesh;
class FJsonObject;

/** A received task location. This view cannot unlock or complete ROS work. */
struct FRedlineMissionSite
{
    FString Id,Title,Kind,Actor,State,Endpoint;
    FVector Map=FVector::ZeroVector;
    double RadiusMetres=0;
    bool bRemote=false,bEnabled=false;
};

struct FRedlineMissionSitesState
{
    FString RunId,OperationState;
    int64 Revision=-1;
    int32 ActiveIndex=INDEX_NONE;
    double Progress=0;
    bool bDone=false;
    TArray<FRedlineMissionSite> Sites;
};

/** Passive, bounded site labels/tool staging. No commands, robot or collision authority. */
UCLASS()
class REDLINE_API ARedlineMissionSites : public AActor
{
    GENERATED_BODY()
public:
    ARedlineMissionSites();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    bool Fresh() const;
    bool GetActiveSiteMap(FVector& OutMap) const;
    FVector ActiveSiteMap() const;
    double DistanceMetres() const;
    bool IsInRange() const;
    FString TaskState() const;
    static bool ParseSnapshot(const TSharedPtr<FJsonObject>& Json,FRedlineMissionSitesState& Out);
    static FVector SiteWorldPosition(FVector MapMetres,double HeightCm=0);
    static constexpr int32 Capacity=32;
private:
    friend class FRedlineMissionSitesPacketTest;
    friend class FRedlineMissionSitesAuthorityTest;
    UPROPERTY(Transient) TObjectPtr<URedlineBridgeSubsystem> Bridge;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextRenderComponent>> Labels;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Props;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<UStaticMesh>> ToolMeshes;
    TMap<FName,double> ToolMinimumZ;
    FDelegateHandle TopicHandle;
    FRedlineMissionSitesState State;
    TArray<int32> VisualTasks;
    TArray<FVector> GroundMaps;
    TArray<bool> HasGround;
    double Receipt=-1,LastGroundUpdate=-1;
    bool AcceptSnapshot(const TSharedPtr<FJsonObject>& Json,double Now);
    bool FreshAt(double Now,bool Connected) const;
    void Receive(const FString& Topic,const TSharedPtr<FJsonObject>& Json);
    UFUNCTION() void ConnectionChanged(bool Connected);
    void LoadProps();
    void HideAll();
    void UpdateVisuals(double Now);
};
