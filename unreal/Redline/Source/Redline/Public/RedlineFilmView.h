#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RedlineFilmView.generated.h"
class ACameraActor;
UCLASS()
class REDLINE_API ARedlineFilmView : public AActor
{
    GENERATED_BODY()
public:
    ARedlineFilmView();virtual void BeginPlay() override;virtual void Tick(float Delta) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TObjectPtr<ACameraActor> Camera;
    int32 Mode=0;double Angle=0;
    void Select(int32 NewMode);
};
