#include "RedlineRoverScienceVisuals.h"
#include "RedlineBridgeSubsystem.h"
#include "RedlineCampaignConsole.h"
#include "RedlineRoverActor.h"
#include "RedlineCoords.h"
#include "RedlineTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Math/RotationMatrix.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace RoverScienceVisuals
{
FString S(const TSharedPtr<FJsonObject>& J,const TCHAR* K){FString V;return J && J->TryGetStringField(K,V) ? V : FString();}
TSharedPtr<FJsonObject> O(const TSharedPtr<FJsonObject>& J,const TCHAR* K){const TSharedPtr<FJsonObject>* V;return J && J->TryGetObjectField(K,V) ? *V : nullptr;}
bool N(const TSharedPtr<FJsonObject>& J,const TCHAR* K,double& V,double Max=1000){return J && J->TryGetNumberField(K,V) && FMath::IsFinite(V) && V>=0 && V<=Max;}
UStaticMesh* Load(const TCHAR* Path){return LoadObject<UStaticMesh>(nullptr,Path,nullptr,LOAD_NoWarn);}
}

ARedlineRoverScienceVisuals::ARedlineRoverScienceVisuals()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickGroup=TG_PostUpdateWork;RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("ReadOnlyScienceRoot"));SetActorEnableCollision(false);
    Tool=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SourceTool"));Bit=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SeparateBit"));Arm=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ScenarioArmBridge"));Flash=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ScenarioLaserFlash"));
    for(auto* Part:{Tool.Get(),Bit.Get(),Arm.Get(),Flash.Get()}){Part->SetupAttachment(RootComponent);Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetGenerateOverlapEvents(false);Part->SetSimulatePhysics(false);Part->SetHiddenInGame(true);}
    BitPivot=CreateDefaultSubobject<USceneComponent>(TEXT("ActualSourceBitPivot"));BitPivot->SetupAttachment(RootComponent);Bit->SetupAttachment(BitPivot);
    Label=CreateDefaultSubobject<UTextRenderComponent>(TEXT("SimulationDisclosure"));Label->SetupAttachment(RootComponent);Label->SetHorizontalAlignment(EHTA_Center);Label->SetWorldSize(10);Label->SetTextRenderColor(FColor(215,196,171));Label->SetHiddenInGame(true);Label->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void ARedlineRoverScienceVisuals::BeginPlay()
{
    Super::BeginPlay();using namespace RoverScienceVisuals;
    Tools.Add(TEXT("drill"),Load(TEXT("/Game/MissionProps/tool_drill/SM_tool_drill.SM_tool_drill")));
    Tools.Add(TEXT("libs"),Load(TEXT("/Game/MissionProps/tool_libs/SM_tool_libs.SM_tool_libs")));
    Tools.Add(TEXT("dan"),Load(TEXT("/Game/MissionProps/tool_neutron/SM_tool_neutron.SM_tool_neutron")));
    Tools.Add(TEXT("xrf"),Load(TEXT("/Game/MissionProps/tool_apxs/SM_tool_apxs.SM_tool_apxs")));
    LoadDrillParts();
    Arm->SetStaticMesh(Load(TEXT("/Engine/BasicShapes/Cylinder.Cylinder")));Flash->SetStaticMesh(Load(TEXT("/Engine/BasicShapes/Sphere.Sphere")));Flash->SetRelativeScale3D(FVector(.025));Flash->SetCastShadow(false);
    if(auto* GI=GetGameInstance())Bridge=GI->GetSubsystem<URedlineBridgeSubsystem>();
    if(Bridge){TopicHandle=Bridge->OnTopic.AddUObject(this,&ARedlineRoverScienceVisuals::Receive);Bridge->OnConnectionChanged.AddDynamic(this,&ARedlineRoverScienceVisuals::ConnectionChanged);Bridge->Subscribe(TEXT("/redline/campaign/state"),TEXT("std_msgs/msg/String"),100,3);Bridge->Subscribe(TEXT("/redline/science/status"),TEXT("std_msgs/msg/String"),100,3);Bridge->Subscribe(TEXT("/redline/presentation/rover_1/odom"),TEXT("nav_msgs/msg/Odometry"),100,2);}
}
void ARedlineRoverScienceVisuals::LoadDrillParts()
{
    using namespace RoverScienceVisuals;FString Raw;if(!FFileHelper::LoadFileToString(Raw,*(FPaths::ProjectContentDir()/TEXT("MissionProps/tool_drill_parts.json"))) || Raw.Len()>64000)return;
    auto J=FRedlineJson::Parse(Raw);bool Passed=false;const TArray<TSharedPtr<FJsonValue>>* Parts=nullptr;
    if(!J || S(J,TEXT("schema"))!=TEXT("redline.drill_parts.v1") || !J->TryGetBoolField(TEXT("passed"),Passed) || !Passed || !J->TryGetArrayField(TEXT("parts"),Parts) || Parts->Num()<2 || Parts->Num()>64)return;
    struct PartRecord {TObjectPtr<UStaticMesh> Mesh;bool IsBit=false;FVector Pivot,Offset;};TArray<PartRecord> Checked;int32 Bits=0;
    auto Vector=[](const TSharedPtr<FJsonObject>& P,const TCHAR* K,FVector& Out){const TArray<TSharedPtr<FJsonValue>>* V;if(!P || !P->TryGetArrayField(K,V) || V->Num()!=3)return false;double X,Y,Z;if(!(*V)[0]->TryGetNumber(X) || !(*V)[1]->TryGetNumber(Y) || !(*V)[2]->TryGetNumber(Z) || !FMath::IsFinite(X) || !FMath::IsFinite(Y) || !FMath::IsFinite(Z) || FMath::Max3(FMath::Abs(X),FMath::Abs(Y),FMath::Abs(Z))>1000)return false;Out=FVector(X,Y,Z);return true;};
    for(const auto& Value:*Parts)
    {
        auto P=Value->AsObject();PartRecord Item;const FString Path=S(P,TEXT("mesh_asset"));
        Item.IsBit=S(P,TEXT("name")).Contains(TEXT("_bit_LOD"));
        if(!P || !Path.StartsWith(TEXT("/Game/MissionProps/tool_drill_parts/")) || Path.Len()>256 || !Vector(P,TEXT("pivot_cm"),Item.Pivot) || !Vector(P,TEXT("pivot_child_offset_cm"),Item.Offset) || !(Item.Pivot+Item.Offset).IsNearlyZero(.001))return;
        Item.Mesh=LoadObject<UStaticMesh>(nullptr,*Path,nullptr,LOAD_NoWarn);if(!Item.Mesh)return;Bits+=Item.IsBit ? 1 : 0;Checked.Add(Item);
    }
    if(Bits!=1)return;
    for(const auto& Item:Checked)
    {
        if(Item.IsBit){Bit->SetStaticMesh(Item.Mesh);BitOrigin=Item.Pivot;BitChildOffset=Item.Offset;continue;}
        auto* Part=NewObject<UStaticMeshComponent>(this);AddInstanceComponent(Part);Part->SetupAttachment(RootComponent);Part->SetStaticMesh(Item.Mesh);Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetGenerateOverlapEvents(false);Part->SetSimulatePhysics(false);Part->SetHiddenInGame(true);Part->RegisterComponent();DrillParts.Add(Part);
    }
    bSeparateBit=true;
}
bool ARedlineRoverScienceVisuals::ParseDrillFeedback(const TSharedPtr<FJsonObject>& J,FRedlineDrillVisualFeedback& Out)
{
    using namespace RoverScienceVisuals;FRedlineDrillVisualFeedback Next;
    if(S(J,TEXT("schema"))!=TEXT("redline.science.status.v1") || S(J,TEXT("instrument"))!=TEXT("DRILL") || S(J,TEXT("actor_id"))!=TEXT("rover_1") || S(J,TEXT("status"))!=TEXT("SIMULATED"))return false;
    Next.Request=S(J,TEXT("request_id"));Next.Phase=S(J,TEXT("phase"));
    if(Next.Request.IsEmpty() || Next.Request.Len()>96 || Next.Phase.IsEmpty() || Next.Phase.Len()>96 || !N(J,TEXT("progress"),Next.Progress,1))return false;
    Next.bHasDepth=J->HasField(TEXT("depth_mm"));Next.bHasRequested=J->HasField(TEXT("requested_depth_mm"));
    if((Next.bHasDepth && !N(J,TEXT("depth_mm"),Next.DepthMm)) || (Next.bHasRequested && !N(J,TEXT("requested_depth_mm"),Next.RequestedMm)) || (Next.bHasDepth && Next.bHasRequested && Next.DepthMm>Next.RequestedMm))return false;
    Out=MoveTemp(Next);return true;
}
bool ARedlineRoverScienceVisuals::DrillRotates(const FString& P)
{return P==TEXT("ACQUIRING") || P==TEXT("PERCUSSIVE_RECOVERY");}
double ARedlineRoverScienceVisuals::ReportedDepthCm(double Mm,bool Has)
{return Has && FMath::IsFinite(Mm) && Mm>=0 && Mm<=1000 ? Mm*.1 : 0.;}
void ARedlineRoverScienceVisuals::Receive(const FString& Topic,const TSharedPtr<FJsonObject>& J)
{
    using namespace RoverScienceVisuals;const double Now=FPlatformTime::Seconds();
    if(Topic==TEXT("/redline/presentation/rover_1/odom"))
    {FRedlineOdometry O;FString Error;if(FRedlineOdometry::Parse(J,O,Error) && O.FrameId==TEXT("map") && O.ChildFrameId==TEXT("rover_1/base_link") && O.PhysicsStampSec!=PoseStamp){PoseStamp=O.PhysicsStampSec;PoseReceipt=Now;}return;}
    FString Raw;if(!J || !J->TryGetStringField(TEXT("data"),Raw) || Raw.Len()>(Topic==TEXT("/redline/campaign/state") ? 240000 : 16000))return;auto P=FRedlineJson::Parse(Raw);
    if(Topic==TEXT("/redline/science/status"))
    {FRedlineDrillVisualFeedback F;if(ParseDrillFeedback(P,F) && F.Request==Request && Kind==TEXT("drill")){Phase=F.Phase;Progress=F.Progress;FeedbackReceipt=Now;bHasDepth=F.bHasDepth;ActualDepthMm=F.DepthMm;bHasRequested=F.bHasRequested;ActualRequestedMm=F.RequestedMm;}return;}
    if(Topic!=TEXT("/redline/campaign/state") || !ARedlineCampaignConsole::ValidateSnapshot(P))return;
    double R;if(!N(P,TEXT("revision"),R,MAX_uint32))return;const FString NewRun=S(P,TEXT("run_id"));if(NewRun==Run && R<Revision)return;
    auto Task=O(P,TEXT("task"));const FString NewRequest=S(P,TEXT("operation_id"));
    if(NewRequest!=Request || NewRun!=Run){bHasDepth=bHasRequested=bHasAchieved=false;FeedbackReceipt=-1;Angle=0;}
    Run=NewRun;Request=NewRequest;Revision=int64(R);Kind=S(Task,TEXT("kind"));TaskTarget=S(Task,TEXT("target_id"));OperationState=S(P,TEXT("state"));
    bBusy=(OperationState==TEXT("pending") || OperationState==TEXT("running")) && S(Task,TEXT("actor"))==TEXT("rover_1") && Tools.Contains(FName(*Kind));
    const TArray<TSharedPtr<FJsonValue>>* XY;if(Task->TryGetArrayField(TEXT("xy"),XY) && XY->Num()==2)TargetMap=FVector((*XY)[0]->AsNumber(),(*XY)[1]->AsNumber(),0);else bBusy=false;
    if(Now-FeedbackReceipt>2)Phase=S(P,TEXT("operation_phase"));N(P,TEXT("progress"),Progress,1);Receipt=Now;
    const TArray<TSharedPtr<FJsonValue>>* Products;
    if(P->TryGetArrayField(TEXT("products"),Products))for(const auto& Value:*Products)
    {
        auto Product=Value->AsObject();auto Summary=O(Product,TEXT("summary"));auto Drill=O(Summary,TEXT("drill"));
        if(S(Product,TEXT("instrument"))==TEXT("DRILL") && S(Product,TEXT("target_id"))==TaskTarget && S(Summary,TEXT("request_id"))==Request)
        {double Requested,Achieved;if(N(Drill,TEXT("requested_depth_mm"),Requested) && N(Drill,TEXT("achieved_depth_mm"),Achieved) && Achieved<=Requested){ActualRequestedMm=Requested;ActualAchievedMm=Achieved;bHasRequested=bHasAchieved=true;}}
    }
    if(!bBusy)HideVisuals();
}
void ARedlineRoverScienceVisuals::HideVisuals()
{for(auto* Part:{Tool.Get(),Bit.Get(),Arm.Get(),Flash.Get()})Part->SetHiddenInGame(true);for(const auto& Part:DrillParts)Part->SetHiddenInGame(true);Label->SetHiddenInGame(true);}
void ARedlineRoverScienceVisuals::ConnectionChanged(bool Connected){Receipt=PoseReceipt=FeedbackReceipt=-1;HideVisuals();}
void ARedlineRoverScienceVisuals::Tick(float Dt)
{
    Super::Tick(Dt);HideVisuals();const double Now=FPlatformTime::Seconds();
    if(!Bridge || !Bridge->IsConnected() || !bBusy || Request.IsEmpty() || Now-Receipt>2 || Now-PoseReceipt>2 || Phase.StartsWith(TEXT("ROVER_NAVIGATING")))return;
    if(!Rover.IsValid())for(TActorIterator<ARedlineRoverActor> It(GetWorld());It;++It)if(It->BaseFrame==TEXT("rover_1/base_link")){Rover=*It;break;}
    auto* R=Rover.Get();if(!R || R->AppliedPoseCount<=0)return;
    const FVector RoverMap=R->LastMapPositionMetres;if(RoverMap.ContainsNaN() || FVector::Dist2D(RoverMap,TargetMap)>4.5)return;
    FVector Probe=TargetMap;Probe.Z=RoverMap.Z;FVector Surface;if(!URedlineCoords::TraceTerrainHeight(this,Probe,3,Surface))return;
    const FVector Ground=URedlineCoords::RosToUeLocation(Surface);const FQuat Rotation=URedlineCoords::RosToUeRotation(R->LastMapOrientation);
    const FVector Mount=R->GetActorLocation()+Rotation.RotateVector(FVector(65,0,55));
    const auto* Source=Tools.Find(FName(*Kind));if(!Source || !Source->Get())return;
    Tool->SetStaticMesh(Source->Get());
    FVector ToolWorld=Mount;FString Caption=TEXT("SIMULATED / SCENARIO · ROS ")+Phase;
    if(Kind==TEXT("drill"))
    {
        const bool LiveDepth=bHasDepth && Now-FeedbackReceipt<=2;const double Depth=ReportedDepthCm(bHasAchieved ? ActualAchievedMm : ActualDepthMm,bHasAchieved || LiveDepth);
        const double Lift=Phase==TEXT("SELECTED") || Phase==TEXT("REACH_OK") ? 30 : Phase==TEXT("PRE_POSITIONED") ? 15 : Phase==TEXT("RETRACT") ? 12 : 0;
        ToolWorld=Ground+FVector(0,0,Lift-Depth);Tool->SetWorldRotation(FRotator::ZeroRotator);
        if(DrillRotates(Phase) && FMath::IsFinite(Dt) && Dt>0 && Dt<=.1)Angle=FMath::Fmod(Angle+Dt*720.,360.);
        if(bSeparateBit)
        {
            for(const auto& Part:DrillParts){Part->SetWorldLocationAndRotation(ToolWorld,FRotator::ZeroRotator);Part->SetWorldScale3D(FVector::OneVector);Part->SetHiddenInGame(false);}
            BitPivot->SetWorldLocationAndRotation(ToolWorld+BitOrigin,FRotator(0,Angle,0));Bit->SetRelativeLocation(BitChildOffset);Bit->SetRelativeRotation(FRotator::ZeroRotator);Bit->SetRelativeScale3D(FVector::OneVector);Bit->SetHiddenInGame(false);
        }
        Caption+=LiveDepth || bHasAchieved ? FString::Printf(TEXT(" · %.1f mm"),bHasAchieved ? ActualAchievedMm : ActualDepthMm) : TEXT(" · derinlik verisi bekleniyor");
        if(!bSeparateBit)Caption+=TEXT(" · ayrı uç yok; dönme gösterilmedi");
    }
    else if(Kind==TEXT("libs"))
    {
        ToolWorld=Mount+FVector(0,0,55);Tool->SetWorldRotation((Ground-ToolWorld).Rotation());
        const bool Firing=Phase==TEXT("RASTER") || Phase==TEXT("INTEGRATING");
        if(Firing && FMath::Fmod(Now,.25)<.045){Flash->SetWorldLocation(Ground+FVector(0,0,2));Flash->SetHiddenInGame(false);}
        Caption+=TEXT(" · lazer parlaması kozmetik");
    }
    else if(Kind==TEXT("dan")){ToolWorld=R->GetActorLocation()+Rotation.RotateVector(FVector(-60,0,-15));Tool->SetWorldRotation(Rotation);Caption+=TEXT(" · durağan sayım modeli");}
    else {ToolWorld=Ground+FVector(0,0,10);Tool->SetWorldRotation((Ground-Mount).Rotation());}
    Tool->SetWorldLocation(ToolWorld);Tool->SetWorldScale3D(FVector::OneVector);Tool->SetHiddenInGame(Kind==TEXT("drill") && bSeparateBit);
    const FVector Mid=(Mount+ToolWorld)*.5,Delta=ToolWorld-Mount;
    Arm->SetWorldLocationAndRotation(Mid,FRotationMatrix::MakeFromZ(Delta).Rotator());Arm->SetWorldScale3D(FVector(.035,.035,Delta.Size()/100.));Arm->SetHiddenInGame(false);
    Label->SetText(FText::FromString(Caption));Label->SetWorldLocation(ToolWorld+FVector(0,0,90));if(auto* PC=GetWorld()->GetFirstPlayerController())if(PC->PlayerCameraManager)Label->SetWorldRotation((PC->PlayerCameraManager->GetCameraLocation()-Label->GetComponentLocation()).Rotation());Label->SetHiddenInGame(false);
}
void ARedlineRoverScienceVisuals::EndPlay(const EEndPlayReason::Type Reason)
{HideVisuals();if(Bridge){Bridge->OnTopic.Remove(TopicHandle);Bridge->OnConnectionChanged.RemoveDynamic(this,&ARedlineRoverScienceVisuals::ConnectionChanged);}Super::EndPlay(Reason);}
