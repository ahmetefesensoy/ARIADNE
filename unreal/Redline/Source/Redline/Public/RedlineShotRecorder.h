#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FrameGrabber.h"
#include "RedlineShotRecorder.generated.h"

class FJsonObject;
class FJsonValue;

/** Opt-in local game viewport and game master-submix recording. No desktop/mic. */
UCLASS()
class REDLINE_API ARedlineShotRecorder : public AActor
{
    GENERATED_BODY()
public:
    ARedlineShotRecorder();
    virtual ~ARedlineShotRecorder() override;
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    UFUNCTION(BlueprintCallable, Category="REDLINE|Capture") bool StartRecording();
    UFUNCTION(BlueprintCallable, Category="REDLINE|Capture") void StopRecording();
    UFUNCTION(BlueprintPure, Category="REDLINE|Capture") bool IsRecording()const{return bRecording;}
private:
    TUniquePtr<FFrameGrabber> Grabber;
    TArray<TSharedPtr<FJsonValue>> Frames;
    FString OutputRoot,ShotName,ShotDirectory,StartedUtc,LastFailure;
    FIntPoint FrameSize=FIntPoint::ZeroValue;
    double StartedAt=0,StoppedAt=0,NextCapture=0,AutoStartAt=0,LimitSeconds=120,TargetFps=30;
    int32 PendingFrames=0,RequestedFrames=0,SavedFrames=0,SkippedCaptureTicks=0;
    int64 WrittenBytes=0;
    bool bReady=false,bRecording=false,bFinishing=false,bAutoStart=false;
    void DrainFrames();
    void FinishRecording(bool Force);
    void SaveManifest(bool Complete);
};
