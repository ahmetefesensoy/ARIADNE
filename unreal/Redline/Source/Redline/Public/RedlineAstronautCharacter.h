#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "RedlineAstronautCharacter.generated.h"
class URedlineBridgeSubsystem;
class USpringArmComponent;
class UCameraComponent;
class UAnimSequence;
class URedlineLocomotionInstance;
class FJsonObject;

/** UE owns EV1; robot physics/control remains in ROS/Gazebo. */
UCLASS()
class REDLINE_API ARedlineAstronautCharacter : public ACharacter
{
    GENERATED_BODY()
public:
    ARedlineAstronautCharacter();
    virtual void BeginPlay() override;
    virtual void PossessedBy(AController* NewController) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float Delta) override;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<USpringArmComponent> CameraArm;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UCameraComponent> FollowCamera;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UCameraComponent> FirstPersonCamera;
    int32 PublishedPoses=0;
    bool bMovementProfileReady=false;
    bool bIntroMode=false;
    bool bMissionStateFresh=false;
    int32 MissionPhase=0;
    FVector BriefingMap=FVector::ZeroVector,StationMap=FVector::ZeroVector;
    FString InteractionMessage;
    bool bPresentationLocked=false;
    bool bMissionJournalOpen=false;
    bool bSprinting=false;
    bool bFirstPersonView=true;
    void SetFirstPersonView(bool Enabled);
    static double RequestedSpeed(double WalkMps,bool Sprint,double Multiplier,double CapMps);
    static TSharedRef<FJsonObject> PoseMessage(FVector CapsuleCm,FQuat UeRotation,double CapsuleHalfHeightCm,double PublicationUtcSec);
private:
    UPROPERTY(Transient) TObjectPtr<URedlineBridgeSubsystem> Bridge;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Idle;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Walk;
    UPROPERTY(Transient) TObjectPtr<URedlineLocomotionInstance> Locomotion;
    FDelegateHandle TopicHandle;
    TArray<FVector2D> SpeedTable;
    double UnknownSpeedFactor=0,CellSpeedFactor=0,LastPoseAt=0,LastQueryAt=0,ProbeStart=-1,ProbeSeconds=0;
    FVector LastQueriedMap=FVector::ZeroVector;
    bool bQueryPending=false;
    FString PoseLog;
    double MissionReceipt=-1,LastInteractionAt=-10;
    double NextAnimationLog=0;
    double ForwardPulse=-1,BackPulse=-1,RightPulse=-1,LeftPulse=-1;
    double SprintPulse=-1,SprintMultiplier=1,SprintCapMps=0;
    void AdvanceMission();
    bool LoadMovementProfile();
    double WalkingSpeed(double Grade) const;
    void QueryCell(FVector Map);
    void OnState(const FString& Topic,const TSharedPtr<FJsonObject>& Json);
};
