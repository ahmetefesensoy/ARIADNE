#include "RedlineShotRecorder.h"
#include "FrameGrabber.h"
#include "AudioMixerBlueprintLibrary.h"
#include "Engine/GameViewportClient.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Widgets/SViewport.h"
#include "InputCoreTypes.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "RenderingThread.h"

DEFINE_LOG_CATEGORY_STATIC(LogRedlineShot,Log,All);
namespace RedlineShot
{
struct FPayload final: IFramePayload
{
    int32 Index;double RequestAt,ReadyAt=0;
    FPayload(int32 InIndex,double Time):Index(InIndex),RequestAt(Time){}
    virtual bool OnFrameReady_RenderThread(FColor*,FIntPoint,FIntPoint)const override
    {const_cast<FPayload*>(this)->ReadyAt=FPlatformTime::Seconds();return true;}
};
bool SafeName(const FString& Name)
{if(Name.IsEmpty() || Name.Len()>80)return false;for(TCHAR C:Name)if(!FChar::IsAlnum(C) && C!='_' && C!='-')return false;return true;}
}
ARedlineShotRecorder::ARedlineShotRecorder(){PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickGroup=TG_PostUpdateWork;SetActorEnableCollision(false);}
ARedlineShotRecorder::~ARedlineShotRecorder()=default;
void ARedlineShotRecorder::BeginPlay()
{
    Super::BeginPlay();
    if(!FParse::Value(FCommandLine::Get(),TEXT("RedlineShotDir="),OutputRoot))return;
    ShotName=TEXT("gameplay");FParse::Value(FCommandLine::Get(),TEXT("RedlineShotName="),ShotName);
    FParse::Value(FCommandLine::Get(),TEXT("RedlineShotSeconds="),LimitSeconds);
    FParse::Value(FCommandLine::Get(),TEXT("RedlineShotFps="),TargetFps);
    double Delay=5;FParse::Value(FCommandLine::Get(),TEXT("RedlineShotDelay="),Delay);
    if(FPaths::IsRelative(OutputRoot) || OutputRoot.StartsWith(TEXT("\\\\")) || OutputRoot.StartsWith(TEXT("//")) || !RedlineShot::SafeName(ShotName)
       || !FMath::IsFinite(LimitSeconds) || LimitSeconds<1 || LimitSeconds>120 || !FMath::IsFinite(TargetFps) || TargetFps<1 || TargetFps>30 || !FMath::IsFinite(Delay) || Delay<0 || Delay>30)
    {UE_LOG(LogRedlineShot,Error,TEXT("Invalid local recording path/name/duration/FPS; capture disabled"));return;}
    OutputRoot=FPaths::ConvertRelativePathToFull(OutputRoot);bReady=true;
    bAutoStart=FParse::Param(FCommandLine::Get(),TEXT("RedlineShotAutoStart"));AutoStartAt=FPlatformTime::Seconds()+Delay;
    UE_LOG(LogRedlineShot,Display,TEXT("Local viewport/master audio capture ready: F10 toggle, max %.1fs; output %s"),LimitSeconds,*OutputRoot);
}
bool ARedlineShotRecorder::StartRecording()
{
    check(IsInGameThread());if(!bReady || bRecording || bFinishing || !GetWorld() || !GetWorld()->IsGameWorld())return false;
    auto* Client=GetWorld()->GetGameViewport();auto Widget=Client ? Client->GetGameViewportWidget() : nullptr;
    auto Interface=Widget.IsValid() ? Widget->GetViewportInterface().Pin() : nullptr;
    if(!Client || !Client->GetGameViewport() || !Interface.IsValid())return false;
    auto Viewport=StaticCastSharedPtr<FSceneViewport>(Interface);
    if(Viewport.Get()!=Client->GetGameViewport())return false;
    FrameSize=Viewport->GetSize();
    if(FrameSize.X<64 || FrameSize.Y<64 || FrameSize.X>3840 || FrameSize.Y>2160)return false;
    // Immutable size while recording; no scaling or desktop/window lookup.
    ShotDirectory=OutputRoot/(ShotName+TEXT("-")+FDateTime::UtcNow().ToString(TEXT("%Y%m%dT%H%M%SZ"))+TEXT("-")+FGuid::NewGuid().ToString(EGuidFormats::Digits).Left(8));
    if(!IFileManager::Get().MakeDirectory(*(ShotDirectory/TEXT("frames")),true))return false;
    Frames.Reset();SavedFrames=RequestedFrames=PendingFrames=SkippedCaptureTicks=0;WrittenBytes=0;LastFailure.Empty();
    StartedUtc=FDateTime::UtcNow().ToIso8601();StartedAt=FPlatformTime::Seconds();StoppedAt=0;NextCapture=StartedAt;
    Grabber=MakeUnique<FFrameGrabber>(Viewport.ToSharedRef(),FrameSize,PF_B8G8R8A8,3);Grabber->StartCapturingFrames();
    StartedAt=FPlatformTime::Seconds();NextCapture=StartedAt;
    UAudioMixerBlueprintLibrary::StartRecordingOutput(this,float(LimitSeconds),nullptr);
    bRecording=true;bAutoStart=false;SaveManifest(false);
    UE_LOG(LogRedlineShot,Display,TEXT("Recording actual game viewport + game master submix: %s"),*ShotDirectory);return true;
}
void ARedlineShotRecorder::StopRecording()
{
    check(IsInGameThread());if(!bRecording)return;
    bRecording=false;bFinishing=true;StoppedAt=FPlatformTime::Seconds();
    UAudioMixerBlueprintLibrary::StopRecordingOutput(this,EAudioRecordingExportType::WavFile,TEXT("master"),ShotDirectory,nullptr);
    if(Grabber && Grabber->IsCapturingFrames())Grabber->StopCapturingFrames();
    SaveManifest(false);
}
void ARedlineShotRecorder::DrainFrames()
{
    if(!Grabber)return;
    auto Captured=Grabber->GetCapturedFrames();
    auto& Module=FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper"));
    for(auto& Frame:Captured)
    {
        PendingFrames=FMath::Max(0,PendingFrames-1);const auto* Payload=Frame.GetPayload<RedlineShot::FPayload>();
        if(!Payload || Frame.BufferSize!=FrameSize || Frame.ColorBuffer.Num()!=FrameSize.X*FrameSize.Y){LastFailure=TEXT("Invalid captured frame dimensions");continue;}
        if(StoppedAt>0 && Payload->ReadyAt>StoppedAt)continue;
        auto PNG=Module.CreateImageWrapper(EImageFormat::PNG);
        if(!PNG || !PNG->SetRaw(Frame.ColorBuffer.GetData(),int64(Frame.ColorBuffer.Num())*sizeof(FColor),FrameSize.X,FrameSize.Y,ERGBFormat::BGRA,8))
        {LastFailure=TEXT("PNG encoding failed");continue;}
        const auto& Data=PNG->GetCompressed(-1); // Fast lossless compression; actual timing remains in manifest.
        const FString Relative=FString::Printf(TEXT("frames/frame_%06d.png"),SavedFrames);
        if(!FFileHelper::SaveArrayToFile(Data,*(ShotDirectory/Relative))){LastFailure=TEXT("PNG file write failed");continue;}
        WrittenBytes+=Data.Num();auto Item=MakeShared<FJsonObject>();Item->SetStringField(TEXT("file"),Relative);
        Item->SetNumberField(TEXT("index"),Payload->Index);Item->SetNumberField(TEXT("request_wall_s"),Payload->RequestAt-StartedAt);
        Item->SetNumberField(TEXT("captured_wall_s"),Payload->ReadyAt-StartedAt);Frames.Add(MakeShared<FJsonValueObject>(Item));++SavedFrames;
    }
}
void ARedlineShotRecorder::SaveManifest(bool Complete)
{
    if(ShotDirectory.IsEmpty())return;
    auto J=MakeShared<FJsonObject>();J->SetStringField(TEXT("schema"),TEXT("redline.unreal.shot.v1"));J->SetStringField(TEXT("name"),ShotName);
    J->SetStringField(TEXT("started_at_utc"),StartedUtc);J->SetBoolField(TEXT("complete"),Complete);J->SetBoolField(TEXT("recording"),bRecording);
    J->SetStringField(TEXT("source"),TEXT("Unreal game viewport FFrameGrabber + game master submix; no desktop or microphone"));
    J->SetNumberField(TEXT("width"),FrameSize.X);J->SetNumberField(TEXT("height"),FrameSize.Y);J->SetNumberField(TEXT("requested_fps"),TargetFps);
    J->SetNumberField(TEXT("duration_wall_s"),(StoppedAt>0 ? StoppedAt : FPlatformTime::Seconds())-StartedAt);
    J->SetNumberField(TEXT("requested_frames"),RequestedFrames);J->SetNumberField(TEXT("saved_frames"),SavedFrames);J->SetNumberField(TEXT("skipped_capture_ticks"),SkippedCaptureTicks);
    J->SetStringField(TEXT("audio_file"),TEXT("master.wav"));J->SetStringField(TEXT("audio_state"),Complete ? TEXT("asynchronous export requested; encoder must validate WAV") : TEXT("recording/export pending"));
    J->SetStringField(TEXT("audio_alignment"),TEXT("Same game-thread start/stop requests; audio-device latency is not calibrated. No missing game sounds or music are synthesized."));
    J->SetStringField(TEXT("failure"),LastFailure);J->SetArrayField(TEXT("frames"),Frames);
    FString Text;auto Writer=TJsonWriterFactory<>::Create(&Text);FJsonSerializer::Serialize(J,Writer);
    FFileHelper::SaveStringToFile(Text,*(ShotDirectory/TEXT("manifest.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}
void ARedlineShotRecorder::FinishRecording(bool Force)
{
    if(!bFinishing)return;
    DrainFrames();if(!Force && Grabber && Grabber->HasOutstandingFrames() && FPlatformTime::Seconds()-StoppedAt<2)return;
    if(Grabber){FlushRenderingCommands();Grabber->Shutdown();DrainFrames();Grabber.Reset();}
    bFinishing=false;SaveManifest(true);
    UE_LOG(LogRedlineShot,Display,TEXT("Shot closed: %d actual PNG frames in %s; WAV export requested"),SavedFrames,*ShotDirectory);
    if(FParse::Param(FCommandLine::Get(),TEXT("RedlineShotExitAfter")))GEngine->Exec(GetWorld(),TEXT("QUIT"));
}
void ARedlineShotRecorder::Tick(float Dt)
{
    Super::Tick(Dt);const double Now=FPlatformTime::Seconds();auto* PC=GetWorld()->GetFirstPlayerController();auto* Client=GetWorld()->GetGameViewport();
    const bool Focus=Client && Client->Viewport && Client->Viewport->HasFocus();
    if(bAutoStart && bReady && Now>=AutoStartAt)StartRecording();
    if(Focus && PC && PC->WasInputKeyJustPressed(EKeys::F10)){if(bRecording)StopRecording();else StartRecording();}
    DrainFrames();
    if(bRecording)
    {
        if(!Client || !Client->GetGameViewport() || Client->GetGameViewport()->GetSize()!=FrameSize)LastFailure=TEXT("Viewport resized or closed during recording");
        if(Now-StartedAt>=LimitSeconds || WrittenBytes>int64(8)*1024*1024*1024 || SavedFrames>=3600 || !LastFailure.IsEmpty())StopRecording();
        else if(Now>=NextCapture)
        {
            NextCapture=Now+1./TargetFps;
            if(PendingFrames<2){Grabber->CaptureThisFrame(MakeShared<RedlineShot::FPayload,ESPMode::ThreadSafe>(RequestedFrames++,Now));++PendingFrames;}
            else ++SkippedCaptureTicks;
        }
    }
    FinishRecording(false);
}
void ARedlineShotRecorder::EndPlay(const EEndPlayReason::Type Reason)
{StopRecording();FinishRecording(true);Super::EndPlay(Reason);}
