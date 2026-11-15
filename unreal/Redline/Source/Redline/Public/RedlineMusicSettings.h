#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "RedlineMusicSettings.generated.h"

class USoundBase;

/** Presentation-only music configuration. ROS/Gazebo remains the mission and physics authority. */
UCLASS(Config=Game, DefaultConfig, meta=(DisplayName="REDLINE Presentation Music"))
class REDLINE_API URedlineMusicSettings : public UDeveloperSettings
{
    GENERATED_BODY()

public:
    UPROPERTY(Config, EditAnywhere, Category="Tracks")
    TSoftObjectPtr<USoundBase> ExplorationTrack;

    UPROPERTY(Config, EditAnywhere, Category="Tracks")
    TSoftObjectPtr<USoundBase> CrisisTrack;

    UPROPERTY(Config, EditAnywhere, Category="Playback", meta=(ClampMin="0.0", ClampMax="1.0"))
    float MusicVolume = 0.28f;

    UPROPERTY(Config, EditAnywhere, Category="Playback", meta=(ClampMin="0.0", Units="s"))
    float CrossfadeSeconds = 2.5f;

    /** A take is crossfaded into a fresh pass of itself this long before its end, so music keeps playing
     *  through long walks without the unauditioned loop seam (the waves stay non-looping). */
    UPROPERTY(Config, EditAnywhere, Category="Playback", meta=(ClampMin="0.0", Units="s"))
    float ContinuationCrossfadeSeconds = 4.0f;

    UPROPERTY(Config, EditAnywhere, Category="Playback")
    bool bAutoStart = true;
};
