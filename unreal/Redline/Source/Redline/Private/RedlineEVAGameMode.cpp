#include "RedlineEVAGameMode.h"
#include "RedlineAstronautCharacter.h"
#include "RedlineOverlay.h"
#include "RedlineCoords.h"
#include "RedlineBridgeSubsystem.h"
#include "RedlineStaleMonitor.h"
#include "Engine/GameInstance.h"
#include "Engine/Canvas.h"
#include "Engine/Texture2D.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Materials/MaterialInterface.h"
#include "RedlinePrologueDirector.h"
#include "RedlineCampaignConsole.h"
#include "RedlineDroneActor.h"
#include "RedlineSurfaceDust.h"
#include "RedlineFieldTablet.h"
#include "RedlineTaskFilm.h"
#include "RedlineFootprints.h"
#include "RedlineAmbientDust.h"
#include "RedlineStormFX.h"
#include "RedlineShotRecorder.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "MediaPlayer.h"
#include "MediaTexture.h"
#include "FileMediaSource.h"

namespace RedlineMissionHUD
{
const FLinearColor Graphite(.018f,.028f,.037f,.96f),Panel(.038f,.053f,.064f,.96f);
const FLinearColor Amber(1.f,.72f,.29f,1.f),Cyan(.39f,.82f,.86f,1.f),Muted(.58f,.65f,.69f,1.f);
struct FStep {const TCHAR* Title;const TCHAR* Action;};
const FStep Steps[]={
    {TEXT("Çıkış brifingi"),TEXT("Habitat panosunu incele. Çıkışı E ile onayla.")},
    {TEXT("Bağlam istasyonuna ulaş"),TEXT("İşaretli istasyona ilerle; yakında E ile incele.")},
    {TEXT("Yüzey bağlamını değerlendir"),TEXT("Sırt ve çukur düzenini gözle. E ile dönüşü iste.")},
    {TEXT("Habitat güvenliğine dön"),TEXT("Habitat işaretini takip et; yakında E ile tamamla.")},
    {TEXT("Prova kaydını tamamla"),TEXT("ROS görevi bitirdiğinde dönüş kaydı görünür.")}
};
int32 StepForPhase(int32 Phase)
{switch(Phase){case 0:return 0;case 2:return 1;case 3:return 2;case 4:case 5:return 3;case 6:return 4;default:return INDEX_NONE;}}
bool ClockFresh(const URedlineBridgeSubsystem* Bridge)
{return Bridge && Bridge->bHasMissionClock && Bridge->StaleMonitor && Bridge->StaleMonitor->IsFresh(TEXT("/redline/mission/clock"),FPlatformTime::Seconds());}
FString AgeText(double Receipt)
{return Receipt>=0 ? FString::Printf(TEXT("%.1f sn önce"),FMath::Max(0.,FPlatformTime::Seconds()-Receipt)) : TEXT("henüz gelmedi");}
}

