#include "RedlineMissionSites.h"
#include "RedlineBridgeSubsystem.h"
#include "RedlineCoords.h"
#include "RedlineTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Camera/PlayerCameraManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace MissionSites
{
TSharedPtr<FJsonObject> Object(const TSharedPtr<FJsonObject>& J,const TCHAR* Key)
{const TSharedPtr<FJsonObject>* V;return J && J->TryGetObjectField(Key,V) ? *V : nullptr;}
bool String(const TSharedPtr<FJsonObject>& J,const TCHAR* Key,FString& Out,int32 Max)
{return J && J->TryGetStringField(Key,Out) && !Out.IsEmpty() && Out.Len()<=Max;}
bool Number(const TSharedPtr<FJsonObject>& J,const TCHAR* Key,double& Out,double Min,double Max)
{return J && J->TryGetNumberField(Key,Out) && FMath::IsFinite(Out) && Out>=Min && Out<=Max;}
bool XY(const TSharedPtr<FJsonObject>& J,const TCHAR* Key,FVector& Out)
{
    const TArray<TSharedPtr<FJsonValue>>* V;
    if(!J || !J->TryGetArrayField(Key,V) || V->Num()!=2)return false;
    double X,Y;if(!(*V)[0]->TryGetNumber(X) || !(*V)[1]->TryGetNumber(Y) || !FMath::IsFinite(X) || !FMath::IsFinite(Y) || FMath::Max(FMath::Abs(X),FMath::Abs(Y))>1e7)return false;
    Out=FVector(X,Y,0);return true;
}
FString Endpoint(const FString& Kind)
{
    if(Kind==TEXT("scout"))return TEXT("/scout_1/execute_scout");
    if(Kind==TEXT("collect"))return TEXT("/redline/science/collect_sample");
    if(Kind==TEXT("xrf"))return TEXT("/rover_1/contact_science");
    if(Kind==TEXT("libs"))return TEXT("/rover_1/remote_libs");
    if(Kind==TEXT("dan"))return TEXT("/rover_1/neutron_survey");
    if(Kind==TEXT("drill"))return TEXT("/rover_1/drill");
    if(Kind==TEXT("cache"))return TEXT("/redline/science/cache_sample");
    if(Kind==TEXT("weather"))return TEXT("/redline/science/deploy_station");
    return TEXT("/redline/campaign/command");
}
FName Tool(const FString& Kind)
{
    if(Kind==TEXT("collect"))return TEXT("sample_tube");if(Kind==TEXT("xrf"))return TEXT("tool_apxs");
    if(Kind==TEXT("cache"))return TEXT("sample_case");if(Kind==TEXT("weather"))return TEXT("science_station");
    return NAME_None; // Remote robot tools belong to the actual robot presentation.
}
}

