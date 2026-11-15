#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineStormFX.generated.h"
class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class APostProcessVolume;
class UExponentialHeightFogComponent;
class ARedlineOverlay;
class AHUD;
class UCanvas;

/** SCENARIO presentation: wind-blown sand near the ground and the crew-side view of the SEP storm.
 *  Wind, gusts and the storm-time sand are authored drama, not measured Mars weather: a solar particle
 *  event is radiation, and the HUD says so while the gust runs. The storm state itself follows the real
 *  ROS SEP alert (/env/dose_rate, ARCHIVE RAD replay). Camera speckles scale with the replayed dose ratio,
 *  as energetic particles mark real rover camera frames. -RedlineStormPreview=<s> forces the storm after
 *  s seconds for look development and filming without ROS; the HUD then shows a PREVIEW label. */
UCLASS()
class REDLINE_API ARedlineStormFX : public AActor
{
    GENERATED_BODY()
public:
    ARedlineStormFX();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;
    /** Storm level 0..1: rises over ~6 s on an alert, settles over ~12 s after it. */
    static float ApproachStorm(float Current,float Target,float DeltaSeconds);
    /** Camera speckles per frame: none without a storm, more with a higher dose ratio, bounded. */
    static int32 SpeckleCount(float Storm,double DoseRatio);
    /** Live sand streaks: a calm baseline, up to the pool size in a full storm. */
    static int32 ActiveStreaks(float Storm);
    static constexpr int32 MaxStreaks=240;
    static constexpr int32 MaxSheets=44;
    float GetStorm() const {return Storm;}
private:
    struct FGrain {FVector Pos=FVector::ZeroVector;FVector Vel=FVector::ZeroVector;float BaseZ=0,Hop=0,Age=0,Life=1,Len=100,Thick=10;bool bLive=false;};
    TArray<FGrain> Streaks,Sheets;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> StreakPlanes;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> SheetPlanes;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> StreakMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SheetMaterial;
    UPROPERTY(Transient) TObjectPtr<APostProcessVolume> Post;
    UPROPERTY(Transient) TObjectPtr<ARedlineOverlay> Overlay;
    struct FFogBase {TWeakObjectPtr<UExponentialHeightFogComponent> Fog;float Density=0;FLinearColor Color=FLinearColor::Black;};
    TArray<FFogBase> Fogs;
    FDelegateHandle HudHandle;
    double PreviewAt=-1,NextOutdoorCheck=0;
    double DoseRatio=1;
    float Storm=0,Time=0;
    bool bOutdoors=true,bPreviewActive=false,bLiveAlert=false,bLookDevPending=false;
    FVector WindDir=FVector(.94f,.34f,0.f);
    void Spawn(FGrain& G,const FVector& Viewer,bool bSheet,bool bAnywhere);
    float GroundZ(const FVector& At,float Fallback) const;
    void UpdatePlanes(TArray<FGrain>& Pool,TArray<TObjectPtr<UStaticMeshComponent>>& Planes,int32 Active,bool bSheet,const FVector& Viewer,const FVector& Forward,float SpeedScale,float Dt);
    void UpdateLook();
    void DrawSpeckles(AHUD* Hud,UCanvas* Canvas);
};