ARedlineEVAGameMode::ARedlineEVAGameMode()
{DefaultPawnClass=ARedlineAstronautCharacter::StaticClass();HUDClass=ARedlineEVAHUD::StaticClass();}
void ARedlineEVAGameMode::StartPlay()
{
    auto* Overlay=GetWorld()->SpawnActor<ARedlineOverlay>();
    Overlay->FieldMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/EVAFixtures/M_FieldTile.M_FieldTile"));
    GetWorld()->SpawnActor<ARedlinePrologueDirector>();
    // SCENARIO presentation layers (playtest 2026-11-15): boot prints on terrain and faint drifting dust.
    GetWorld()->SpawnActor<ARedlineFootprints>();GetWorld()->SpawnActor<ARedlineAmbientDust>();
    // SCENARIO wind sand and the crew-side SEP storm look; the storm follows the ROS alert (D-storm-fx).
    GetWorld()->SpawnActor<ARedlineStormFX>();
    if(FParse::Param(FCommandLine::Get(),TEXT("RedlineCampaign")))
    {
        // Drawing follows physical ground contact; Nav2 keeps estimated odometry.
        for(TActorIterator<ARedlineRoverActor> It(GetWorld());It;++It)It->OdometryTopic=TEXT("/redline/presentation/rover_1/odom");
        GetWorld()->SpawnActor<ARedlineCampaignConsole>();GetWorld()->SpawnActor<ARedlineDroneActor>();
        GetWorld()->SpawnActor<ARedlineSurfaceDust>();
        GetWorld()->SpawnActor<ARedlineFieldTablet>();
    }
    else
    {
        // F10 recording outside the campaign too (C1 live storm): the campaign console spawns it otherwise.
        FString ShotRoot;if(FParse::Value(FCommandLine::Get(),TEXT("RedlineShotDir="),ShotRoot) && !ShotRoot.IsEmpty())GetWorld()->SpawnActor<ARedlineShotRecorder>();
    }
    Super::StartPlay();
}
void ARedlineEVAHUD::DrawMissionJournal(const ARedlineAstronautCharacter* Astronaut,const ARedlineOverlay* View,const URedlineBridgeSubsystem* Bridge)
{
    using namespace RedlineMissionHUD;
    const float S=FMath::Min(Canvas->SizeX/1280.f,Canvas->SizeY/720.f);
    const float W=1120*S,H=548*S,X=(Canvas->SizeX-W)*.5f,Y=(Canvas->SizeY-H)*.5f;
    const bool PhaseFresh=Astronaut && Astronaut->bMissionStateFresh,IsOrientation=Astronaut && Astronaut->bIntroMode;
    const int32 Phase=PhaseFresh ? Astronaut->MissionPhase : INDEX_NONE,Active=IsOrientation ? StepForPhase(Phase) : INDEX_NONE;
    // Only the sequential orientation phases prove previous interactions.
    // CONTINGENCY does not prove a preceding station was visited.
    const int32 Done=Phase==6 ? 5 : Phase==5 || Active==INDEX_NONE ? 0 : Active;
    const bool LineFresh=View->Fresh(View->LineReceipt),CrewFresh=View->Fresh(View->CrewReceipt,3),PetFresh=ClockFresh(Bridge);
    auto Text=[&](const FString& Value,FLinearColor Color,float LX,float LY,float Scale=1.f)
    {DrawText(Value,Color,X+LX*S,Y+LY*S,nullptr,Scale*S);};
    auto Rect=[&](FLinearColor Color,float LX,float LY,float LW,float LH)
    {DrawRect(Color,X+LX*S,Y+LY*S,LW*S,LH*S);};
    DrawRect(FLinearColor(0,0,0,.58f),0,0,Canvas->SizeX,Canvas->SizeY);
    Rect(Graphite,0,0,1120,548);Rect(Cyan,0,0,1120,3);
    Text(TEXT("REDLINE / GÖREV GÜNLÜĞÜ"),FLinearColor::White,28,22,1.6f);
    Text(TEXT("BOXWORK-BATI · EV1 · YÖNLENDİRME PROVASI"),Muted,28,53,.95f);
    Text(PhaseFresh ? TEXT("ROS DURUMU GÜNCEL") : TEXT("GÖREV VERİSİ BEKLENİYOR"),PhaseFresh ? Cyan : Amber,796,28,.9f);
    Text(TEXT("J / Esc · Kapat"),Muted,954,57,.9f);
    Rect(Panel,28,91,690,346);Text(IsOrientation ? TEXT("EVA AKIŞI") : TEXT("EVA AKIŞI / BU KOŞUDA BAĞLI DEĞİL"),Muted,44,105,.95f);
    Text(PhaseFresh && IsOrientation ? FString::Printf(TEXT("%d / 5 tamamlandı"),Done) : TEXT("Durum bekleniyor"),Muted,550,105,.95f);
    for(int32 I=0;I<5;++I)
    {
        const bool Completed=PhaseFresh && IsOrientation && I<Done,Current=PhaseFresh && IsOrientation && I==Active && Phase!=6;
        const float RowY=134+I*58.f;
        if(Current)Rect(FLinearColor(.12f,.105f,.06f,.95f),36,RowY-2,674,56);
        const FLinearColor Color=Completed ? Cyan : Current ? Amber : Muted;
        Text(FString::Printf(TEXT("%02d"),I+1),Color,46,RowY+2,1.3f);
        Text(Steps[I].Title,Completed || Current ? FLinearColor::White : Muted,84,RowY+1,1.15f);
        Text(Steps[I].Action,Muted,84,RowY+24,.95f);
        Text(Completed ? TEXT("TAMAM") : Current ? Phase==5 ? TEXT("ACİL") : TEXT("ETKİN") : PhaseFresh && IsOrientation && Phase!=5 ? TEXT("SIRADA") : TEXT("—"),Color,636,RowY+3,.8f);
    }
    Rect(Panel,738,91,354,346);Text(TEXT("CANLI DURUM"),Muted,756,105,.95f);
    Text(PetFresh ? FString::Printf(TEXT("PET %.1f dk"),Bridge->MissionClockSec/60.) : TEXT("PET —"),PetFresh ? FLinearColor::White : Muted,756,135,1.55f);
    Text(LineFresh && View->Line.bHasMargin ? FString::Printf(TEXT("Dönüş payı %.1f dk"),View->Line.MarginMinutes) : TEXT("Dönüş payı —"),LineFresh ? Amber : Muted,756,174,1.35f);
    Text(LineFresh && View->Line.bHasMargin ? TEXT("Sınırlayan ekip: ")+View->Line.LimitingCrew : TEXT("Pay verisi bekleniyor"),Muted,756,205,.95f);
    Text(CrewFresh ? FString::Printf(TEXT("Oksijen  %.2f kg"),View->Crew.OxygenKg) : TEXT("Oksijen  —"),CrewFresh ? FLinearColor::White : Muted,756,242,1.1f);
    Text(CrewFresh ? FString::Printf(TEXT("Su           %.2f kg"),View->Crew.WaterKg) : TEXT("Su           —"),CrewFresh ? FLinearColor::White : Muted,756,270,1.1f);
    Text(CrewFresh ? FString::Printf(TEXT("Pil            %.0f Wh"),View->Crew.BatteryWh) : TEXT("Pil            —"),CrewFresh ? FLinearColor::White : Muted,756,298,1.1f);
    if(PhaseFresh && Astronaut && (Phase==0 || Phase==2 || Phase==3 || Phase==4))
    {
        const bool Station=Phase==2 || Phase==3;const FVector Target=Station ? Astronaut->StationMap : Astronaut->BriefingMap;
        const double Distance=FVector::Dist2D(URedlineCoords::UeToRosLocation(Astronaut->GetActorLocation()),Target);
        Text(FString::Printf(TEXT("%s · %.1f m"),Station ? TEXT("BAĞLAM İSTASYONU") : TEXT("HABİTAT / KOMUTA"),Distance),Cyan,756,347,1.1f);
        Text(Distance<=4 ? TEXT("E · Yakın etkileşim") : TEXT("Önce işaretli hedefe yaklaş"),Muted,756,376,.95f);
    }
    else Text(Phase==6 ? TEXT("Dönüş ROS tarafından onaylandı") : Phase==5 ? TEXT("Acil dönüş emri öncelikli") : TEXT("Hedef durumu bekleniyor"),Muted,756,351,.95f);
    Text(TEXT("VERİ YAŞI"),Muted,28,454,.85f);
    Text(TEXT("Harita: ")+AgeText(View->TileReceipt)+(View->Fresh(View->TileReceipt) ? TEXT(" · güncel") : TEXT(" · eski / yok")),View->Fresh(View->TileReceipt) ? Cyan : Amber,28,478,.9f);
    Text(TEXT("Pay: ")+AgeText(View->LineReceipt)+(LineFresh ? TEXT(" · güncel") : TEXT(" · eski / yok")),LineFresh ? Cyan : Amber,368,478,.9f);
    Text(TEXT("Giysi: ")+AgeText(View->CrewReceipt)+(CrewFresh ? TEXT(" · güncel") : TEXT(" · eski / yok")),CrewFresh ? Cyan : Amber,738,478,.9f);
    Text(TEXT("SONRAKİ BÖLÜMLER · Robot öncü keşif / istasyon bilimi"),Muted,28,519,.9f);
    Text(TEXT("Görev saati durmaz."),Muted,920,519,.85f);
}

