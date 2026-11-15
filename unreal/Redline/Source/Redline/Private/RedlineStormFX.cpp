#include "RedlineStormFX.h"
#include "RedlineOverlay.h"
#include "CanvasItem.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/HUD.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"

DEFINE_LOG_CATEGORY_STATIC(LogRedlineStorm,Log,All);

namespace RedlineStorm
{
constexpr float StreakRadius=1600.f,SheetRadius=3600.f;
FLinearColor Lerp(const FLinearColor& A,const FLinearColor& B,float T){return A+(B-A)*T;}
}

ARedlineStormFX::ARedlineStormFX()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickGroup=TG_PostUpdateWork;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}
float ARedlineStormFX::ApproachStorm(float Current,float Target,float Dt)
{
    if(!FMath::IsFinite(Current))Current=0.f;
    if(!FMath::IsFinite(Target) || !FMath::IsFinite(Dt) || Dt<0.f)return FMath::Clamp(Current,0.f,1.f);
    Target=FMath::Clamp(Target,0.f,1.f);
    const float Rate=Target>Current ? 1.f/6.f : 1.f/12.f;
    return FMath::Clamp(Current+FMath::Clamp(Target-Current,-Rate*Dt,Rate*Dt),0.f,1.f);
}
int32 ARedlineStormFX::SpeckleCount(float Storm,double DoseRatio)
{
    if(!FMath::IsFinite(Storm) || !FMath::IsFinite(DoseRatio) || Storm<=.02f)return 0;
    const double Ratio=FMath::Max(1.,DoseRatio);
    return FMath::Clamp(FMath::RoundToInt(FMath::Clamp(Storm,0.f,1.f)*(6.+12.*FMath::Log2(Ratio))),0,90);
}
int32 ARedlineStormFX::ActiveStreaks(float Storm)
{
    const float S=FMath::IsFinite(Storm) ? FMath::Clamp(Storm,0.f,1.f) : 0.f;
    return FMath::RoundToInt(FMath::Lerp(70.f,float(MaxStreaks),S));
}
void ARedlineStormFX::BeginPlay()
{
    Super::BeginPlay();
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Plane.Plane"));
    // Light sand material when prepared (scripts/prepare_wind_sand.py); the darker footstep dust otherwise.
    auto* Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Campaign/Materials/M_WindSand.M_WindSand"));
    if(!Material)Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Campaign/Materials/M_SurfaceDust.M_SurfaceDust"));
    if(Mesh && Material)
    {
        StreakMaterial=UMaterialInstanceDynamic::Create(Material,this);
        SheetMaterial=UMaterialInstanceDynamic::Create(Material,this);
        auto Make=[&](int32 Count,UMaterialInstanceDynamic* Mat,TArray<TObjectPtr<UStaticMeshComponent>>& Out)
        {
            for(int32 I=0;I<Count;++I)
            {
                auto* Plane=NewObject<UStaticMeshComponent>(this);Plane->SetupAttachment(RootComponent);Plane->SetStaticMesh(Mesh);
                Plane->SetMobility(EComponentMobility::Movable);Plane->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                Plane->SetCastShadow(false);Plane->SetMaterial(0,Mat);Plane->SetVisibility(false);Plane->RegisterComponent();Out.Add(Plane);
            }
        };
        Make(MaxStreaks,StreakMaterial,StreakPlanes);Make(MaxSheets,SheetMaterial,SheetPlanes);
        Streaks.SetNum(MaxStreaks);Sheets.SetNum(MaxSheets);
    }
    else UE_LOG(LogRedlineStorm,Warning,TEXT("Wind sand disabled: plane or M_SurfaceDust missing; storm grading still runs"));
    FActorSpawnParameters Params;Params.Owner=this;
    Post=GetWorld()->SpawnActor<APostProcessVolume>(Params);
    if(Post){Post->bUnbound=true;Post->Priority=50.f;Post->BlendWeight=1.f;}
    for(TActorIterator<AExponentialHeightFog> It(GetWorld());It;++It)
        if(auto* Fog=It->GetComponent())Fogs.Add({Fog,Fog->FogDensity,Fog->FogInscatteringLuminance});
    double Delay=-1;
    if(FParse::Value(FCommandLine::Get(),TEXT("RedlineStormPreview="),Delay) && FMath::IsFinite(Delay) && Delay>=0 && Delay<=3600)
        PreviewAt=FPlatformTime::Seconds()+Delay;
    HudHandle=AHUD::OnHUDPostRender.AddUObject(this,&ARedlineStormFX::DrawSpeckles);
    // Look development only: place the player on the habitat apron outdoors (map ENU 300,-480 m).
    if(FParse::Param(FCommandLine::Get(),TEXT("RedlineStormLookDev")))bLookDevPending=true;
    UE_LOG(LogRedlineStorm,Display,TEXT("SCENARIO wind sand %d+%d quads, %d fog layer(s); storm follows the ROS SEP alert%s"),
        StreakPlanes.Num(),SheetPlanes.Num(),Fogs.Num(),PreviewAt>=0 ? TEXT(" (preview flag set)") : TEXT(""));
}
void ARedlineStormFX::EndPlay(const EEndPlayReason::Type Reason)
{
    AHUD::OnHUDPostRender.Remove(HudHandle);
    for(const FFogBase& F:Fogs)if(F.Fog.IsValid()){F.Fog->SetFogDensity(F.Density);F.Fog->SetFogInscatteringColor(F.Color);}
    Super::EndPlay(Reason);
}
float ARedlineStormFX::GroundZ(const FVector& At,float Fallback) const
{
    FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(RedlineStormGround),false);Query.AddIgnoredActor(this);
    if(auto* PC=GetWorld()->GetFirstPlayerController())if(PC->GetPawn())Query.AddIgnoredActor(PC->GetPawn());
    const FVector Start(At.X,At.Y,Fallback+900.f),End(At.X,At.Y,Fallback-2000.f);
    return GetWorld()->LineTraceSingleByChannel(Hit,Start,End,ECC_Visibility,Query) ? Hit.ImpactPoint.Z : Fallback;
}
void ARedlineStormFX::Spawn(FGrain& G,const FVector& Viewer,bool bSheet,bool)
{
    const float Radius=bSheet ? RedlineStorm::SheetRadius : RedlineStorm::StreakRadius;
    const float Angle=FMath::FRandRange(0.f,2*PI),Distance=FMath::Pow(FMath::FRand(),bSheet ? .5f : .9f)*Radius;
    const FVector Side(-WindDir.Y,WindDir.X,0.f);
    FVector P=Viewer+FVector(FMath::Cos(Angle),FMath::Sin(Angle),0.f)*Distance;
    const float Ground=GroundZ(P,Viewer.Z-170.f);
    if(bSheet)
    {
        G.BaseZ=Ground+FMath::FRandRange(10.f,120.f+160.f*Storm);G.Hop=FMath::FRandRange(0.f,70.f);
        G.Len=FMath::FRandRange(700.f,1700.f);G.Thick=FMath::FRandRange(180.f,520.f);G.Life=FMath::FRandRange(4.f,9.f);
        G.Vel=WindDir*FMath::FRandRange(250.f,520.f)+Side*FMath::FRandRange(-40.f,40.f);
    }
    else
    {
        // Saltation-like hops: a few cm to half a metre above the surface, streaked along the wind.
        // In a storm the sand rises to head height and thickens.
        G.BaseZ=Ground+FMath::FRandRange(2.f,30.f+170.f*Storm);G.Hop=FMath::FRandRange(5.f,45.f+40.f*Storm);
        G.Len=FMath::FRandRange(50.f,160.f);G.Thick=FMath::FRandRange(5.f,12.f)*(1.f+.8f*Storm);G.Life=FMath::FRandRange(.7f,1.8f);
        G.Vel=WindDir*FMath::FRandRange(450.f,850.f)+Side*FMath::FRandRange(-40.f,40.f);
    }
    G.Pos=FVector(P.X,P.Y,G.BaseZ);G.Age=0.f;G.bLive=true;
}
void ARedlineStormFX::UpdatePlanes(TArray<FGrain>& Pool,TArray<TObjectPtr<UStaticMeshComponent>>& Planes,int32 Active,bool bSheet,
    const FVector& Viewer,const FVector& Forward,float SpeedScale,float Dt)
{
    const float Radius=bSheet ? RedlineStorm::SheetRadius : RedlineStorm::StreakRadius;
    FVector Across=WindDir-Forward*FVector::DotProduct(WindDir,Forward);
    if(!Across.Normalize())Across=FVector::CrossProduct(Forward,FVector::UpVector).GetSafeNormal();
    const FRotator Facing=FRotationMatrix::MakeFromZX(-Forward,Across).Rotator();
    for(int32 I=0;I<Pool.Num() && I<Planes.Num();++I)
    {
        FGrain& G=Pool[I];UStaticMeshComponent* Plane=Planes[I];
        const bool Expired=!G.bLive || G.Age>=G.Life || FVector::Dist2D(G.Pos,Viewer)>Radius*1.15f;
        if(Expired){if(I<Active)Spawn(G,Viewer,bSheet,true);else G.bLive=false;}
        if(!G.bLive || !bOutdoors){Plane->SetVisibility(false);continue;}
        G.Age+=Dt;G.Pos+=G.Vel*Dt*SpeedScale;
        const float F=FMath::Clamp(G.Age/G.Life,0.f,1.f),Fade=FMath::Sqrt(FMath::Max(0.f,FMath::Sin(PI*F)));
        const FVector Where(G.Pos.X,G.Pos.Y,G.BaseZ+G.Hop*FMath::Sin(PI*F));
        const float Length=G.Len*(bSheet ? 1.f : FMath::Min(SpeedScale,2.f));
        Plane->SetWorldTransform(FTransform(Facing,Where,FVector(FMath::Max(.01f,Length/100.f*(bSheet ? Fade : 1.f)),FMath::Max(.001f,G.Thick/100.f*Fade),1.f)));
        Plane->SetVisibility(Fade>.02f);
    }
}
void ARedlineStormFX::UpdateLook()
{
    if(Post)
    {
        FPostProcessSettings& S=Post->Settings;const float T=Storm;
        S.bOverride_VignetteIntensity=true;S.VignetteIntensity=FMath::Lerp(.30f,.62f,T);
        S.bOverride_FilmGrainIntensity=true;S.FilmGrainIntensity=FMath::Lerp(.03f,.30f,T);
        S.bOverride_SceneColorTint=true;S.SceneColorTint=RedlineStorm::Lerp(FLinearColor::White,FLinearColor(1.f,.80f,.64f),T);
        S.bOverride_ColorSaturation=true;const float Sat=1.07f-.15f*T;S.ColorSaturation=FVector4(Sat,Sat,Sat,1.f);
        S.bOverride_ColorContrast=true;const float Con=1.05f+.06f*T;S.ColorContrast=FVector4(Con,Con,Con,1.f);
        S.bOverride_BloomIntensity=true;S.BloomIntensity=.45f;
        S.bOverride_SceneFringeIntensity=true;S.SceneFringeIntensity=.1f+.9f*T;
    }
    const float Haze=Storm*(bOutdoors ? 3.f : 1.f);
    for(const FFogBase& F:Fogs)
        if(F.Fog.IsValid())
        {
            F.Fog->SetFogDensity(F.Density*(1.f+Haze));
            F.Fog->SetFogInscatteringColor(RedlineStorm::Lerp(F.Color,F.Color*FLinearColor(1.5f,.9f,.6f),Storm));
        }
}
void ARedlineStormFX::Tick(float Dt)
{
    Super::Tick(Dt);Time+=Dt;
    const double Now=FPlatformTime::Seconds();
    if(!Overlay)for(TActorIterator<ARedlineOverlay> It(GetWorld());It;++It){Overlay=*It;break;}
    bLiveAlert=Overlay && Overlay->AcceptedDose>0 && Overlay->Fresh(Overlay->DoseReceipt) && Overlay->Dose.bAlert;
    if(Overlay && Overlay->AcceptedDose>0)
    {
        const FRedlineEVADose& D=Overlay->Dose;
        const double R=D.Detector==TEXT("E") ? (D.BackgroundE>0 ? D.RateE/D.BackgroundE : 1.) : (D.BackgroundB>0 ? D.RateB/D.BackgroundB : 1.);
        DoseRatio=FMath::IsFinite(R) ? FMath::Max(1.,R) : 1.;
    }
    bPreviewActive=PreviewAt>=0 && Now>=PreviewAt;
    if(bPreviewActive && !bLiveAlert)DoseRatio=20.;
    Storm=ApproachStorm(Storm,bLiveAlert || bPreviewActive ? 1.f : 0.f,Dt);
    auto* PC=GetWorld()->GetFirstPlayerController();
    if(bLookDevPending && PC && PC->GetPawn() && Time>1.5f)
    {
        const FVector At(30000.f,48000.f,PC->GetPawn()->GetActorLocation().Z);
        PC->GetPawn()->SetActorLocation(FVector(At.X,At.Y,GroundZ(At,At.Z)+120.f),false,nullptr,ETeleportType::TeleportPhysics);
        PC->SetControlRotation(FRotator(-6.f,25.f,0.f));bLookDevPending=false;
    }
    if(!PC || !PC->PlayerCameraManager){UpdateLook();return;}
    const FVector Viewer=PC->PlayerCameraManager->GetCameraLocation();
    const FVector Forward=PC->PlayerCameraManager->GetCameraRotation().Vector();
    if(Now>=NextOutdoorCheck)
    {
        FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(RedlineStormRoof),false);Query.AddIgnoredActor(this);
        if(PC->GetPawn())Query.AddIgnoredActor(PC->GetPawn());
        bOutdoors=!GetWorld()->LineTraceSingleByChannel(Hit,Viewer,Viewer+FVector(0,0,3000),ECC_Visibility,Query);
        NextOutdoorCheck=Now+.25;
    }
    const float Gust=1.f+.25f*FMath::Sin(Time*.7f)*FMath::Sin(Time*.23f+1.f);
    const float SpeedScale=Gust*FMath::Lerp(1.f,2.3f,Storm);
    if(StreakMaterial)
    {
        StreakMaterial->SetScalarParameterValue(TEXT("PuffOpacity"),FMath::Lerp(.30f,.80f,Storm));
        StreakMaterial->SetScalarParameterValue(TEXT("SandGlow"),FMath::Lerp(.18f,.40f,Storm));
    }
    if(SheetMaterial)
    {
        SheetMaterial->SetScalarParameterValue(TEXT("PuffOpacity"),FMath::Lerp(.07f,.34f,Storm));
        SheetMaterial->SetScalarParameterValue(TEXT("SandGlow"),FMath::Lerp(.12f,.30f,Storm));
    }
    UpdatePlanes(Streaks,StreakPlanes,ActiveStreaks(Storm),false,Viewer,Forward,SpeedScale,Dt);
    UpdatePlanes(Sheets,SheetPlanes,FMath::RoundToInt(FMath::Lerp(6.f,float(MaxSheets),Storm)),true,Viewer,Forward,SpeedScale,Dt);
    UpdateLook();
}
void ARedlineStormFX::DrawSpeckles(AHUD* Hud,UCanvas* Canvas)
{
    if(!Hud || !Canvas || Hud->GetWorld()!=GetWorld() || Storm<=.02f)return;
    // Energetic particles leave short bright marks on camera frames; count follows the replayed dose ratio.
    const int32 Count=SpeckleCount(Storm,DoseRatio);
    for(int32 I=0;I<Count;++I)
    {
        const bool Trail=FMath::FRand()<.3f;
        const FVector2D Size=Trail ? (FMath::RandBool() ? FVector2D(1,FMath::RandRange(3,7)) : FVector2D(FMath::RandRange(3,7),1)) : FVector2D(FMath::RandRange(1,2),FMath::RandRange(1,2));
        FCanvasTileItem Dot(FVector2D(FMath::FRandRange(0.f,Canvas->SizeX),FMath::FRandRange(0.f,Canvas->SizeY)),Size,FLinearColor(1,1,1,FMath::FRandRange(.5f,.95f)));
        Dot.BlendMode=SE_BLEND_Translucent;Canvas->DrawItem(Dot);
    }
    if(Storm<.08f || !GEngine)return;
    const float Y=Canvas->SizeY-62.f;
    Canvas->SetDrawColor(FColor(255,190,120,220));
    Canvas->DrawText(GEngine->GetSmallFont(),FString::Printf(TEXT("RUZGAR/KUM: SENARYO  |  KAMERA PARAZITI: RAD DOZ ORANI x%.1f"),DoseRatio),24.f,Y,1.1f,1.1f);
    if(bPreviewActive && !bLiveAlert)
    {
        Canvas->SetDrawColor(FColor(255,120,90,230));
        Canvas->DrawText(GEngine->GetSmallFont(),TEXT("ONIZLEME: FIRTINA ZORLANDI (ROS ALARMI YOK)"),24.f,Y-22.f,1.1f,1.1f);
    }
}
