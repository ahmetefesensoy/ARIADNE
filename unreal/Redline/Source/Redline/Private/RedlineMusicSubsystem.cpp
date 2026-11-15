#include "RedlineMusicSubsystem.h"

#include "RedlineBridgeSubsystem.h"
#include "RedlineMusicSettings.h"
#include "Components/AudioComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"

DEFINE_LOG_CATEGORY_STATIC(LogRedlineMusic, Log, All);

namespace RedlineMusic
{
constexpr uint8 Briefing = 0;
constexpr uint8 Precursor = 1;
constexpr uint8 Traverse = 2;
constexpr uint8 StationScience = 3;
constexpr uint8 Return = 4;
constexpr uint8 Contingency = 5;
constexpr uint8 Debrief = 6;
const TCHAR* MissionStateTopic = TEXT("/redline/mission/state");
}

bool URedlineMusicSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
    return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void URedlineMusicSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);

    const URedlineMusicSettings* Settings = GetDefault<URedlineMusicSettings>();
    ExplorationSound = Settings->ExplorationTrack.LoadSynchronous();
    CrisisSound = Settings->CrisisTrack.LoadSynchronous();

    if (!ExplorationSound || !CrisisSound)
    {
        UE_LOG(LogRedlineMusic, Error, TEXT("Music assets are missing: exploration=%s crisis=%s"),
            ExplorationSound ? TEXT("ready") : TEXT("missing"), CrisisSound ? TEXT("ready") : TEXT("missing"));
    }

    if (UGameInstance* GameInstance = InWorld.GetGameInstance())
    {
        Bridge = GameInstance->GetSubsystem<URedlineBridgeSubsystem>();
        if (Bridge)
        {
            Bridge->Subscribe(RedlineMusic::MissionStateTopic, TEXT("redline_msgs/msg/MissionState"), 0, 5.0);
            TopicDelegateHandle = Bridge->OnTopic.AddUObject(this, &URedlineMusicSubsystem::HandleTopic);
        }
    }

    if (Settings->bAutoStart)
    {
        SetMusicBed(ERedlineMusicBed::Exploration);
    }
}

void URedlineMusicSubsystem::OnWorldEndPlay(UWorld& InWorld)
{
    UnbindBridge();
    StopAndReleaseAudio();
    Super::OnWorldEndPlay(InWorld);
}

void URedlineMusicSubsystem::Deinitialize()
{
    UnbindBridge();
    StopAndReleaseAudio();
    ExplorationSound = nullptr;
    CrisisSound = nullptr;
    Super::Deinitialize();
}

ERedlineMusicBed URedlineMusicSubsystem::RouteMissionPhase(const uint8 Phase)
{
    switch (Phase)
    {
    case RedlineMusic::Briefing:
    case RedlineMusic::Precursor:
    case RedlineMusic::Traverse:
    case RedlineMusic::StationScience:
    case RedlineMusic::Debrief:
        return ERedlineMusicBed::Exploration;
    case RedlineMusic::Return:
    case RedlineMusic::Contingency:
        return ERedlineMusicBed::Crisis;
    default:
        return ERedlineMusicBed::Silent;
    }
}

void URedlineMusicSubsystem::ApplyMissionPhase(const uint8 Phase)
{
    SetMusicBed(RouteMissionPhase(Phase));
}

bool URedlineMusicSubsystem::IsMusicPlaying() const
{
    return ActiveComponent && ActiveComponent->IsPlaying();
}
void URedlineMusicSubsystem::SetPresentationDuck(float Value)
{
    PresentationDuck=FMath::IsFinite(Value) ? FMath::Clamp(Value,0.f,1.f) : 1.f;
    if(ActiveComponent)ActiveComponent->AdjustVolume(.25f,GetDefault<URedlineMusicSettings>()->MusicVolume*PresentationDuck);
}

bool URedlineMusicSubsystem::SetMusicBed(const ERedlineMusicBed Bed)
{
    if (Bed == ActiveBed)
    {
        return true;
    }

    const URedlineMusicSettings* Settings = GetDefault<URedlineMusicSettings>();
    if (Bed == ERedlineMusicBed::Silent)
    {
        ClearContinuation();
        if (ActiveComponent && ActiveComponent->IsPlaying())
        {
            ActiveComponent->FadeOut(Settings->CrossfadeSeconds, 0.0f, EAudioFaderCurve::Sin);
        }
        ActiveComponent = nullptr;
        ActiveBed = Bed;
        return true;
    }

    USoundBase* Sound = SoundForBed(Bed);
    if (!Sound)
    {
        UE_LOG(LogRedlineMusic, Warning, TEXT("Cannot switch music bed %d because its sound asset is unavailable."),
            static_cast<int32>(Bed));
        return false;
    }

    UAudioComponent* NextComponent = PrepareNextComponent(Sound);
    if (!NextComponent)
    {
        UE_LOG(LogRedlineMusic, Warning, TEXT("Audio playback is unavailable in world %s."), *GetNameSafe(GetWorld()));
        return false;
    }

    if (ActiveComponent && ActiveComponent->IsPlaying())
    {
        ActiveComponent->FadeOut(Settings->CrossfadeSeconds, 0.0f, EAudioFaderCurve::Sin);
    }
    NextComponent->FadeIn(Settings->CrossfadeSeconds, Settings->MusicVolume*PresentationDuck, 0.0f, EAudioFaderCurve::Sin);
    ActiveComponent = NextComponent;
    ActiveBed = Bed;
    ScheduleContinuation(Sound);
    UE_LOG(LogRedlineMusic, Display, TEXT("Presentation music switched to bed %d."), static_cast<int32>(Bed));
    return true;
}