void ARedlineEVAHUD::DrawObjectiveMarker(const ARedlineAstronautCharacter* Astronaut)
{
    using namespace RedlineMissionHUD;
    auto* PC=GetOwningPlayerController();
    ARedlineCampaignConsole* Campaign=nullptr;for(TActorIterator<ARedlineCampaignConsole> It(GetWorld());It;++It){Campaign=*It;break;}
    if(!PC || !Astronaut || !Astronaut->bMovementProfileReady || !Astronaut->bMissionStateFresh || (!Astronaut->bIntroMode && !Campaign))return;
    const int32 Phase=Astronaut->MissionPhase;
    if(!Campaign && Phase!=0 && Phase!=2 && Phase!=3 && Phase!=4)return;
    if(Campaign && !Campaign->Fresh())return;
    const bool Station=Phase==2 || Phase==3;
    FVector Target=Campaign ? Campaign->TaskMap() : Station ? Astronaut->StationMap : Astronaut->BriefingMap;
    const FVector Here=URedlineCoords::UeToRosLocation(Astronaut->GetActorLocation());
    const double Distance=FVector::Dist2D(Here,Target),Now=FPlatformTime::Seconds();
    if(Campaign)Target=Campaign->NavigationTarget(Here);
    if(Target.ContainsNaN() || !FMath::IsFinite(Distance))return;
    if(FVector::Dist2D(Target,CachedObjective)>.01){CachedObjective=Target;bHasObjectiveHeight=false;NextObjectiveTrace=-1;}
    // Height affects only the floating navigation pin. Goal XY/distance still
    // come from the ROS orientation profile, never from a new route planner.
    if(Now>=NextObjectiveTrace)
    {
        NextObjectiveTrace=Now+1.;FVector Surface;Target.Z=Here.Z;
        if(URedlineCoords::TraceTerrainHeight(this,Target,100,Surface)){CachedObjectiveSurface=Surface;bHasObjectiveHeight=true;}
    }
    Target.Z=bHasObjectiveHeight ? CachedObjectiveSurface.Z : Here.Z-.94;
    FVector WorldTarget=URedlineCoords::RosToUeLocation(Target)+FVector(0,0,170);
    const FName GoalTag=Station ? TEXT("prologue_station_story_actor") : TEXT("prologue_command_operator");
    if(!Campaign)for(TActorIterator<AActor> It(GetWorld());It;++It)if(It->ActorHasTag(GoalTag)){WorldTarget=It->GetActorLocation()+FVector(0,0,170);break;}
    FVector CameraLocation;FRotator CameraRotation;PC->GetPlayerViewPoint(CameraLocation,CameraRotation);
    const FRotator FlatCamera(0,CameraRotation.Yaw,0);
    const FVector Delta=(WorldTarget-CameraLocation).GetSafeNormal2D();
    const double Angle=FMath::Atan2(FVector::DotProduct(Delta,FRotationMatrix(FlatCamera).GetUnitAxis(EAxis::Y)),FVector::DotProduct(Delta,FlatCamera.Vector()));
    const float S=FMath::Clamp(FMath::Min(Canvas->SizeX/1280.f,Canvas->SizeY/720.f),.6f,2.f);
    const FVector2D Minimum(142*S,100*S),Maximum(Canvas->SizeX-142*S,Canvas->SizeY-245*S);
    FVector2D Anchor;const bool Projected=PC->ProjectWorldLocationToScreen(WorldTarget,Anchor);
    const bool InFront=FVector::DotProduct(WorldTarget-CameraLocation,CameraRotation.Vector())>0;
    const bool OnScreen=Projected && InFront && Anchor.X>=Minimum.X && Anchor.X<=Maximum.X && Anchor.Y>=Minimum.Y && Anchor.Y<=Maximum.Y;
    FVector2D Direction(FMath::Sin(Angle),-FMath::Cos(Angle));
    if(!OnScreen)
    {
        const FVector2D Center=(Minimum+Maximum)*.5,Extent=(Maximum-Minimum)*.5;
        if(Projected && InFront)Direction=(Anchor-Center).GetSafeNormal();
        if(Direction.IsNearlyZero())Direction=FVector2D(0,-1);
        const double TX=FMath::Abs(Direction.X)>.001 ? Extent.X/FMath::Abs(Direction.X) : DBL_MAX;
        const double TY=FMath::Abs(Direction.Y)>.001 ? Extent.Y/FMath::Abs(Direction.Y) : DBL_MAX;
        Anchor=Center+Direction*FMath::Min(TX,TY);
        // Reserve the telemetry and minimap corners for their existing cards.
        if(Anchor.X<480*S && Anchor.Y<205*S)Anchor.Y=205*S;
        if(Anchor.X>Canvas->SizeX-360*S && Anchor.Y>Canvas->SizeY-440*S)Anchor.Y=Canvas->SizeY-440*S;
    }
    const double Radius=Campaign ? Campaign->InteractionRadius() : 4.;
    const FLinearColor Color=Distance<=Radius ? Amber : Cyan;
    auto Line=[&](FVector2D A,FVector2D B,float Width=2.5f)
    {DrawLine(A.X,A.Y,B.X,B.Y,FLinearColor(0,0,0,.9f),(Width+3)*S);DrawLine(A.X,A.Y,B.X,B.Y,Color,Width*S);};
    if(OnScreen)
    {
        const FVector2D V[]={Anchor+FVector2D(0,-16*S),Anchor+FVector2D(14*S,0),Anchor+FVector2D(0,16*S),Anchor+FVector2D(-14*S,0)};
        for(int32 I=0;I<4;++I)Line(V[I],V[(I+1)%4]);
        Line(Anchor+FVector2D(0,16*S),Anchor+FVector2D(0,25*S));
    }
    else
    {
        const FVector2D Side(-Direction.Y,Direction.X),Tip=Anchor+Direction*18*S;
        Line(Anchor-Direction*14*S,Tip,3.f);Line(Tip,Tip-Direction*13*S+Side*8*S,3.f);Line(Tip,Tip-Direction*13*S-Side*8*S,3.f);
    }
    const float BX=Anchor.X-120*S,BY=Anchor.Y+29*S;
    DrawRect(Graphite,BX,BY,240*S,66*S);DrawRect(Color,BX,BY,3*S,66*S);
    DrawText(Campaign ? Campaign->TaskTitle().Left(31) : Station ? TEXT("BAĞLAM İSTASYONU") : TEXT("HABİTAT / KOMUTA"),Color,BX+12*S,BY+9*S,nullptr,1.1f*S);
    const TCHAR* Turn=FMath::Abs(Angle)>PI*.65 ? TEXT("Arkanda · dön") : Angle>.35 ? TEXT("Sağa dön") : Angle<-.35 ? TEXT("Sola dön") : TEXT("İleri");
    const FString Detail=FString::Printf(TEXT("%.1f m · %s"),Distance,Distance<=Radius ? TEXT("E etkileşim") : OnScreen ? TEXT("İşarete ilerle") : Turn);
    DrawText(Detail,FLinearColor::White,BX+12*S,BY+37*S,nullptr,1.1f*S);
}

