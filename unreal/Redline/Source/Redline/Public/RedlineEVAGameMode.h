#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/HUD.h"
#include "RedlineEVAGameMode.generated.h"
class ARedlineAstronautCharacter;
class ARedlineOverlay;
class ARedlineCampaignConsole;
class URedlineBridgeSubsystem;
class UMediaPlayer;
class UMediaTexture;
class UFileMediaSource;

/** Read-only mission journal and field HUD. Mission progression remains in ROS. */
UCLASS()
class REDLINE_API ARedlineEVAHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
    /** Science and robot tasks get a short briefing before the player starts them. */
    static bool NeedsBriefing(const FString& Kind);
    /** "How it works" video for a task kind under Content/Movies, or empty when there is none. */
    static FString BriefingVideoFor(const FString& Kind);
    /** One or two lines: what the instrument does and why (presentation; results come from ROS). */
    static FString BriefingPurposeFor(const FString& Kind);
    bool IsBriefingVisible() const {return bBriefingVisible;}
private:
    bool bMapVisible=true;
    FString BriefedTask;
    bool bBriefingVisible=false;
    UPROPERTY(Transient) TObjectPtr<UMediaPlayer> BriefingPlayer;
    UPROPERTY(Transient) TObjectPtr<UMediaTexture> BriefingTexture;
    UPROPERTY(Transient) TObjectPtr<UFileMediaSource> BriefingSource;
    void UpdateBriefing(ARedlineCampaignConsole* Campaign,APlayerController* PC);
    void CloseBriefing();
    void DrawBriefing(const ARedlineCampaignConsole* Campaign,const ARedlineAstronautCharacter* Astronaut);
    void DrawControlBar(const URedlineBridgeSubsystem* Bridge,const ARedlineCampaignConsole* Campaign);
    bool bMissionJournalVisible=false;
    void DrawMissionJournal(const ARedlineAstronautCharacter* Astronaut,const ARedlineOverlay* View,const URedlineBridgeSubsystem* Bridge);
    void DrawObjectiveMarker(const ARedlineAstronautCharacter* Astronaut);
    FVector CachedObjective=FVector::ZeroVector,CachedObjectiveSurface=FVector::ZeroVector;
    double NextObjectiveTrace=-1;
    bool bHasObjectiveHeight=false;
};

UCLASS()
class REDLINE_API ARedlineEVAGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    ARedlineEVAGameMode();
    virtual void StartPlay() override;
};
