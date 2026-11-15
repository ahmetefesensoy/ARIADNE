#include "RedlineFilmView.h"
#include "RedlineRoverActor.h"
#include "RedlineDroneActor.h"
#include "RedlineCampaignConsole.h"
#include "RedlineCoords.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "EngineUtils.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "RedlineTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"

ARedlineFilmView::ARedlineFilmView(){PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickGroup=TG_PostUpdateWork;SetActorEnableCollision(false);}
void ARedlineFilmView::BeginPlay()
{
    Super::BeginPlay();Camera=GetWorld()->SpawnActor<ACameraActor>();if(Camera)Camera->GetCameraComponent()->SetFieldOfView(55);
    FString Start;if(FParse::Value(FCommandLine::Get(),TEXT("RedlineFilmView="),Start))Select(Start==TEXT("drone") ? 2 : Start==TEXT("rover") ? 1 : Start==TEXT("task") ? 3 : 0);
    FString Path,Raw;if(FParse::Value(FCommandLine::Get(),TEXT("RedlineFilmRocks="),Path) && FFileHelper::LoadFileToString(Raw,*Path) && Raw.Len()<64000)
    {
        auto J=FRedlineJson::Parse(Raw);const TArray<TSharedPtr<FJsonValue>>* Rocks=nullptr;FString Schema;
        auto* Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Filming/Rocks/SM_rock_07.SM_rock_07"));
        if(J && Mesh && J->TryGetStringField(TEXT("schema"),Schema) && Schema==TEXT("redline.filming.rocks.v1") && J->TryGetArrayField(TEXT("rocks"),Rocks) && Rocks->Num()<=16)
        for(auto Value:*Rocks)
        {
            auto R=Value->AsObject();const TArray<TSharedPtr<FJsonValue>> *P=nullptr,*S=nullptr;double Yaw=0;
            if(!R || !R->TryGetArrayField(TEXT("map_xyz_m"),P) || P->Num()!=3 || !R->TryGetArrayField(TEXT("source_scale"),S) || S->Num()!=3 || !R->TryGetNumberField(TEXT("yaw_rad"),Yaw))continue;
            FVector Map((*P)[0]->AsNumber(),(*P)[1]->AsNumber(),(*P)[2]->AsNumber()),Scale((*S)[0]->AsNumber(),(*S)[1]->AsNumber(),(*S)[2]->AsNumber());
            if(Map.ContainsNaN() || Scale.ContainsNaN() || !FMath::IsFinite(Yaw) || Scale.GetMin()<=0 || Scale.GetMax()>20)continue;
            auto* Rock=GetWorld()->SpawnActor<AStaticMeshActor>(URedlineCoords::RosToUeLocation(Map),FRotator(0,-FMath::RadiansToDegrees(Yaw),0));if(!Rock)continue;
            Rock->GetStaticMeshComponent()->SetStaticMesh(Mesh);Rock->SetActorScale3D(Scale);Rock->SetActorEnableCollision(false);Rock->Tags.Add(TEXT("SCENARIO_MatchedGazeboRock"));
            // Gazebo alone supplies robot collision. This exact-pose copy is
            // local presentation and is never published into a costmap.
        }
    }
}
void ARedlineFilmView::Select(int32 NewMode){Mode=NewMode;auto* PC=GetWorld()->GetFirstPlayerController();if(PC){if(Mode && Camera)PC->SetViewTarget(Camera);else if(PC->GetPawn())PC->SetViewTarget(PC->GetPawn());}}
void ARedlineFilmView::Tick(float Delta)
{
    Super::Tick(Delta);auto* PC=GetWorld()->GetFirstPlayerController();auto* View=GetWorld()->GetGameViewport();if(!PC || !Camera)return;
    if(View && View->Viewport && View->Viewport->HasFocus())
    {if(PC->WasInputKeyJustPressed(EKeys::F5))Select(1);if(PC->WasInputKeyJustPressed(EKeys::F6))Select(2);if(PC->WasInputKeyJustPressed(EKeys::F7))Select(0);if(PC->WasInputKeyJustPressed(EKeys::F9))Select(3);}
    if(!Mode)return;FVector Target;bool Found=false;double Distance=500,Height=200;
    if(Mode==1 || Mode==2)for(TActorIterator<ARedlineRoverActor> It(GetWorld());It;++It)
    {
        const bool Drone=It->IsA<ARedlineDroneActor>();if(Drone!=(Mode==2) || It->AppliedPoseCount<=0)continue;
        Target=It->GetActorLocation()+FVector(0,0,Mode==1 ? 65 : 0);Found=true;Distance=Mode==1 ? 550 : 450;Height=Mode==1 ? 170 : 100;break;
    }
    if(Mode==3)for(TActorIterator<ARedlineCampaignConsole> It(GetWorld());It;++It)if(It->Fresh())
    {FVector Map=It->TaskMap(),Ground;if(PC->GetPawn())Map.Z=PC->GetPawn()->GetActorLocation().Z/100;if(URedlineCoords::TraceTerrainHeight(this,Map,500,Ground)){Target=URedlineCoords::RosToUeLocation(Ground)+FVector(0,0,25);Found=true;Distance=240;Height=110;}break;}
    if(!Found)return;Angle+=FMath::Clamp(double(Delta),0.,.1)*.025;
    FVector Position=Target+FVector(FMath::Cos(Angle)*Distance,FMath::Sin(Angle)*Distance,Height);
    FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(RedlineFilmCamera),true,this);Query.AddIgnoredActor(Camera);
    if(GetWorld()->LineTraceSingleByChannel(Hit,Target+FVector(0,0,20),Position,ECC_Camera,Query))Position=Hit.ImpactPoint+(Target-Hit.ImpactPoint).GetSafeNormal()*15;
    Camera->SetActorLocationAndRotation(Position,(Target-Position).Rotation());if(PC->GetViewTarget()!=Camera)PC->SetViewTarget(Camera);
}
void ARedlineFilmView::EndPlay(const EEndPlayReason::Type Reason){Select(0);if(Camera)Camera->Destroy();Super::EndPlay(Reason);}
