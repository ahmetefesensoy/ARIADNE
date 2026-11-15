#include "RedlineBridgeSubsystem.h"
#include "RedlineSettings.h"
#include "RedlineStaleMonitor.h"
#include "RedlineTypes.h"
#include "Async/Async.h"
#include "IWebSocket.h"
#include "WebSocketsModule.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
DEFINE_LOG_CATEGORY(LogRedlineBridge);

void URedlineBridgeSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    StaleMonitor=NewObject<URedlineStaleMonitor>(this);
    TickHandle=FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this,&URedlineBridgeSubsystem::Tick));
    Subscribe(TEXT("/clock"),TEXT("rosgraph_msgs/msg/Clock"));
    Subscribe(TEXT("/redline/mission/clock"),TEXT("rosgraph_msgs/msg/Clock"));
    FString OfflinePath;
    if (FParse::Value(FCommandLine::Get(),TEXT("RedlineFeed="),OfflinePath))
    { FString Error; if (!StartOfflineFeed(OfflinePath,Error)) UE_LOG(LogRedlineBridge,Error,TEXT("Offline feed rejected: %s"),*Error); }
    else if (GetDefault<URedlineSettings>()->bAutoConnect) Connect();
}
void URedlineBridgeSubsystem::Deinitialize()
{
    bStopping=true; FTSTicker::GetCoreTicker().RemoveTicker(TickHandle); Disconnect(); OnTopic.Clear(); Super::Deinitialize();
}
void URedlineBridgeSubsystem::Connect()
{
    check(IsInGameThread()); bOffline=false; bWantsConnection=true;
    if (!Socket.IsValid()) OpenSocket();
}
void URedlineBridgeSubsystem::Disconnect()
{
    check(IsInGameThread()); bWantsConnection=false; bOffline=false; ++Generation;
    if (Socket) { Socket->OnConnected().Clear(); Socket->OnConnectionError().Clear(); Socket->OnClosed().Clear(); Socket->OnMessage().Clear(); Socket->Close(); Socket.Reset(); }
    if (bConnected) { bConnected=false; OnConnectionChanged.Broadcast(false); }
    if (StaleMonitor) StaleMonitor->Disconnected();
    FailPending(TEXT("disconnected; commands are never replayed"));
}
void URedlineBridgeSubsystem::OpenSocket()
{
    check(IsInGameThread());
    const URedlineSettings* Settings=GetDefault<URedlineSettings>();
    FString Url=Settings->RosbridgeUrl; FParse::Value(FCommandLine::Get(),TEXT("RedlineRosbridgeUrl="),Url);
    Socket=FWebSocketsModule::Get().CreateWebSocket(Url);
    const uint64 G=++Generation; const TWeakObjectPtr<URedlineBridgeSubsystem> Weak(this);
    Socket->OnConnected().AddLambda([Weak,G]() { AsyncTask(ENamedThreads::GameThread,[Weak,G](){if (auto* Self=Weak.Get()) Self->Connected(G);}); });
    Socket->OnConnectionError().AddLambda([Weak,G](const FString& Error) { AsyncTask(ENamedThreads::GameThread,[Weak,G,Error](){if (auto* Self=Weak.Get()) Self->Lost(G,Error);}); });
    Socket->OnClosed().AddLambda([Weak,G](int32 Code,const FString& Reason,bool Clean) { AsyncTask(ENamedThreads::GameThread,[Weak,G,Reason](){if (auto* Self=Weak.Get()) Self->Lost(G,Reason);}); });
    Socket->OnMessage().AddLambda([Weak,G](const FString& Message) { AsyncTask(ENamedThreads::GameThread,[Weak,G,Message](){if (auto* Self=Weak.Get(); Self && !Self->bStopping && Self->Generation==G) Self->HandleEnvelope(Message);}); });
    UE_LOG(LogRedlineBridge,Display,TEXT("Connecting rosbridge %s generation %llu"),*Url,G);
    Socket->Connect();
}
void URedlineBridgeSubsystem::Connected(uint64 G)
{
    if (G!=Generation || bStopping || !bWantsConnection) return;
    bConnected=true; ++ConnectionCount; ReconnectDelay=GetDefault<URedlineSettings>()->ReconnectInitialSec;
    for (const auto& Pair:Subscriptions) SendSubscription(Pair.Key,Pair.Value);
    for (const auto& Pair:Advertisements) { TSharedRef<FJsonObject> E=MakeShared<FJsonObject>(); E->SetStringField(TEXT("op"),TEXT("advertise")); E->SetStringField(TEXT("topic"),Pair.Key); E->SetStringField(TEXT("type"),Pair.Value); Send(E); }
    OnConnectionChanged.Broadcast(true); UE_LOG(LogRedlineBridge,Display,TEXT("Connected; restored %d subscriptions (connection %d)"),Subscriptions.Num(),ConnectionCount);
}
void URedlineBridgeSubsystem::Lost(uint64 G,const FString& Reason)
{
    if (G!=Generation || bStopping) return;
    ++Generation; Socket.Reset(); bConnected=false; StaleMonitor->Disconnected(); FailPending(TEXT("connection lost; not replayed")); OnConnectionChanged.Broadcast(false);
    NextReconnect=FPlatformTime::Seconds()+ReconnectDelay;
    ReconnectDelay=FMath::Min(GetDefault<URedlineSettings>()->ReconnectMaxSec,ReconnectDelay*2);
    UE_LOG(LogRedlineBridge,Display,TEXT("Connection lost: %s. Reconnect scheduled."),*Reason);
}
bool URedlineBridgeSubsystem::Send(const TSharedRef<FJsonObject>& Envelope)
{ check(IsInGameThread()); if (!bConnected || bOffline || !Socket || !Socket->IsConnected()) return false; Socket->Send(FRedlineJson::Write(Envelope)); return true; }
void URedlineBridgeSubsystem::Subscribe(const FString& Topic,const FString& Type,int32 ThrottleMs,double MaxAgeSec)
{
    check(IsInGameThread()); FSubscription S; S.Type=Type; S.Throttle=FMath::Max(0,ThrottleMs); Subscriptions.Add(Topic,S);
    StaleMonitor->Watch(Topic,MaxAgeSec>0 ? MaxAgeSec : GetDefault<URedlineSettings>()->TopicMaxAgeSec,FPlatformTime::Seconds());
    if (bConnected && !bOffline) SendSubscription(Topic,S);
}
void URedlineBridgeSubsystem::SendSubscription(const FString& Topic,const FSubscription& S)
{
    const bool bStatic=Topic==TEXT("/tf_static") || Topic==TEXT("/redline/bridge/tf_static_snapshot") || Topic==TEXT("/redline/bridge/tf_static_snapshot_status");
    TSharedRef<FJsonObject> E=MakeShared<FJsonObject>(); E->SetStringField(TEXT("op"),TEXT("subscribe")); E->SetStringField(TEXT("id"),TEXT("sub:")+Topic); E->SetStringField(TEXT("topic"),Topic); E->SetStringField(TEXT("type"),S.Type); E->SetNumberField(TEXT("throttle_rate"),S.Throttle); E->SetNumberField(TEXT("queue_length"),bStatic?100:1);
    if (bStatic)
    {
        TSharedRef<FJsonObject> Qos=MakeShared<FJsonObject>(); Qos->SetStringField(TEXT("history"),TEXT("keep_last")); Qos->SetNumberField(TEXT("depth"),100); Qos->SetStringField(TEXT("reliability"),TEXT("reliable")); Qos->SetStringField(TEXT("durability"),TEXT("transient_local")); E->SetObjectField(TEXT("qos"),Qos);
    }
    Send(E);
}
void URedlineBridgeSubsystem::Advertise(const FString& Topic,const FString& Type)
{
    check(IsInGameThread()); Advertisements.Add(Topic,Type); TSharedRef<FJsonObject> E=MakeShared<FJsonObject>(); E->SetStringField(TEXT("op"),TEXT("advertise")); E->SetStringField(TEXT("topic"),Topic); E->SetStringField(TEXT("type"),Type); Send(E);
}
bool URedlineBridgeSubsystem::Publish(const FString& Topic,const TSharedRef<FJsonObject>& Message)
{ if (!Advertisements.Contains(Topic)) return false; TSharedRef<FJsonObject> E=MakeShared<FJsonObject>(); E->SetStringField(TEXT("op"),TEXT("publish")); E->SetStringField(TEXT("topic"),Topic); E->SetObjectField(TEXT("msg"),Message); return Send(E); }
FString URedlineBridgeSubsystem::CallService(const FString& Service,const FString& Type,const TSharedRef<FJsonObject>& Args,FRedlineServiceCallback Callback)
{
    check(IsInGameThread());
    if (!bConnected || bOffline) { if (Callback) Callback(false,nullptr,TEXT("not connected to live ROS")); return FString(); }
    const FString Id=FString::Printf(TEXT("srv-%llu-%llu"),Generation,++NextService);
    FPending Pending; Pending.Callback=MoveTemp(Callback); Pending.Deadline=FPlatformTime::Seconds()+GetDefault<URedlineSettings>()->ServiceTimeoutSec; PendingServices.Add(Id,MoveTemp(Pending));
    TSharedRef<FJsonObject> E=MakeShared<FJsonObject>(); E->SetStringField(TEXT("op"),TEXT("call_service")); E->SetStringField(TEXT("id"),Id); E->SetStringField(TEXT("service"),Service); E->SetStringField(TEXT("type"),Type); E->SetObjectField(TEXT("args"),Args);
    if (!Send(E)) { FPending P=MoveTemp(PendingServices.FindChecked(Id)); PendingServices.Remove(Id); if (P.Callback) P.Callback(false,nullptr,TEXT("send failed")); return FString(); }
    return Id;
}
bool URedlineBridgeSubsystem::DispatchMissionCommand(const FString& Id,const FString& Service,const FString& Type,const TSharedRef<FJsonObject>& Args,const TArray<FString>& Fresh,FRedlineServiceCallback Callback,FString& Error)
{
    check(IsInGameThread());
    if (Id.IsEmpty() || CommandIds.Contains(Id)) { Error=TEXT("empty or duplicate command id"); return false; }
    if (!bConnected || bOffline) { Error=TEXT("commands require live ROS connection"); return false; }
    for (const FString& Topic:Fresh) if (!StaleMonitor->IsFresh(Topic,FPlatformTime::Seconds())) { Error=TEXT("stale prerequisite: ")+Topic; return false; }
    if (CommandIds.Num()>=10000) { Error=TEXT("command history full; start a new run"); return false; }
    CommandIds.Add(Id);
    return !CallService(Service,Type,Args,MoveTemp(Callback)).IsEmpty();
}
void URedlineBridgeSubsystem::FailPending(const FString& Reason)
{
    TMap<FString,FPending> Pending=MoveTemp(PendingServices); PendingServices.Empty();
    for (auto& Pair:Pending) if (Pair.Value.Callback) Pair.Value.Callback(false,nullptr,Reason);
}
void URedlineBridgeSubsystem::HandleEnvelope(const FString& Message)
{
    check(IsInGameThread()); const TSharedPtr<FJsonObject> E=FRedlineJson::Parse(Message); FString Op;
    if (!E || !E->TryGetStringField(TEXT("op"),Op)) return;
    if (Op==TEXT("publish"))
    {
        FString Topic; const TSharedPtr<FJsonObject>* Msg;
        if (!E->TryGetStringField(TEXT("topic"),Topic) || !E->TryGetObjectField(TEXT("msg"),Msg) || !Subscriptions.Contains(Topic)) return;
        // Mandatory typed streams become fresh only after successful parsing.
        // Generic streams track transport receipt, not semantic validity.
        if (Topic.EndsWith(TEXT("/odom")))
        {
            FRedlineOdometry Odom; FString Error;
            if (!FRedlineOdometry::Parse(*Msg,Odom,Error)) return;
            const bool bPresentation=Topic==TEXT("/redline/presentation/rover_1/odom");
            const FString Vehicle=bPresentation ? TEXT("rover_1") : Topic.LeftChop(5).Mid(1);
            if (bPresentation && Odom.FrameId!=TEXT("map")) return;
            if ((Odom.FrameId!=TEXT("map") && Odom.FrameId!=Vehicle+TEXT("/odom")) || Odom.ChildFrameId!=Vehicle+TEXT("/base_link")) return;
        }
        if (Topic==TEXT("/clock") || Topic==TEXT("/redline/mission/clock"))
        {
            const TSharedPtr<FJsonObject>* Clock; double Time;
            if (!(*Msg)->TryGetObjectField(TEXT("clock"),Clock) || !FRedlineJson::Stamp(*Clock,Time)) return;
            if (Topic==TEXT("/clock")) { PhysicsClockSec=Time; bHasPhysicsClock=true; } else { MissionClockSec=Time; bHasMissionClock=true; }
        }
        StaleMonitor->Received(Topic,FPlatformTime::Seconds()); ++ReceivedCount;
        OnTopic.Broadcast(Topic,*Msg);
    }
    else if (Op==TEXT("service_response"))
    {
        FString Id; bool bResult=false; const TSharedPtr<FJsonObject>* Values;
        if (!E->TryGetStringField(TEXT("id"),Id) || !PendingServices.Contains(Id)) return;
        FPending P=MoveTemp(PendingServices.FindChecked(Id)); PendingServices.Remove(Id); E->TryGetBoolField(TEXT("result"),bResult);
        const TSharedPtr<FJsonObject> Reply=E->TryGetObjectField(TEXT("values"),Values) ? *Values : nullptr;
        if (P.Callback) P.Callback(bResult,Reply,bResult?TEXT("service response; execution status belongs to ROS mission state"):TEXT("service rejected"));
    }
}
bool URedlineBridgeSubsystem::StartOfflineFeed(const FString& Path,FString& Error)
{
    check(IsInGameThread()); TArray<FString> Lines;
    if (!FFileHelper::LoadFileToStringArray(Lines,*Path)) { Error=TEXT("cannot read feed"); return false; }
    TArray<FFeedLine> Parsed; double Previous=-1;
    for (const FString& Line:Lines)
    {
        if (Line.TrimStartAndEnd().IsEmpty()) continue;
        const TSharedPtr<FJsonObject> E=FRedlineJson::Parse(Line); FString Op; double Elapsed;
        if (!E || !E->TryGetStringField(TEXT("op"),Op) || Op!=TEXT("publish") || !E->TryGetNumberField(TEXT("_redline_elapsed_sec"),Elapsed) || !FMath::IsFinite(Elapsed) || Elapsed<0 || Elapsed<Previous)
        { Error=TEXT("feed requires ordered rosbridge publish envelopes with monotonic _redline_elapsed_sec"); return false; }
        FFeedLine F; F.Elapsed=Elapsed; F.Message=Line; Parsed.Add(MoveTemp(F)); Previous=Elapsed;
    }
    if (Parsed.IsEmpty()) { Error=TEXT("empty feed"); return false; }
    Disconnect(); Feed=MoveTemp(Parsed); FeedIndex=0; FeedStarted=FPlatformTime::Seconds(); bOffline=true; bConnected=true; OnConnectionChanged.Broadcast(true); return true;
}
bool URedlineBridgeSubsystem::Tick(float Delta)
{
    if (bStopping) return false;
    const double Now=FPlatformTime::Seconds(); StaleMonitor->Evaluate(Now);
    if (bOffline)
    {
        while (FeedIndex<Feed.Num() && Feed[FeedIndex].Elapsed<=Now-FeedStarted) HandleEnvelope(Feed[FeedIndex++].Message);
    }
    else if (bWantsConnection && !Socket.IsValid() && Now>=NextReconnect) OpenSocket();
    TArray<FString> Expired; for (const auto& Pair:PendingServices) if (Now>Pair.Value.Deadline) Expired.Add(Pair.Key);
    // Remove every expired entry before invoking user callbacks: callbacks may
    // disconnect, enqueue other services or synchronously clear the pending map.
    TArray<FPending> TimedOut;
    for (const FString& Id:Expired) { TimedOut.Add(MoveTemp(PendingServices.FindChecked(Id))); PendingServices.Remove(Id); }
    for (FPending& P:TimedOut) if (P.Callback) P.Callback(false,nullptr,TEXT("service timeout; execution outcome unknown; never replayed"));
    return true;
}
