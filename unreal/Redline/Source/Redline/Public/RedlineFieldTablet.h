#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineFieldTablet.generated.h"
class URedlineBridgeSubsystem;class UStaticMeshComponent;class UCanvasRenderTarget2D;class UTexture2D;
class UMaterialInstanceDynamic;class UCanvas;class UPoseableMeshComponent;class ARedlineAstronautCharacter;class ARedlineCampaignConsole;
UCLASS()
class REDLINE_API ARedlineFieldTablet : public AActor
{
    GENERATED_BODY()
public:
    ARedlineFieldTablet();
    virtual void BeginPlay() override;virtual void Tick(float Delta) override;virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    bool IsOpen()const{return bOpen || Raise>0;}
    bool Open();void Close(bool Immediate=false);
    static bool DecodeImage(const TSharedPtr<FJsonObject>& Json,TArray<uint8>& Pixels,int32& Width,int32& Height);
private:
    friend class FRedlineTabletImageTest;
    UPROPERTY(Transient) TObjectPtr<URedlineBridgeSubsystem> Bridge;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Shell;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Screen;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UPoseableMeshComponent> Arms;
    UPROPERTY(Transient) TObjectPtr<UCanvasRenderTarget2D> Display;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> RvizImage;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ScreenMaterial;
    TWeakObjectPtr<ARedlineAstronautCharacter> Human;TWeakObjectPtr<ARedlineCampaignConsole> Console;
    FDelegateHandle Handle;
    TSharedPtr<FJsonObject> Status;
    FString StreamId;
    double ImageAt=-1,StatusAt=-1,LastRender=-1,ImageStamp=-1;
    int32 Page=0,Sequence=-1,AcceptedFrames=0;
    float Raise=0;
    bool bOpen=false,bReady=false,bZoom=false,bOwnLock=false,bOldHidden=false,bOldOwnerNoSee=false,bOldFirstPerson=true;
    void Receive(const FString& Topic,const TSharedPtr<FJsonObject>& Json);
    bool StreamFresh()const;
    void UpdateGrip();
    void SolveArm(FName Upper,FName Lower,FName Hand,FVector Target,FVector Pole);
    UFUNCTION() void Render(UCanvas* Canvas,int32 Width,int32 Height);
};
