#include "RedlineCoords.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "CollisionQueryParams.h"
FVector URedlineCoords::RosToUeLocation(FVector P) { return FVector(100.0*P.X, -100.0*P.Y, 100.0*P.Z); }
FVector URedlineCoords::UeToRosLocation(FVector P) { return FVector(P.X/100.0, -P.Y/100.0, P.Z/100.0); }
FQuat URedlineCoords::RosToUeRotation(FQuat Q) { return FQuat(-Q.X, Q.Y, -Q.Z, Q.W); }
FQuat URedlineCoords::UeToRosRotation(FQuat Q) { return FQuat(-Q.X, Q.Y, -Q.Z, Q.W); }
int32 URedlineCoords::MapToCellIndex(FVector P, FVector Origin, double Resolution, int32 Width, int32 Height)
{
    if (!FMath::IsFinite(Resolution) || Resolution <= 0 || Width <= 0 || Height <= 0 || P.ContainsNaN() || Origin.ContainsNaN()) return INDEX_NONE;
    const double X = (P.X-Origin.X)/Resolution, Y = (P.Y-Origin.Y)/Resolution;
    if (X < 0 || Y < 0 || X >= Width || Y >= Height || static_cast<int64>(Width)*Height > MAX_int32) return INDEX_NONE;
    return FMath::FloorToInt(Y)*Width + FMath::FloorToInt(X);
}
bool URedlineCoords::TraceTerrainHeight(const UObject* Context,FVector P,double HalfRange,FVector& HitMapMetres)
{
    HitMapMetres=FVector::ZeroVector;
    if (!GEngine || !Context || P.ContainsNaN() || !FMath::IsFinite(HalfRange) || HalfRange<=0) return false;
    UWorld* World=GEngine->GetWorldFromContextObject(Context,EGetWorldErrorMode::ReturnNull);
    if (!World) return false;
    const FVector Start=RosToUeLocation(P+FVector(0,0,HalfRange));
    const FVector End=RosToUeLocation(P-FVector(0,0,HalfRange));
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(RedlineTerrainVerification),true);
    if (!World->LineTraceSingleByChannel(Hit,Start,End,ECC_Visibility,Query) || !Hit.bBlockingHit) return false;
    HitMapMetres=UeToRosLocation(Hit.ImpactPoint); return true;
}
