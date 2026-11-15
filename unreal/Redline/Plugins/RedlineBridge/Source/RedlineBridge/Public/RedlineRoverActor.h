#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineRoverActor.generated.h"
class UStaticMeshComponent;
class URedlineBridgeSubsystem;
class FJsonObject;
class UMaterialInterface;
class UMaterialParameterCollection;
class UDecalComponent;

/** Technical presentation proxy. Collision and simulation are disabled; Gazebo owns robot physics. */
UCLASS(Blueprintable)
class REDLINEBRIDGE_API ARedlineRoverActor : public AActor
{
    GENERATED_BODY()
public:
    ARedlineRoverActor();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;
    /** Keyboard intent only. ROS owns all control and physics. Focus/brake wins. */
    static FVector2D ManualIntent(bool bFocused,bool bForward,bool bBackward,bool bLeft,bool bRight,bool bBrake);
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="REDLINE") TObjectPtr<UStaticMeshComponent> PresentationMesh;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="REDLINE") FString OdometryTopic=TEXT("/rover_1/odom");
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="REDLINE") FString OdomFrame=TEXT("rover_1/odom");
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="REDLINE") FString BaseFrame=TEXT("rover_1/base_link");
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="REDLINE") double MaxDynamicTfSkewSec=0.5;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="REDLINE|Presentation") TObjectPtr<UMaterialInterface> TrackDecalMaterial;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="REDLINE|Presentation") TObjectPtr<UMaterialParameterCollection> SandWheelCollection;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="REDLINE") FVector LastMapPositionMetres=FVector::ZeroVector;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="REDLINE") FQuat LastMapOrientation=FQuat::Identity;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="REDLINE") int32 AppliedPoseCount=0;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="REDLINE") int32 RejectedPoseCount=0;
    static FTransform ComposeRosPose(const FTransform& MapFromOdom,const FVector& OdomPosition,const FQuat& OdomOrientation);
private:
    friend class FRedlineFrameGuards;
    friend class FRedlineWheelVisuals;
    UPROPERTY(Transient) TObjectPtr<URedlineBridgeSubsystem> Bridge;
    FDelegateHandle TopicHandle;
    FTransform MapFromOdom=FTransform::Identity;
    bool bHasMapFromOdom=false;
    bool bStaticTransform=false;
    bool bStaticSnapshotInvalid=false;
    double TransformStamp=0;
    double LastLogTime=0;
    FString PoseLog;
    bool bManualKeyboard=false;
    bool bTimeControls=false;
    double LastManualSend=0;
    double RequestedTimeScale=1;
    double ActualTimeScale=1;
    TMap<FString,TWeakObjectPtr<AActor>> WheelVisuals;
    TMap<FString,TWeakObjectPtr<AActor>> MovingVisuals;
    TMap<FString,FVector> LastTrackPositions;
    double LastWheelStamp=-1;
    TArray<TWeakObjectPtr<UDecalComponent>> TrackDecals;
    int32 AppliedWheelSceneCount=0;
    void ApplyWheelScene(const TSharedPtr<FJsonObject>& Json);
    void PublishManual(const FVector2D& Intent);
    void PublishTimeScale(double Factor);
    void TimeNormal() { PublishTimeScale(1); }
    void TimeDouble() { PublishTimeScale(2); }
    void TimeQuadruple() { PublishTimeScale(4); }
    void OnMessage(const FString& Topic,const TSharedPtr<FJsonObject>& Json);
    UFUNCTION() void ConnectionChanged(bool bConnected);
};
