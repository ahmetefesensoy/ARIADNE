#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "RedlineBridgeSubsystem.generated.h"

class IWebSocket;
class URedlineStaleMonitor;
DECLARE_LOG_CATEGORY_EXTERN(LogRedlineBridge, Log, All);
DECLARE_MULTICAST_DELEGATE_TwoParams(FRedlineTopicEvent,const FString&,const TSharedPtr<FJsonObject>&);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FRedlineConnectionEvent,bool,bConnected);
using FRedlineServiceCallback = TFunction<void(bool, const TSharedPtr<FJsonObject>&, const FString&)>;

/** All state, callbacks and delegates are game-thread owned. Socket closures use weak UObject + generation fences. */
UCLASS()
class REDLINEBRIDGE_API URedlineBridgeSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    UFUNCTION(BlueprintCallable,Category="REDLINE|Bridge") void Connect();
    UFUNCTION(BlueprintCallable,Category="REDLINE|Bridge") void Disconnect();
    UFUNCTION(BlueprintPure,Category="REDLINE|Bridge") bool IsConnected() const { return bConnected; }
    UFUNCTION(BlueprintPure,Category="REDLINE|Bridge") bool IsOfflineReplay() const { return bOffline; }
    UFUNCTION(BlueprintCallable,Category="REDLINE|Bridge") bool StartOfflineFeed(const FString& Path, FString& Error);
    UPROPERTY(BlueprintAssignable,Category="REDLINE|Bridge") FRedlineConnectionEvent OnConnectionChanged;
    UPROPERTY(Transient,BlueprintReadOnly,Category="REDLINE|Bridge") TObjectPtr<URedlineStaleMonitor> StaleMonitor;
    FRedlineTopicEvent OnTopic;
    void Subscribe(const FString& Topic,const FString& Type,int32 ThrottleMs=0,double MaxAgeSec=-1);
    void Advertise(const FString& Topic,const FString& Type);
    bool Publish(const FString& Topic,const TSharedRef<FJsonObject>& Message);
    FString CallService(const FString& Service,const FString& Type,const TSharedRef<FJsonObject>& Args,FRedlineServiceCallback Callback);
    /** Command ID is consumed once. A service reply is acceptance only; ROS action execution stays in mission_manager. */
    bool DispatchMissionCommand(const FString& CommandId,const FString& Service,const FString& Type,const TSharedRef<FJsonObject>& Args,const TArray<FString>& RequiredFreshTopics,FRedlineServiceCallback Callback,FString& Error);
    double PhysicsClockSec = 0;
    double MissionClockSec = 0;
    bool bHasPhysicsClock = false;
    bool bHasMissionClock = false;
    int32 ConnectionCount = 0;
    int32 ReceivedCount = 0;
    // Entry point shared by live socket and offline replay. Always game thread.
    void HandleEnvelope(const FString& Message);
private:
    friend class FRedlineServiceReentrancy;
    friend class FRedlineOfflineReplay;
    struct FSubscription { FString Type; int32 Throttle=0; };
    struct FPending { FRedlineServiceCallback Callback; double Deadline=0; };
    struct FFeedLine { double Elapsed=0; FString Message; };
    TSharedPtr<IWebSocket> Socket;
    TMap<FString,FSubscription> Subscriptions;
    TMap<FString,FString> Advertisements;
    TMap<FString,FPending> PendingServices;
    TSet<FString> CommandIds;
    TArray<FFeedLine> Feed;
    int32 FeedIndex=0;
    double FeedStarted=0;
    FTSTicker::FDelegateHandle TickHandle;
    bool bConnected=false;
    bool bOffline=false;
    bool bWantsConnection=false;
    bool bStopping=false;
    uint64 Generation=0;
    uint64 NextService=0;
    double NextReconnect=0;
    double ReconnectDelay=0.5;
    bool Tick(float Delta);
    void OpenSocket();
    void Connected(uint64 SocketGeneration);
    void Lost(uint64 SocketGeneration,const FString& Reason);
    bool Send(const TSharedRef<FJsonObject>& Envelope);
    void SendSubscription(const FString& Topic,const FSubscription& Subscription);
    void FailPending(const FString& Reason);
};
