#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "RedlineTypes.generated.h"

/** ROS stamp retained as physics/source time, never used for wall-time freshness. */
USTRUCT(BlueprintType)
struct REDLINEBRIDGE_API FRedlineOdometry
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="REDLINE") FString FrameId;
    UPROPERTY(BlueprintReadOnly, Category="REDLINE") FString ChildFrameId;
    UPROPERTY(BlueprintReadOnly, Category="REDLINE") double PhysicsStampSec = 0;
    UPROPERTY(BlueprintReadOnly, Category="REDLINE") FVector PositionMetres = FVector::ZeroVector;
    UPROPERTY(BlueprintReadOnly, Category="REDLINE") FQuat Orientation = FQuat::Identity;
    static bool Parse(const TSharedPtr<FJsonObject>& Json, FRedlineOdometry& Out, FString& Error);
};

struct REDLINEBRIDGE_API FRedlineJson
{
    static TSharedPtr<FJsonObject> Parse(const FString& Text);
    static FString Write(const TSharedRef<FJsonObject>& Json);
    static bool Vector(const TSharedPtr<FJsonObject>& Json, FVector& Out);
    static bool Quaternion(const TSharedPtr<FJsonObject>& Json, FQuat& Out);
    static bool Transform(const TSharedPtr<FJsonObject>& Json, FTransform& Out);
    static bool Stamp(const TSharedPtr<FJsonObject>& Json, double& Out);
};