// --- task briefing (playtest 2026-11-15: "before a science task: where, what, how it works") -----------------
bool ARedlineEVAHUD::NeedsBriefing(const FString& Kind)
{
    static const TSet<FString> Kinds={TEXT("scout"),TEXT("collect"),TEXT("xrf"),TEXT("weather"),TEXT("libs"),TEXT("dan"),TEXT("drill"),TEXT("cache")};
    return Kinds.Contains(Kind);
}
FString ARedlineEVAHUD::BriefingVideoFor(const FString& Kind)
{
    const FString Name=Kind==TEXT("drill") ? TEXT("drill") : (Kind==TEXT("xrf") || Kind==TEXT("collect")) ? TEXT("apxs") : Kind==TEXT("libs") ? TEXT("libs") : FString();
    if(Name.IsEmpty())return FString();
    const FString Path=FPaths::ConvertRelativePathToFull(FPaths::ProjectContentDir()/TEXT("Movies")/(TEXT("explainer_")+Name+TEXT(".mp4")));
    return IFileManager::Get().FileExists(*Path) ? Path : FString();
}
FString ARedlineEVAHUD::BriefingPurposeFor(const FString& Kind)
{
    if(Kind==TEXT("scout"))return TEXT("Drone yürüyüş koridorunu önden tarar. Engel bulursa rota yeniden planlanır;\nkanıt gelmeden saha kararı açılmaz.");
    if(Kind==TEXT("collect"))return TEXT("Yüzey numunesi tüpe alınır. Alındığı nokta, derinlik ve zaman kayda girer ve değişmez;\npH ve bileşim sonra laboratuvarda ölçülür.");
    if(Kind==TEXT("xrf"))return TEXT("El tipi XRF kayanın elementlerini sayar. Aleti kayaya iyi yerleştir:\ngerçek APXS arşivine göre iyi temas, uzun beklemekten daha çok kazandırır.");
    if(Kind==TEXT("weather"))return TEXT("Doz ve hava istasyonu kurulur. Uzay havası alarmı sahada da görünür olur;\ndoz değeri gerçek MSL RAD kaydından gelir.");
    if(Kind==TEXT("libs"))return TEXT("Rover hedefe Nav2 ile gider; direkteki lazer kayayı uzaktan buharlaştırır.\nPlazmanın spektrumu elementleri söyler.");
    if(Kind==TEXT("dan"))return TEXT("Rover durup nötron sayar; bir sonraki nokta en belirsiz yerdir.\nYeraltı su eşdeğeri ve belirsizliği veri panosuna gelir.");
    if(Kind==TEXT("drill"))return TEXT("Rover matkabı 5 cm iner. Sıkışırsa geri çeker, beslemeyi azaltır, darbeli moda geçer;\ntoz numune tüpe gider.");
    if(Kind==TEXT("cache"))return TEXT("Tüp taşıma kutusuna kilitlenir; numune zinciri laboratuvara kopmadan gider.");
    return FString();
}
void ARedlineEVAHUD::CloseBriefing()
{
    bBriefingVisible=false;
    if(BriefingPlayer)BriefingPlayer->Close();
}
void ARedlineEVAHUD::UpdateBriefing(ARedlineCampaignConsole* Campaign,APlayerController* PC)
{
    if(!Campaign || !Campaign->Fresh() || !Campaign->HasState())return;
    const FString Title=Campaign->TaskTitle(),Kind=Campaign->TaskKind();
    if(Title!=BriefedTask)
    {
        BriefedTask=Title;
        if(NeedsBriefing(Kind) && !Campaign->IsBusy())
        {
            bBriefingVisible=true;
            const FString Video=BriefingVideoFor(Kind);
            if(!Video.IsEmpty())
            {
                if(!BriefingPlayer){BriefingPlayer=NewObject<UMediaPlayer>(this);BriefingPlayer->SetLooping(true);BriefingPlayer->PlayOnOpen=true;}
                if(!BriefingTexture){BriefingTexture=NewObject<UMediaTexture>(this);BriefingTexture->SetMediaPlayer(BriefingPlayer);BriefingTexture->UpdateResource();}
                BriefingSource=NewObject<UFileMediaSource>(this);BriefingSource->SetFilePath(Video);
                BriefingPlayer->OpenSource(BriefingSource);
            }
            else if(BriefingPlayer)BriefingPlayer->Close();
        }
    }
    if(bBriefingVisible && (Campaign->IsBusy() || !NeedsBriefing(Kind)))CloseBriefing();
    if(bBriefingVisible && PC && (PC->WasInputKeyJustPressed(EKeys::Enter) || PC->WasInputKeyJustPressed(EKeys::SpaceBar)
        || PC->WasInputKeyJustPressed(EKeys::Escape) || PC->WasInputKeyJustPressed(EKeys::E)))CloseBriefing();
}
void ARedlineEVAHUD::DrawBriefing(const ARedlineCampaignConsole* Campaign,const ARedlineAstronautCharacter* Astronaut)
{
    using namespace RedlineMissionHUD;
    const float S=FMath::Clamp(FMath::Min(Canvas->SizeX/1280.f,Canvas->SizeY/720.f),.6f,2.f);
    const float W=1120*S,H=520*S,X=(Canvas->SizeX-W)*.5f,Y=(Canvas->SizeY-H)*.5f;
    DrawRect(FLinearColor(0,0,0,.88f),X,Y,W,H);DrawRect(Amber,X,Y,W,4*S);
    DrawText(TEXT("GÖREV BRİFİNGİ"),Amber,X+28*S,Y+20*S,nullptr,1.1f*S);
    DrawText(Campaign->TaskTitle(),FLinearColor::White,X+28*S,Y+46*S,nullptr,1.6f*S);
    const bool Video=BriefingTexture && BriefingPlayer && BriefingPlayer->IsPlaying();
    const float VW=Video ? 560*S : 0,VH=315*S,VX=X+28*S,VY=Y+96*S;
    if(Video)
    {
        DrawRect(FLinearColor(.05f,.05f,.05f,1),VX-2*S,VY-2*S,VW+4*S,VH+4*S);DrawTexture(BriefingTexture,VX,VY,VW,VH,0,0,1,1);
        DrawText(TEXT("Nasıl çalışır · simülasyon anlatımı"),Muted,VX,VY+VH+8*S,nullptr,.9f*S);
    }
    const float TX=Video ? VX+VW+28*S : X+28*S,TW=X+W-28*S-TX;
    float LineY=VY;
    auto Block=[&](const FString& Heading,const FString& Body,FLinearColor Color)
    {
        DrawText(Heading,Color,TX,LineY,nullptr,1.0f*S);LineY+=24*S;
        TArray<FString> Lines;Body.ParseIntoArray(Lines,TEXT("\n"));
        const int32 Max=FMath::Max(28,int32(TW/(8.6f*S)));
        for(const FString& L:Lines)
        {
            FString Rest=L;
            while(Rest.Len()>Max){int32 Cut=Max;while(Cut>10 && Rest[Cut]!=TEXT(' '))--Cut;DrawText(Rest.Left(Cut),FLinearColor::White,TX,LineY,nullptr,.95f*S);LineY+=21*S;Rest=Rest.Mid(Cut+1);}
            DrawText(Rest,FLinearColor::White,TX,LineY,nullptr,.95f*S);LineY+=21*S;
        }
        LineY+=12*S;
    };
    Block(TEXT("NE YAPILACAK"),Campaign->TaskInstruction(),Amber);
    Block(TEXT("NEDEN"),BriefingPurposeFor(Campaign->TaskKind()),Cyan);
    if(Astronaut)
    {
        const FVector Here=URedlineCoords::UeToRosLocation(Astronaut->GetActorLocation()),Target=Campaign->TaskMap();
        Block(TEXT("NEREYE"),FString::Printf(TEXT("Görev noktası %.0f m uzakta. Ekrandaki işareti izle; %.1f m içinde E ile başlat."),
            FVector::Dist2D(Here,Target),Campaign->InteractionRadius()),Cyan);
    }
    DrawText(TEXT("Enter / Space / E · brifingi kapat ve göreve git"),FLinearColor::White,X+28*S,Y+H-36*S,nullptr,1.0f*S);
    DrawText(TEXT("Sonuçlar ROS'tan gelir · SIMULATED ölçüm"),Muted,X+W-330*S,Y+H-36*S,nullptr,.9f*S);
}
void ARedlineEVAHUD::DrawControlBar(const URedlineBridgeSubsystem* Bridge,const ARedlineCampaignConsole* Campaign)
{
    using namespace RedlineMissionHUD;
    const bool Live=Bridge && Bridge->IsConnected() && !Bridge->IsOfflineReplay();
    const bool Clock=RedlineMissionHUD::ClockFresh(Bridge);
    const bool Task=Campaign && Campaign->Fresh();
    const FString Status=!Bridge ? TEXT("ROS YOK") : Bridge->IsOfflineReplay() ? TEXT("KAYIT OYNATIMI") : !Live ? TEXT("ROS BAĞLANTISI YOK")
        : !Clock ? TEXT("ROS · görev saati bekleniyor") : (Campaign && !Task) ? TEXT("ROS · görev durumu bekleniyor") : TEXT("ROS CANLI");
    const FLinearColor Dot=!Live ? FLinearColor(1,.25f,.2f) : (!Clock || (Campaign && !Task)) ? Amber : FLinearColor(.3f,1,.45f);
    const FString Keys=TEXT("E etkileşim · M pano · T tablet · J görevler · Tab harita · V kamera · Shift koşu");
    float KW=0,KH=0;GetTextSize(Keys,KW,KH,nullptr,.95f);
    const float Y=Canvas->SizeY-30,W=KW+300,X=(Canvas->SizeX-W)*.5f;
    DrawRect(FLinearColor(0,0,0,.6f),X,Y-6,W,28);
    DrawRect(Dot,X+10,Y+3,10,10);DrawText(Status,Dot,X+28,Y,nullptr,.95f);
    DrawText(Keys,Muted,X+290,Y,nullptr,.95f);
}

