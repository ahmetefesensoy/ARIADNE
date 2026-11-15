#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "RedlineEVAImportLibrary.generated.h"
class USkeletalMesh;
class UAnimSequence;
class UStaticMesh;

UCLASS()
class REDLINE_API URedlineEVAImportLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Editor import conversion only: match the clip root to its own mesh bind scale. */
    UFUNCTION(BlueprintCallable,Category="REDLINE|Import")
    static bool NormalizeLocomotionRoot(USkeletalMesh* Mesh,UAnimSequence* Animation);
    /** Derive from immutable source keys on every call; repeated imports cannot accumulate root shift. */
    UFUNCTION(BlueprintCallable,Category="REDLINE|Import")
    static bool MakeSeatedIdle(USkeletalMesh* Mesh,UAnimSequence* SourceIdle,UAnimSequence* DerivedAnimation);
    /** Editor-only static architecture query collision; never enables rigid-body simulation. */
    UFUNCTION(BlueprintCallable,Category="REDLINE|Import")
    static bool PrepareInteriorQueryCollision(UStaticMesh* Mesh);
};
