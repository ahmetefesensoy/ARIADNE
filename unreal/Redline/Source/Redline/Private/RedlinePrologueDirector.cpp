#include "RedlinePrologueDirector.h"
#include "RedlineCampaignConsole.h"
#include "RedlineHabitatDoor.h"
#include "RedlineAstronautCharacter.h"
#include "RedlineMusicSubsystem.h"
#include "RedlineOverlay.h"
#include "RedlineTypes.h"
#include "RedlineBridgeSubsystem.h"
#include "RedlineStaleMonitor.h"
#include "Engine/GameInstance.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "UnrealClient.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Animation/AnimSequence.h"
#include "Sound/SoundBase.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "InputCoreTypes.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
DEFINE_LOG_CATEGORY_STATIC(LogRedlinePrologue,Log,All);

ARedlinePrologueDirector::ARedlinePrologueDirector()
{
    PrimaryActorTick.bCanEverTick=true;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("PresentationRoot"));
    Camera=CreateDefaultSubobject<UCameraComponent>(TEXT("StoryCamera"));Camera->SetupAttachment(RootComponent);Camera->SetFieldOfView(62);
    NarrativeBody=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("CinematicOnlyAstronaut"));NarrativeBody->SetupAttachment(RootComponent);
    NarrativeBody->SetCollisionEnabled(ECollisionEnabled::NoCollision);NarrativeBody->SetSimulatePhysics(false);NarrativeBody->SetReceivesDecals(false);
    NarrativeBody->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    NarrativeBody->SetHiddenInGame(true);
    Narrator=CreateDefaultSubobject<UAudioComponent>(TEXT("TurkishNarration"));Jazz=CreateDefaultSubobject<UAudioComponent>(TEXT("LocalRecordPlayer"));Foley=CreateDefaultSubobject<UAudioComponent>(TEXT("AirlockFoley"));
    for(UAudioComponent* Audio:{Narrator.Get(),Jazz.Get(),Foley.Get()}){Audio->bAutoActivate=false;Audio->bIsUISound=true;Audio->SetupAttachment(RootComponent);}
    Narrator->SetVolumeMultiplier(.85f);Jazz->SetVolumeMultiplier(1.f);Foley->SetVolumeMultiplier(.45f);
}
bool ARedlinePrologueDirector::ReadScript()
{
    FString Text;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("Prologue/script.json"))) || Text.Len()>32768)return false;
    const auto J=FRedlineJson::Parse(Text);const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
    Shots.Reset();Voices.Reset();
    if(!J || !J->TryGetArrayField(TEXT("shots"),Values) || Values->Num()!=5)return false;
    const TArray<FString> Order={TEXT("landing"),TEXT("rest"),TEXT("data"),TEXT("airlock"),TEXT("ready")};
    for(int32 I=0;I<Values->Num();++I)
    {
        if(!(*Values)[I] || (*Values)[I]->Type!=EJson::Object)return false;auto O=(*Values)[I]->AsObject();FShot S;
        if(!O->TryGetStringField(TEXT("id"),S.Id) || S.Id!=Order[I] || !O->TryGetStringField(TEXT("title"),S.Title) ||
           !O->TryGetStringField(TEXT("subtitle"),S.Subtitle) || !O->TryGetNumberField(TEXT("duration_s"),S.Duration) || !FMath::IsFinite(S.Duration) || S.Duration<1 || S.Duration>60)return false;
        Shots.Add(S);
        Voices.Add(LoadObject<USoundBase>(nullptr,*(TEXT("/Game/Prologue/Audio/VO_")+S.Id+TEXT(".VO_")+S.Id)));
        if(!Voices.Last())return false;
    }
    const TArray<TSharedPtr<FJsonValue>>* Intros=nullptr;
    if(J->TryGetArrayField(TEXT("mission_intros"),Intros))
    {
        if(Intros->Num()>8)return false;TSet<int32> Phases;
        for(const auto& Value:*Intros)
        {
            if(!Value || Value->Type!=EJson::Object)return false;const auto O=Value->AsObject();FShot S;double Phase;
            if(!O->TryGetStringField(TEXT("id"),S.Id) || !S.Id.StartsWith(TEXT("mission_")) || S.Id.Contains(TEXT("/")) || S.Id.Contains(TEXT(".")) ||
               !O->TryGetStringField(TEXT("title"),S.Title) || !O->TryGetStringField(TEXT("subtitle"),S.Subtitle) ||
               !O->TryGetNumberField(TEXT("duration_s"),S.Duration) || !FMath::IsFinite(S.Duration) || S.Duration<1 || S.Duration>60 ||
               !O->TryGetNumberField(TEXT("phase"),Phase) || !FMath::IsFinite(Phase) || Phase!=FMath::FloorToDouble(Phase) || (Phase!=2 && Phase!=3 && Phase!=4 && Phase!=6))return false;
            S.Phase=static_cast<int32>(Phase);if(Phases.Contains(S.Phase))return false;Phases.Add(S.Phase);
            Shots.Add(S);Voices.Add(LoadObject<USoundBase>(nullptr,*(TEXT("/Game/Prologue/Audio/VO_")+S.Id+TEXT(".VO_")+S.Id)));
            if(!Voices.Last())return false;
        }
    }
    return true;
}
void ARedlinePrologueDirector::DiscoverScene()
{
    for(TActorIterator<AActor> It(GetWorld());It;++It)for(const FName& Tag:It->Tags)
    {
        if(Tag.ToString().StartsWith(TEXT("prologue_")))Markers.Add(Tag,*It);
    }
    auto Find=[&](const TCHAR* Name){return Markers.FindRef(FName(Name));};
    Seat=Find(TEXT("prologue_seat"));Record=Find(TEXT("prologue_record"));Door=Find(TEXT("prologue_outer_door"));InnerDoor=Find(TEXT("prologue_inner_door"));
    DataScreen=Find(TEXT("prologue_data_screen"));DataText=Find(TEXT("prologue_data_text"));
    Lander=Find(TEXT("prologue_lander"));LandingTarget=Find(TEXT("prologue_landing_target"));
    for(int32 I=0;I<4;++I)if(auto A=Markers.FindRef(FName(FString::Printf(TEXT("prologue_dust_%d"),I)));A.IsValid())
    {
        DustActors.Add(A);
        if(auto* Mesh=A->FindComponentByClass<UStaticMeshComponent>())DustMaterials.Add(Mesh->CreateDynamicMaterialInstance(0));
    }
    if(Door.IsValid())DoorClosed=Door->GetActorLocation();if(InnerDoor.IsValid())InnerDoorClosed=InnerDoor->GetActorLocation();
    // Existing tagged actors stay as immutable layout markers. Replace each
    // single cube visually and for human queries, without editing the Tripo shell.
    TMap<AActor*,ARedlineHabitatDoor*> Replacements;
    for(const auto& Pair:Markers)
    {
        const FString Tag=Pair.Key.ToString();auto* Source=Pair.Value.Get();
        if(!Source || !(Tag.StartsWith(TEXT("prologue_room_door_")) || Tag==TEXT("prologue_inner_door") || Tag==TEXT("prologue_outer_door")))continue;
        ARedlineHabitatDoor* Replacement=Replacements.FindRef(Source);
        if(!Replacement)
        {
            FActorSpawnParameters Params;Params.Owner=this;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            Replacement=GetWorld()->SpawnActor<ARedlineHabitatDoor>(ARedlineHabitatDoor::StaticClass(),Source->GetActorLocation(),Source->GetActorRotation(),Params);
            if(!Replacement || !Replacement->InitializeFromMarker(Source)){if(Replacement)Replacement->Destroy();continue;}
            Replacements.Add(Source,Replacement);
        }
        AnimatedDoors.Add(Pair.Key,Replacement);
    }
}
bool ARedlinePrologueDirector::HasRequiredScene() const
{
    if(!Seat.IsValid() || !Markers.FindRef(TEXT("prologue_stand")).IsValid() || !Lander.IsValid() || !LandingTarget.IsValid())return false;
    for(const FShot& Shot:Shots)for(const TCHAR* Suffix:{TEXT("_start"),TEXT("_end")})
        if(!Markers.FindRef(FName(TEXT("prologue_cam_")+Shot.Id+Suffix)).IsValid())return false;
    return true;
}
void ARedlinePrologueDirector::BeginPlay()
{
    Super::BeginPlay();DiscoverScene();Music=GetWorld()->GetSubsystem<URedlineMusicSubsystem>();
    JazzSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Prologue/Audio/SFX_vardiya_arasi_jazz.SFX_vardiya_arasi_jazz"));
    PressureSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Prologue/Audio/SFX_airlock_pressure.SFX_airlock_pressure"));
    DoorSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Prologue/Audio/SFX_airlock_door.SFX_airlock_door"));
    ReadySound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Prologue/Audio/SFX_ready_chime.SFX_ready_chime"));
    LandingSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Prologue/Audio/SFX_landing_thrust.SFX_landing_thrust"));
    SeatedIdle=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Prologue/AN_SeatedIdle.AN_SeatedIdle"));
    StandingIdle=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/EVAFixtures/Astronaut/AN_Idle.AN_Idle"));
    if(auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/EVAFixtures/Astronaut/SK_Astronaut.SK_Astronaut")))NarrativeBody->SetSkeletalMeshAsset(Mesh);
    if(auto* M=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/EVAFixtures/M_EV1_Original.M_EV1_Original")))NarrativeBody->SetMaterial(0,M);
    bContentReady=ReadScript() && HasRequiredScene() && JazzSound && LandingSound && SeatedIdle && StandingIdle && NarrativeBody->GetSkeletalMeshAsset();
    if(!bContentReady){bFinished=true;UE_LOG(LogRedlinePrologue,Warning,TEXT("Prologue content unavailable; retaining ordinary player control"));}
    if(FParse::Param(FCommandLine::Get(),TEXT("RedlineSkipPrologue")))bFinished=true;
}
void ARedlinePrologueDirector::StartSequence()
{
    if(!bContentReady || !IsValid(Astronaut) || !Player.IsValid() || Shots.IsEmpty())return;
    bPlaying=true;Astronaut->bPresentationLocked=true;Astronaut->GetCharacterMovement()->StopMovementImmediately();Astronaut->SetActorHiddenInGame(true);
    Player->SetViewTarget(this);SelectShot(0);UE_LOG(LogRedlinePrologue,Display,TEXT("Presentation prologue started; no ROS phase/time command"));
}
void ARedlinePrologueDirector::StartMissionClip(int32 Index)
{
    if(!bContentReady || !IsValid(Astronaut) || !Player.IsValid() || !Shots.IsValidIndex(Index))return;
    bResting=false;bPhaseClip=true;bPlaying=true;Astronaut->bPresentationLocked=true;
    Astronaut->GetCharacterMovement()->StopMovementImmediately();Astronaut->SetActorHiddenInGame(true);
    Player->SetViewTarget(this);SelectShot(Index);
}
void ARedlinePrologueDirector::SetBody(bool Seated)
{
    TWeakObjectPtr<AActor> Anchor=Seated ? Seat : Markers.FindRef(TEXT("prologue_stand"));
    if(Anchor.IsValid()){NarrativeBody->SetWorldLocationAndRotation(Anchor->GetActorLocation(),Anchor->GetActorRotation());NarrativeBody->SetHiddenInGame(false);}
    if(auto* A=Seated ? SeatedIdle.Get() : StandingIdle.Get())NarrativeBody->PlayAnimation(A,true);
}
void ARedlinePrologueDirector::SelectShot(int32 Index)
{
    Narrator->Stop();Foley->Stop();Jazz->Stop();
    if(!Shots.IsValidIndex(Index) || (!bPhaseClip && Index>=5)){Finish();return;}
    ShotIndex=Index;ShotStarted=FPlatformTime::Seconds();bDoorSoundPlayed=false;
    SetBody(Shots[Index].Id==TEXT("rest"));
    if(bPhaseClip)NarrativeBody->SetHiddenInGame(true);
    if(Music)Music->SetPresentationDuck(.12f);
    Narrator->SetSound(Voices[Index]);Narrator->Play();
    const FString& Id=Shots[Index].Id;
    if(Id==TEXT("landing")){NarrativeBody->SetHiddenInGame(true);SetLandingProgress(0);Foley->SetSound(LandingSound);Foley->Play();}
    else {SetLandingProgress(1);SetDustAmount(0);}
    if(Id==TEXT("rest")){Jazz->SetSound(JazzSound);Jazz->FadeIn(.8f,1.f);if(Music)Music->SetPresentationDuck(0);}
    if(Id==TEXT("airlock")){NarrativeBody->SetHiddenInGame(true);Foley->SetSound(PressureSound);Foley->Play();}
    if(Id==TEXT("ready")){Foley->SetSound(ReadySound);Foley->Play();}
    SetCamera(Shots[Index].Id,0);
    UE_LOG(LogRedlinePrologue,Display,TEXT("Prologue shot=%s narration=%s voice_playing=%d jazz_playing=%d foley_playing=%d mission_phase=%d human_pose_published=%d"),*Shots[Index].Id,*GetNameSafe(Voices[Index]),Narrator->IsPlaying(),Jazz->IsPlaying(),Foley->IsPlaying(),Astronaut ? Astronaut->MissionPhase : -1,Astronaut ? Astronaut->PublishedPoses : -1);
}
void ARedlinePrologueDirector::SetCamera(const FString& Id,double Alpha)
{
    auto Start=Markers.FindRef(FName(TEXT("prologue_cam_")+Id+TEXT("_start"))),End=Markers.FindRef(FName(TEXT("prologue_cam_")+Id+TEXT("_end")));
    if(!Start.IsValid() || !End.IsValid())return;
    const double T=Alpha*Alpha*(3-2*Alpha);
    Camera->SetWorldLocationAndRotation(FMath::Lerp(Start->GetActorLocation(),End->GetActorLocation(),T),FQuat::Slerp(Start->GetActorQuat(),End->GetActorQuat(),T));
    if(Id==TEXT("landing") && Lander.IsValid())Camera->SetWorldRotation((Lander->GetActorLocation()+FVector(0,0,180)-Camera->GetComponentLocation()).Rotation());
}
void ARedlinePrologueDirector::SetLandingProgress(double Alpha)
{
    if(Lander.IsValid() && LandingTarget.IsValid())
    {
        const double Remaining=FMath::Square(1.-FMath::Clamp(Alpha,0.,1.));
        Lander->SetActorLocation(LandingTarget->GetActorLocation()+FVector(500*Remaining,0,2500*Remaining));
    }
}
void ARedlinePrologueDirector::SetDustAmount(float Amount)
{
    // Playtest 2026-11-15: when the dust material failed to compile, the four 11-17 m planes rendered with the
    // opaque default material and hung over the landing area. They are now hidden whenever there is no dust.
    for(auto& Material:DustMaterials)if(IsValid(Material))Material->SetScalarParameterValue(TEXT("DustAmount"),Amount);
    for(auto& Actor:DustActors)if(Actor.IsValid())Actor->SetActorHiddenInGame(Amount<=.001f);
}
void ARedlinePrologueDirector::StopPresentationAudio()
{for(auto* Audio:{Narrator.Get(),Jazz.Get(),Foley.Get()})if(IsValid(Audio))Audio->Stop();}
void ARedlinePrologueDirector::Finish()
{
    const bool WasActive=bPlaying || bResting;bPlaying=bResting=bPhaseClip=false;bFinished=true;
    StopPresentationAudio();if(IsValid(NarrativeBody))NarrativeBody->SetHiddenInGame(true);SetLandingProgress(1);SetDustAmount(0);
    for(const auto& Pair:AnimatedDoors)if(auto* Animated=Pair.Value.Get()){Animated->SetAutomaticOpen(true);Animated->RequestPresentationOpen(false);}
    if(IsValid(Astronaut)){Astronaut->bPresentationLocked=false;Astronaut->SetActorHiddenInGame(false);if(!bEnding && Player.IsValid())Player->SetViewTarget(Astronaut);}
    if(IsValid(Music))Music->SetPresentationDuck(1.f);
    if(WasActive)UE_LOG(LogRedlinePrologue,Display,TEXT("Prologue/rest finished; restored player, stopped narration/jazz/Foley; ROS/PET unchanged"));
}
void ARedlinePrologueDirector::SkipCurrent(){if(bPlaying){if(bPhaseClip)Finish();else SelectShot(ShotIndex+1);}}
void ARedlinePrologueDirector::SkipAll(){Finish();}
FString ARedlinePrologueDirector::Title() const{return bResting ? TEXT("Vardiya Arası · Bir plak, bir nefes") : Shots.IsValidIndex(ShotIndex) ? Shots[ShotIndex].Title : FString();}
FString ARedlinePrologueDirector::Caption() const{return bResting ? TEXT("Biraz dinlen. Hazır olduğunda [F] ile kalk.") : Shots.IsValidIndex(ShotIndex) ? Shots[ShotIndex].Subtitle : FString();}
bool ARedlinePrologueDirector::CanRest() const
{
    if(!bContentReady || !bFinished || IsCinematic() || !IsValid(Astronaut) || !Player.IsValid() || !Seat.IsValid() || Astronaut->MissionPhase==4 || Astronaut->MissionPhase==5)return false;
    const FVector Feet=Astronaut->GetActorLocation()-FVector(0,0,Astronaut->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    if(FMath::Abs(Feet.Z-Seat->GetActorLocation().Z)>60 || FVector::Dist2D(Feet,Seat->GetActorLocation())>250)return false;
    FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(RedlineRestReach),false,Astronaut);
    return !GetWorld()->LineTraceSingleByChannel(Hit,Astronaut->GetActorLocation(),Seat->GetActorLocation()+FVector(0,0,90),ECC_Visibility,Query);
}
void ARedlinePrologueDirector::SetResting(bool Value)
{
    if(!Value){Finish();return;}if(!CanRest())return;
    bResting=true;Astronaut->bPresentationLocked=true;Astronaut->GetCharacterMovement()->StopMovementImmediately();Astronaut->SetActorHiddenInGame(true);
    SetBody(true);SetCamera(TEXT("rest"),.5);if(Player.IsValid())Player->SetViewTarget(this);
    Narrator->Stop();Foley->Stop();Jazz->SetSound(JazzSound);Jazz->FadeIn(.8f,1.f);if(Music)Music->SetPresentationDuck(0);
    UE_LOG(LogRedlinePrologue,Display,TEXT("Optional record-player rest started; resources/time are not restored or paused"));
}
void ARedlinePrologueDirector::UpdateDataScreen()
{
    // The campaign console owns the live world-screen texture in this mode.
    for(TActorIterator<ARedlineCampaignConsole> It(GetWorld());It;++It)return;
    if(!DataScreen.IsValid())return;
    ARedlineOverlay* View=nullptr;for(TActorIterator<ARedlineOverlay> It(GetWorld());It;++It){View=*It;break;}
    if(auto* Mesh=DataScreen->FindComponentByClass<UStaticMeshComponent>())
    {
        if(!ScreenMaterial)ScreenMaterial=Mesh->CreateDynamicMaterialInstance(0);
        if(ScreenMaterial)
        {
            const bool Fresh=View && View->FieldTexture && View->Fresh(View->TileReceipt);
            ScreenMaterial->SetScalarParameterValue(TEXT("DataFresh"),Fresh ? 1.f : 0.f);
            if(Fresh)ScreenMaterial->SetTextureParameterValue(TEXT("DisplayMap"),View->FieldTexture);
        }
    }
    if(DataText.IsValid())if(auto* Text=DataText->FindComponentByClass<UTextRenderComponent>())
    {
        Text->SetVerticalAlignment(EVRTA_TextTop);
        FString Message=TEXT("BXW / DÖNÜŞ HARİTASI\nCanlı veri bekleniyor");
        if(View && View->Fresh(View->LineReceipt) && View->Line.bHasMargin)
        {
            Message=FString::Printf(TEXT("BXW / DÖNÜŞ PAYI\n%.1f dakika\nTüretilmiş arazi / senaryo giysi"),View->Line.MarginMinutes);
            if(View->Fresh(View->CrewReceipt,3))Message+=FString::Printf(TEXT("\nO2 %.2f kg / Su %.2f kg\nPil %.0f Wh"),View->Crew.OxygenKg,View->Crew.WaterKg,View->Crew.BatteryWh);
        }
        Text->SetText(FText::FromString(Message));
    }
}
void ARedlinePrologueDirector::UpdateRooms(float Delta)
{
    for(const auto& Pair:AnimatedDoors)if(auto* Animated=Pair.Value.Get())
    {
        Animated->SetAutomaticOpen(!IsCinematic());
        const bool ExitDoor=Pair.Key==TEXT("prologue_outer_door") || Pair.Key==TEXT("prologue_room_door_exit");
        const bool AirlockShot=bPlaying && Shots.IsValidIndex(ShotIndex) && Shots[ShotIndex].Id==TEXT("airlock");
        Animated->RequestPresentationOpen(ExitDoor && AirlockShot && FPlatformTime::Seconds()-ShotStarted>6.);
    }
    auto Screen=Markers.FindRef(TEXT("prologue_command_screen"));
    if(Screen.IsValid() && ScreenMaterial)if(auto* Mesh=Screen->FindComponentByClass<UStaticMeshComponent>())Mesh->SetMaterial(0,ScreenMaterial);
    auto Board=Markers.FindRef(TEXT("prologue_mission_board"));
    if(Board.IsValid())if(auto* Text=Board->FindComponentByClass<UTextRenderComponent>())
    {
        // The board marker is its top row, not its bottom baseline. This is
        // also set at runtime so previously prepared maps cannot grow upward.
        Text->SetVerticalAlignment(EVRTA_TextTop);
        FString Status=TEXT("KOMUTA / GÖREV DURUMU\nBağlantı bekleniyor");
        if(IsValid(Astronaut) && Astronaut->bMissionStateFresh)
        {
            const TMap<int32,FString> Labels={{0,TEXT("01  ÇIKIŞ BRİFİNGİ")},{2,TEXT("02  YÜZEYE GEÇİŞ")},{3,TEXT("03  SAHA BAĞLAMI")},{4,TEXT("04  HABİTATA DÖNÜŞ")},{5,TEXT("ACİL DÖNÜŞ")},{6,TEXT("05  DEBRİEF")}};
            Status=TEXT("REDLINE / KOMUTA\n")+Labels.FindRef(Astronaut->MissionPhase);
            ARedlineOverlay* Overlay=nullptr;for(TActorIterator<ARedlineOverlay> It(GetWorld());It;++It){Overlay=*It;break;}
            bool ClockFresh=false;
            if(auto* GI=GetGameInstance())if(auto* Bridge=GI->GetSubsystem<URedlineBridgeSubsystem>())
                if(Bridge->bHasMissionClock && Bridge->StaleMonitor && Bridge->StaleMonitor->IsFresh(TEXT("/redline/mission/clock"),FPlatformTime::Seconds()))
                {Status+=FString::Printf(TEXT("\nPET  %.1f dk"),Bridge->MissionClockSec/60);ClockFresh=true;}
            if(!ClockFresh)Status+=TEXT("\nPET  -- / veri eski");
            if(Overlay && Overlay->Fresh(Overlay->LineReceipt) && Overlay->Line.bHasMargin)
                Status+=FString::Printf(TEXT("\nDÖNÜŞ PAYI  %.1f dk"),Overlay->Line.MarginMinutes);
            else Status+=TEXT("\nDÖNÜŞ PAYI  -- / veri eski");
            if(Overlay && Overlay->Fresh(Overlay->CrewReceipt,3))
                Status+=FString::Printf(TEXT("\nO2 %.2f kg / SU %.2f kg\nPIL %.0f Wh"),Overlay->Crew.OxygenKg,Overlay->Crew.WaterKg,Overlay->Crew.BatteryWh);
            else Status+=TEXT("\nGİYSİ VERİSİ BEKLENİYOR");
            Status+=TEXT("\n\n[J] Görevler   [V] Kamera\n[E] Hedefte onay");
        }
        Text->SetText(FText::FromString(Status));
    }
}
void ARedlinePrologueDirector::Tick(float Delta)
{
    Super::Tick(Delta);const double Now=FPlatformTime::Seconds();
    if(!IsValid(Astronaut))
    {
        Player=GetWorld()->GetFirstPlayerController();if(Player.IsValid())Astronaut=Cast<ARedlineAstronautCharacter>(Player->GetPawn());
    }
    if(!IsValid(Astronaut) || !Player.IsValid())return;
    auto* View=GetWorld()->GetGameViewport();const bool Focus=View && View->Viewport && View->Viewport->HasFocus();
    // Campaign uses its own command service; it can share the story clips
    // without enabling the old orientation interaction handler.
    const bool StoryEnabled=Astronaut->bIntroMode || FParse::Param(FCommandLine::Get(),TEXT("RedlineCampaign"));
    if(!bFinished && !bPlaying && Astronaut->bMissionStateFresh && Focus)
    {if(StoryEnabled && Astronaut->MissionPhase==0)StartSequence();else bFinished=true;}
    if(Astronaut->bMissionStateFresh)
    {
        const int32 Phase=Astronaut->MissionPhase;
        if(bFinished && !IsCinematic() && StoryEnabled && LastObservedPhase>=0 && Phase!=LastObservedPhase)
            for(int32 I=5;I<Shots.Num();++I)if(Shots[I].Phase==Phase){StartMissionClip(I);break;}
        LastObservedPhase=Phase;
    }
    if(Focus)
    {
        if(IsCinematic() && Player->WasInputKeyJustPressed(EKeys::Escape)){SkipAll();return;}
        if(bPlaying && Player->WasInputKeyJustPressed(EKeys::SpaceBar)){SkipCurrent();return;}
        if(Player->WasInputKeyJustPressed(EKeys::F)){if(bResting)SetResting(false);else if(CanRest())SetResting(true);}
    }
    if(IsCinematic() && Astronaut->bMissionStateFresh && ((!bPhaseClip && Astronaut->MissionPhase==4) || Astronaut->MissionPhase==5)){Finish();return;}
    if(bPlaying)
    {
        const double Elapsed=Now-ShotStarted;const double Alpha=FMath::Clamp(Elapsed/Shots[ShotIndex].Duration,0.,1.);
        const FString& Id=Shots[ShotIndex].Id;
        if(Id==TEXT("landing")){SetLandingProgress(Alpha);SetDustAmount(Alpha>.65 ? FMath::Sin(FMath::Clamp((Alpha-.65)/.35,0.,1.)*PI)*.55 : 0);}
        SetCamera(Id,Alpha);
        if(Elapsed>=Shots[ShotIndex].Duration){if(bPhaseClip)Finish();else SelectShot(ShotIndex+1);}
    }
    if((bResting || (bPlaying && Shots[ShotIndex].Id==TEXT("rest"))) && Record.IsValid())Record->AddActorLocalRotation(FRotator(0,200.f*Delta,0));
    if(Now-LastDataRefresh>.5){LastDataRefresh=Now;UpdateDataScreen();}
    UpdateRooms(Delta);
}
void ARedlinePrologueDirector::EndPlay(const EEndPlayReason::Type Reason)
{bEnding=true;Finish();Super::EndPlay(Reason);}
