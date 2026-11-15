#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "RedlineCoords.generated.h"

UCLASS()
class REDLINEBRIDGE_API URedlineCoords : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintPure, Category="REDLINE|Coordinates") static FVector RosToUeLocation(FVector Metres);
    UFUNCTION(BlueprintPure, Category="REDLINE|Coordinates") static FVector UeToRosLocation(FVector Centimetres);
    UFUNCTION(BlueprintPure, Category="REDLINE|Coordinates") static FQuat RosToUeRotation(FQuat RosQuaternion);
    UFUNCTION(BlueprintPure, Category="REDLINE|Coordinates") static FQuat UeToRosRotation(FQuat UeQuaternion);
    /** Half-open map grid bounds; returns INDEX_NONE outside the grid. */
    UFUNCTION(BlueprintPure, Category="REDLINE|Coordinates") static int32 MapToCellIndex(FVector MapMetres, FVector OriginMetres, double ResolutionMetres, int32 Width, int32 Height);
    /** Query-only acceptance check. ROS map metres in/out; never moves a robot. */
    UFUNCTION(BlueprintCallable, Category="REDLINE|Verification", meta=(WorldContext="WorldContextObject"))
    static bool TraceTerrainHeight(const UObject* WorldContextObject, FVector MapMetres, double HalfRangeMetres, FVector& HitMapMetres);
};
