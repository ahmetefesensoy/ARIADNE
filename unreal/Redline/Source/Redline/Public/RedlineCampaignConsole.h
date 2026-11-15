#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineCampaignConsole.generated.h"
class URedlineBridgeSubsystem;
class UCanvas;
class UCanvasRenderTarget2D;
class UMaterialInstanceDynamic;
class ARedlineSampleInteraction;
class FJsonObject;
class UTexture2D;

/** Campaign commands are accepted by ROS; only ROS results update this view. */
UCLASS()
class REDLINE_API ARedlineCampaignConsole : public AActor
{
    GENERATED_BODY()
public:
    ARedlineCampaignConsole();
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    bool Fresh() const;
    bool HasState() const {return State.IsValid();}
    bool IsBusy() const;
    FString TaskTitle() const;
    FString TaskInstruction() const;
    FString TaskKind() const;
    FVector TaskMap() const;
    FVector NavigationTarget(FVector Here) const;
    double InteractionRadius() const;
    FString Message() const {return LastCommandMessage;}
    /** Seconds since the last command feedback (refusal, answer or timeout); large when none yet. */
    double MessageAgeSec() const {return MessageTime<0 ? 1e9 : FPlatformTime::Seconds()-MessageTime;}
    /** A command whose answer never came unlocks after 5 s with a visible message. */
    void ExpirePendingCommand(double Now);
    void Interact();
    void SendCommand(const FString& Command);
    void DrawConsole(UCanvas* Target,int32 Width,int32 Height,bool WorldScreen=false);
    void DrawMissionBoard(UCanvas* Target,int32 Width,int32 Height);
    void DrawMissionPrompt(UCanvas* Target);
    void DrawTabletPage(UCanvas* Target,int32 Width,int32 Height,int32 PageIndex);
    static constexpr int32 PageCount=8;
    static int32 TabletPageCount() {return PageCount;}
    static FString PageTitle(int32 PageIndex);
    void CyclePage(int32 Delta);
    void CycleProduct(int32 Delta,int32 PageIndex=INDEX_NONE);
    void CycleAtlasLayer();
    void CycleAtlasStation(int32 Delta);
    void CycleAtlasTask(int32 Delta);
    static bool ValidateAtlasManifest(const TSharedPtr<FJsonObject>& Json);
    static FVector2D AtlasUV(FVector2D Map,FVector4 Bounds);
    void StartLabAssay();
    FString LabMessage;
    static bool ValidateScienceSummary(const TSharedPtr<FJsonObject>& Summary,const FString& Instrument);
    static bool IsPHProduct(const TSharedPtr<FJsonObject>& Product);
    void DrawTaskCard(UCanvas* Target);
    static bool ValidateSnapshot(const TSharedPtr<FJsonObject>& Json);
    bool bConsoleOpen=false;
    bool bTabletOpen=false;
    bool bLocalWorkOwnsPresentation=false;
    int32 Page=0;
    int32 ProductSelection=-1;
private:
    friend class ARedlineFieldWorkActor;
    friend class FRedlineCampaignSnapshotTest;
    friend class FRedlineCampaignChartTest;
    friend class FRedlineCampaignRobotTelemetryTest;
    friend class FRedlineCampaignRobotPathTest;
    friend class FRedlineCampaignSciencePayloadTest;
    friend class FRedlineCampaignScienceSelectionTest;
    friend class FRedlineCampaignScoutMapTest;
    friend class FRedlineTabletAtlasTest;
    friend class FRedlineCampaignCommandFeedbackTest;
    struct FRadSample {double Time=0,Rate=0,Background=0,HistoricalUtc=0;FString Detector,SourceFile;int32 Sol=0;bool bMissionTime=false,bHasHistoricalUtc=false;};
    static constexpr int32 RadCapacity=360;
    TArray<FRadSample> RadHistory;
    int32 NextRadIndex=0;
    double RadReceipt=-1;
    struct FRoverTrackPoint {FVector MapMetres=FVector::ZeroVector;double PhysicsSec=0;};
    static constexpr int32 RoverTrackCapacity=512;
    static constexpr int32 RobotPathCapacity=256;
    TArray<FRoverTrackPoint> RoverTrack;
    TArray<FVector2D> RobotPath;
    FVector RoverMap=FVector::ZeroVector;
    double RoverPhysicsSec=-1,RoverReceipt=-1,RoverSpeedMps=0,RobotPathReceipt=-1,RobotPathPhysicsSec=-1,NavStatusReceipt=-1,NavGoalStamp=-1;
    FString NavGoalId;
    int32 NavStatus=0;
    bool bHasRoverSpeed=false;
    struct FScoutObservation {FVector2D Point;FString Id;int32 Passability=-1,Status=3;};
    TArray<FScoutObservation> ScoutObservations;
    TSet<FString> ScoutObservationIds;
    TArray<FVector2D> ScoutTrack;
    double ScoutObservationReceipt=-1;
    UPROPERTY(Transient) TObjectPtr<URedlineBridgeSubsystem> Bridge;
    UPROPERTY(Transient) TObjectPtr<UCanvasRenderTarget2D> ScreenTexture;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ScreenMaterial;
    UPROPERTY(Transient) TObjectPtr<ARedlineSampleInteraction> Interaction;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> AtlasTexture;
    struct FAtlasTask {FString Id,Action,Actor,Asset,Purpose,Status;};
    struct FAtlasStation {FString Id,Role,Name;FVector2D Map=FVector2D::ZeroVector;double TEpsMin=-1;TArray<FAtlasTask> Tasks;};
    TArray<FAtlasStation> AtlasStations;
    UPROPERTY(Transient) TArray<TObjectPtr<UTexture2D>> AtlasLayers;
    FVector4 AtlasBounds=FVector4(-1500,-1500,1500,1500);
    int32 AtlasLayer=0,AtlasStation=0,AtlasTask=0;
    bool bAtlasTried=false;
    void LoadAtlas();
    void DrawSiteMap(UCanvas* C,int32 W,int32 H);
    FDelegateHandle TopicHandle;
    TSharedPtr<FJsonObject> State;
    TWeakObjectPtr<AActor> ScreenActor;
    FString LastCommandMessage,AnimatingRequest;
    double Receipt=-1,LastRender=-1,LastCommand=-10,MessageTime=-1;
    void Notify(const FString& Text);
    bool bPendingCommand=false;
    void Receive(const FString& Topic,const TSharedPtr<FJsonObject>& Json);
    const TSharedPtr<FJsonObject> Task() const;
    void UpdateInteraction();
    void CaptureRad(const TSharedPtr<FJsonObject>& Json);
    void CaptureRoverPose(const TSharedPtr<FJsonObject>& Json,double Now);
    void CaptureRobotPath(const TSharedPtr<FJsonObject>& Json,double Now);
    void CaptureNavStatus(const TSharedPtr<FJsonObject>& Json,double Now);
    void CaptureScoutEvidence(const TSharedPtr<FJsonObject>& Json,double Now);
    TSharedPtr<FJsonObject> SelectedProductForPage(int32 PageIndex) const;
    void ResetRobotTelemetry();
    bool RobotFresh(double ReceiptTime,double MaxAge=2.) const;
    static bool FitRobotMap(const TArray<FVector2D>& Points,FVector2D PixelSize,FVector2D& Minimum,FVector2D& Maximum);
    const FRadSample& RadAt(int32 ChronologicalIndex) const;
    UFUNCTION() void ConnectionChanged(bool bConnected);
    UFUNCTION() void RenderScreen(UCanvas* Target,int32 Width,int32 Height);
};
