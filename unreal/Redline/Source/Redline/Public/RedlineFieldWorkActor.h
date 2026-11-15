#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineFieldWork.h"
#include "RedlineFieldWorkActor.generated.h"

class ARedlineCampaignConsole;
class ARedlineAstronautCharacter;
class ARedlineSampleInteraction;
class UCanvas;

/** Local, input-driven preparation. ROS alone records science/task results. */
UCLASS()
class REDLINE_API ARedlineFieldWorkActor : public AActor
{
    GENERATED_BODY()
public:
    ARedlineFieldWorkActor();
    bool BeginWork(ARedlineCampaignConsole* Campaign);
    bool IsWorking() const {return bWorking;}
    void DrawWork(UCanvas* Canvas);
    void CancelWork();
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    TWeakObjectPtr<ARedlineCampaignConsole> Console;
    TWeakObjectPtr<ARedlineAstronautCharacter> Human;
    UPROPERTY(Transient) TObjectPtr<ARedlineSampleInteraction> Pose;
    FRedlineFieldWork Work;
    FString RunId,TaskId,OperationId;
    FVector WorkMap=FVector::ZeroVector,WorkWorld=FVector::ZeroVector;
    FRotator InitialCamera=FRotator::ZeroRotator;
    double CameraYaw=0,CameraPitch=0,DispatchedAt=-1,WaitStarted=-1;
    int32 OriginalTaskIndex=-1;
    bool bWorking=false,bDispatched=false,bSawRunning=false,bAligned=false;
    double LeftPulse=-1,RightPulse=-1,InteractPulse=-1;
    bool Focused() const;
    void Finish(bool Success,const FString& Message);
};
