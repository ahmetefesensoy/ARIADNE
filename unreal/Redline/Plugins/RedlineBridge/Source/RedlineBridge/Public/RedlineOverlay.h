#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineEVAData.h"
#include "RedlineOverlay.generated.h"
class URedlineBridgeSubsystem;
class UTexture2D;
class UDecalComponent;
class UMaterialInterface;

/** Technical T5 view. PNG/lines are ROS results, never a second planning implementation. */
UCLASS()
class REDLINEBRIDGE_API ARedlineOverlay : public AActor
{
    GENERATED_BODY()
public:
    ARedlineOverlay();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float Delta) override;
    void Receive(const FString& Topic,const TSharedPtr<FJsonObject>& Json);
    bool Fresh(double Receipt,double MaxAge=5) const;
    UPROPERTY(VisibleAnywhere,Category="REDLINE") TObjectPtr<UDecalComponent> FieldProjection;
    UPROPERTY(EditAnywhere,Category="REDLINE") TObjectPtr<UMaterialInterface> FieldMaterial;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> FieldTexture;
    FRedlineFieldTile Tile;
    FRedlineEVALine Line;
    FRedlineEVACrew Crew;
    FRedlineEVADose Dose;
    double TileReceipt=-1,LineReceipt=-1,CrewReceipt=-1,DoseReceipt=-1;
    int32 AcceptedTiles=0,AcceptedLines=0,AcceptedCrew=0,AcceptedDose=0,Rejected=0;
private:
    UPROPERTY(Transient) TObjectPtr<URedlineBridgeSubsystem> Bridge;
    FDelegateHandle TopicHandle;
    TMap<FIntPoint,double> Heights;
    void UploadTile();
    bool GroundPoint(FVector Map,FVector& World);
};