void ARedlineEVAHUD::DrawHUD()
{
    Super::DrawHUD();if(!Canvas)return;
    for(TActorIterator<ARedlineTaskFilm> It(GetWorld());It;++It){It->DrawCaption(Canvas);return;}
    auto* PC=GetOwningPlayerController();auto* Astronaut=PC ? Cast<ARedlineAstronautCharacter>(PC->GetPawn()) : nullptr;
    ARedlinePrologueDirector* Story=nullptr;for(TActorIterator<ARedlinePrologueDirector> It(GetWorld());It;++It){Story=*It;break;}
    if(Story && Story->IsCinematic())
    {
        bMissionJournalVisible=false;if(Astronaut)Astronaut->bMissionJournalOpen=false;
        DrawRect(FLinearColor::Black,0,0,Canvas->SizeX,58);DrawRect(FLinearColor(0,0,0,.92f),0,Canvas->SizeY-118,Canvas->SizeX,118);
        DrawText(Story->Title(),FLinearColor(1,.88f,.6f),32,20,nullptr,1.3f);
        FString Caption=Story->Caption();if(Caption.Len()>95){int32 Split=95;while(Split>30 && Caption[Split]!=TEXT(' '))--Split;Caption.InsertAt(Split,TEXT('\n'));}
        DrawText(Caption,FLinearColor::White,48,Canvas->SizeY-97,nullptr,1.25f);
        DrawText(Story->IsResting() ? TEXT("F · Kalk") : TEXT("Space · Sahneyi geç     Esc · Açılışı atla"),FLinearColor(.75f,.75f,.75f),48,Canvas->SizeY-29,nullptr,1.f);
        return;
    }
    ARedlineOverlay* View=nullptr;for(TActorIterator<ARedlineOverlay> It(GetWorld());It;++It){View=*It;break;}
    if(!View)return;
    ARedlineCampaignConsole* Campaign=nullptr;for(TActorIterator<ARedlineCampaignConsole> It(GetWorld());It;++It){Campaign=*It;break;}
    if(Campaign && Campaign->bTabletOpen)return;
    if(PC)
    {
        if((!Campaign || !Campaign->bTabletOpen) && PC->WasInputKeyJustPressed(EKeys::Tab))bMapVisible=!bMapVisible;
        if((!Campaign || !Campaign->bTabletOpen) && PC->WasInputKeyJustPressed(EKeys::J)){if(Campaign){Campaign->bConsoleOpen=!Campaign->bConsoleOpen;Campaign->Page=0;}else bMissionJournalVisible=!bMissionJournalVisible;}
        if(bMissionJournalVisible && PC->WasInputKeyJustPressed(EKeys::Escape))bMissionJournalVisible=false;
    }
    UpdateBriefing(Campaign,PC);
    if(Astronaut)Astronaut->bMissionJournalOpen=bMissionJournalVisible || (Campaign && Campaign->bConsoleOpen) || bBriefingVisible;
    auto* GI=GetGameInstance();auto* Bridge=GI ? GI->GetSubsystem<URedlineBridgeSubsystem>() : nullptr;
    const bool LineFresh=View->Fresh(View->LineReceipt),CrewFresh=View->Fresh(View->CrewReceipt,3),TileFresh=View->Fresh(View->TileReceipt);
    if(Campaign && Campaign->bConsoleOpen){Campaign->DrawConsole(Canvas,Canvas->SizeX,Canvas->SizeY);return;}
    if(bMissionJournalVisible)
    {
        DrawMissionJournal(Astronaut,View,Bridge);
        // A critical alert must remain visible over the open journal.
        const FString Alert=View->Dose.AlarmText(View->Fresh(View->DoseReceipt));
        if(View->AcceptedDose>0 && !Alert.IsEmpty()){DrawRect(FLinearColor(.35f,0,0,.95f),18,18,640,40);DrawText(Alert,FLinearColor(1,.37f,.27f),30,28,nullptr,1.2f);}
        return;
    }
    const FString Mode=Bridge && Bridge->IsOfflineReplay() ? TEXT("KAYIT OYNATIMI") : Bridge && Bridge->IsConnected() ? TEXT("CANLI ROS") : TEXT("BAĞLANTI YOK");
    DrawRect(FLinearColor(0,0,0,.65f),18,18,440,150);
    DrawText(TEXT("REDLINE | EV1 ASTRONOT | ")+Mode,FLinearColor::White,30,28,nullptr,1.15f);
    const FString Margin=LineFresh && View->Line.bHasMargin ? FString::Printf(TEXT("DONUS PAYI  %.1f dk | %s"),View->Line.MarginMinutes,*View->Line.LimitingCrew) : TEXT("DONUS PAYI  -- | veri eski / bekleniyor");
    DrawText(Margin,LineFresh ? FLinearColor(1,.8f,.3f) : FLinearColor(.7f,.7f,.7f),30,56,nullptr,1.15f);
    DrawText(CrewFresh ? FString::Printf(TEXT("O2 %.2f kg | Su %.2f kg | Pil %.0f Wh"),View->Crew.OxygenKg,View->Crew.WaterKg,View->Crew.BatteryWh) : TEXT("Sarf: veri eski / bekleniyor"),FLinearColor::White,30,82);
    DrawText(RedlineMissionHUD::ClockFresh(Bridge) ? FString::Printf(TEXT("PET %.1f dk | J görevler | Tab harita"),Bridge->MissionClockSec/60) : TEXT("Görev saati bekleniyor | J görevler"),FLinearColor::White,30,105);
    DrawText(TEXT("SCENARIO EV1/giysi | DERIVED BXW donus alani"),FLinearColor(.7f,.7f,.7f),30,130);
    if(Astronaut)
    {
        const float X=Canvas->SizeX-252;
        DrawRect(RedlineMissionHUD::Graphite,X,18,234,60);
        DrawText(FString::Printf(TEXT("%.1f m/sn · %s"),Astronaut->GetVelocity().Size2D()/100.,Astronaut->bSprinting ? TEXT("KOŞU") : TEXT("YÜRÜYÜŞ")),Astronaut->bSprinting ? RedlineMissionHUD::Amber : RedlineMissionHUD::Cyan,X+12,28,nullptr,1.1f);
        DrawText(Astronaut->bFirstPersonView ? TEXT("V · Kamera: 1. kişi") : TEXT("V · Kamera: 3. kişi"),RedlineMissionHUD::Muted,X+12,53,nullptr,.95f);
    }
    if(Story && Story->CanRest())DrawText(TEXT("[F] Plağı dinle / dinlen"),FLinearColor(1,.85f,.5f),30,Canvas->SizeY-160,nullptr,1.15f);
    if(Astronaut && Astronaut->bIntroMode)
    {
        using namespace RedlineMissionHUD;
        const float Y=Canvas->SizeY-128;DrawRect(Graphite,18,Y,552,103);DrawRect(Amber,18,Y,3,103);
        const int32 Active=Astronaut->bMissionStateFresh ? StepForPhase(Astronaut->MissionPhase) : INDEX_NONE;
        const FString Heading=Active==INDEX_NONE ? TEXT("GÖREV BAĞLANTISI BEKLENİYOR") : Astronaut->MissionPhase==5 ? TEXT("ACİL DÖNÜŞ") : FString::Printf(TEXT("%02d / %s"),Active+1,Steps[Active].Title);
        DrawText(Heading,Amber,32,Y+12,nullptr,1.2f);
        DrawText(Active==INDEX_NONE ? TEXT("Görev verisi güncellendiğinde hedef burada görünür.") : Astronaut->MissionPhase==6 ? TEXT("Yönlendirme provası tamamlandı. J ile kaydı incele.") : Steps[Active].Action,FLinearColor::White,32,Y+39,nullptr,.95f);
        FString Guidance=TEXT("WASD + fare · Shift koşu · J görevler");
        if(Astronaut->bMissionStateFresh && (Astronaut->MissionPhase==0 || Astronaut->MissionPhase==2 || Astronaut->MissionPhase==3 || Astronaut->MissionPhase==4))
        {
            const bool Station=Astronaut->MissionPhase==2 || Astronaut->MissionPhase==3;
            const FVector Target=Station ? Astronaut->StationMap : Astronaut->BriefingMap;
            const FVector Here=URedlineCoords::UeToRosLocation(Astronaut->GetActorLocation());
            const double Distance=FVector::Dist2D(Here,Target);
            Guidance=FString::Printf(TEXT("%s %.1f m · %s · Shift koşu · J görevler"),Station ? TEXT("İstasyon") : TEXT("Komuta"),Distance,Distance<=4 ? TEXT("E etkileşim") : TEXT("hedefe yaklaş"));
        }
        DrawText(Guidance,Muted,32,Y+74,nullptr,.95f);
        if(!Astronaut->InteractionMessage.IsEmpty())DrawText(Astronaut->InteractionMessage.Left(85),Muted,30,Y-27,nullptr,.95f);
    }
    DrawObjectiveMarker(Astronaut);
    if(Campaign)Campaign->DrawTaskCard(Canvas);
    DrawControlBar(Bridge,Campaign);
    if(Campaign && bBriefingVisible){DrawBriefing(Campaign,Astronaut);return;}
    if(Campaign && !Campaign->Message().IsEmpty() && Campaign->MessageAgeSec()<6.)
    {
        // Every E press gets an answer on screen: accepted, refused with ROS's reason, or still waiting.
        const FString Feedback=TEXT("E · ")+Campaign->Message().Left(110);
        float W=0,H=0;GetTextSize(Feedback,W,H,nullptr,1.15f);
        const float BX=(Canvas->SizeX-W)*.5f-18,BY=Canvas->SizeY*.72f;
        DrawRect(FLinearColor(0,0,0,.78f),BX,BY,W+36,H+18);DrawRect(RedlineMissionHUD::Amber,BX,BY,4,H+18);
        DrawText(Feedback,FLinearColor::White,BX+18,BY+9,nullptr,1.15f);
    }
    if(View->Fresh(View->DoseReceipt))
    {
        const bool E=View->Dose.Detector==TEXT("E");
        const FString Dose=FString::Printf(TEXT("RAD %s %.2f uGy/h | arka plan %.2f | sol %d"),*View->Dose.Detector,E ? View->Dose.RateE : View->Dose.RateB,E ? View->Dose.BackgroundE : View->Dose.BackgroundB,View->Dose.SourceSol);
        DrawText(Dose,FLinearColor(1,.8f,.3f),30,180);
    }
    else if(View->AcceptedDose>0)DrawText(TEXT("RAD: veri eski / baglanti yok"),FLinearColor::Yellow,30,180);
    const FString Alarm=View->Dose.AlarmText(View->Fresh(View->DoseReceipt));
    if(View->AcceptedDose>0 && !Alarm.IsEmpty()){DrawRect(FLinearColor(.35f,0,0,.85f),18,204,640,40);DrawText(Alarm,FLinearColor::Red,30,214,nullptr,1.25f);}
    if(!bMapVisible || !View->FieldTexture || !TileFresh)return;
    const double Size=FMath::Min(300.,Canvas->SizeY*.42),X=Canvas->SizeX-Size-24,Y=Canvas->SizeY-Size-24;
    DrawRect(FLinearColor(.08f,.08f,.08f,.9f),X-4,Y-24,Size+8,Size+28);
    DrawText(TEXT("DONUS HARITASI | Kirmizi: donus siniri"),FLinearColor::White,X,Y-19);
    // PNG row 0 is the southern row. Flip V for the north-up screen map.
    DrawTexture(View->FieldTexture,X,Y,Size,Size,0,1,1,-1,FLinearColor(1,1,1,1),BLEND_Translucent);
    auto Screen=[&](FVector P){return FVector2D(X+(P.X-View->Tile.Origin.X)/(View->Tile.Width*View->Tile.Resolution)*Size,Y+Size-(P.Y-View->Tile.Origin.Y)/(View->Tile.Height*View->Tile.Resolution)*Size);};
    auto Rings=[&](const TArray<TArray<FVector>>& All,FLinearColor Color)
    {for(const auto& Ring:All)for(int32 I=0;I<Ring.Num();++I){auto A=Screen(Ring[I]),B=Screen(Ring[(I+1)%Ring.Num()]);DrawLine(A.X,A.Y,B.X,B.Y,Color,1.5);}};
    if(LineFresh){Rings(View->Line.Abort,FLinearColor::Red);Rings(View->Line.Terminate,FLinearColor::Yellow);}
    if(PC && PC->GetPawn()){auto P=Screen(URedlineCoords::UeToRosLocation(PC->GetPawn()->GetActorLocation()));if(P.X>=X && P.X<=X+Size && P.Y>=Y && P.Y<=Y+Size)DrawRect(FLinearColor::White,P.X-3,P.Y-3,6,6);}
}
