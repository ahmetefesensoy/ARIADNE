#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineRoverScienceVisuals.generated.h"

class URedlineBridgeSubsystem;class ARedlineRoverActor;class USceneComponent;class UStaticMeshComponent;class UTextRenderComponent;class UStaticMesh;class FJsonObject;

/** Finite values actually reported by the ROS science model, not inferred force/depth. */
struct FRedlineDrillVisualFeedback
{
    FString Request,Phase;
    double Progress=0,DepthMm=0,RequestedMm=0;
    bool bHasDepth=false,bHasRequested=false;
};

/** Read-only SCENARIO arm/tool performance on the one ROS/Gazebo-owned rover. */
UCLASS()
class REDLINE_API ARedlineRoverScienceVisuals : public AActor
{
    GENERATED_BODY()
public:
    ARedlineRoverScienceVisuals();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    static bool ParseDrillFeedback(const TSharedPtr<FJsonObject>& Json,FRedlineDrillVisualFeedback& Out);
    static bool DrillRotates(const FString& Phase);
    static double ReportedDepthCm(double DepthMm,bool bHasDepth);
private:
    UPROPERTY(Transient) TObjectPtr<URedlineBridgeSubsystem> Bridge;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Tool;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Bit;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> BitPivot;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Arm;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Flash;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UTextRenderComponent> Label;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<UStaticMesh>> Tools;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> DrillParts;
    TWeakObjectPtr<ARedlineRoverActor> Rover;
    FDelegateHandle TopicHandle;
    FString Run,Request,Kind,Phase,TaskTarget,OperationState;
    FVector TargetMap=FVector::ZeroVector;
    FVector BitOrigin=FVector::ZeroVector,BitChildOffset=FVector::ZeroVector;
    double Receipt=-1,FeedbackReceipt=-1,PoseReceipt=-1,PoseStamp=-1,Progress=0,Angle=0;
    double ActualDepthMm=0,ActualRequestedMm=0,ActualAchievedMm=0;
    int64 Revision=-1;
    bool bHasDepth=false,bHasRequested=false,bHasAchieved=false,bBusy=false,bSeparateBit=false;
    void Receive(const FString& Topic,const TSharedPtr<FJsonObject>& Json);
    void HideVisuals();
    void LoadDrillParts();
    UFUNCTION() void ConnectionChanged(bool Connected);
};
