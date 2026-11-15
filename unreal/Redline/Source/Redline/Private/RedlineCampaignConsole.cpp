#include "RedlineCampaignConsole.h"
#include "RedlineAstronautCharacter.h"
#include "RedlineSampleInteraction.h"
#include "RedlineBridgeSubsystem.h"
#include "RedlineTypes.h"
#include "RedlineCoords.h"
#include "RedlineOverlay.h"
#include "RedlinePrologueDirector.h"
#include "RedlineStaleMonitor.h"
#include "RedlineEVAData.h"
#include "Engine/Canvas.h"
#include "Engine/CanvasRenderTarget2D.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "EngineUtils.h"
#include "CanvasItem.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "InputCoreTypes.h"
#include "Dom/JsonObject.h"
#include "UnrealClient.h"
#include "RedlineConsoleTheme.h"
#include "RedlineMissionSites.h"
#include "RedlineFieldWorkActor.h"
#include "RedlineShotRecorder.h"
#include "RedlineRoverScienceVisuals.h"
#include "RedlineFilmView.h"
#include "RedlineTaskFilm.h"
DEFINE_LOG_CATEGORY_STATIC(LogRedlineCampaign,Log,All);

namespace CampaignDrawing
{
const FLinearColor Background=RedlineConsoleTheme::Background,Panel=RedlineConsoleTheme::Surface,Cyan=RedlineConsoleTheme::Text,Amber=RedlineConsoleTheme::Warning,Muted=RedlineConsoleTheme::Secondary;
FString Str(const TSharedPtr<FJsonObject>& J,const TCHAR* Key,const FString& Default=TEXT("—"))
{FString V;return J && J->TryGetStringField(Key,V) ? V : Default;}
double Num(const TSharedPtr<FJsonObject>& J,const TCHAR* Key,double Default=0)
{double V;return J && J->TryGetNumberField(Key,V) && FMath::IsFinite(V) ? V : Default;}
const TArray<TSharedPtr<FJsonValue>>& Array(const TSharedPtr<FJsonObject>& J,const TCHAR* Key)
{static const TArray<TSharedPtr<FJsonValue>> Empty;const TArray<TSharedPtr<FJsonValue>>* Values;return J && J->TryGetArrayField(Key,Values) ? *Values : Empty;}
TSharedPtr<FJsonObject> Obj(const TSharedPtr<FJsonObject>& J,const TCHAR* Key)
{const TSharedPtr<FJsonObject>* O;return J && J->TryGetObjectField(Key,O) ? *O : nullptr;}
bool BoundedString(const TSharedPtr<FJsonObject>& J,const TCHAR* Key,int32 Maximum,bool AllowEmpty=false)
{FString Value;return J && J->TryGetStringField(Key,Value) && Value.Len()<=Maximum && (AllowEmpty || !Value.IsEmpty());}
bool FiniteNumber(const TSharedPtr<FJsonObject>& J,const TCHAR* Key,double Min,double Max,bool Integer=false)
{double Value;return J && J->TryGetNumberField(Key,Value) && FMath::IsFinite(Value) && Value>=Min && Value<=Max && (!Integer || Value==FMath::FloorToDouble(Value));}
bool NumericArray(const TArray<TSharedPtr<FJsonValue>>& Values,int32 Count,double Min=-1e9,double Max=1e9)
{if(Values.Num()!=Count)return false;for(const auto& Value:Values){double Number;if(!Value || !Value->TryGetNumber(Number) || !FMath::IsFinite(Number) || Number<Min || Number>Max)return false;}return true;}
bool RequiredArray(const TSharedPtr<FJsonObject>& J,const TCHAR* Key,int32 Maximum,const TArray<TSharedPtr<FJsonValue>>*& Out)
{return J && J->TryGetArrayField(Key,Out) && Out && Out->Num()<=Maximum;}
bool TaskValid(const TSharedPtr<FJsonObject>& T)
{return BoundedString(T,TEXT("id"),96) && BoundedString(T,TEXT("title"),160) && BoundedString(T,TEXT("instruction"),512) && BoundedString(T,TEXT("kind"),32) &&
    BoundedString(T,TEXT("actor"),64) && BoundedString(T,TEXT("target_id"),256) && NumericArray(Array(T,TEXT("xy")),2) && FiniteNumber(T,TEXT("phase"),0,6,true) &&
    (!T->HasField(TEXT("radius_m")) || FiniteNumber(T,TEXT("radius_m"),.2,4));}
struct FDraw
{
    UCanvas* C;float S;
    void Rect(float X,float Y,float W,float H,FLinearColor Color)const
    {FCanvasTileItem Item(FVector2D(X*S,Y*S),FVector2D(W*S,H*S),Color);Item.BlendMode=SE_BLEND_Translucent;C->DrawItem(Item);}
    void Text(const FString& V,float X,float Y,float Size=1,FLinearColor Color=FLinearColor::White)const
    {FCanvasTextItem Item(FVector2D(X*S,Y*S),FText::FromString(V),GEngine->GetSmallFont(),Color);Item.Scale=FVector2D(Size*S,Size*S);C->DrawItem(Item);}
    void Line(float X,float Y,float X2,float Y2,FLinearColor Color,float Thick=1)const
    {FCanvasLineItem Item(FVector2D(X*S,Y*S),FVector2D(X2*S,Y2*S));Item.SetColor(Color);Item.LineThickness=Thick*S;C->DrawItem(Item);}
};
FString Provenance(const TSharedPtr<FJsonObject>& Product)
{
    const int32 Status=Num(Product,TEXT("status"),-1);
    const TCHAR* Labels[]={TEXT("ARCHIVE"),TEXT("DERIVED"),TEXT("SIMULATED"),TEXT("SCENARIO")};
    return Status>=0 && Status<4 ? Labels[Status] : TEXT("KAYNAK DURUMU YOK");
}
bool TimeSeriesValid(const TSharedPtr<FJsonObject>& Series,const TCHAR* ValueKey,double Low,double High)
{
    const auto& Times=Array(Series,TEXT("time_s"));const auto& Values=Array(Series,ValueKey);
    if(Times.Num()<2 || Times.Num()>512 || !NumericArray(Times,Times.Num(),0,1e9) || !NumericArray(Values,Times.Num(),Low,High))return false;
    for(int32 I=1;I<Times.Num();++I)if(Times[I]->AsNumber()<=Times[I-1]->AsNumber())return false;
    return true;
}
void SeriesGraph(const FDraw& D,const TArray<TSharedPtr<FJsonValue>>& Times,const TArray<TSharedPtr<FJsonValue>>& Values,
    float X,float Y,float W,float H,FLinearColor Color,const FString& Label)
{
    if(Times.Num()<2 || Times.Num()!=Values.Num())return;
    double Minimum=DBL_MAX,Maximum=-DBL_MAX;
    for(const auto& V:Values){Minimum=FMath::Min(Minimum,V->AsNumber());Maximum=FMath::Max(Maximum,V->AsNumber());}
    const double Pad=FMath::Max((Maximum-Minimum)*.12,.01);Minimum-=Pad;Maximum+=Pad;
    const double Start=Times[0]->AsNumber(),Span=FMath::Max(.001,Times.Last()->AsNumber()-Start);
    D.Text(Label,X,Y-23,.85,Color);D.Line(X,Y+H,X+W,Y+H,Muted);
    auto Point=[&](int32 I){return FVector2D(X+(Times[I]->AsNumber()-Start)/Span*W,Y+H-(Values[I]->AsNumber()-Minimum)/(Maximum-Minimum)*H);};
    for(int32 I=1;I<Times.Num();++I){const auto A=Point(I-1),B=Point(I);D.Line(A.X,A.Y,B.X,B.Y,Color,2);}
    D.Text(FString::Printf(TEXT("%.2f"),Maximum),X+W+6,Y-3,.7,Muted);
    D.Text(FString::Printf(TEXT("%.2f"),Minimum),X+W+6,Y+H-9,.7,Muted);
    D.Text(FString::Printf(TEXT("%.0f–%.0f s / %d kayıt"),Start,Times.Last()->AsNumber(),Times.Num()),X,Y+H+9,.72,Muted);
}
void HeatMap(const FDraw& D,const TSharedPtr<FJsonObject>& Grid,const TCHAR* Key,float X,float Y,float Size,const FString& Label)
{
    const int32 W=Num(Grid,TEXT("width")),H=Num(Grid,TEXT("height"));const auto& Values=Array(Grid,Key);
    if(W<2 || H<2 || Values.Num()!=W*H)return;
    double Lo=DBL_MAX,Hi=-DBL_MAX;for(const auto& V:Values){Lo=FMath::Min(Lo,V->AsNumber());Hi=FMath::Max(Hi,V->AsNumber());}
    D.Text(Label,X,Y-25,.9,Cyan);
    for(int32 Row=0;Row<H;++Row)for(int32 Col=0;Col<W;++Col)
    {
        const double A=Hi-Lo>1e-9 ? (Values[Row*W+Col]->AsNumber()-Lo)/(Hi-Lo) : .5;
        D.Rect(X+Col*Size/W,Y+(H-1-Row)*Size/H,Size/W+.2f,Size/H+.2f,FLinearColor::LerpUsingHSV(FLinearColor(.05,.045,.035,1),FLinearColor(.96,.65,.18,1),A));
    }
    D.Text(FString::Printf(TEXT("%.3f–%.3f %%"),Lo,Hi),X,Y+Size+8,.8,Muted);
}
}

