#pragma once

#include "CoreMinimal.h"
#include "Engine/TimerHandle.h"
#include "Subsystems/WorldSubsystem.h"
#include "RedlineMusicSubsystem.generated.h"

class FJsonObject;
class UAudioComponent;
class URedlineBridgeSubsystem;
class USoundBase;

UENUM(BlueprintType)
enum class ERedlineMusicBed : uint8
{
    Silent,
    Exploration,
    Crisis
};

/**
 * Routes the two selected score takes from mission phase messages.
 * Music is presentation-only and cannot affect ROS mission/control state.
 */
UCLASS()
class REDLINE_API URedlineMusicSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()

public:
    virtual void Deinitialize() override;
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
    virtual void OnWorldEndPlay(UWorld& InWorld) override;

    UFUNCTION(BlueprintCallable, Category="REDLINE|Music")
    void ApplyMissionPhase(uint8 Phase);

    UFUNCTION(BlueprintCallable, Category="REDLINE|Music")
    bool SetMusicBed(ERedlineMusicBed Bed);

    UFUNCTION(BlueprintPure, Category="REDLINE|Music")
    ERedlineMusicBed GetActiveMusicBed() const { return ActiveBed; }

    UFUNCTION(BlueprintPure, Category="REDLINE|Music")
    bool IsMusicPlaying() const;
    /** Presentation duck for narration/local record player; no mission effects. */
    UFUNCTION(BlueprintCallable,Category="REDLINE|Music")
    void SetPresentationDuck(float Multiplier);

    /** Crossfade the active take into a fresh pass of itself (presentation only). False when silent. */
    UFUNCTION(BlueprintCallable, Category="REDLINE|Music")
    bool ContinueActiveBed();

    UFUNCTION(BlueprintPure, Category="REDLINE|Music")
    bool IsContinuationScheduled() const;

    static ERedlineMusicBed RouteMissionPhase(uint8 Phase);

    /** Seconds after a pass starts when the next pass is crossfaded in; 0 = never (unknown duration). */
    static float ContinuationDelaySeconds(float TrackSeconds, float CrossfadeSeconds);

protected:
    virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

private:
    void HandleTopic(const FString& Topic, const TSharedPtr<FJsonObject>& Message);
    UAudioComponent* PrepareNextComponent(USoundBase* Sound);
    USoundBase* SoundForBed(ERedlineMusicBed Bed) const;
    void ScheduleContinuation(const USoundBase* Sound);
    void ClearContinuation();
    void HandleContinuationTimer();
    void UnbindBridge();
    void StopAndReleaseAudio();

    UPROPERTY(Transient)
    TObjectPtr<URedlineBridgeSubsystem> Bridge;

    UPROPERTY(Transient)
    TObjectPtr<USoundBase> ExplorationSound;

    UPROPERTY(Transient)
    TObjectPtr<USoundBase> CrisisSound;

    UPROPERTY(Transient)
    TObjectPtr<UAudioComponent> ComponentA;

    UPROPERTY(Transient)
    TObjectPtr<UAudioComponent> ComponentB;

    UPROPERTY(Transient)
    TObjectPtr<UAudioComponent> ActiveComponent;

    FDelegateHandle TopicDelegateHandle;
    FTimerHandle ContinuationTimer;
    ERedlineMusicBed ActiveBed = ERedlineMusicBed::Silent;
    float PresentationDuck=1.f;
};
