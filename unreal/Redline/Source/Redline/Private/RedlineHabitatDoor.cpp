#include "RedlineHabitatDoor.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "CollisionShape.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "Materials/MaterialInterface.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"
#include "UObject/ConstructorHelpers.h"

ARedlineHabitatDoor::ARedlineHabitatDoor()
{
    PrimaryActorTick.bCanEverTick=true;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("DoorOpening"));
    RootComponent->SetMobility(EComponentMobility::Movable);
    LeftPanel=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LeftSlidingPanel"));
    RightPanel=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RightSlidingPanel"));
    CenterSeal=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ClosedCenterSeal"));
    FrameLeft=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FrameLeft"));
    FrameRight=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FrameRight"));
    FrameTop=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FrameTop"));
    LeftLock=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LeftLatch"));
    RightLock=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RightLatch"));
    AmberLens=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("MovingWarningLens"));
    ReadyLens=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PassageReadyLens"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    for(auto* Mesh:{LeftPanel.Get(),RightPanel.Get(),CenterSeal.Get(),FrameLeft.Get(),FrameRight.Get(),FrameTop.Get(),LeftLock.Get(),RightLock.Get(),AmberLens.Get(),ReadyLens.Get()})
    {
        Mesh->SetupAttachment(RootComponent);Mesh->SetMobility(EComponentMobility::Movable);
        if(Cube.Succeeded())Mesh->SetStaticMesh(Cube.Object);
        Mesh->SetSimulatePhysics(false);Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Mesh->SetGenerateOverlapEvents(false);Mesh->SetReceivesDecals(false);
    }
    for(auto* Mesh:{LeftPanel.Get(),RightPanel.Get(),FrameLeft.Get(),FrameRight.Get(),FrameTop.Get()})
    {
        Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Mesh->SetCollisionResponseToAllChannels(ECR_Ignore);
        Mesh->SetCollisionResponseToChannel(ECC_Pawn,ECR_Block);Mesh->SetCollisionResponseToChannel(ECC_Camera,ECR_Block);
        Mesh->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    }
    WarningLight=CreateDefaultSubobject<UPointLightComponent>(TEXT("DoorStatusLight"));WarningLight->SetupAttachment(RootComponent);
    WarningLight->SetMobility(EComponentMobility::Movable);WarningLight->SetAttenuationRadius(100);WarningLight->SetCastShadows(false);
    DoorAudio=CreateDefaultSubobject<UAudioComponent>(TEXT("DoorMotorAudio"));DoorAudio->SetupAttachment(RootComponent);
    DoorAudio->bAutoActivate=false;DoorAudio->bIsUISound=false;DoorAudio->SetVolumeMultiplier(.28f);
    DoorAudio->bOverrideAttenuation=true;DoorAudio->AttenuationOverrides.bAttenuate=true;DoorAudio->AttenuationOverrides.bSpatialize=true;
    DoorAudio->AttenuationOverrides.AttenuationShapeExtents=FVector(120,0,0);DoorAudio->AttenuationOverrides.FalloffDistance=650;
    ApplyPose();
}

bool ARedlineHabitatDoor::ConfigureOpening(const FTransform& ClosedTransform,FVector SizeCm)
{
    if(ClosedTransform.ContainsNaN() || SizeCm.ContainsNaN() || SizeCm.X<=0 || SizeCm.Y<80 || SizeCm.Z<150 || SizeCm.Y>500 || SizeCm.Z>500)return false;
    SetActorLocationAndRotation(ClosedTransform.GetLocation(),ClosedTransform.GetRotation());SetActorScale3D(FVector::OneVector);
    OpeningSize=SizeCm;State=ERedlineHabitatDoorState::Closed;Openness=UnlockProgress=StateElapsed=HoldRemaining=VisualElapsed=0;SafetyReopenCount=0;
    auto* Paint=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Prologue/Materials/M_AirlockPaint.M_AirlockPaint"));
    auto* Frame=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Prologue/Materials/M_GraphiteFrame.M_GraphiteFrame"));
    auto* Amber=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Prologue/Materials/M_WarmPractical.M_WarmPractical"));
    auto* Blue=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Prologue/Materials/M_BluePractical.M_BluePractical"));
    if(Paint)for(auto* Mesh:{LeftPanel.Get(),RightPanel.Get()})Mesh->SetMaterial(0,Paint);
    if(Frame)for(auto* Mesh:{FrameLeft.Get(),FrameRight.Get(),FrameTop.Get(),CenterSeal.Get(),LeftLock.Get(),RightLock.Get()})Mesh->SetMaterial(0,Frame);
    if(Amber)AmberLens->SetMaterial(0,Amber);if(Blue)ReadyLens->SetMaterial(0,Blue);
    SlideSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Prologue/Audio/SFX_airlock_door.SFX_airlock_door"));
    bConfigured=true;ApplyPose();return true;
}