bool URedlineMusicSubsystem::ContinueActiveBed()
{
    USoundBase* Sound = SoundForBed(ActiveBed);
    if (ActiveBed == ERedlineMusicBed::Silent || !Sound)
    {
        return false;
    }
    UAudioComponent* NextComponent = PrepareNextComponent(Sound);
    if (!NextComponent)
    {
        return false;
    }
    const float Fade = GetDefault<URedlineMusicSettings>()->ContinuationCrossfadeSeconds;
    if (ActiveComponent && ActiveComponent->IsPlaying())
    {
        ActiveComponent->FadeOut(Fade, 0.0f, EAudioFaderCurve::Sin);
    }
    NextComponent->FadeIn(Fade, GetDefault<URedlineMusicSettings>()->MusicVolume * PresentationDuck, 0.0f,
        EAudioFaderCurve::Sin);
    ActiveComponent = NextComponent;
    ScheduleContinuation(Sound);
    return true;
}

bool URedlineMusicSubsystem::IsContinuationScheduled() const
{
    const UWorld* World = GetWorld();
    return World && World->GetTimerManager().IsTimerActive(ContinuationTimer);
}

float URedlineMusicSubsystem::ContinuationDelaySeconds(const float TrackSeconds, const float CrossfadeSeconds)
{
    if (!FMath::IsFinite(TrackSeconds) || TrackSeconds <= 0.0f)
    {
        return 0.0f;
    }
    const float Fade = FMath::IsFinite(CrossfadeSeconds) ? FMath::Max(CrossfadeSeconds, 0.0f) : 0.0f;
    // A take shorter than two crossfades continues at its midpoint instead of overlapping itself.
    return TrackSeconds > 2.0f * Fade ? TrackSeconds - Fade : 0.5f * TrackSeconds;
}

USoundBase* URedlineMusicSubsystem::SoundForBed(const ERedlineMusicBed Bed) const
{
    switch (Bed)
    {
    case ERedlineMusicBed::Exploration:
        return ExplorationSound.Get();
    case ERedlineMusicBed::Crisis:
        return CrisisSound.Get();
    default:
        return nullptr;
    }
}

void URedlineMusicSubsystem::ScheduleContinuation(const USoundBase* Sound)
{
    ClearContinuation();
    UWorld* World = GetWorld();
    const float Delay = Sound ? ContinuationDelaySeconds(Sound->GetDuration(),
        GetDefault<URedlineMusicSettings>()->ContinuationCrossfadeSeconds) : 0.0f;
    if (World && Delay > 0.0f)
    {
        World->GetTimerManager().SetTimer(ContinuationTimer, this, &URedlineMusicSubsystem::HandleContinuationTimer,
            Delay, false);
    }
}

void URedlineMusicSubsystem::ClearContinuation()
{
    if (UWorld* World = GetWorld())
    {
        World->GetTimerManager().ClearTimer(ContinuationTimer);
    }
    ContinuationTimer.Invalidate();
}

void URedlineMusicSubsystem::HandleContinuationTimer()
{
    ContinueActiveBed();
}

UAudioComponent* URedlineMusicSubsystem::PrepareNextComponent(USoundBase* Sound)
{
    TObjectPtr<UAudioComponent>& Next = ActiveComponent == ComponentA ? ComponentB : ComponentA;
    if (!Next)
    {
        Next = UGameplayStatics::CreateSound2D(GetWorld(), Sound, 0.0f, 1.0f, 0.0f, nullptr, false, false);
    }
    else
    {
        Next->Stop();
        Next->SetSound(Sound);
    }
    return Next.Get();
}

void URedlineMusicSubsystem::HandleTopic(const FString& Topic, const TSharedPtr<FJsonObject>& Message)
{
    if (Topic != RedlineMusic::MissionStateTopic || !Message)
    {
        return;
    }

    double PhaseValue = 0.0;
    if (!Message->TryGetNumberField(TEXT("phase"), PhaseValue) || !FMath::IsFinite(PhaseValue)
        || PhaseValue < 0.0 || PhaseValue > static_cast<double>(MAX_uint8)
        || !FMath::IsNearlyEqual(PhaseValue, FMath::RoundToDouble(PhaseValue)))
    {
        UE_LOG(LogRedlineMusic, Warning, TEXT("Ignored malformed mission phase in presentation stream."));
        return;
    }
    ApplyMissionPhase(static_cast<uint8>(PhaseValue));
}

void URedlineMusicSubsystem::UnbindBridge()
{
    if (Bridge && TopicDelegateHandle.IsValid())
    {
        Bridge->OnTopic.Remove(TopicDelegateHandle);
    }
    TopicDelegateHandle.Reset();
    Bridge = nullptr;
}

void URedlineMusicSubsystem::StopAndReleaseAudio()
{
    ClearContinuation();
    for (UAudioComponent* Component : {ComponentA.Get(), ComponentB.Get()})
    {
        if (Component)
        {
            Component->Stop();
            Component->DestroyComponent();
        }
    }
    ComponentA = nullptr;
    ComponentB = nullptr;
    ActiveComponent = nullptr;
    ActiveBed = ERedlineMusicBed::Silent;
}
