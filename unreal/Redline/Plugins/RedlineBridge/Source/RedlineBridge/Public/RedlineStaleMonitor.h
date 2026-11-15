#pragma once
#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "RedlineStaleMonitor.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FRedlineStaleEvent, const FString&, Topic, bool, bStale);
UCLASS(BlueprintType)
class REDLINEBRIDGE_API URedlineStaleMonitor : public UObject
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintAssignable, Category="REDLINE") FRedlineStaleEvent OnStale;
    void Watch(const FString& Topic, double MaxAge, double Now);
    void Received(const FString& Topic, double Now);
    void Disconnected();
    void Evaluate(double Now);
    bool IsFresh(const FString& Topic, double Now) const;
    double Age(const FString& Topic, double Now) const;
private:
    struct FEntry { double MaxAge=2; double Last=0; bool bSeen=false; bool bStale=true; };
    TMap<FString,FEntry> Entries;
};