bool ARedlineHabitatDoor::InitializeFromMarker(AActor* Source)
{
    if(!IsValid(Source) || Source==this)return false;
    auto* Mesh=Source->FindComponentByClass<UStaticMeshComponent>();
    if(!Mesh || !Mesh->GetStaticMesh())return false;
    const FBox Box=Mesh->GetStaticMesh()->GetBoundingBox();
    const FVector Size=Box.GetSize()*Mesh->GetComponentScale().GetAbs();
    const FVector Center=Mesh->GetComponentTransform().TransformPosition(Box.GetCenter());
    if(!ConfigureOpening(FTransform(Mesh->GetComponentQuat(),Center),Size))return false;
    SourceMarker=Source;Source->SetActorHiddenInGame(true);Source->SetActorEnableCollision(false);
    return true;
}

bool ARedlineHabitatDoor::HumanApproaching() const
{
    for(TActorIterator<ACharacter> It(GetWorld());It;++It)if(IsValid(*It))
    {
        const FVector Local=GetActorTransform().InverseTransformPosition(It->GetActorLocation());
        if(FMath::Abs(Local.X)<225 && FMath::Abs(Local.Y)<OpeningSize.Y*.5+70 && FMath::Abs(Local.Z)<OpeningSize.Z*.5+100)return true;
    }
    return false;
}

bool ARedlineHabitatDoor::IsPassageBlocked() const
{
    if(!bConfigured || !GetWorld())return false;
    // A capsule in the full closing envelope keeps the door open even when
    // auto-proximity is disabled by a cinematic. Hidden real players still count.
    for(TActorIterator<ACharacter> It(GetWorld());It;++It)if(auto* Capsule=It->GetCapsuleComponent())
    {
        const FVector Local=GetActorTransform().InverseTransformPosition(Capsule->GetComponentLocation());
        const double Radius=Capsule->GetScaledCapsuleRadius(),Half=Capsule->GetScaledCapsuleHalfHeight();
        if(FMath::Abs(Local.X)<=OpeningSize.X*.5+Radius+22 && FMath::Abs(Local.Y)<=OpeningSize.Y*.5+Radius+6 && FMath::Abs(Local.Z)<=OpeningSize.Z*.5+Half)return true;
    }
    TArray<FOverlapResult> Hits;FCollisionQueryParams Query(SCENE_QUERY_STAT(RedlineDoorPassage),false,this);
    if(SourceMarker.IsValid())Query.AddIgnoredActor(SourceMarker.Get());
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_Pawn);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    GetWorld()->OverlapMultiByObjectType(Hits,GetActorLocation(),GetActorQuat(),Objects,
        FCollisionShape::MakeBox(FVector(OpeningSize.X*.5+22,OpeningSize.Y*.5+6,OpeningSize.Z*.5-3)),Query);
    for(const FOverlapResult& Hit:Hits)if(auto* Component=Hit.GetComponent())
        if(Component->GetCollisionEnabled()!=ECollisionEnabled::NoCollision && Component->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block)return true;
    return false;
}

void ARedlineHabitatDoor::EnterState(ERedlineHabitatDoorState NewState)
{
    if(State==NewState)return;State=NewState;StateElapsed=0;
    if((State==ERedlineHabitatDoorState::Opening || State==ERedlineHabitatDoorState::Closing) && SlideSound)
    {DoorAudio->Stop();DoorAudio->SetSound(SlideSound);DoorAudio->Play();}
}

