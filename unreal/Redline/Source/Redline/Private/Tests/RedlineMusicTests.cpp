#if WITH_DEV_AUTOMATION_TESTS

#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/AutomationTest.h"
#include "RedlineBridgeSubsystem.h"
#include "RedlineMusicSettings.h"
#include "RedlineMusicSubsystem.h"
#include "RedlineSettings.h"
#include "Sound/SoundWave.h"
#include "Tests/AutomationCommon.h"
#include "UObject/UObjectGlobals.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineMusicPhaseRoutingTest, "Redline.Music.PhaseRouting",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FRedlineMusicPhaseRoutingTest::RunTest(const FString& Parameters)
{
    for (const uint8 Phase : {uint8(0), uint8(1), uint8(2), uint8(3), uint8(6)})
    {
        TestEqual(FString::Printf(TEXT("phase %u uses exploration take"), Phase),
            URedlineMusicSubsystem::RouteMissionPhase(Phase), ERedlineMusicBed::Exploration);
    }
    for (const uint8 Phase : {uint8(4), uint8(5)})
    {
        TestEqual(FString::Printf(TEXT("phase %u uses crisis take"), Phase),
            URedlineMusicSubsystem::RouteMissionPhase(Phase), ERedlineMusicBed::Crisis);
    }
    TestEqual(TEXT("unknown phase is silent"), URedlineMusicSubsystem::RouteMissionPhase(255),
        ERedlineMusicBed::Silent);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineMusicContinuationDelayTest, "Redline.Music.ContinuationDelay",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FRedlineMusicContinuationDelayTest::RunTest(const FString& Parameters)
{
    // A ~60 s take must keep playing through a several-minute walk: a fresh pass of the same take is
    // crossfaded in before the generated ending, so the unauditioned loop seam is never heard.
    TestEqual(TEXT("exploration take continues before its end"),
        URedlineMusicSubsystem::ContinuationDelaySeconds(59.63f, 4.0f), 55.63f, 1.0e-3f);
    TestEqual(TEXT("crisis take continues before its end"),
        URedlineMusicSubsystem::ContinuationDelaySeconds(62.41f, 4.0f), 58.41f, 1.0e-3f);
    TestEqual(TEXT("a take shorter than two crossfades continues at its midpoint"),
        URedlineMusicSubsystem::ContinuationDelaySeconds(6.0f, 4.0f), 3.0f, 1.0e-3f);
    TestEqual(TEXT("an unknown duration never schedules a continuation"),
        URedlineMusicSubsystem::ContinuationDelaySeconds(0.0f, 4.0f), 0.0f);
    TestEqual(TEXT("a non-finite duration never schedules a continuation"),
        URedlineMusicSubsystem::ContinuationDelaySeconds(NAN, 4.0f), 0.0f);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineMusicAssetsTest, "Redline.Music.Assets",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FRedlineMusicAssetsTest::RunTest(const FString& Parameters)
{
    const URedlineMusicSettings* Settings = GetDefault<URedlineMusicSettings>();
    TestNotNull(TEXT("exploration track resolves from DefaultGame.ini"), Settings->ExplorationTrack.LoadSynchronous());
    TestNotNull(TEXT("crisis track resolves from DefaultGame.ini"), Settings->CrisisTrack.LoadSynchronous());

    const TCHAR* Paths[] = {
        TEXT("/Game/Audio/Music/SW_REDLINE_SessizYorunge_Exploration.SW_REDLINE_SessizYorunge_Exploration"),
        TEXT("/Game/Audio/Music/SW_REDLINE_SessizYorunge_Crisis.SW_REDLINE_SessizYorunge_Crisis")
    };

    for (const TCHAR* Path : Paths)
    {
        USoundWave* Wave = Cast<USoundWave>(StaticLoadObject(USoundWave::StaticClass(), nullptr, Path));
        TestNotNull(FString::Printf(TEXT("sound wave exists: %s"), Path), Wave);
        if (Wave)
        {
            TestTrue(FString::Printf(TEXT("duration is plausible: %s"), Path),
                Wave->GetDuration() >= 55.0f && Wave->GetDuration() <= 65.0f);
            TestFalse(FString::Printf(TEXT("unverified loop remains disabled: %s"), Path), Wave->bLooping != 0);
        }
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineMusicRuntimePhaseRoutingTest, "Redline.Music.RuntimePhaseRouting",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FRedlineMusicRuntimePhaseRoutingTest::RunTest(const FString& Parameters)
{
    URedlineSettings* BridgeSettings = GetMutableDefault<URedlineSettings>();
    URedlineMusicSettings* MusicSettings = GetMutableDefault<URedlineMusicSettings>();
    TGuardValue<bool> AutoConnectGuard(BridgeSettings->bAutoConnect, false);
    TGuardValue<float> VolumeGuard(MusicSettings->MusicVolume, 0.0f);
    TGuardValue<float> CrossfadeGuard(MusicSettings->CrossfadeSeconds, 0.0f);
    TGuardValue<float> ContinuationGuard(MusicSettings->ContinuationCrossfadeSeconds, 0.0f);
    TGuardValue<bool> AutoStartGuard(MusicSettings->bAutoStart, true);

    // The wrapper creates a real game-type UWorld and UGameInstance. Audio stays muted for automation,
    // but the UAudioComponent playback state and the bridge delegate path are exercised end to end.
    FTestWorldWrapper TestWorld;
    if (!TestWorld.CreateTestWorld(EWorldType::Game) || !TestWorld.BeginPlayInTestWorld())
    {
        TestWorld.ForwardErrorMessages(this);
        AddError(TEXT("Could not start the presentation-music game world."));
        return false;
    }

    UWorld* World = TestWorld.GetTestWorld();
    UGameInstance* GameInstance = World ? World->GetGameInstance() : nullptr;
    URedlineMusicSubsystem* Music = World ? World->GetSubsystem<URedlineMusicSubsystem>() : nullptr;
    URedlineBridgeSubsystem* Bridge = GameInstance ? GameInstance->GetSubsystem<URedlineBridgeSubsystem>() : nullptr;

    TestNotNull(TEXT("game world owns the music subsystem"), Music);
    TestNotNull(TEXT("game instance owns the ROS presentation bridge"), Bridge);
    if (!Music || !Bridge)
    {
        return false;
    }

    TestEqual(TEXT("briefing auto-starts exploration take"), Music->GetActiveMusicBed(),
        ERedlineMusicBed::Exploration);
    TestTrue(TEXT("exploration take has a live (muted) audio component"), Music->IsMusicPlaying());
    TestTrue(TEXT("a playing take schedules its own continuation"), Music->IsContinuationScheduled());
    TestTrue(TEXT("continuation crossfades into a fresh pass"), Music->ContinueActiveBed());
    TestEqual(TEXT("continuation keeps the same take"), Music->GetActiveMusicBed(), ERedlineMusicBed::Exploration);
    TestTrue(TEXT("the fresh pass is playing"), Music->IsMusicPlaying());
    TestTrue(TEXT("the fresh pass schedules the next continuation"), Music->IsContinuationScheduled());

    const int32 InitialMessages = Bridge->ReceivedCount;
    Bridge->HandleEnvelope(TEXT(R"({"op":"publish","topic":"/redline/mission/state","msg":{"phase":5}})"));
    TestEqual(TEXT("contingency switches to crisis take"), Music->GetActiveMusicBed(), ERedlineMusicBed::Crisis);
    TestTrue(TEXT("crisis take has a live (muted) audio component"), Music->IsMusicPlaying());

    Bridge->HandleEnvelope(TEXT(R"({"op":"publish","topic":"/redline/mission/state","msg":{"phase":4}})"));
    TestEqual(TEXT("return keeps the crisis take"), Music->GetActiveMusicBed(), ERedlineMusicBed::Crisis);

    Bridge->HandleEnvelope(TEXT(R"({"op":"publish","topic":"/redline/mission/state","msg":{"phase":6}})"));
    TestEqual(TEXT("debrief returns to exploration take"), Music->GetActiveMusicBed(),
        ERedlineMusicBed::Exploration);
    TestTrue(TEXT("restored exploration take is playing"), Music->IsMusicPlaying());
    TestEqual(TEXT("all mission-state envelopes traversed the subscribed bridge path"),
        Bridge->ReceivedCount, InitialMessages + 3);

    TestTrue(TEXT("silence is a valid bed"), Music->SetMusicBed(ERedlineMusicBed::Silent));
    TestFalse(TEXT("silence has no continuation"), Music->IsContinuationScheduled());
    TestFalse(TEXT("nothing to continue while silent"), Music->ContinueActiveBed());

    TestWorld.ForwardErrorMessages(this);
    return true;
}

#endif
