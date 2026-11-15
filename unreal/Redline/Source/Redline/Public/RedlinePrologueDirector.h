#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlinePrologueDirector.generated.h"
class ARedlineAstronautCharacter;
class APlayerController;
class UCameraComponent;
class USkeletalMeshComponent;
class UAudioComponent;
class USoundBase;
class UAnimSequence;
class UMaterialInstanceDynamic;
class URedlineMusicSubsystem;
class ARedlineHabitatDoor;

/** Local, skippable staging. Never advances ROS phase, PET, resources or robot control. */
UCLASS()
class REDLINE_API ARedlinePrologueDirector : public AActor
{
    GENERATED_BODY()
public:
    ARedlinePrologueDirector();
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    void SkipCurrent();
    void SkipAll();
    bool IsCinematic() const {return bPlaying || bResting;}
    bool IsResting() const {return bResting;}
    FString Title() const;
    FString Caption() const;
    bool CanRest() const;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<USkeletalMeshComponent> NarrativeBody;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UAudioComponent> Narrator;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UAudioComponent> Jazz;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UAudioComponent> Foley;
private:
    friend class FRedlinePrologueSkip;
    struct FShot {FString Id,Title,Subtitle;double Duration=10;int32 Phase=-1;};
    TArray<FShot> Shots;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundBase>> Voices;
    UPROPERTY(Transient) TObjectPtr<USoundBase> JazzSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> PressureSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> DoorSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ReadySound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> LandingSound;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> SeatedIdle;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> StandingIdle;
    UPROPERTY(Transient) TObjectPtr<ARedlineAstronautCharacter> Astronaut;
    UPROPERTY(Transient) TObjectPtr<URedlineMusicSubsystem> Music;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ScreenMaterial;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> DustMaterials;
    TWeakObjectPtr<APlayerController> Player;
    TWeakObjectPtr<AActor> Seat,Record,Door,InnerDoor,DataScreen,DataText,Lander,LandingTarget;
    TArray<TWeakObjectPtr<AActor>> DustActors;
    TMap<FName,TWeakObjectPtr<AActor>> Markers;
    TMap<FName,TWeakObjectPtr<ARedlineHabitatDoor>> AnimatedDoors;
    FVector DoorClosed=FVector::ZeroVector,InnerDoorClosed=FVector::ZeroVector;
    int32 ShotIndex=0,LastObservedPhase=-1;
    double ShotStarted=0,LastDataRefresh=-1;
    bool bPlaying=false,bResting=false,bFinished=false,bDoorSoundPlayed=false,bContentReady=false,bEnding=false,bPhaseClip=false;
    void DiscoverScene();
    bool ReadScript();
    bool HasRequiredScene() const;
    void StartSequence();
    void StartMissionClip(int32 Index);
    void UpdateRooms(float Delta);
    void SelectShot(int32 Index);
    void Finish();
    void SetResting(bool Resting);
    void SetCamera(const FString& Id,double Alpha);
    void SetLandingProgress(double Alpha);
    void SetDustAmount(float Amount);
    void StopPresentationAudio();
    void SetBody(bool Seated);
    void UpdateDataScreen();
};
