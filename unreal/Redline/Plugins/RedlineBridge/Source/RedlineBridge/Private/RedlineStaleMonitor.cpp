#include "RedlineStaleMonitor.h"
void URedlineStaleMonitor::Watch(const FString& Topic, double MaxAge, double Now)
{ FEntry& E=Entries.FindOrAdd(Topic); E.MaxAge=FMath::Max(0.001,MaxAge); if (!E.bSeen) E.Last=Now; }
void URedlineStaleMonitor::Received(const FString& Topic, double Now)
{ if (FEntry* E=Entries.Find(Topic)) { E->Last=Now; E->bSeen=true; if (E->bStale) { E->bStale=false; OnStale.Broadcast(Topic,false); } } }
void URedlineStaleMonitor::Disconnected()
{ TArray<FString> Changed; for (auto& Pair: Entries) { FEntry& E=Pair.Value; E.bSeen=false; if (!E.bStale) { E.bStale=true; Changed.Add(Pair.Key); } } for (const FString& Topic:Changed) OnStale.Broadcast(Topic,true); }
void URedlineStaleMonitor::Evaluate(double Now)
{ TArray<TPair<FString,bool>> Changed; for (auto& Pair: Entries) { FEntry& E=Pair.Value; const bool bStale=!E.bSeen || Now-E.Last>E.MaxAge; if (bStale!=E.bStale) { E.bStale=bStale; Changed.Emplace(Pair.Key,bStale); } } for (const auto& Pair:Changed) OnStale.Broadcast(Pair.Key,Pair.Value); }
bool URedlineStaleMonitor::IsFresh(const FString& Topic,double Now) const
{ const FEntry* E=Entries.Find(Topic); return E && E->bSeen && Now-E->Last<=E->MaxAge && Now>=E->Last; }
double URedlineStaleMonitor::Age(const FString& Topic,double Now) const
{ const FEntry* E=Entries.Find(Topic); return E && E->bSeen ? FMath::Max(0.0,Now-E->Last) : TNumericLimits<double>::Max(); }