ARedlineCampaignConsole::ARedlineCampaignConsole(){PrimaryActorTick.bCanEverTick=true;}
void ARedlineCampaignConsole::BeginPlay()
{
    Super::BeginPlay();
    bConsoleOpen=FParse::Param(FCommandLine::Get(),TEXT("RedlineOpenBoard"));
    if(auto* GI=GetGameInstance())Bridge=GI->GetSubsystem<URedlineBridgeSubsystem>();
    if(Bridge)
    {
        TopicHandle=Bridge->OnTopic.AddUObject(this,&ARedlineCampaignConsole::Receive);
        Bridge->OnConnectionChanged.AddDynamic(this,&ARedlineCampaignConsole::ConnectionChanged);
        Bridge->Subscribe(TEXT("/redline/campaign/state"),TEXT("std_msgs/msg/String"),200,3);
        Bridge->Subscribe(TEXT("/env/dose_rate"),TEXT("redline_msgs/msg/DoseRate"),200,5);
        Bridge->Subscribe(TEXT("/redline/evidence"),TEXT("redline_msgs/msg/EvidenceRecord"),0,5);
        Bridge->Subscribe(TEXT("/redline/science/lab_status"),TEXT("std_msgs/msg/String"),200,3);
        // These are display subscriptions only. The physics trace must never
        // feed back into localization, Nav2, the goal service or TF.
        Bridge->Subscribe(TEXT("/redline/presentation/rover_1/odom"),TEXT("nav_msgs/msg/Odometry"),100,2);
        Bridge->Subscribe(TEXT("/rover_1/plan"),TEXT("nav_msgs/msg/Path"),200,3);
        Bridge->Subscribe(TEXT("/rover_1/navigate_to_pose/_action/status"),TEXT("action_msgs/msg/GoalStatusArray"),200,3);
    }
    ScreenTexture=UCanvasRenderTarget2D::CreateCanvasRenderTarget2D(this,UCanvasRenderTarget2D::StaticClass(),2048,1152);
    if(ScreenTexture)ScreenTexture->OnCanvasRenderTargetUpdate.AddDynamic(this,&ARedlineCampaignConsole::RenderScreen);
    for(TActorIterator<AActor> It(GetWorld());It;++It)if(It->ActorHasTag(TEXT("prologue_command_screen")))
    {
        // This wall plane is viewed from the reverse side of its original UVs.
        ScreenActor=*It;It->SetActorScale3D(FVector(-2.6,1.4,1));It->SetActorLocation(It->GetActorLocation()+FVector(0,70,0));
        if(auto* Mesh=It->FindComponentByClass<UStaticMeshComponent>())
        {
            if(auto* Display=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Campaign/Materials/M_CampaignDisplay.M_CampaignDisplay")))Mesh->SetMaterial(0,Display);
            ScreenMaterial=Mesh->CreateDynamicMaterialInstance(0);if(ScreenMaterial){ScreenMaterial->SetTextureParameterValue(TEXT("DisplayMap"),ScreenTexture);ScreenMaterial->SetScalarParameterValue(TEXT("DataFresh"),1);}
        }
        break;
    }
    for(TActorIterator<AActor> It(GetWorld());It;++It)
        if(It->ActorHasTag(TEXT("prologue_mission_board")) || It->ActorHasTag(TEXT("prologue_command_wall_title")) || It->ActorHasTag(TEXT("prologue_command_map_title")) || It->ActorHasTag(TEXT("prologue_command_data_credit")))It->SetActorHiddenInGame(true);
    Interaction=GetWorld()->SpawnActor<ARedlineSampleInteraction>();
    bool HasSites=false;for(TActorIterator<ARedlineMissionSites> It(GetWorld());It;++It){HasSites=true;break;}
    if(!HasSites)GetWorld()->SpawnActor<ARedlineMissionSites>();
    GetWorld()->SpawnActor<ARedlineRoverScienceVisuals>();
    if(FParse::Param(FCommandLine::Get(),TEXT("RedlineFilming")))GetWorld()->SpawnActor<ARedlineFilmView>();
    FString TaskFilm;if(FParse::Value(FCommandLine::Get(),TEXT("RedlineTaskFilm="),TaskFilm))GetWorld()->SpawnActor<ARedlineTaskFilm>();
    FString ShotRoot;if(FParse::Value(FCommandLine::Get(),TEXT("RedlineShotDir="),ShotRoot) && !ShotRoot.IsEmpty())GetWorld()->SpawnActor<ARedlineShotRecorder>();
}
void ARedlineCampaignConsole::EndPlay(const EEndPlayReason::Type Reason)
{if(Bridge){Bridge->OnTopic.Remove(TopicHandle);Bridge->OnConnectionChanged.RemoveDynamic(this,&ARedlineCampaignConsole::ConnectionChanged);}if(Interaction)Interaction->EndInteraction(false);Super::EndPlay(Reason);}
bool ARedlineCampaignConsole::ValidateSnapshot(const TSharedPtr<FJsonObject>& J)
{
    using namespace CampaignDrawing;
    if(Str(J,TEXT("schema"))!=TEXT("redline.campaign.v1"))return false;
    const TArray<TSharedPtr<FJsonValue>> *Tasks=nullptr,*Products=nullptr,*Samples=nullptr,*Evidence=nullptr;
    if(!TaskValid(Obj(J,TEXT("task"))) || !RequiredArray(J,TEXT("tasks"),32,Tasks) || Tasks->IsEmpty() ||
       !RequiredArray(J,TEXT("products"),20,Products) || !RequiredArray(J,TEXT("samples"),20,Samples) || !RequiredArray(J,TEXT("evidence_ids"),100,Evidence) ||
       !FiniteNumber(J,TEXT("revision"),0,MAX_uint32,true) || !FiniteNumber(J,TEXT("progress"),0,1) ||
       !FiniteNumber(J,TEXT("task_count"),Tasks->Num(),Tasks->Num(),true) || !FiniteNumber(J,TEXT("task_index"),0,Tasks->Num(),true) ||
       !FiniteNumber(J,TEXT("pet_s"),0,1e9) || !BoundedString(J,TEXT("run_id"),256) || !BoundedString(J,TEXT("message"),512,true) ||
       !BoundedString(J,TEXT("operation_phase"),128,true) || !BoundedString(J,TEXT("operation_id"),96,true))return false;
    const FString Status=Str(J,TEXT("state"));
    if(Status!=TEXT("ready") && Status!=TEXT("pending") && Status!=TEXT("running") && Status!=TEXT("complete") && Status!=TEXT("failed"))return false;
    if((Status==TEXT("pending") || Status==TEXT("running")) && Str(J,TEXT("operation_id")).IsEmpty())return false;
    for(const auto& Value:*Tasks)if(!Value || Value->Type!=EJson::Object || !TaskValid(Value->AsObject()))return false;
    if(J->HasField(TEXT("route_xy_m")))
    {
        const TArray<TSharedPtr<FJsonValue>>* Route=nullptr;
        if(!RequiredArray(J,TEXT("route_xy_m"),512,Route))return false;
        for(const auto& P:*Route){const TArray<TSharedPtr<FJsonValue>>* Pair=nullptr;if(!P || !P->TryGetArray(Pair) || !NumericArray(*Pair,2))return false;}
    }
    if(auto Scout=Obj(J,TEXT("scout"));Scout && Scout->HasField(TEXT("map_xyz_m")))
        if(!NumericArray(Array(Scout,TEXT("map_xyz_m")),3) || !FiniteNumber(Scout,TEXT("battery_wh"),0,1e6))return false;
    if(J->HasField(TEXT("scout_observations")))
    {
        const TArray<TSharedPtr<FJsonValue>>* Observations=nullptr;
        if(!RequiredArray(J,TEXT("scout_observations"),128,Observations))return false;
        for(const auto& Value:*Observations)if(!Value || Value->Type!=EJson::Object)return false;
    }
    for(const auto& Value:*Evidence){FString Id;if(!Value || !Value->TryGetString(Id) || Id.Len()>512)return false;}
    for(const auto& Value:*Products)
    {
        if(!Value || Value->Type!=EJson::Object)return false;const auto Product=Value->AsObject(),Summary=Obj(Product,TEXT("summary"));
        if(!BoundedString(Product,TEXT("product_id"),512) || !BoundedString(Product,TEXT("instrument"),64) || !BoundedString(Product,TEXT("target_id"),256) || !Summary)return false;
        if(!ValidateScienceSummary(Summary,Str(Product,TEXT("instrument"))))return false;
    }
    for(const auto& Value:*Samples)
    {
        if(!Value || Value->Type!=EJson::Object)return false;const auto Sample=Value->AsObject();
        if(!BoundedString(Sample,TEXT("sample_id"),256) || !BoundedString(Sample,TEXT("container_id"),512,true) || !FiniteNumber(Sample,TEXT("state"),0,8,true) ||
            !NumericArray(Array(Sample,TEXT("origin_point_m")),3) || !NumericArray(Array(Sample,TEXT("analysis_point_m")),3))return false;
    }
    return true;
}
void ARedlineCampaignConsole::Receive(const FString& Topic,const TSharedPtr<FJsonObject>& Json)
{
    if(Topic==TEXT("/redline/science/lab_status"))
    {
        FString Raw;if(!Json || !Json->TryGetStringField(TEXT("data"),Raw) || Raw.Len()>4096)return;
        auto J=FRedlineJson::Parse(Raw);if(CampaignDrawing::Str(J,TEXT("schema"))!=TEXT("redline.lab.status.v1"))return;
        LabMessage=CampaignDrawing::Str(J,TEXT("state"))+FString::Printf(TEXT(" · %.0f%% · "),CampaignDrawing::Num(J,TEXT("progress"))*100)+CampaignDrawing::Str(J,TEXT("sample_id"));return;
    }
    if(Topic==TEXT("/redline/evidence")){CaptureScoutEvidence(Json,FPlatformTime::Seconds());return;}
    if(Topic==TEXT("/env/dose_rate")){CaptureRad(Json);return;}
    if(Topic==TEXT("/redline/presentation/rover_1/odom")){CaptureRoverPose(Json,FPlatformTime::Seconds());return;}
    if(Topic==TEXT("/rover_1/plan")){CaptureRobotPath(Json,FPlatformTime::Seconds());return;}
    if(Topic==TEXT("/rover_1/navigate_to_pose/_action/status")){CaptureNavStatus(Json,FPlatformTime::Seconds());return;}
    if(Topic!=TEXT("/redline/campaign/state"))return;FString Data;
    if(!Json || !Json->TryGetStringField(TEXT("data"),Data) || Data.Len()>240000)return;
    const auto Parsed=FRedlineJson::Parse(Data);if(!ValidateSnapshot(Parsed))return;
    if(State && CampaignDrawing::Str(State,TEXT("run_id"))!=CampaignDrawing::Str(Parsed,TEXT("run_id")))ResetRobotTelemetry();
    State=Parsed;Receipt=FPlatformTime::Seconds();
    for(const auto& Value:CampaignDrawing::Array(State,TEXT("scout_observations")))CaptureScoutEvidence(Value->AsObject(),Receipt);
    const auto Scout=CampaignDrawing::Obj(State,TEXT("scout"));const auto& XYZ=CampaignDrawing::Array(Scout,TEXT("map_xyz_m"));
    if(XYZ.Num()==3 && CampaignDrawing::Num(State,TEXT("scout_age_s"),9999)<=2)
    {
        const FVector2D Point(XYZ[0]->AsNumber(),XYZ[1]->AsNumber());
        if(ScoutTrack.IsEmpty() || FVector2D::Distance(ScoutTrack.Last(),Point)>.1)
        {if(!ScoutTrack.IsEmpty() && FVector2D::Distance(ScoutTrack.Last(),Point)>50)ScoutTrack.Reset();if(ScoutTrack.Num()>=512)ScoutTrack.RemoveAt(0,1,EAllowShrinking::No);ScoutTrack.Add(Point);}
    }
    UpdateInteraction();
}
void ARedlineCampaignConsole::ResetRobotTelemetry()
{
    RoverTrack.Reset();RobotPath.Reset();RoverPhysicsSec=RoverReceipt=RobotPathReceipt=RobotPathPhysicsSec=NavStatusReceipt=NavGoalStamp=-1;
    RoverMap=FVector::ZeroVector;RoverSpeedMps=0;bHasRoverSpeed=false;NavStatus=0;NavGoalId.Empty();
    ScoutObservations.Reset();ScoutObservationIds.Reset();ScoutTrack.Reset();ScoutObservationReceipt=-1;
}
void ARedlineCampaignConsole::ConnectionChanged(bool bConnected)
{ResetRobotTelemetry();}
bool ARedlineCampaignConsole::RobotFresh(double When,double MaxAge) const
{const double Age=FPlatformTime::Seconds()-When;return Bridge && Bridge->IsConnected() && When>=0 && Age>=0 && Age<=MaxAge;}
void ARedlineCampaignConsole::CaptureRoverPose(const TSharedPtr<FJsonObject>& Json,double Now)
{
    FRedlineOdometry Odom;FString Error;
    if(!FMath::IsFinite(Now) || !FRedlineOdometry::Parse(Json,Odom,Error) || Odom.FrameId!=TEXT("map") ||
       Odom.ChildFrameId!=TEXT("rover_1/base_link") || Odom.PositionMetres.GetAbsMax()>1e7)return;
    // Repeated source stamps cannot keep a stopped physics stream fresh.
    if(RoverPhysicsSec>=0 && Odom.PhysicsStampSec==RoverPhysicsSec)return;
    if(RoverPhysicsSec>=0 && Odom.PhysicsStampSec<RoverPhysicsSec)ResetRobotTelemetry();
    const double Dt=Odom.PhysicsStampSec-RoverPhysicsSec,Distance=FVector::Dist2D(Odom.PositionMetres,RoverMap);
    const bool Continuous=RoverPhysicsSec>=0 && Dt>=1e-6 && Dt<=2 && Now-RoverReceipt>=0 && Now-RoverReceipt<=2 && Distance<=20 && Distance/Dt<=20;
    bHasRoverSpeed=Continuous;
    if(Continuous)RoverSpeedMps=Distance/Dt;
    else{RoverTrack.Reset();RoverSpeedMps=0;}
    RoverMap=Odom.PositionMetres;RoverPhysicsSec=Odom.PhysicsStampSec;RoverReceipt=Now;
    if(RoverTrack.IsEmpty() || RoverPhysicsSec-RoverTrack.Last().PhysicsSec>=.1)
    {
        if(RoverTrack.Num()>=RoverTrackCapacity)RoverTrack.RemoveAt(0,1,EAllowShrinking::No);
        RoverTrack.Add({RoverMap,RoverPhysicsSec});
    }
}
void ARedlineCampaignConsole::CaptureRobotPath(const TSharedPtr<FJsonObject>& Json,double Now)
{
    using namespace CampaignDrawing;
    const auto Header=Obj(Json,TEXT("header"));double Stamp=-1;const TArray<TSharedPtr<FJsonValue>>* Poses=nullptr;
    if(!FMath::IsFinite(Now) || Str(Header,TEXT("frame_id"))!=TEXT("map") || !FRedlineJson::Stamp(Obj(Header,TEXT("stamp")),Stamp) ||
       !RequiredArray(Json,TEXT("poses"),4096,Poses) || Stamp<RobotPathPhysicsSec)return;
    TArray<FVector2D> Validated;Validated.Reserve(Poses->Num());
    for(const auto& Value:*Poses)
    {
        if(!Value || Value->Type!=EJson::Object)return;
        const auto P=Value->AsObject(),H=Obj(P,TEXT("header")),Pose=Obj(P,TEXT("pose"));
        const FString Frame=Str(H,TEXT("frame_id"),TEXT(""));FVector Position;FQuat Rotation;
        if((!Frame.IsEmpty() && Frame!=TEXT("map")) || !FRedlineJson::Vector(Obj(Pose,TEXT("position")),Position) ||
           Position.GetAbsMax()>1e7 || !FRedlineJson::Quaternion(Obj(Pose,TEXT("orientation")),Rotation))return;
        Validated.Add(FVector2D(Position.X,Position.Y));
    }
    if(Stamp==RobotPathPhysicsSec)return;
    RobotPath.Reset();
    const int32 Count=FMath::Min(Validated.Num(),RobotPathCapacity);
    for(int32 I=0;I<Count;++I)
    {
        const int32 Index=Count<=1 ? 0 : FMath::RoundToInt(double(I)*(Validated.Num()-1)/(Count-1));
        RobotPath.Add(Validated[Index]);
    }
    RobotPathReceipt=Now;RobotPathPhysicsSec=Stamp;
}
void ARedlineCampaignConsole::CaptureNavStatus(const TSharedPtr<FJsonObject>& Json,double Now)
{
    using namespace CampaignDrawing;const TArray<TSharedPtr<FJsonValue>>* Entries=nullptr;
    if(!FMath::IsFinite(Now) || !RequiredArray(Json,TEXT("status_list"),64,Entries))return;
    double Newest=-1;int32 Status=0;FString GoalId;
    for(const auto& Entry:*Entries)
    {
        if(!Entry || Entry->Type!=EJson::Object)return;
        const auto S=Entry->AsObject(),Info=Obj(S,TEXT("goal_info")),Id=Obj(Info,TEXT("goal_id"));double Stamp;
        const auto& Uuid=Array(Id,TEXT("uuid"));
        if(!FiniteNumber(S,TEXT("status"),0,6,true) || !FRedlineJson::Stamp(Obj(Info,TEXT("stamp")),Stamp) || !NumericArray(Uuid,16,0,255))return;
        FString Candidate;for(const auto& Byte:Uuid){const double B=Byte->AsNumber();if(B!=FMath::FloorToDouble(B))return;Candidate+=FString::Printf(TEXT("%02x"),static_cast<int32>(B));}
        if(Stamp>Newest){Newest=Stamp;Status=Num(S,TEXT("status"));GoalId=Candidate;}
    }
    if(Newest<NavGoalStamp)return;
    NavStatus=Status;NavGoalStamp=Newest;NavGoalId=GoalId;NavStatusReceipt=Now;
}
bool ARedlineCampaignConsole::FitRobotMap(const TArray<FVector2D>& Points,FVector2D Size,FVector2D& Minimum,FVector2D& Maximum)
{
    if(Points.IsEmpty() || Size.ContainsNaN() || Size.X<=0 || Size.Y<=0)return false;
    Minimum=Maximum=Points[0];
    for(const FVector2D& P:Points){if(P.ContainsNaN())return false;Minimum.X=FMath::Min(Minimum.X,P.X);Minimum.Y=FMath::Min(Minimum.Y,P.Y);Maximum.X=FMath::Max(Maximum.X,P.X);Maximum.Y=FMath::Max(Maximum.Y,P.Y);}
    const FVector2D Centre=(Minimum+Maximum)*.5;
    const double MetresPerPixel=FMath::Max(FMath::Max(20.,Maximum.X-Minimum.X)/Size.X,FMath::Max(20.,Maximum.Y-Minimum.Y)/Size.Y)*1.12;
    const FVector2D Half=Size*MetresPerPixel*.5;Minimum=Centre-Half;Maximum=Centre+Half;return true;
}
const ARedlineCampaignConsole::FRadSample& ARedlineCampaignConsole::RadAt(int32 Index) const
{check(RadHistory.IsValidIndex(Index));return RadHistory[(RadHistory.Num()<RadCapacity ? Index : NextRadIndex+Index)%RadHistory.Num()];}
void ARedlineCampaignConsole::CaptureRad(const TSharedPtr<FJsonObject>& Json)
{
    FRedlineEVADose Dose;FString Error;if(!FRedlineEVADose::Parse(Json,Dose,Error))return;
    FRadSample Sample;Sample.Rate=Dose.Detector==TEXT("E") ? Dose.RateE : Dose.RateB;
    Sample.Background=Dose.Detector==TEXT("E") ? Dose.BackgroundE : Dose.BackgroundB;
    if(Sample.Rate>1e9 || Sample.Background>1e9)return;
    Sample.Detector=Dose.Detector;Sample.SourceFile=Dose.SourceFile;Sample.Sol=Dose.SourceSol;
    const double Now=FPlatformTime::Seconds();
    Sample.bMissionTime=Bridge && Bridge->bHasMissionClock && Bridge->StaleMonitor && Bridge->StaleMonitor->IsFresh(TEXT("/redline/mission/clock"),Now);
    Sample.Time=Sample.bMissionTime ? Bridge->MissionClockSec : Now;
    const TSharedPtr<FJsonObject>* Historical=nullptr;
    Sample.bHasHistoricalUtc=Json->TryGetObjectField(TEXT("historical_utc"),Historical) && FRedlineJson::Stamp(*Historical,Sample.HistoricalUtc);
    if(!RadHistory.IsEmpty())
    {
        const FRadSample& Last=RadAt(RadHistory.Num()-1);
        if(Last.Detector!=Sample.Detector || Last.bMissionTime!=Sample.bMissionTime || Sample.Time<Last.Time)
        {RadHistory.Reset();NextRadIndex=0;}
        else if(FMath::IsNearlyEqual(Last.Time,Sample.Time,1e-6))
        {RadHistory[(RadHistory.Num()<RadCapacity ? RadHistory.Num()-1 : NextRadIndex+RadCapacity-1)%RadHistory.Num()]=Sample;RadReceipt=Now;return;}
    }
    if(RadHistory.Num()<RadCapacity)RadHistory.Add(Sample);
    else{RadHistory[NextRadIndex]=Sample;NextRadIndex=(NextRadIndex+1)%RadCapacity;}
    RadReceipt=Now;
}
const TSharedPtr<FJsonObject> ARedlineCampaignConsole::Task()const{return CampaignDrawing::Obj(State,TEXT("task"));}
bool ARedlineCampaignConsole::Fresh()const{return Bridge && Bridge->IsConnected() && Receipt>=0 && FPlatformTime::Seconds()-Receipt<=3;}
bool ARedlineCampaignConsole::IsBusy()const{const FString S=CampaignDrawing::Str(State,TEXT("state"));return S==TEXT("pending") || S==TEXT("running");}
FString ARedlineCampaignConsole::TaskTitle()const{return CampaignDrawing::Str(Task(),TEXT("title"));}
FString ARedlineCampaignConsole::TaskInstruction()const{return CampaignDrawing::Str(Task(),TEXT("instruction"));}
FString ARedlineCampaignConsole::TaskKind()const{return CampaignDrawing::Str(Task(),TEXT("kind"));}
FVector ARedlineCampaignConsole::TaskMap()const
{const auto& XY=CampaignDrawing::Array(Task(),TEXT("xy"));return XY.Num()==2 ? FVector(XY[0]->AsNumber(),XY[1]->AsNumber(),0) : FVector::ZeroVector;}
double ARedlineCampaignConsole::InteractionRadius()const{return CampaignDrawing::Num(Task(),TEXT("radius_m"),4.);}
FVector ARedlineCampaignConsole::NavigationTarget(FVector Here)const
{
    const FVector Final=TaskMap();const auto& Route=CampaignDrawing::Array(State,TEXT("route_xy_m"));
    if(Route.IsEmpty() || FVector::Dist2D(Here,Final)<20)return Final;
    int32 Nearest=0;double Distance=DBL_MAX;
    for(int32 I=0;I<Route.Num();++I){const auto& Pair=Route[I]->AsArray();const FVector Point(Pair[0]->AsNumber(),Pair[1]->AsNumber(),Here.Z);const double D=FVector::DistSquared2D(Point,Here);if(D<Distance){Distance=D;Nearest=I;}}
    const auto& Pair=Route[FMath::Min(Nearest+3,Route.Num()-1)]->AsArray();return FVector(Pair[0]->AsNumber(),Pair[1]->AsNumber(),Here.Z);
}
void ARedlineCampaignConsole::Interact()
{
    if(FParse::Param(FCommandLine::Get(),TEXT("RedlineReadOnlyFilm")))return;
    const FString Kind=TaskKind();
    if(Kind==TEXT("decision") || Kind==TEXT("assessment"))
    {bConsoleOpen=true;Page=0;Notify(TEXT("Bu görev bir karar: panoda 1 veya 2 ile seç."));return;}
    if(Kind==TEXT("collect") || Kind==TEXT("xrf") || Kind==TEXT("weather") || Kind==TEXT("cache"))
    {
        ARedlineFieldWorkActor* Work=nullptr;for(TActorIterator<ARedlineFieldWorkActor> It(GetWorld());It;++It){Work=*It;break;}
        if(!Work)Work=GetWorld()->SpawnActor<ARedlineFieldWorkActor>();
        if(Work)Work->BeginWork(this);return;
    }
    SendCommand(TEXT("START"));
}
void ARedlineCampaignConsole::Notify(const FString& Text)
{
    LastCommandMessage=Text;MessageTime=FPlatformTime::Seconds();
    UE_LOG(LogRedlineCampaign,Display,TEXT("Command feedback: %s"),*Text);
}
void ARedlineCampaignConsole::ExpirePendingCommand(double Now)
{
    if(bPendingCommand && Now-LastCommand>5.)
    {bPendingCommand=false;Notify(TEXT("Komutun cevabı 5 s içinde gelmedi; durumu kontrol edip tekrar dene."));}
}
void ARedlineCampaignConsole::SendCommand(const FString& Command)
{
    // Playtest: silent returns made E look broken. Every refusal now leaves a visible message.
    const double Now=FPlatformTime::Seconds();
    if(!Fresh()){Notify(TEXT("ROS görev durumu bekleniyor; bağlantı gelince tekrar dene."));return;}
    if(bPendingCommand){Notify(TEXT("Önceki komutun cevabı bekleniyor."));return;}
    if(Now-LastCommand<.5)return;  // key repeat, not a refusal
    LastCommand=Now;bPendingCommand=true;
    UE_LOG(LogRedlineCampaign,Display,TEXT("Command %s sent for task %s"),*Command,*TaskTitle());
    auto Args=MakeShared<FJsonObject>();const FString ID=FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphens);
    Args->SetStringField(TEXT("request_id"),ID);Args->SetStringField(TEXT("command"),Command);
    Args->SetStringField(TEXT("target_id"),CampaignDrawing::Str(Task(),TEXT("target_id")));
    Args->SetNumberField(TEXT("expected_revision"),CampaignDrawing::Num(State,TEXT("revision")));
    TWeakObjectPtr<ARedlineCampaignConsole> Weak(this);FString Error;
    Bridge->DispatchMissionCommand(ID,TEXT("/redline/campaign/command"),TEXT("redline_msgs/srv/MissionCommand"),Args,
        {TEXT("/redline/campaign/state"),TEXT("/redline/mission/clock"),TEXT("/crew/EV1/state")},
        [Weak](bool OK,const TSharedPtr<FJsonObject>& Values,const FString& Why)
        {if(auto* Self=Weak.Get()){Self->bPendingCommand=false;Self->Notify(OK ? CampaignDrawing::Str(Values,TEXT("reason")) : TEXT("Komut bağlantısı kesildi; yeniden göndermeden durumu kontrol et."));}},Error);
    if(!Error.IsEmpty()){bPendingCommand=false;Notify(Error.StartsWith(TEXT("stale prerequisite")) ? TEXT("Veri akışı bekleniyor (")+Error.Mid(20)+TEXT(")") : Error);}
}
void ARedlineCampaignConsole::UpdateInteraction()
{
    if(!Interaction || !State || bLocalWorkOwnsPresentation)return;
    using namespace CampaignDrawing;
    const FString Kind=TaskKind(),Request=Str(State,TEXT("operation_id"));
    const bool Human=Str(Task(),TEXT("actor"))==TEXT("EV1");
    // Manual field work owns its own pose from preparation through ROS result.
    // A cancelled view must not be reacquired by this legacy feedback preview.
    if(Human && (Kind==TEXT("collect") || Kind==TEXT("xrf") || Kind==TEXT("weather") || Kind==TEXT("cache")))return;
    if(IsBusy() && Human && (Kind==TEXT("collect") || Kind==TEXT("xrf") || Kind==TEXT("weather") || Kind==TEXT("cache")))
    {
        if(AnimatingRequest!=Request)
        {
            auto* PC=GetWorld()->GetFirstPlayerController();auto* A=PC ? Cast<ARedlineAstronautCharacter>(PC->GetPawn()) : nullptr;
            FVector Target=TaskMap(),Surface;if(A){Target.Z=URedlineCoords::UeToRosLocation(A->GetActorLocation()).Z;if(URedlineCoords::TraceTerrainHeight(this,Target,100,Surface))Target.Z=Surface.Z;}
            if(Interaction->IsInteracting())Interaction->EndInteraction(false);
            if(!Interaction->BeginInteraction(A,Target,Kind))return;
            AnimatingRequest=Request;
        }
        Interaction->SetProgress(Num(State,TEXT("progress")),Str(State,TEXT("operation_phase")));
    }
    else if(!AnimatingRequest.IsEmpty())
    {Interaction->EndInteraction(Str(State,TEXT("state"))!=TEXT("failed"));AnimatingRequest.Empty();}
}
void ARedlineCampaignConsole::Tick(float Delta)
{
    Super::Tick(Delta);ExpirePendingCommand(FPlatformTime::Seconds());auto* PC=GetWorld()->GetFirstPlayerController();auto* View=GetWorld()->GetGameViewport();
    bool Cinematic=false;for(TActorIterator<ARedlinePrologueDirector> It(GetWorld());It;++It){Cinematic=It->IsCinematic();break;}
    if(PC && View && View->Viewport && View->Viewport->HasFocus() && !Cinematic && !bTabletOpen)
    {
        if(PC->WasInputKeyJustPressed(EKeys::M))bConsoleOpen=!bConsoleOpen;
        if(bConsoleOpen && PC->WasInputKeyJustPressed(EKeys::Escape))bConsoleOpen=false;
        if(bConsoleOpen)
        {
            if(PC->WasInputKeyJustPressed(EKeys::Tab))CyclePage(1);
            if(Page==7)
            {
                if(PC->WasInputKeyJustPressed(EKeys::L))CycleAtlasLayer();
                if(PC->WasInputKeyJustPressed(EKeys::Right))CycleAtlasStation(1);
                if(PC->WasInputKeyJustPressed(EKeys::Left))CycleAtlasStation(-1);
                if(PC->WasInputKeyJustPressed(EKeys::Up))CycleAtlasTask(-1);
                if(PC->WasInputKeyJustPressed(EKeys::Down))CycleAtlasTask(1);
            }
            if(PC->WasInputKeyJustPressed(EKeys::P))StartLabAssay();
            const int32 Count=CampaignDrawing::Array(State,TEXT("products")).Num();
            if(Page==1 && Count>0)
            {
                if(PC->WasInputKeyJustPressed(EKeys::Right))ProductSelection=(ProductSelection+1+Count)%Count;
                if(PC->WasInputKeyJustPressed(EKeys::Left))ProductSelection=(ProductSelection<0 ? Count-1 : ProductSelection+Count-1)%Count;
            }
            const FString Kind=TaskKind();
            if(PC->WasInputKeyJustPressed(EKeys::One))
            {if(Kind==TEXT("decision"))SendCommand(TEXT("CHOOSE_RIDGE"));else if(Kind==TEXT("assessment"))SendCommand(TEXT("SUPPORT_PATTERN"));}
            if(PC->WasInputKeyJustPressed(EKeys::Two))
            {if(Kind==TEXT("decision"))SendCommand(TEXT("CHOOSE_HOLLOW"));else if(Kind==TEXT("assessment"))SendCommand(TEXT("NEED_MORE_DATA"));}
            if(PC->WasInputKeyJustPressed(EKeys::E))Interact();
            if(PC->WasInputKeyJustPressed(EKeys::X))SendCommand(TEXT("CANCEL"));
        }
    }
    if(!Fresh() && !AnimatingRequest.IsEmpty()){Interaction->EndInteraction(false);AnimatingRequest.Empty();}
    if(ScreenTexture && FPlatformTime::Seconds()-LastRender>.5){LastRender=FPlatformTime::Seconds();ScreenTexture->UpdateResource();}
}
void ARedlineCampaignConsole::RenderScreen(UCanvas* Target,int32 Width,int32 Height){DrawConsole(Target,Width,Height,true);}
void ARedlineCampaignConsole::DrawConsole(UCanvas* Target,int32 Width,int32 Height,bool WorldScreen)
{
    if(Page>=4){DrawTabletPage(Target,Width,Height,Page);return;}
    using namespace CampaignDrawing;if(!Target)return;if(Page==0){DrawMissionBoard(Target,Width,Height);return;}FDraw D{Target,FMath::Min(Width/1280.f,Height/720.f)};
    D.Rect(0,0,1280,720,Background);
    D.Text(TEXT("REDLINE    /    Sefer kaydı"),30,22,1.65);
    D.Text(Fresh() ? TEXT("CANLI ROS · ")+Str(State,TEXT("run_id")) : TEXT("VERİ ESKİ / BAĞLANTI BEKLENİYOR"),30,52,.9,Fresh() ? Cyan : Amber);
    D.Text(TEXT("M / Esc kapat   Tab sayfa   E işlem   X iptal"),742,30,.95,Muted);
    const TCHAR* Pages[]={TEXT("GÖREVLER"),TEXT("BİLİM / NUMUNELER"),TEXT("ROBOTLAR"),TEXT("ÇEVRE / GÜVENLİK")};
    for(int32 I=0;I<4;++I){if(I==Page)D.Rect(28+I*309,114,160,2,RedlineConsoleTheme::Copper);D.Text(Pages[I],40+I*309,94,1.1,I==Page ? Cyan : Muted);}
    if(!HasState()){D.Text(TEXT("Görev akışı bekleniyor. Eski bir görev tamamlandı sayılmaz."),38,155,1.3,Amber);return;}
    D.Text(TaskTitle(),34,137,1.35,Amber);
    D.Text(TaskInstruction().Left(146),34,164,.9);
    D.Text(Str(State,TEXT("message")).Left(155),34,190,.95,Cyan);
    D.Rect(30,219,1220,10,Panel);D.Rect(30,219,1220*Num(State,TEXT("progress")),10,Cyan);
    D.Text(Str(State,TEXT("operation_phase"))+FString::Printf(TEXT(" · %.0f%%"),100*Num(State,TEXT("progress"))),34,237,.95,Muted);
    const auto& Products=Array(State,TEXT("products"));const auto& Samples=Array(State,TEXT("samples"));
    if(Page==0)
    {
        const auto& Tasks=Array(State,TEXT("tasks"));const int32 Current=Num(State,TEXT("task_index"));
        const int32 First=FMath::Min(Current/12*12,FMath::Max(0,(Tasks.Num()-1)/12*12));
        for(int32 I=First;I<FMath::Min(First+12,Tasks.Num());++I)
        {
            const auto T=Tasks[I]->AsObject();const int32 Col=(I-First)/6,Row=(I-First)%6;const float X=30+Col*620,Y=280+Row*49;
            D.Rect(X,Y,606,44,I==Current ? FLinearColor(.12,.11,.065,1) : Panel);
            D.Text(Str(T,TEXT("title")),X+12,Y+6,1.05,I<Current ? Cyan : I==Current ? Amber : Muted);
            D.Text(Str(T,TEXT("actor"))+TEXT(" / ")+Str(T,TEXT("target_id")),X+12,Y+25,.8,Muted);
            D.Text(I<Current ? TEXT("KAYITLI") : I==Current ? TEXT("ETKİN") : TEXT("SIRADA"),X+515,Y+9,.8,I<Current ? Cyan : Muted);
        }
        if(TaskKind()==TEXT("decision"))D.Text(TEXT("1 · Sırt rotası     2 · Çukur rotası / ölçüm karşılaştırması"),34,595,1.2,Amber);
        if(TaskKind()==TEXT("assessment"))D.Text(TEXT("1 · Örüntü lehine karar     2 · Belirsizlik / ek ölçüm gerekli"),34,595,1.2,Amber);
    }
    else if(Page==1)
    {
        TSharedPtr<FJsonObject> Product;
        if(Products.IsValidIndex(ProductSelection))Product=Products[ProductSelection]->AsObject();
        else for(int32 I=Products.Num()-1;I>=0;--I){auto P=Products[I]->AsObject();if(Array(Obj(P,TEXT("summary")),TEXT("values")).Num()>1){Product=P;break;}}
        if(Product)
        {
            const auto Summary=Obj(Product,TEXT("summary"));const auto& Values=Array(Summary,TEXT("values"));const auto& Sigma=Array(Summary,TEXT("sigma"));const auto& Labels=Array(Summary,TEXT("labels"));
            D.Text(Str(Product,TEXT("instrument"))+TEXT(" / ")+Str(Product,TEXT("target_id")),35,274,1.1,Cyan);
            const FString Unit=Str(Summary,TEXT("unit"));
            const FString UnitLabel=Unit==TEXT("mass_percent_SCENARIO") ? TEXT("Kütlece yüzde (%) · Senaryo") : Unit==TEXT("percent_SCENARIO") ? TEXT("Yüzde (%) · Senaryo") : Unit==TEXT("scenario_index") ? TEXT("Senaryo indeksi") : Unit;
            D.Text(UnitLabel+TEXT(" · ±1σ"),35,300,.85,Muted);
            const int32 N=FMath::Min(Values.Num(),8);double Max=1;
            for(int32 I=0;I<N;++I)Max=FMath::Max(Max,Values[I]->AsNumber()+(Sigma.IsValidIndex(I) ? Sigma[I]->AsNumber() : 0));
            const float X0=66,Y0=507,H=165,Step=540.f/FMath::Max(1,N);D.Line(X0,Y0,X0+540,Y0,Muted);
            for(int32 I=0;I<N;++I)
            {
                const float V=Values[I]->AsNumber(),E=Sigma.IsValidIndex(I) ? Sigma[I]->AsNumber() : 0,X=X0+I*Step+Step*.5f,Y=Y0-V/Max*H;
                D.Rect(X-Step*.27f,Y,Step*.54f,Y0-Y,RedlineConsoleTheme::Copper);D.Line(X,Y-E/Max*H,X,Y+E/Max*H,Amber,2);
                D.Line(X-8,Y-E/Max*H,X+8,Y-E/Max*H,Amber,2);D.Line(X-8,Y+E/Max*H,X+8,Y+E/Max*H,Amber,2);
                D.Text(FString::Printf(TEXT("%.1f"),V),X-14,Y-28,.8);D.Text(Labels.IsValidIndex(I) ? Labels[I]->AsString() : FString::FromInt(I),X-24,Y0+12,.8,Muted);
            }
            D.Text(TEXT("0"),38,Y0-8,.8,Muted);D.Text(FString::Printf(TEXT("%.1f"),Max),35,Y0-H,.8,Muted);
            D.Text(Str(Product,TEXT("product_id")).Left(70),35,552,.75,Muted);
        }
        else D.Text(TEXT("Henüz bileşim ürünü yok. Ölçüm tamamlanınca grafik oluşur."),35,298,1.,Muted);
        D.Rect(650,275,594,310,Panel);D.Text(FString::Printf(TEXT("NUMUNE ZİNCİRİ / %d kayıt"),Samples.Num()),665,287,1.1,Cyan);
        for(int32 I=0;I<FMath::Min(3,Samples.Num());++I)
        {
            const auto S=Samples[I]->AsObject();const auto& O=Array(S,TEXT("origin_point_m"));const auto& A=Array(S,TEXT("analysis_point_m"));const int32 Y=321+I*82;
            D.Text(Str(S,TEXT("sample_id")).Left(57),665,Y,.85);
            const TCHAR* States[]={TEXT("Seçildi"),TEXT("Erişim uygun"),TEXT("Ön konumda"),TEXT("Hazır"),TEXT("Toplanıyor"),TEXT("Alındı"),TEXT("Çantada saklanıyor"),TEXT("Laboratuvarda kayıtlı"),TEXT("İşlem başarısız")};
            const int32 SampleState=static_cast<int32>(Num(S,TEXT("state"),-1));
            D.Text(SampleState>=0 && SampleState<UE_ARRAY_COUNT(States) ? States[SampleState] : TEXT("Durum bekleniyor"),665,Y+20,.9,Muted);
            if(O.Num()==3 && A.Num()==3)D.Text(FString::Printf(TEXT("Köken E%.1f N%.1f / Analiz E%.1f N%.1f"),O[0]->AsNumber(),O[1]->AsNumber(),A[0]->AsNumber(),A[1]->AsNumber()),665,Y+42,.85,Cyan);
        }
        D.Text(TEXT("← / → Ürün değiştir · SIMULATED / kalibre edilmemiş senaryo gürültüsü"),35,610,.95,Amber);
    }
    else if(Page==2)
    {
        const bool PoseFresh=RobotFresh(RoverReceipt),PathFresh=RobotFresh(RobotPathReceipt,3),StatusFresh=RobotFresh(NavStatusReceipt,3);
        const double Now=FPlatformTime::Seconds();
        D.Rect(30,277,600,330,Panel);D.Rect(650,277,596,330,Panel);
        D.Text(TEXT("ROVER / GERÇEK İZ VE NAV2 PLANI"),48,291,1.12,Cyan);
        D.Text(TEXT("ENU · metre · üstten görünüm · fizik pozu yalnız sunum"),48,313,.78,Muted);
        const FVector2D MapStart(64,349),MapSize(548,208);TArray<FVector2D> Points;
        for(const auto& P:RoverTrack)Points.Add(FVector2D(P.MapMetres.X,P.MapMetres.Y));
        Points.Append(RobotPath);
        if(RoverReceipt>=0)Points.Add(FVector2D(RoverMap.X,RoverMap.Y));
        const bool RoverTask=Str(Task(),TEXT("actor"))==TEXT("rover_1");
        if(RoverTask){const FVector Goal=TaskMap();Points.Add(FVector2D(Goal.X,Goal.Y));}
        FVector2D Minimum,Maximum;
        if(FitRobotMap(Points,MapSize,Minimum,Maximum))
        {
            auto Pixel=[&](FVector2D P){return MapStart+FVector2D((P.X-Minimum.X)/(Maximum.X-Minimum.X)*MapSize.X,(Maximum.Y-P.Y)/(Maximum.Y-Minimum.Y)*MapSize.Y);};
            const FLinearColor Grid(.07,.12,.15,1);
            for(int32 I=0;I<=4;++I){const double A=I/4.;D.Line(MapStart.X+A*MapSize.X,MapStart.Y,MapStart.X+A*MapSize.X,MapStart.Y+MapSize.Y,Grid);D.Line(MapStart.X,MapStart.Y+A*MapSize.Y,MapStart.X+MapSize.X,MapStart.Y+A*MapSize.Y,Grid);}
            for(int32 I=1;I<RobotPath.Num();++I){const FVector2D A=Pixel(RobotPath[I-1]),B=Pixel(RobotPath[I]);D.Line(A.X,A.Y,B.X,B.Y,PathFresh ? FLinearColor(.4,1,.45,1) : Muted,2);}
            for(int32 I=1;I<RoverTrack.Num();++I){const FVector2D A=Pixel(FVector2D(RoverTrack[I-1].MapMetres)),B=Pixel(FVector2D(RoverTrack[I].MapMetres));D.Line(A.X,A.Y,B.X,B.Y,PoseFresh ? Cyan : Muted,2);}
            if(RoverReceipt>=0){const FVector2D P=Pixel(FVector2D(RoverMap));D.Rect(P.X-4,P.Y-4,8,8,PoseFresh ? Amber : Muted);}
            if(RoverTask){const FVector2D G=Pixel(FVector2D(TaskMap()));D.Line(G.X-5,G.Y,G.X+5,G.Y,Amber,2);D.Line(G.X,G.Y-5,G.X,G.Y+5,Amber,2);}
            D.Text(FString::Printf(TEXT("N %.0f"),Maximum.Y),45,335,.7,Muted);
            D.Text(FString::Printf(TEXT("E %.0f / N %.0f"),Minimum.X,Minimum.Y),48,MapStart.Y+MapSize.Y+3,.7,Muted);D.Text(FString::Printf(TEXT("E %.0f"),Maximum.X),535,MapStart.Y+MapSize.Y+3,.7,Muted);
        }
        else D.Text(TEXT("Gerçek poz / Nav2 planı bekleniyor"),73,417,1.1,Amber);
        D.Text(TEXT("Turkuaz: gerçek iz   Yeşil: Nav2 planı   Sarı: rover/hedef"),48,584,.78,Muted);
        D.Text(TEXT("ROVER / ROS–GAZEBO"),668,291,1.15,Cyan);
        D.Text(RoverReceipt<0 ? TEXT("Fizik pozu henüz gelmedi") : FString::Printf(TEXT("Fizik pozu · %.1f sn önce · %s"),FMath::Max(0.,Now-RoverReceipt),PoseFresh ? TEXT("güncel") : TEXT("ESKİ")),668,318,.93,PoseFresh ? Cyan : Amber);
        if(RoverReceipt>=0)D.Text(FString::Printf(TEXT("E %.1f   N %.1f   Z %.1f m"),RoverMap.X,RoverMap.Y,RoverMap.Z),668,342,.92);
        D.Text(PoseFresh && bHasRoverSpeed ? FString::Printf(TEXT("Hız %.2f m/sn · fizik poz farkından"),RoverSpeedMps) : TEXT("Hız — · güncel ardışık fizik pozu gerekli"),668,366,.9,PoseFresh ? FLinearColor::White : Muted);
        const TCHAR* StatusNames[]={TEXT("Bilinmiyor"),TEXT("Kabul edildi"),TEXT("Yürütülüyor"),TEXT("İptal ediliyor"),TEXT("Hedefe ulaştı"),TEXT("İptal edildi"),TEXT("Başarısız")};
        D.Text(NavGoalId.IsEmpty() ? TEXT("Son Nav2 görevi: henüz yok") : FString::Printf(TEXT("Son Nav2 görevi: %s%s"),StatusNames[FMath::Clamp(NavStatus,0,6)],StatusFresh ? TEXT("") : TEXT(" · ESKİ")),668,392,.93,StatusFresh ? Cyan : Muted);
        D.Text(RobotPathReceipt<0 ? TEXT("Nav2 planı henüz gelmedi") : FString::Printf(TEXT("Plan · %.1f sn önce · %d nokta%s"),FMath::Max(0.,Now-RobotPathReceipt),RobotPath.Num(),PathFresh ? TEXT("") : TEXT(" · ESKİ")),668,416,.85,PathFresh ? Cyan : Muted);
        D.Line(668,441,1228,441,Muted);
        const auto Scout=Obj(State,TEXT("scout"));const bool ScoutFresh=Fresh() && Scout && Num(State,TEXT("scout_age_s"),9999)+FMath::Max(0.,Now-Receipt)<2;
        D.Text(TEXT("SCOUT / ÖNCÜ KEŞİF"),668,454,1.08,Cyan);
        D.Text(ScoutFresh ? Str(Scout,TEXT("phase"))+FString::Printf(TEXT(" · Pil %.1f Wh"),Num(Scout,TEXT("battery_wh"))) : TEXT("Scout verisi eski / henüz yok"),668,480,.95,ScoutFresh ? Cyan : Amber);
        const auto& XYZ=Array(Scout,TEXT("map_xyz_m"));
        if(ScoutFresh && XYZ.Num()==3)D.Text(FString::Printf(TEXT("E %.1f   N %.1f   Z %.1f m"),XYZ[0]->AsNumber(),XYZ[1]->AsNumber(),XYZ[2]->AsNumber()),668,505,.9);
        D.Text(TEXT("Gözlem SIMULATED · sensör algısı değildir"),668,531,.85,Muted);
        D.Text(FString::Printf(TEXT("Ürün %d   Kanıt %d   Numune %d"),Products.Num(),Array(State,TEXT("evidence_ids")).Num(),Samples.Num()),668,568,.95);
        D.Text(TEXT("E · Etkin robot görevini başlat   X · İptal iste"),38,620,1.05,Amber);
    }
    else
    {
        ARedlineOverlay* O=nullptr;for(TActorIterator<ARedlineOverlay> It(GetWorld());It;++It){O=*It;break;}
        D.Text(FString::Printf(TEXT("PET %.1f dakika"),Num(State,TEXT("pet_s"))/60.),38,282,1.4,Cyan);
        if(O && O->Fresh(O->LineReceipt) && O->Line.bHasMargin)D.Text(FString::Printf(TEXT("Dönüş payı %.1f dk"),O->Line.MarginMinutes),38,324,1.4,Amber);
        if(O && O->Fresh(O->CrewReceipt,3)){D.Text(FString::Printf(TEXT("O2 %.3f kg    Su %.3f kg    Pil %.1f Wh"),O->Crew.OxygenKg,O->Crew.WaterKg,O->Crew.BatteryWh),38,371,1.2);}
        D.Text(TEXT("Görev saati ve Gazebo fizik saati ayrıdır."),38,431,.9,Muted);
        D.Text(TEXT("Arazi: DERIVED · Ekip/giysi: SCENARIO"),38,468,.9,Muted);
        if(O && O->AcceptedDose>0)D.Text(O->Dose.AlarmText(O->Fresh(O->DoseReceipt)),38,518,1.1,Amber);
        D.Rect(650,274,596,310,Panel);
        if(RadHistory.IsEmpty())D.Text(TEXT("RAD ÖLÇÜMÜ BEKLENİYOR"),670,298,1.1,Amber);
        else
        {
            const FRadSample& Last=RadAt(RadHistory.Num()-1),First=RadAt(0);
            const bool DoseFresh=Bridge && Bridge->IsConnected() && RadReceipt>=0 && FPlatformTime::Seconds()-RadReceipt<=5;
            D.Text(TEXT("RAD ")+Last.Detector+TEXT(" / DOZ HIZI (µGy/sa)"),668,287,1.1,Cyan);
            D.Text(DoseFresh ? TEXT("GÜNCEL") : TEXT("VERİ ESKİ"),1120,289,.85,DoseFresh ? Cyan : Amber);
            const double MaxTime=Last.Time,MinTime=First.Time,Range=FMath::Max(1.,MaxTime-MinTime);
            double MaxValue=1.;for(int32 I=0;I<RadHistory.Num();++I){const auto& V=RadAt(I);MaxValue=FMath::Max(MaxValue,FMath::Max(V.Rate,V.Background*1.25));}MaxValue*=1.12;
            const float GX=705,GY=515,GW=504,GH=170;
            D.Line(GX,GY,GX+GW,GY,Muted);D.Line(GX,GY-GH,GX,GY,Muted);
            D.Text(TEXT("0"),674,GY-8,.8,Muted);D.Text(FString::Printf(TEXT("%.2f"),MaxValue),664,GY-GH-7,.8,Muted);
            auto PX=[&](double Time){return GX+float((Time-MinTime)/Range)*GW;};
            auto PY=[&](double Value){return GY-float(Value/MaxValue)*GH;};
            for(int32 I=1;I<RadHistory.Num();++I)
            {
                const auto& A=RadAt(I-1);const auto& B=RadAt(I);const float XA=PX(A.Time),XB=PX(B.Time);
                // The archive replay is nearest-neighbour/stepwise. Do not draw
                // an invented linearly interpolated dose between observations.
                D.Line(XA,PY(A.Rate),XB,PY(A.Rate),DoseFresh ? Cyan : Muted,2);D.Line(XB,PY(A.Rate),XB,PY(B.Rate),DoseFresh ? Cyan : Muted,2);
                D.Line(XA,PY(A.Background*1.25),XB,PY(A.Background*1.25),Amber,1);
            }
            if(RadHistory.Num()==1)D.Rect(PX(Last.Time)-2,PY(Last.Rate)-2,4,4,Cyan);
            D.Text(FString::Printf(TEXT("%.1f"),Last.bMissionTime ? MinTime/60. : 0.),GX,GY+12,.8,Muted);
            D.Text(FString::Printf(TEXT("%.1f %s"),Last.bMissionTime ? MaxTime/60. : Range/60.,Last.bMissionTime ? TEXT("PET dk") : TEXT("geçen dk")),GX+GW-90,GY+12,.8,Muted);
            D.Text(FString::Printf(TEXT("Doz %.2f · Arka plan +%%25 %.2f"),Last.Rate,Last.Background*1.25),668,552,.85,Amber);
            D.Text(FString::Printf(TEXT("PDS PPI · sol %d · ölçüm · %d örnek"),Last.Sol,RadHistory.Num()),650,599,.9,Cyan);
            if(Last.bHasHistoricalUtc)D.Text((FDateTime::FromUnixTimestamp(int64(Last.HistoricalUtc))).ToString(TEXT("%Y-%m-%d %H:%M UTC")),650,621,.8,Muted);
            else D.Text(TEXT("Arşiv gözlem zamanı bu akışta yok"),650,621,.8,Muted);
        }
    }
    D.Rect(28,648,1220,1,Cyan);D.Text(LastCommandMessage.Left(155),32,661,.9,Amber);
    D.Text(FString::Printf(TEXT("%.0f / %.0f adım · ürünler ve kararlar diske kaydedilir · %s"),Num(State,TEXT("task_index")),Num(State,TEXT("task_count")),Fresh() ? TEXT("güncel") : TEXT("ESKİ VERİ")),32,690,.85,Muted);
}
void ARedlineCampaignConsole::DrawTaskCard(UCanvas* Target)
{
    for(TActorIterator<ARedlineFieldWorkActor> It(GetWorld());It;++It)if(It->IsWorking()){It->DrawWork(Target);return;}
    DrawMissionPrompt(Target);
}
