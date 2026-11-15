#include "RedlineOverlay.h"
#include "RedlineBridgeSubsystem.h"
#include "RedlineCoords.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "Components/DecalComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "DrawDebugHelpers.h"
#include "GameFramework/PlayerController.h"

ARedlineOverlay::ARedlineOverlay()
{
    PrimaryActorTick.bCanEverTick=true;
    FieldProjection=CreateDefaultSubobject<UDecalComponent>(TEXT("DerivedMarginProjection"));
    RootComponent=FieldProjection;FieldProjection->SetRelativeRotation(FRotator(-90,0,0));
}
void ARedlineOverlay::BeginPlay()
{
    Super::BeginPlay();
    if(auto* GI=GetGameInstance())Bridge=GI->GetSubsystem<URedlineBridgeSubsystem>();
    if(!Bridge)return;
    TopicHandle=Bridge->OnTopic.AddUObject(this,&ARedlineOverlay::Receive);
    Bridge->Subscribe(TEXT("/redline/tiles/margin_min"),TEXT("redline_msgs/msg/FieldTile"),500,5);
    Bridge->Subscribe(TEXT("/redline/redline"),TEXT("redline_msgs/msg/RedLine"),200,5);
    Bridge->Subscribe(TEXT("/crew/EV1/state"),TEXT("redline_msgs/msg/CrewState"),100,3);
    Bridge->Subscribe(TEXT("/env/dose_rate"),TEXT("redline_msgs/msg/DoseRate"),200,5);
}
void ARedlineOverlay::EndPlay(const EEndPlayReason::Type Reason)
{if(Bridge)Bridge->OnTopic.Remove(TopicHandle);Super::EndPlay(Reason);}
bool ARedlineOverlay::Fresh(double Receipt,double MaxAge) const
{
    return Bridge && (Bridge->IsConnected() || Bridge->IsOfflineReplay()) && Receipt>=0 && FPlatformTime::Seconds()-Receipt<=MaxAge;
}
void ARedlineOverlay::Receive(const FString& Topic,const TSharedPtr<FJsonObject>& Json)
{
    check(IsInGameThread());FString Error;const double Now=FPlatformTime::Seconds();bool OK=true;
    if(Topic==TEXT("/redline/tiles/margin_min"))
    {OK=FRedlineFieldTile::Parse(Json,Tile,Error);TileReceipt=OK ? Now : -1;if(OK){++AcceptedTiles;UploadTile();}}
    else if(Topic==TEXT("/redline/redline"))
    {OK=FRedlineEVALine::Parse(Json,Line,Error);LineReceipt=OK ? Now : -1;if(OK)++AcceptedLines;}
    else if(Topic==TEXT("/crew/EV1/state"))
    {OK=FRedlineEVACrew::Parse(Json,Crew,Error);CrewReceipt=OK ? Now : -1;if(OK)++AcceptedCrew;}
    else if(Topic==TEXT("/env/dose_rate"))
    {OK=FRedlineEVADose::Parse(Json,Dose,Error);DoseReceipt=OK ? Now : -1;if(OK)++AcceptedDose;}
    else return;
    if(!OK){++Rejected;UE_LOG(LogRedlineBridge,Warning,TEXT("EVA rejected %s: %s"),*Topic,*Error);}
    if((Topic==TEXT("/redline/redline") && AcceptedLines && AcceptedLines%20==0) || (AcceptedTiles==1 && Topic.Contains(TEXT("tiles"))))
        UE_LOG(LogRedlineBridge,Display,TEXT("EVA view tiles=%d lines=%d crew=%d dose=%d rejected=%d margin=%.3f"),AcceptedTiles,AcceptedLines,AcceptedCrew,AcceptedDose,Rejected,Line.MarginMinutes);
}
void ARedlineOverlay::UploadTile()
{
    // Ownership of upload data/region passes to the render-command cleanup;
    // no UObject is captured by a background callback.
    const int32 Bytes=Tile.Width*Tile.Height*4;
    uint8* Pixels=static_cast<uint8*>(FMemory::Malloc(Bytes));
    for(int32 I=0;I<Tile.Pixels.Num();++I)
    {
        const bool Known=Tile.Pixels[I]!=Tile.Nodata;const double M=Tile.Pixels[I]*Tile.Scale+Tile.Offset;
        const FColor C=!Known ? FColor(45,45,45,0) : M<0 ? FColor(220,40,28,85) : M<30 ? FColor(235,175,25,65) : FColor(25,125,80,38);
        Pixels[I*4]=C.B;Pixels[I*4+1]=C.G;Pixels[I*4+2]=C.R;Pixels[I*4+3]=C.A;
    }
    if(!FieldTexture || FieldTexture->GetSizeX()!=Tile.Width || FieldTexture->GetSizeY()!=Tile.Height)
    {
        FieldTexture=UTexture2D::CreateTransient(Tile.Width,Tile.Height,PF_B8G8R8A8);
        FieldTexture->SRGB=false;FieldTexture->Filter=TF_Nearest;FieldTexture->UpdateResource();
    }
    auto* Region=new FUpdateTextureRegion2D(0,0,0,0,Tile.Width,Tile.Height);
    FieldTexture->UpdateTextureRegions(0,1,Region,Tile.Width*4,4,Pixels,
        [](uint8* Data,const FUpdateTextureRegion2D* R){FMemory::Free(Data);delete R;});
    if(FieldMaterial)
    {
        if(!FieldProjection->GetDecalMaterial())FieldProjection->SetDecalMaterial(FieldMaterial);
        auto* Material=Cast<UMaterialInstanceDynamic>(FieldProjection->GetDecalMaterial());
        if(!Material)Material=FieldProjection->CreateDynamicMaterialInstance();
        if(Material){Material->SetTextureParameterValue(TEXT("FieldTile"),FieldTexture);Material->SetVectorParameterValue(TEXT("GridOrigin"),FLinearColor(Tile.Origin.X*100,Tile.Origin.Y*100,0));Material->SetVectorParameterValue(TEXT("GridSize"),FLinearColor(Tile.Width*Tile.Resolution*100,Tile.Height*Tile.Resolution*100,0));}
        const double X=Tile.Origin.X+Tile.Width*Tile.Resolution*.5,Y=Tile.Origin.Y+Tile.Height*Tile.Resolution*.5;
        double Z=-359800.;if(auto* P=GetWorld()->GetFirstPlayerController())if(APawn* Pawn=P->GetPawn())Z=Pawn->GetActorLocation().Z;
        SetActorLocation(FVector(X*100,-Y*100,Z+10000));SetActorRotation(FRotator(-90,0,0));
        FieldProjection->DecalSize=FVector(100000,Tile.Height*Tile.Resolution*50,Tile.Width*Tile.Resolution*50);
    }
}
bool ARedlineOverlay::GroundPoint(FVector Map,FVector& World)
{
    const FIntPoint Key(FMath::RoundToInt(Map.X*16),FMath::RoundToInt(Map.Y*16));
    if(const double* Height=Heights.Find(Key))Map.Z=*Height;
    else
    {
        FVector Ground;Map.Z=-3598.;if(auto* PC=GetWorld()->GetFirstPlayerController())if(APawn* P=PC->GetPawn())Map.Z=P->GetActorLocation().Z/100;
        if(!URedlineCoords::TraceTerrainHeight(this,Map,150,Ground))return false;
        Map.Z=Ground.Z;Heights.Add(Key,Map.Z);
    }
    World=URedlineCoords::RosToUeLocation(Map)+FVector(0,0,12);return true;
}
void ARedlineOverlay::Tick(float Delta)
{
    Super::Tick(Delta);
    FieldProjection->SetVisibility(Fresh(TileReceipt));
    if(!Fresh(LineReceipt))return;
    auto* PC=GetWorld()->GetFirstPlayerController();if(!PC || !PC->GetPawn())return;
    const FVector Here=URedlineCoords::UeToRosLocation(PC->GetPawn()->GetActorLocation());
    if(Heights.Num()>20000)Heights.Reset();int32 Drawn=0;
    auto Draw=[&](const TArray<TArray<FVector>>& Rings,FColor Color)
    {
        for(const auto& Ring:Rings)for(int32 I=0;I<Ring.Num() && Drawn<400;++I)
        {
            FVector A=Ring[I],B=Ring[(I+1)%Ring.Num()];A.Z=Here.Z;B.Z=Here.Z;
            if(FMath::PointDistToSegment(Here,A,B)>200)continue;
            FVector WA,WB;if(GroundPoint(A,WA) && GroundPoint(B,WB)){DrawDebugLine(GetWorld(),WA,WB,Color,false,0,0,5);++Drawn;}
        }
    };
    Draw(Line.Abort,FColor::Red);Draw(Line.Terminate,FColor::Yellow);
}
