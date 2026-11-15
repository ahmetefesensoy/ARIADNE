#pragma once
#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "RedlineSettings.generated.h"

UCLASS(Config=Game, DefaultConfig, meta=(DisplayName="REDLINE Bridge"))
class REDLINEBRIDGE_API URedlineSettings : public UDeveloperSettings
{
    GENERATED_BODY()
public:
    UPROPERTY(Config, EditAnywhere, Category="Connection") FString RosbridgeUrl = TEXT("ws://localhost:9090");
    UPROPERTY(Config, EditAnywhere, Category="Site") FString SiteId = TEXT("BXW");
    UPROPERTY(Config, EditAnywhere, Category="Site") FString ManifestPath;
    UPROPERTY(Config, EditAnywhere, Category="Connection", meta=(ClampMin="0.1")) double ReconnectInitialSec = 0.5;
    UPROPERTY(Config, EditAnywhere, Category="Connection", meta=(ClampMin="0.5")) double ReconnectMaxSec = 8.0;
    UPROPERTY(Config, EditAnywhere, Category="Freshness", meta=(ClampMin="0.1")) double TopicMaxAgeSec = 2.0;
    UPROPERTY(Config, EditAnywhere, Category="Connection", meta=(ClampMin="0.1")) double ServiceTimeoutSec = 5.0;
    UPROPERTY(Config, EditAnywhere, Category="Connection") bool bAutoConnect = true;
};
