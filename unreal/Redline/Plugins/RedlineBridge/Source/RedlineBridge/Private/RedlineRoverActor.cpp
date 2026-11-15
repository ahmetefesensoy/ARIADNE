#include "RedlineRoverActor.h"
#include "RedlineBridgeSubsystem.h"
#include "RedlineCoords.h"
#include "RedlineTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "UObject/ConstructorHelpers.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "RedlineStaleMonitor.h"
#include "GameFramework/PlayerController.h"
#include "Engine/GameViewportClient.h"
#include "Engine/Engine.h"
#include "UnrealClient.h"
#include "InputCoreTypes.h"
#include "Components/InputComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Components/DecalComponent.h"
#include "EngineUtils.h"

ARedlineRoverActor::ARedlineRoverActor()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.bStartWithTickEnabled=false;
    PresentationMesh=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PresentationOnlyCube")); RootComponent=PresentationMesh;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded()) PresentationMesh->SetStaticMesh(Cube.Object);
    PresentationMesh->SetSimulatePhysics(false); PresentationMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision); PresentationMesh->SetGenerateOverlapEvents(false);
    PresentationMesh->SetMobility(EComponentMobility::Movable);
}
void ARedlineRoverActor::BeginPlay()
{
    Super::BeginPlay();
    if (UGameInstance* GI=GetGameInstance()) Bridge=GI->GetSubsystem<URedlineBridgeSubsystem>();
    if (!Bridge) return;
    // Explicit presentation-only source override. Does not change localization,
    // Nav2 inputs or the T4 default estimated-pose contract.
    FParse::Value(FCommandLine::Get(),TEXT("RedlinePresentationPoseTopic="),OdometryTopic);
    bManualKeyboard=FParse::Param(FCommandLine::Get(),TEXT("RedlineManualDrive")) && !Bridge->IsOfflineReplay();
    bTimeControls=(bManualKeyboard || FParse::Param(FCommandLine::Get(),TEXT("RedlineTimeControl"))) && !Bridge->IsOfflineReplay();
    if (bManualKeyboard) Bridge->Advertise(TEXT("/redline/manual/rover_1/cmd_vel"),TEXT("geometry_msgs/msg/TwistStamped"));
    if (bTimeControls)
    {
        Bridge->Advertise(TEXT("/redline/simulation/time_scale"),TEXT("std_msgs/msg/Float64"));
        Bridge->Subscribe(TEXT("/redline/simulation/time_status"),TEXT("std_msgs/msg/String"),0,5);
        if (APlayerController* Player=GetWorld()->GetFirstPlayerController())
        {
            EnableInput(Player);
            InputComponent->BindKey(EKeys::One,IE_Pressed,this,&ARedlineRoverActor::TimeNormal);
            InputComponent->BindKey(EKeys::Two,IE_Pressed,this,&ARedlineRoverActor::TimeDouble);
            InputComponent->BindKey(EKeys::Three,IE_Pressed,this,&ARedlineRoverActor::TimeQuadruple);
        }
        SetActorTickEnabled(true);
    }
    TopicHandle=Bridge->OnTopic.AddUObject(this,&ARedlineRoverActor::OnMessage);
    Bridge->OnConnectionChanged.AddDynamic(this,&ARedlineRoverActor::ConnectionChanged);
    Bridge->Subscribe(OdometryTopic,TEXT("nav_msgs/msg/Odometry"),OdometryTopic==TEXT("/redline/presentation/rover_1/odom") ? 16 : 50);
    if (OdometryTopic==TEXT("/redline/presentation/rover_1/odom"))
    {
        Bridge->Subscribe(TEXT("/redline/presentation/scene"),TEXT("std_msgs/msg/String"),16,1);
        TArray<AActor*> AttachedVisuals;GetAttachedActors(AttachedVisuals);
        for(AActor* Child:AttachedVisuals) for(const FName& Tag:Child->Tags)
            if(Tag.ToString().StartsWith(TEXT("wheel_"))) WheelVisuals.Add(Tag.ToString(),Child);
        for(TActorIterator<AActor> It(GetWorld());It;++It) for(const FName& Tag:It->Tags)
            if(Tag.ToString().StartsWith(TEXT("SCENARIO_moving_")))MovingVisuals.Add(Tag.ToString(),*It);
    }
    Bridge->Subscribe(TEXT("/tf"),TEXT("tf2_msgs/msg/TFMessage"),0);
    Bridge->Subscribe(TEXT("/redline/bridge/tf_static_snapshot"),TEXT("tf2_msgs/msg/TFMessage"),0,86400);
    Bridge->Subscribe(TEXT("/redline/bridge/tf_static_snapshot_status"),TEXT("std_msgs/msg/String"),0,86400);
    FParse::Value(FCommandLine::Get(),TEXT("RedlinePoseLog="),PoseLog);
    if (!PoseLog.IsEmpty()) FFileHelper::SaveStringToFile(TEXT("receipt_wall_sec,physics_stamp_sec,frame,map_x_m,map_y_m,map_z_m,map_qx,map_qy,map_qz,map_qw,ue_x_cm,ue_y_cm,ue_z_cm,ue_qx,ue_qy,ue_qz,ue_qw\n"),*PoseLog);
}
void ARedlineRoverActor::EndPlay(const EEndPlayReason::Type Reason)
{
    if (bManualKeyboard) PublishManual(FVector2D::ZeroVector);
    if (bTimeControls) PublishTimeScale(1);
    if (Bridge) { Bridge->OnTopic.Remove(TopicHandle); Bridge->OnConnectionChanged.RemoveDynamic(this,&ARedlineRoverActor::ConnectionChanged); }
    Super::EndPlay(Reason);
}
FVector2D ARedlineRoverActor::ManualIntent(bool bFocused,bool bForward,bool bBackward,bool bLeft,bool bRight,bool bBrake)
{
    if (!bFocused || bBrake) return FVector2D::ZeroVector;
    return FVector2D((int32(bForward)-int32(bBackward))*0.3,(int32(bLeft)-int32(bRight))*0.3);
}
void ARedlineRoverActor::PublishManual(const FVector2D& Intent)
{
    if (!Bridge || !Bridge->IsConnected() || Bridge->IsOfflineReplay() || !Bridge->bHasPhysicsClock) return;
    const double Stamp=Bridge->PhysicsClockSec;
    if (!FMath::IsFinite(Stamp) || Stamp<0) return;
    TSharedRef<FJsonObject> Message=MakeShared<FJsonObject>();
    TSharedRef<FJsonObject> Header=MakeShared<FJsonObject>();
    TSharedRef<FJsonObject> Time=MakeShared<FJsonObject>();
    const double Sec=FMath::FloorToDouble(Stamp);
    Time->SetNumberField(TEXT("sec"),Sec); Time->SetNumberField(TEXT("nanosec"),FMath::Clamp(FMath::FloorToDouble((Stamp-Sec)*1e9),0.0,999999999.0));
    Header->SetObjectField(TEXT("stamp"),Time); Header->SetStringField(TEXT("frame_id"),BaseFrame);
    Message->SetObjectField(TEXT("header"),Header);
    TSharedRef<FJsonObject> Twist=MakeShared<FJsonObject>();
    TSharedRef<FJsonObject> Linear=MakeShared<FJsonObject>();
    TSharedRef<FJsonObject> Angular=MakeShared<FJsonObject>();
    Linear->SetNumberField(TEXT("x"),Intent.X);Linear->SetNumberField(TEXT("y"),0);Linear->SetNumberField(TEXT("z"),0);
    Angular->SetNumberField(TEXT("x"),0);Angular->SetNumberField(TEXT("y"),0);Angular->SetNumberField(TEXT("z"),Intent.Y);
    Twist->SetObjectField(TEXT("linear"),Linear);Twist->SetObjectField(TEXT("angular"),Angular);
    Message->SetObjectField(TEXT("twist"),Twist);
    Bridge->Publish(TEXT("/redline/manual/rover_1/cmd_vel"),Message);
}
void ARedlineRoverActor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bTimeControls || !Bridge) return;
    const double Now=FPlatformTime::Seconds();
    if (Now-LastManualSend<0.05) return;
    LastManualSend=Now;
    APlayerController* Player=GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
    UGameViewportClient* Client=GetWorld() ? GetWorld()->GetGameViewport() : nullptr;
    const bool bFresh=Bridge->StaleMonitor && Bridge->StaleMonitor->IsFresh(TEXT("/clock"),Now);
    const bool bFocused=Player && Client && Client->Viewport && Client->Viewport->HasFocus() && bFresh;
    auto Down=[Player](const FKey& Key) { return Player && Player->IsInputKeyDown(Key); };
    if (bFocused)
    {
        const double Scale=Down(EKeys::One) ? 1 : Down(EKeys::Two) ? 2 : Down(EKeys::Three) ? 4 : RequestedTimeScale;
        if (Scale!=RequestedTimeScale) PublishTimeScale(Scale);
    }
    const FVector2D Intent=ManualIntent(bFocused,Down(EKeys::W)||Down(EKeys::Up),Down(EKeys::S)||Down(EKeys::Down),
        Down(EKeys::A)||Down(EKeys::Left),Down(EKeys::D)||Down(EKeys::Right),Down(EKeys::SpaceBar));
    if (bManualKeyboard) PublishManual(Intent);
    if (GEngine) GEngine->AddOnScreenDebugMessage(71401,0.15,FColor::White,
        FString::Printf(TEXT("%s | TIME 1:1x 2:2x 3:4x | requested %.0fx, actual %.2fx"),
            bManualKeyboard ? TEXT("MANUAL | WASD/arrows | SPACE stop") : TEXT("AUTO | ROS navigation + live LiDAR obstacle avoidance"),RequestedTimeScale,ActualTimeScale));
}
void ARedlineRoverActor::PublishTimeScale(double Factor)
{
    if (!Bridge || !Bridge->IsConnected() || Bridge->IsOfflineReplay() || (Factor!=1 && Factor!=2 && Factor!=4)) return;
    TSharedRef<FJsonObject> Message=MakeShared<FJsonObject>(); Message->SetNumberField(TEXT("data"),Factor);
    if (Bridge->Publish(TEXT("/redline/simulation/time_scale"),Message)) RequestedTimeScale=Factor;
}
void ARedlineRoverActor::ConnectionChanged(bool bConnected)
{ if (!bConnected) { bHasMapFromOdom=false; bStaticSnapshotInvalid=false; } }
FTransform ARedlineRoverActor::ComposeRosPose(const FTransform& T,const FVector& P,const FQuat& Q)
{ return FTransform((T.GetRotation()*Q).GetNormalized(),T.GetTranslation()+T.GetRotation().RotateVector(P)); }
void ARedlineRoverActor::OnMessage(const FString& Topic,const TSharedPtr<FJsonObject>& Json)
{
    check(IsInGameThread());
    if (Topic==TEXT("/redline/presentation/scene")) { ApplyWheelScene(Json);return; }
    if (Topic==TEXT("/redline/simulation/time_status"))
    {
        FString Data;
        if (Json->TryGetStringField(TEXT("data"),Data))
        {
            const TSharedPtr<FJsonObject> Status=FRedlineJson::Parse(Data);
            double Requested=0,Actual=0;
            if (Status && Status->TryGetNumberField(TEXT("requested_factor"),Requested) && (Requested==1 || Requested==2 || Requested==4)) RequestedTimeScale=Requested;
            if (Status && Status->TryGetNumberField(TEXT("actual_factor"),Actual) && FMath::IsFinite(Actual) && Actual>=0) ActualTimeScale=Actual;
        }
        return;
    }
    if (Topic==TEXT("/redline/bridge/tf_static_snapshot_status"))
    {
        FString Data; bool bValid=false;
        const TSharedPtr<FJsonObject> Status=Json->TryGetStringField(TEXT("data"),Data) ? FRedlineJson::Parse(Data) : nullptr;
        if (!Status || !Status->TryGetBoolField(TEXT("valid"),bValid) || !bValid)
        {
            bStaticSnapshotInvalid=true; bHasMapFromOdom=false;
            UE_LOG(LogRedlineBridge,Warning,TEXT("Static TF snapshot invalid; presentation frozen until reconnect to a valid session."));
        }
        return;
    }
    if (Topic==TEXT("/tf") || Topic==TEXT("/tf_static") || Topic==TEXT("/redline/bridge/tf_static_snapshot"))
    {
        if (bStaticSnapshotInvalid) return;
        const TArray<TSharedPtr<FJsonValue>>* Transforms;
        if (!Json->TryGetArrayField(TEXT("transforms"),Transforms)) return;
        for (const auto& Value:*Transforms)
        {
            const TSharedPtr<FJsonObject> T=Value->AsObject(); const TSharedPtr<FJsonObject>* Header; const TSharedPtr<FJsonObject>* Transform; const TSharedPtr<FJsonObject>* Stamp;
            FString Parent,Child; FTransform Parsed; double Time;
            if (!T || !T->TryGetObjectField(TEXT("header"),Header) || !(*Header)->TryGetStringField(TEXT("frame_id"),Parent) || !T->TryGetStringField(TEXT("child_frame_id"),Child) || Parent!=TEXT("map") || Child!=OdomFrame || !T->TryGetObjectField(TEXT("transform"),Transform) || !FRedlineJson::Transform(*Transform,Parsed) || !(*Header)->TryGetObjectField(TEXT("stamp"),Stamp) || !FRedlineJson::Stamp(*Stamp,Time)) continue;
            MapFromOdom=Parsed; TransformStamp=Time; bStaticTransform=Topic!=TEXT("/tf"); bHasMapFromOdom=true;
        }
        return;
    }
    if (Topic!=OdometryTopic) return;
    if (bStaticSnapshotInvalid) { ++RejectedPoseCount; return; }
    FRedlineOdometry Odom; FString Error;
    if (!FRedlineOdometry::Parse(Json,Odom,Error) || Odom.ChildFrameId!=BaseFrame || (Odom.FrameId!=TEXT("map") && Odom.FrameId!=OdomFrame)) { ++RejectedPoseCount; return; }
    FTransform MapPose(Odom.Orientation,Odom.PositionMetres);
    if (Odom.FrameId!=TEXT("map"))
    {
        if (!bHasMapFromOdom || (!bStaticTransform && FMath::Abs(TransformStamp-Odom.PhysicsStampSec)>MaxDynamicTfSkewSec)) { ++RejectedPoseCount; return; }
        MapPose=ComposeRosPose(MapFromOdom,Odom.PositionMetres,Odom.Orientation);
    }
    LastMapPositionMetres=MapPose.GetTranslation(); LastMapOrientation=MapPose.GetRotation(); ++AppliedPoseCount;
    SetActorLocationAndRotation(URedlineCoords::RosToUeLocation(LastMapPositionMetres),URedlineCoords::RosToUeRotation(LastMapOrientation),false,nullptr,ETeleportType::None);
    const double Now=FPlatformTime::Seconds();
    if (Now-LastLogTime>=0.2)
    {
        LastLogTime=Now; const FVector U=GetActorLocation(); const FQuat Q=LastMapOrientation; const FQuat UQ=GetActorQuat();
        if (!PoseLog.IsEmpty()) FFileHelper::SaveStringToFile(FString::Printf(TEXT("%.9f,%.9f,%s,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f,%.9f\n"),Now,Odom.PhysicsStampSec,*Odom.FrameId,LastMapPositionMetres.X,LastMapPositionMetres.Y,LastMapPositionMetres.Z,Q.X,Q.Y,Q.Z,Q.W,U.X,U.Y,U.Z,UQ.X,UQ.Y,UQ.Z,UQ.W),*PoseLog,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_Append);
        UE_LOG(LogRedlineBridge,Log,TEXT("PresentationPose count=%d source=%s map_m=(%.3f,%.3f,%.3f) ue_cm=(%.3f,%.3f,%.3f) physics=%.6f"),AppliedPoseCount,*Odom.FrameId,LastMapPositionMetres.X,LastMapPositionMetres.Y,LastMapPositionMetres.Z,U.X,U.Y,U.Z,Odom.PhysicsStampSec);
    }
}
void ARedlineRoverActor::ApplyWheelScene(const TSharedPtr<FJsonObject>& Json)
{
    check(IsInGameThread());
    FString Data;if(!Json->TryGetStringField(TEXT("data"),Data))return;
    const TSharedPtr<FJsonObject> Scene=FRedlineJson::Parse(Data);double Stamp=0;
    const TArray<TSharedPtr<FJsonValue>>* Wheels;
    if(!Scene || !Scene->TryGetNumberField(TEXT("physics_stamp_s"),Stamp) || !FMath::IsFinite(Stamp) || Stamp<=LastWheelStamp)return;
    const TArray<TSharedPtr<FJsonValue>>* Moving;
    if(Scene->TryGetArrayField(TEXT("moving_obstacles"),Moving))for(const auto& Value:*Moving)
    {
        const auto M=Value->AsObject();FString Name;const TSharedPtr<FJsonObject>* P;const TSharedPtr<FJsonObject>* Q;FVector Position;FQuat Rotation;
        if(M && M->TryGetStringField(TEXT("name"),Name) && MovingVisuals.Contains(Name) && MovingVisuals[Name].IsValid() &&
           M->TryGetObjectField(TEXT("position"),P) && M->TryGetObjectField(TEXT("orientation"),Q) &&
           FRedlineJson::Vector(*P,Position) && FRedlineJson::Quaternion(*Q,Rotation))
            MovingVisuals[Name]->SetActorLocationAndRotation(URedlineCoords::RosToUeLocation(Position),URedlineCoords::RosToUeRotation(Rotation),false,nullptr,ETeleportType::None);
    }
    if(!Scene->TryGetArrayField(TEXT("wheels"),Wheels) || Wheels->Num()!=6)return;
    TArray<TPair<AActor*,FTransform>> Updates;
    for(const auto& Value:*Wheels)
    {
        const auto W=Value->AsObject();FString Name;
        if(!W || !W->TryGetStringField(TEXT("name"),Name) || !WheelVisuals.Contains(Name) || !WheelVisuals[Name].IsValid())return;
        const TSharedPtr<FJsonObject>* Position;const TSharedPtr<FJsonObject>* Rotation;FVector P;FQuat Q;
        if(!W->TryGetObjectField(TEXT("position"),Position) || !W->TryGetObjectField(TEXT("orientation"),Rotation) || !FRedlineJson::Vector(*Position,P) || !FRedlineJson::Quaternion(*Rotation,Q) || P.Size()>4)return;
        Updates.Emplace(WheelVisuals[Name].Get(),FTransform(URedlineCoords::RosToUeRotation(Q),URedlineCoords::RosToUeLocation(P)));
    }
    LastWheelStamp=Stamp;
    const FVector Up=GetActorQuat().RotateVector(FVector::UpVector);
    int32 Index=0;
    for(const auto& Update:Updates)
    {
        AActor* Wheel=Update.Key;
        Wheel->SetActorRelativeTransform(Update.Value,false,nullptr,ETeleportType::None);
        const FVector Centre=Wheel->GetActorLocation();
        if(SandWheelCollection)
        {
            auto* Collection=GetWorld()->GetParameterCollectionInstance(SandWheelCollection);
            Collection->SetVectorParameterValue(FName(*FString::Printf(TEXT("Wheel%d"),Index)),FLinearColor(Centre.X,Centre.Y,Centre.Z,1));
        }
        const FString Name=Wheel->Tags.Num() ? Wheel->Tags[0].ToString() : Wheel->GetName();
        const FVector Contact=Centre-Up*24.0;
        if(TrackDecalMaterial && (!LastTrackPositions.Contains(Name) || FVector::DistSquared(Contact,LastTrackPositions[Name])>400.0))
        {
            const FRotator Rotation=(-Up).Rotation();
            if(auto* Decal=UGameplayStatics::SpawnDecalAtLocation(GetWorld(),TrackDecalMaterial,FVector(8,20,16),Contact+Up,Rotation,90.0))TrackDecals.Add(Decal);
            if(TrackDecals.Num()>800){if(TrackDecals[0].IsValid())TrackDecals[0]->DestroyComponent();TrackDecals.RemoveAt(0);}
            LastTrackPositions.Add(Name,Contact);
        }
        ++Index;
    }
    ++AppliedWheelSceneCount;
    if(AppliedWheelSceneCount==1 || AppliedWheelSceneCount%300==0)
        UE_LOG(LogRedlineBridge,Log,TEXT("PhysicalWheelScene count=%d wheels=%d moving_visuals=%d live_track_budget=%d physics=%.6f"),AppliedWheelSceneCount,Updates.Num(),MovingVisuals.Num(),TrackDecals.Num(),Stamp);
}