void ARedlineHabitatDoor::AdvanceAnimation(float DeltaSeconds,bool OpenRequest,bool PassageBlocked)
{
    if(!bConfigured || !FMath::IsFinite(DeltaSeconds) || DeltaSeconds<=0)return;
    const double Dt=FMath::Min(double(DeltaSeconds),.2);StateElapsed+=Dt;VisualElapsed+=Dt;
    if(OpenRequest || PassageBlocked)HoldRemaining=.85;else HoldRemaining=FMath::Max(0.,HoldRemaining-Dt);
    const bool KeepOpen=OpenRequest || PassageBlocked || HoldRemaining>0;
    if(PassageBlocked && (State==ERedlineHabitatDoorState::Closing || State==ERedlineHabitatDoorState::Latching))
    {++SafetyReopenCount;UnlockProgress=1;EnterState(ERedlineHabitatDoorState::Opening);}
    switch(State)
    {
    case ERedlineHabitatDoorState::Closed:
        if(KeepOpen)EnterState(ERedlineHabitatDoorState::Unlocking);break;
    case ERedlineHabitatDoorState::Unlocking:
        UnlockProgress=FMath::Clamp(StateElapsed/.35,0.,1.);
        if(UnlockProgress>=1)EnterState(ERedlineHabitatDoorState::Opening);break;
    case ERedlineHabitatDoorState::Opening:
        Openness=FMath::Min(1.,Openness+Dt/1.1);
        if(Openness>=1)EnterState(ERedlineHabitatDoorState::Open);break;
    case ERedlineHabitatDoorState::Open:
        if(!KeepOpen)EnterState(ERedlineHabitatDoorState::Closing);break;
    case ERedlineHabitatDoorState::Closing:
        if(KeepOpen){EnterState(ERedlineHabitatDoorState::Opening);break;}
        Openness=FMath::Max(0.,Openness-Dt/1.1);
        if(Openness<=0)EnterState(ERedlineHabitatDoorState::Latching);break;
    case ERedlineHabitatDoorState::Latching:
        if(KeepOpen){EnterState(ERedlineHabitatDoorState::Unlocking);break;}
        UnlockProgress=1-FMath::Clamp(StateElapsed/.3,0.,1.);
        if(UnlockProgress<=0)EnterState(ERedlineHabitatDoorState::Closed);break;
    }
    ApplyPose();
}

void ARedlineHabitatDoor::ApplyPose()
{
    const double W=OpeningSize.Y,H=OpeningSize.Z,D=OpeningSize.X;
    const double Ease=Openness*Openness*(3-2*Openness),Travel=(W*.5+5)*Ease;
    auto Part=[](UStaticMeshComponent* Component,FVector At,FVector Size){Component->SetRelativeLocation(At);Component->SetRelativeScale3D(Size/100.);};
    Part(LeftPanel,FVector(0,-W*.25-Travel,0),FVector(D,W*.5-1,H));
    Part(RightPanel,FVector(0,W*.25+Travel,0),FVector(D,W*.5-1,H));
    Part(CenterSeal,FVector(D*.5+.3,0,0),FVector(1.2,2,H-4));CenterSeal->SetVisibility(Openness<.015);
    Part(FrameLeft,FVector(0,-W*.5-6,0),FVector(D+8,12,H+12));
    Part(FrameRight,FVector(0,W*.5+6,0),FVector(D+8,12,H+12));
    Part(FrameTop,FVector(0,0,H*.5+6),FVector(D+8,W+24,12));
    Part(LeftLock,FVector(D*.5+2+UnlockProgress*3,-W*.12-Travel,15),FVector(4,15,4));
    Part(RightLock,FVector(D*.5+2+UnlockProgress*3,W*.12+Travel,15),FVector(4,15,4));
    Part(AmberLens,FVector(D*.5+5,-12,H*.5+6),FVector(2,15,3));
    Part(ReadyLens,FVector(D*.5+5,12,H*.5+6),FVector(2,15,3));
    const bool Ready=State==ERedlineHabitatDoorState::Open,Moving=State!=ERedlineHabitatDoorState::Closed && !Ready;
    AmberLens->SetVisibility(!Ready);ReadyLens->SetVisibility(Ready);
    WarningLight->SetRelativeLocation(FVector(D*.5+18,0,H*.5));
    WarningLight->SetLightColor(Ready ? FLinearColor(.15,.8,1) : FLinearColor(1,.35,.07));
    WarningLight->SetIntensity(Moving ? 90+80*FMath::Sin(VisualElapsed*10) : Ready ? 65 : 18);
}

void ARedlineHabitatDoor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    AdvanceAnimation(DeltaSeconds,bPresentationOpen || (bAutomaticOpen && HumanApproaching()),IsPassageBlocked());
}
