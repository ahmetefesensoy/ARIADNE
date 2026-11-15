#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineHabitatDoor.generated.h"

class UStaticMeshComponent;
class UPointLightComponent;
class UAudioComponent;
class USoundBase;

enum class ERedlineHabitatDoorState : uint8 {Closed,Unlocking,Opening,Open,Closing,Latching};

/** SCENARIO human/query-only sliding door. No ROS, robot or pressure authority. */
UCLASS()
class REDLINE_API ARedlineHabitatDoor : public AActor
{
    GENERATED_BODY()
public:
    ARedlineHabitatDoor();
    virtual void Tick(float DeltaSeconds) override;
    /** Retain the source marker/Tripo shell; hide only its obsolete single panel. */
    bool InitializeFromMarker(AActor* Source);
    bool ConfigureOpening(const FTransform& ClosedTransform,FVector SizeCm);
    void SetAutomaticOpen(bool Enabled) {bAutomaticOpen=Enabled;}
    void RequestPresentationOpen(bool Open) {bPresentationOpen=Open;}
    bool IsPassageBlocked() const;
    double GetOpenness() const {return Openness;}
    double GetUnlockProgress() const {return UnlockProgress;}
    ERedlineHabitatDoorState GetDoorState() const {return State;}
    int32 GetSafetyReopenCount() const {return SafetyReopenCount;}
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UStaticMeshComponent> LeftPanel;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UStaticMeshComponent> RightPanel;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UStaticMeshComponent> CenterSeal;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UAudioComponent> DoorAudio;
private:
    friend class FRedlineDoorAnimation;
    friend class FRedlineDoorSafety;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UStaticMeshComponent> FrameLeft;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UStaticMeshComponent> FrameRight;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UStaticMeshComponent> FrameTop;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UStaticMeshComponent> LeftLock;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UStaticMeshComponent> RightLock;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UStaticMeshComponent> AmberLens;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UStaticMeshComponent> ReadyLens;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UPointLightComponent> WarningLight;
    UPROPERTY(Transient) TObjectPtr<USoundBase> SlideSound;
    TWeakObjectPtr<AActor> SourceMarker;
    FVector OpeningSize=FVector(10,210,240);
    ERedlineHabitatDoorState State=ERedlineHabitatDoorState::Closed;
    double Openness=0,UnlockProgress=0,StateElapsed=0,HoldRemaining=0,VisualElapsed=0;
    int32 SafetyReopenCount=0;
    bool bConfigured=false,bAutomaticOpen=true,bPresentationOpen=false;
    bool HumanApproaching() const;
    void AdvanceAnimation(float DeltaSeconds,bool OpenRequest,bool PassageBlocked);
    void EnterState(ERedlineHabitatDoorState NewState);
    void ApplyPose();
};
