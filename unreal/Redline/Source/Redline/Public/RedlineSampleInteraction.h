#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineSampleInteraction.generated.h"

class ARedlineAstronautCharacter;
class APlayerController;
class USkeletalMeshComponent;
class UPoseableMeshComponent;
class UStaticMeshComponent;
class UCameraComponent;
class USceneComponent;
class UStaticMesh;

/** Feedback-driven visual performance; never creates samples or completes ROS actions. */
UCLASS()
class REDLINE_API ARedlineSampleInteraction : public AActor
{
    GENERATED_BODY()
public:
    ARedlineSampleInteraction();
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    bool BeginInteraction(ARedlineAstronautCharacter* Astronaut,FVector TargetMap,const FString& Kind);
    void SetProgress(float Progress,const FString& Phase);
    void EndInteraction(bool Success);
    bool IsInteracting() const {return bActive;}
    float GetProgress() const {return FeedbackProgress;}
    FString GetInteractionPhase() const {return FeedbackPhase;}
    bool WasSampleTransferredVisually() const {return bTransferred;}
    /** Optional actor camera shows hands/body; the previous player view is restored exactly. */
    bool bUseInspectionCamera=true;
    bool bUseActualWorkPoint=false;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UPoseableMeshComponent> PerformanceBody;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UStaticMeshComponent> SampleVisual;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UStaticMeshComponent> HandTool;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UStaticMeshComponent> ToolHead;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UCameraComponent> InspectionCamera;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<USceneComponent> SampleCapPivot;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UStaticMeshComponent> SampleCap;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<USceneComponent> StationRoot;
private:
    friend class FRedlineSamplePresentation;
    TWeakObjectPtr<ARedlineAstronautCharacter> Human;
    TWeakObjectPtr<USkeletalMeshComponent> SourceBody;
    TWeakObjectPtr<APlayerController> Player;
    TWeakObjectPtr<AActor> PreviousView;
    TArray<FTransform> BaseLocalPose,BaseComponentPose;
    FVector WorkPointComponent=FVector::ZeroVector;
    FString InteractionKind,FeedbackPhase;
    float FeedbackProgress=0;
    double PerformanceSeconds=0;
    bool bActive=false,bTransferred=false,bPreviousLocked=false,bPreviousMeshHidden=false,bPreviousMeshVisible=true,bPreviousOwnerNoSee=false,bEnding=false;
    bool bPartsLoaded=false;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> TubeBodyMesh;
    FVector WorkWorld=FVector::ZeroVector,CapBind=FVector::ZeroVector;
    UPROPERTY(Transient) TArray<TObjectPtr<USceneComponent>> StationPivots;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> StationMeshes;
    TArray<FName> StationNames;
    TArray<FVector> StationBinds;
    void LoadInteractionParts();
    void CommitStationVisual();
    TArray<FTransform> ComponentPose() const;
    void SetComponentRotation(int32 Bone,const FQuat& Rotation);
    void SolveLimb(FName Upper,FName Lower,FName Tip,FVector Target,FVector Pole);
    void ApplyPerformance();
};
