#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineFieldWork.h"
#include "RedlineTaskFilm.generated.h"
class ACameraActor;class ARedlineAstronautCharacter;class ARedlineSampleInteraction;class USceneComponent;class UStaticMeshComponent;class UCanvas;class UCanvasRenderTarget2D;class UMaterialInstanceDynamic;
/** Opt-in scripted filming fixture, never a live mission/measurement authority. */
UCLASS()
class REDLINE_API ARedlineTaskFilm : public AActor
{
    GENERATED_BODY()
public:
    ARedlineTaskFilm();virtual void BeginPlay() override;virtual void Tick(float Delta) override;virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    void DrawCaption(UCanvas* Canvas);
private:
    UPROPERTY(Transient) TObjectPtr<ACameraActor> Camera;
    UPROPERTY(Transient) TObjectPtr<ARedlineSampleInteraction> WorkPose;
    UPROPERTY(Transient) TObjectPtr<ARedlineAstronautCharacter> Human;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Props;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> BitPivot;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> LabTube;
    UPROPERTY(Transient) TObjectPtr<UCanvasRenderTarget2D> Screen;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ScreenMaterial;
    FRedlineFieldWork Work;
    FString Kind,Phase,ProductId;
    FVector Site=FVector::ZeroVector,Start=FVector::ZeroVector,CapOrigin=FVector::ZeroVector;
    double Began=-1,PreparedAt=-1;
    bool bStartedWork=false,bEndedWork=false,bIndoor=false;
    TSharedPtr<FJsonObject> Result;
    UStaticMeshComponent* Prop(const FString& Path,FVector Position,FVector Scale=FVector::OneVector);
    void PrepareDrill();void PrepareLab();
    UFUNCTION() void DrawLab(UCanvas* Canvas,int32 Width,int32 Height);
};