ARedlineMissionSites::ARedlineMissionSites()
{
    PrimaryActorTick.bCanEverTick=true;RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("SiteLabelsRoot"));
    SetActorEnableCollision(false);
}
void ARedlineMissionSites::BeginPlay()
{
    Super::BeginPlay();if(auto* GI=GetGameInstance())Bridge=GI->GetSubsystem<URedlineBridgeSubsystem>();
    for(int32 I=0;I<Capacity;++I)
    {
        auto* Label=NewObject<UTextRenderComponent>(this);AddInstanceComponent(Label);Label->SetupAttachment(RootComponent);Label->RegisterComponent();
        Label->SetHorizontalAlignment(EHTA_Center);Label->SetVerticalAlignment(EVRTA_TextCenter);Label->SetCollisionEnabled(ECollisionEnabled::NoCollision);Label->SetCastShadow(false);Labels.Add(Label);
        auto* Prop=NewObject<UStaticMeshComponent>(this);AddInstanceComponent(Prop);Prop->SetupAttachment(RootComponent);Prop->RegisterComponent();
        Prop->SetCollisionEnabled(ECollisionEnabled::NoCollision);Prop->SetSimulatePhysics(false);Props.Add(Prop);
    }
    HideAll();LoadProps();if(Bridge){TopicHandle=Bridge->OnTopic.AddUObject(this,&ARedlineMissionSites::Receive);Bridge->OnConnectionChanged.AddDynamic(this,&ARedlineMissionSites::ConnectionChanged);Bridge->Subscribe(TEXT("/redline/campaign/state"),TEXT("std_msgs/msg/String"),200,3);}
}
bool ARedlineMissionSites::ParseSnapshot(const TSharedPtr<FJsonObject>& J,FRedlineMissionSitesState& Out)
{
    using namespace MissionSites;FRedlineMissionSitesState Next;FString Schema;double Count,Index,Revision;
    const TArray<TSharedPtr<FJsonValue>>* Tasks;const TArray<TSharedPtr<FJsonValue>>* Completed;
    if(!String(J,TEXT("schema"),Schema,64) || Schema!=TEXT("redline.campaign.v1") || !String(J,TEXT("run_id"),Next.RunId,100)
       || !Number(J,TEXT("revision"),Revision,0,MAX_uint32) || Revision!=FMath::FloorToDouble(Revision)
       || !Number(J,TEXT("task_count"),Count,1,Capacity) || Count!=FMath::FloorToDouble(Count)
       || !Number(J,TEXT("task_index"),Index,0,Count) || Index!=FMath::FloorToDouble(Index)
       || !Number(J,TEXT("progress"),Next.Progress,0,1) || !String(J,TEXT("state"),Next.OperationState,16)
       || !J->TryGetBoolField(TEXT("done"),Next.bDone) || Next.bDone!=(Index==Count)
       || !J->TryGetArrayField(TEXT("tasks"),Tasks) || Tasks->Num()!=int32(Count)
       || !J->TryGetArrayField(TEXT("completed"),Completed) || Completed->Num()!=int32(Index))return false;
    if(Next.OperationState!=TEXT("ready") && Next.OperationState!=TEXT("pending") && Next.OperationState!=TEXT("running") && Next.OperationState!=TEXT("complete") && Next.OperationState!=TEXT("failed"))return false;
    if(Next.bDone!=(Next.OperationState==TEXT("complete")))return false;
    FString Frame;if(J->TryGetStringField(TEXT("frame"),Frame) && Frame!=TEXT("map"))return false;
    TSet<FString> Ids;
    for(int32 I=0;I<Tasks->Num();++I)
    {
        auto T=(*Tasks)[I]->AsObject();auto P=Object(T,TEXT("presentation"));FRedlineMissionSite Site;FVector Presented;FString Actor,Mode,Command;bool Requires;
        if(!String(T,TEXT("id"),Site.Id,96) || Ids.Contains(Site.Id) || !String(T,TEXT("title"),Site.Title,256)
           || !String(T,TEXT("kind"),Site.Kind,32) || !String(T,TEXT("actor"),Site.Actor,32)
           || !XY(T,TEXT("xy"),Site.Map) || !Number(T,TEXT("radius_m"),Site.RadiusMetres,.1,100)
           || !String(P,TEXT("state"),Site.State,16) || !XY(P,TEXT("site_xy_m"),Presented) || !Presented.Equals(Site.Map,.001)
           || !String(P,TEXT("actor"),Actor,32) || Actor!=Site.Actor || !String(P,TEXT("endpoint"),Site.Endpoint,128) || Site.Endpoint!=Endpoint(Site.Kind)
           || !String(P,TEXT("command_endpoint"),Command,128) || Command!=TEXT("/redline/campaign/command")
           || !String(P,TEXT("interaction_mode"),Mode,16) || !P->TryGetBoolField(TEXT("requires_proximity"),Requires)
           || !P->TryGetBoolField(TEXT("enabled"),Site.bEnabled))return false;
        const bool RobotKind=Site.Kind==TEXT("libs") || Site.Kind==TEXT("dan") || Site.Kind==TEXT("drill");
        const bool HumanKind=Site.Kind==TEXT("briefing") || Site.Kind==TEXT("decision") || Site.Kind==TEXT("collect") || Site.Kind==TEXT("xrf") || Site.Kind==TEXT("weather") || Site.Kind==TEXT("cache") || Site.Kind==TEXT("assessment") || Site.Kind==TEXT("debrief");
        if(!(RobotKind && Site.Actor==TEXT("rover_1")) && !(HumanKind && Site.Actor==TEXT("EV1")) && !(Site.Kind==TEXT("scout") && Site.Actor==TEXT("scout_1")))return false;
        Site.bRemote=RobotKind;
        if(Mode!=(Site.bRemote ? TEXT("remote") : TEXT("local")) || Requires==Site.bRemote)return false;
        const FString Expected=I<Index ? TEXT("complete") : I==Index ? TEXT("active") : TEXT("locked");
        if(Site.State!=Expected || (Site.State!=TEXT("active") && Site.bEnabled) || ((Next.OperationState==TEXT("pending") || Next.OperationState==TEXT("running")) && Site.bEnabled))return false;
        if(I<Index){FString Id;if(!(*Completed)[I]->TryGetString(Id) || Id!=Site.Id)return false;}
        if(T->TryGetStringField(TEXT("frame"),Frame) && Frame!=TEXT("map"))return false;
        if(P->TryGetStringField(TEXT("frame"),Frame) && Frame!=TEXT("map"))return false;
        Ids.Add(Site.Id);Next.Sites.Add(MoveTemp(Site));
    }
    FString Current;if(!String(Object(J,TEXT("task")),TEXT("id"),Current,96) || Current!=Next.Sites[FMath::Min(int32(Index),Next.Sites.Num()-1)].Id)return false;
    Next.ActiveIndex=Next.bDone ? INDEX_NONE : int32(Index);Next.Revision=int64(Revision);Out=MoveTemp(Next);return true;
}
bool ARedlineMissionSites::AcceptSnapshot(const TSharedPtr<FJsonObject>& J,double Now)
{
    FRedlineMissionSitesState Next;if(!FMath::IsFinite(Now) || !ParseSnapshot(J,Next))return false;
    if(Next.RunId==State.RunId && Next.Revision<State.Revision)return false;
    if(Next.RunId==State.RunId && Next.Revision==State.Revision && Next.ActiveIndex!=State.ActiveIndex)return false;
    State=MoveTemp(Next);Receipt=Now;
    VisualTasks.Reset();GroundMaps.Reset();HasGround.Reset();
    for(int32 I=0;I<State.Sites.Num();++I)
    {
        int32 Existing=INDEX_NONE;
        for(int32 V=0;V<VisualTasks.Num();++V)if(FVector::Dist2D(State.Sites[VisualTasks[V]].Map,State.Sites[I].Map)<.5){Existing=V;break;}
        if(Existing==INDEX_NONE){VisualTasks.Add(I);GroundMaps.Add(State.Sites[I].Map);HasGround.Add(false);}
        else if(I==State.ActiveIndex || (State.Sites[VisualTasks[Existing]].State==TEXT("complete") && State.Sites[I].State==TEXT("locked")))VisualTasks[Existing]=I;
    }
    LastGroundUpdate=-1;return true;
}
void ARedlineMissionSites::Receive(const FString& Topic,const TSharedPtr<FJsonObject>& J)
{
    if(Topic!=TEXT("/redline/campaign/state"))return;FString Raw;
    if(!J || !J->TryGetStringField(TEXT("data"),Raw) || Raw.Len()>240000)return;
    AcceptSnapshot(FRedlineJson::Parse(Raw),FPlatformTime::Seconds());
}
void ARedlineMissionSites::ConnectionChanged(bool Connected){Receipt=-1;HideAll();}
bool ARedlineMissionSites::FreshAt(double Now,bool Connected) const
{return Connected && Receipt>=0 && FMath::IsFinite(Now) && Now>=Receipt && Now-Receipt<=2;}
bool ARedlineMissionSites::Fresh() const{return FreshAt(FPlatformTime::Seconds(),Bridge && Bridge->IsConnected());}
FVector ARedlineMissionSites::SiteWorldPosition(FVector Map,double HeightCm){return URedlineCoords::RosToUeLocation(Map)+FVector(0,0,HeightCm);}
bool ARedlineMissionSites::GetActiveSiteMap(FVector& Out) const
{
    if(!Fresh() || !State.Sites.IsValidIndex(State.ActiveIndex))return false;
    for(int32 V=0;V<VisualTasks.Num();++V)if(VisualTasks[V]==State.ActiveIndex && HasGround[V]){Out=GroundMaps[V];return true;}
    return false;
}
FVector ARedlineMissionSites::ActiveSiteMap() const{FVector Out=FVector::ZeroVector;GetActiveSiteMap(Out);return Out;}
double ARedlineMissionSites::DistanceMetres() const
{
    if(!Fresh() || !State.Sites.IsValidIndex(State.ActiveIndex))return -1;
    const auto* PC=GetWorld()->GetFirstPlayerController();if(!PC || !PC->GetPawn())return -1;
    return FVector::Dist2D(URedlineCoords::UeToRosLocation(PC->GetPawn()->GetActorLocation()),State.Sites[State.ActiveIndex].Map);
}
bool ARedlineMissionSites::IsInRange() const
{const double D=DistanceMetres();return D>=0 && State.Sites.IsValidIndex(State.ActiveIndex) && D<=State.Sites[State.ActiveIndex].RadiusMetres;}
FString ARedlineMissionSites::TaskState() const
{return !Fresh() ? TEXT("stale") : State.Sites.IsValidIndex(State.ActiveIndex) ? State.Sites[State.ActiveIndex].State : TEXT("complete");}
void ARedlineMissionSites::LoadProps()
{
    FString Raw;if(!FFileHelper::LoadFileToString(Raw,*(FPaths::ProjectContentDir()/TEXT("MissionProps/mission_props.json"))) || Raw.Len()>64000)return;
    auto J=FRedlineJson::Parse(Raw);if(!J)return;auto Assets=MissionSites::Object(J,TEXT("assets"));if(!Assets)Assets=J;
    for(const FName Id:{FName(TEXT("tool_apxs")),FName(TEXT("sample_tube")),FName(TEXT("sample_case")),FName(TEXT("science_station"))})
    {
        auto Entry=MissionSites::Object(Assets,*Id.ToString());FString Path;double MinZ;
        const TArray<TSharedPtr<FJsonValue>>* Dimensions;
        if(!MissionSites::String(Entry,TEXT("mesh_asset"),Path,256) || !Path.StartsWith(TEXT("/Game/"))
           || !MissionSites::Number(Entry,TEXT("min_z_cm"),MinZ,-1000,1000) || !Entry->TryGetArrayField(TEXT("dimensions_cm"),Dimensions) || Dimensions->Num()!=3)continue;
        bool Valid=true;for(auto Value:*Dimensions){double D;if(!Value->TryGetNumber(D) || !FMath::IsFinite(D) || D<=0 || D>1000)Valid=false;}
        if(Valid)if(auto* Mesh=LoadObject<UStaticMesh>(nullptr,*Path,nullptr,LOAD_NoWarn)){ToolMeshes.Add(Id,Mesh);ToolMinimumZ.Add(Id,MinZ);}
    }
}
void ARedlineMissionSites::HideAll(){for(const auto& Label:Labels)Label->SetHiddenInGame(true);for(const auto& Prop:Props)Prop->SetHiddenInGame(true);}
void ARedlineMissionSites::UpdateVisuals(double Now)
{
    HideAll();if(!Fresh())return;auto* PC=GetWorld()->GetFirstPlayerController();if(!PC || !PC->GetPawn() || !PC->PlayerCameraManager)return;
    const FVector HumanMap=URedlineCoords::UeToRosLocation(PC->GetPawn()->GetActorLocation());
    if(Now-LastGroundUpdate>.5)
    {
        LastGroundUpdate=Now;
        for(int32 V=0;V<VisualTasks.Num();++V)
        {
            const auto& Site=State.Sites[VisualTasks[V]];FVector Probe=Site.Map,Hit;Probe.Z=HumanMap.Z;
            // Near interior sites trace below the ceiling; far field sites use
            // a broad vertical terrain query without changing their true XY.
            const bool NearRoom=(Site.Kind==TEXT("briefing") || Site.Kind==TEXT("decision") || Site.Kind==TEXT("assessment") || Site.Kind==TEXT("debrief") || Site.Kind==TEXT("cache")) && FVector::Dist2D(HumanMap,Probe)<15;
            if(NearRoom)Probe.Z-=1;
            HasGround[V]=URedlineCoords::TraceTerrainHeight(this,Probe,NearRoom ? 2. : 1500.,Hit);
            if(HasGround[V])GroundMaps[V]=Hit;
        }
    }
    for(int32 V=0;V<VisualTasks.Num() && Labels.IsValidIndex(V);++V)
    {
        if(!HasGround[V])continue;const auto& Site=State.Sites[VisualTasks[V]];const bool Active=VisualTasks[V]==State.ActiveIndex;
        const double Distance=FVector::Dist2D(HumanMap,Site.Map);if(!Active && Distance>220)continue;
        auto* Label=Labels[V].Get();const FVector World=SiteWorldPosition(GroundMaps[V],Active ? 110 : 55);
        FString Title=Site.Title,Prefix,Rest;if(Title.Split(TEXT(" / "),&Prefix,&Rest))Title=Rest;
        const bool Busy=State.OperationState==TEXT("pending") || State.OperationState==TEXT("running");
        const FString Detail=!Active ? Site.State==TEXT("complete") ? TEXT("Kaydedildi") : TEXT("Kilitli · Önceki sonucu bekle")
            : Busy ? FString::Printf(TEXT("İşlem sürüyor · %.0f%%"),State.Progress*100)
            : Site.bRemote ? Site.bEnabled ? TEXT("Tabletten uzaktan işlem") : TEXT("Uzaktan işlem beklemede")
            : Distance>Site.RadiusMetres ? FString::Printf(TEXT("%.0f m · Varıştan sonra E"),Distance)
            : Site.bEnabled ? TEXT("E · İşlemi başlat") : TEXT("İşlem şu an kapalı");
        Label->SetText(FText::FromString(Title+TEXT("\n")+Detail));Label->SetWorldSize(Active ? 14.f : 9.f);
        Label->SetTextRenderColor(Active ? FColor(226,211,190) : FColor(100,88,75));Label->SetWorldLocation(World);Label->SetWorldRotation((PC->PlayerCameraManager->GetCameraLocation()-World).Rotation());Label->SetHiddenInGame(false);
        const FName Id=MissionSites::Tool(Site.Kind);const auto* Found=ToolMeshes.Find(Id);
        if(Active && Site.Actor==TEXT("EV1") && Found && Props.IsValidIndex(V))
        {
            auto* Prop=Props[V].Get();Prop->SetStaticMesh(*Found);Prop->SetWorldLocation(SiteWorldPosition(GroundMaps[V],3-ToolMinimumZ.FindRef(Id)));Prop->SetWorldRotation(FRotator::ZeroRotator);Prop->SetHiddenInGame(false);
        }
    }
}
void ARedlineMissionSites::Tick(float Delta){Super::Tick(Delta);UpdateVisuals(FPlatformTime::Seconds());}
void ARedlineMissionSites::EndPlay(const EEndPlayReason::Type Reason)
{HideAll();if(Bridge){Bridge->OnTopic.Remove(TopicHandle);Bridge->OnConnectionChanged.RemoveDynamic(this,&ARedlineMissionSites::ConnectionChanged);}Super::EndPlay(Reason);}
