#include "RedlineAstronautCharacter.h"
#include "RedlineBridgeSubsystem.h"
#include "RedlineStaleMonitor.h"
#include "RedlineCoords.h"
#include "RedlineTypes.h"
#include "RedlineEVAData.h"
#include "RedlineCampaignConsole.h"
#include "RedlineLocomotionInstance.h"
#include "EngineUtils.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimSequence.h"
#include "Materials/MaterialInterface.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "UnrealClient.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "Engine/World.h"
DEFINE_LOG_CATEGORY_STATIC(LogRedlineEVA,Log,All);

ARedlineAstronautCharacter::ARedlineAstronautCharacter()
{
    PrimaryActorTick.bCanEverTick=true;
    GetCapsuleComponent()->InitCapsuleSize(32,94);
    GetMesh()->SetRelativeLocation(FVector(0,0,-94));GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);GetMesh()->SetReceivesDecals(false);
    bUseControllerRotationYaw=false;
    auto* M=GetCharacterMovement();M->MaxWalkSpeed=0;M->MaxAcceleration=250;M->BrakingDecelerationWalking=350;
    M->bOrientRotationToMovement=true;M->RotationRate=FRotator(0,180,0);M->MaxStepHeight=35;M->bUseFlatBaseForFloorChecks=true;
    CameraArm=CreateDefaultSubobject<USpringArmComponent>(TEXT("EV1CameraArm"));CameraArm->SetupAttachment(GetCapsuleComponent());
    CameraArm->TargetArmLength=220;CameraArm->SocketOffset=FVector(0,32,40);CameraArm->bUsePawnControlRotation=true;
    CameraArm->bDoCollisionTest=true;CameraArm->ProbeSize=12;
    FollowCamera=CreateDefaultSubobject<UCameraComponent>(TEXT("EV1Camera"));FollowCamera->SetupAttachment(CameraArm);FollowCamera->SetFieldOfView(75);
    FirstPersonCamera=CreateDefaultSubobject<UCameraComponent>(TEXT("EV1FirstPerson"));FirstPersonCamera->SetupAttachment(GetCapsuleComponent());
    FirstPersonCamera->SetRelativeLocation(FVector(0,0,74));FirstPersonCamera->bUsePawnControlRotation=true;FirstPersonCamera->SetFieldOfView(88);
    FirstPersonCamera->SetActive(true);FollowCamera->SetActive(false);GetMesh()->SetOwnerNoSee(true);GetMesh()->bCastHiddenShadow=true;
}
void ARedlineAstronautCharacter::SetFirstPersonView(bool Enabled)
{
    bFirstPersonView=Enabled;FirstPersonCamera->SetActive(Enabled);FollowCamera->SetActive(!Enabled);GetMesh()->SetOwnerNoSee(Enabled);
}
bool ARedlineAstronautCharacter::LoadMovementProfile()
{
    FString Path,Text;FParse::Value(FCommandLine::Get(),TEXT("RedlineEVARuntime="),Path);
    if(Path.IsEmpty() || !FFileHelper::LoadFileToString(Text,*Path) || Text.Len()>262144)return false;
    auto J=FRedlineJson::Parse(Text);FString Schema;double Factor,Angle;
    const TArray<TSharedPtr<FJsonValue>>* Samples=nullptr;
    if(!J || !J->TryGetStringField(TEXT("schema"),Schema) || Schema!=TEXT("redline.eva.runtime.v1") ||
       !J->TryGetNumberField(TEXT("unobserved_speed_factor"),Factor) || !FMath::IsFinite(Factor) || Factor<=0 || Factor>1 ||
       !J->TryGetNumberField(TEXT("max_slope_deg"),Angle) || !FMath::IsFinite(Angle) || Angle<=0 || Angle>45 ||
       !J->TryGetArrayField(TEXT("walking_speed_samples"),Samples) || Samples->Num()<2 || Samples->Num()>512)return false;
    double Previous=-DBL_MAX;
    for(const auto& Item:*Samples)
    {
        const TArray<TSharedPtr<FJsonValue>>* Pair=nullptr;double G,V;
        if(!Item || !Item->TryGetArray(Pair) || Pair->Num()!=2 || !(*Pair)[0]->TryGetNumber(G) || !(*Pair)[1]->TryGetNumber(V) ||
           !FMath::IsFinite(G) || !FMath::IsFinite(V) || G<=Previous || V<=0 || V>5)return false;
        SpeedTable.Add(FVector2D(G,V));Previous=G;
    }
    UnknownSpeedFactor=CellSpeedFactor=Factor;GetCharacterMovement()->SetWalkableFloorAngle(Angle);
    const TSharedPtr<FJsonObject>* Gameplay=nullptr;double Multiplier,Cap;
    if(J->TryGetObjectField(TEXT("gameplay_locomotion"),Gameplay) && (*Gameplay)->TryGetNumberField(TEXT("sprint_multiplier"),Multiplier) &&
       (*Gameplay)->TryGetNumberField(TEXT("sprint_cap_m_s"),Cap) && FMath::IsFinite(Multiplier) && Multiplier>=1 && Multiplier<=6 && FMath::IsFinite(Cap) && Cap>0 && Cap<=5)
    {SprintMultiplier=Multiplier;SprintCapMps=Cap;}
    const TSharedPtr<FJsonObject>* Intro=nullptr;
    if(J->TryGetObjectField(TEXT("intro"),Intro))
    {
        const TArray<TSharedPtr<FJsonValue>>* Pair=nullptr;
        if((*Intro)->TryGetArrayField(TEXT("briefing_xy_m"),Pair) && Pair->Num()==2)BriefingMap=FVector((*Pair)[0]->AsNumber(),(*Pair)[1]->AsNumber(),0);
        if((*Intro)->TryGetArrayField(TEXT("station_xy_m"),Pair) && Pair->Num()==2)StationMap=FVector((*Pair)[0]->AsNumber(),(*Pair)[1]->AsNumber(),0);
    }
    return true;
}
double ARedlineAstronautCharacter::WalkingSpeed(double Grade) const
{
    if(SpeedTable.Num()<2)return 0;
    Grade=FMath::Clamp(Grade,SpeedTable[0].X,SpeedTable.Last().X);
    for(int32 I=1;I<SpeedTable.Num();++I)if(Grade<=SpeedTable[I].X)
        return FMath::Lerp(SpeedTable[I-1].Y,SpeedTable[I].Y,(Grade-SpeedTable[I-1].X)/(SpeedTable[I].X-SpeedTable[I-1].X))*CellSpeedFactor;
    return SpeedTable.Last().Y*CellSpeedFactor;
}
double ARedlineAstronautCharacter::RequestedSpeed(double WalkMps,bool Sprint,double Multiplier,double CapMps)
{
    if(!FMath::IsFinite(WalkMps) || WalkMps<=0)return 0;
    if(!Sprint || !FMath::IsFinite(Multiplier) || !FMath::IsFinite(CapMps) || Multiplier<1 || CapMps<=0)return WalkMps;
    return FMath::Min(WalkMps*Multiplier,CapMps);
}
void ARedlineAstronautCharacter::BeginPlay()
{
    Super::BeginPlay();bMovementProfileReady=LoadMovementProfile();
    bIntroMode=FParse::Param(FCommandLine::Get(),TEXT("RedlineEVAIntro"));
    SetFirstPersonView(!FParse::Param(FCommandLine::Get(),TEXT("RedlineThirdPerson")));
    if(!bMovementProfileReady)UE_LOG(LogRedlineEVA,Error,TEXT("EV1 movement disabled: missing/invalid core-generated movement profile"));
    FParse::Value(FCommandLine::Get(),TEXT("RedlineEVAProbeSeconds="),ProbeSeconds);ProbeSeconds=FMath::Clamp(ProbeSeconds,0.,120.);
    FParse::Value(FCommandLine::Get(),TEXT("RedlineEVAPoseLog="),PoseLog);
    if(!PoseLog.IsEmpty())FFileHelper::SaveStringToFile(TEXT("wall_utc_s,map_x_m,map_y_m,map_z_m,published\n"),*PoseLog);
    if(auto* GI=GetGameInstance())Bridge=GI->GetSubsystem<URedlineBridgeSubsystem>();
    if(Bridge){Bridge->Advertise(TEXT("/crew/EV1/pose"),TEXT("geometry_msgs/msg/PoseStamped"));TopicHandle=Bridge->OnTopic.AddUObject(this,&ARedlineAstronautCharacter::OnState);Bridge->Subscribe(TEXT("/crew/EV1/state"),TEXT("redline_msgs/msg/CrewState"),100,3);}
    if(Bridge)Bridge->Subscribe(TEXT("/redline/mission/state"),TEXT("redline_msgs/msg/MissionState"),100,3);
    if(auto* PC=Cast<APlayerController>(GetController()))
    {PC->SetControlRotation(FRotator(bFirstPersonView ? 0 : -15,GetActorRotation().Yaw,0));PC->SetInputMode(FInputModeGameOnly());PC->bShowMouseCursor=false;}
    if(auto* AstronautMesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/EVAFixtures/Astronaut/SK_Astronaut.SK_Astronaut")))GetMesh()->SetSkeletalMeshAsset(AstronautMesh);
    if(auto* SuitMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/EVAFixtures/M_EV1_Original.M_EV1_Original")))GetMesh()->SetMaterial(0,SuitMaterial);
    GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Idle=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/EVAFixtures/Astronaut/AN_Idle.AN_Idle"));
    Walk=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/EVAFixtures/Astronaut/AN_Walk.AN_Walk"));
    GetMesh()->SetAnimInstanceClass(URedlineLocomotionInstance::StaticClass());
    Locomotion=Cast<URedlineLocomotionInstance>(GetMesh()->GetAnimInstance());
    if(!Locomotion || !Locomotion->Configure(Idle,Walk))
    {
        Locomotion=nullptr;
        UE_LOG(LogRedlineEVA,Warning,TEXT("Locomotion blend unavailable; imported idle fallback only"));
        if(Idle)GetMesh()->PlayAnimation(Idle,true);
    }
    if(Bridge && Bridge->IsOfflineReplay())GetCharacterMovement()->DisableMovement();
}
void ARedlineAstronautCharacter::EndPlay(const EEndPlayReason::Type Reason)
{if(Bridge)Bridge->OnTopic.Remove(TopicHandle);Super::EndPlay(Reason);}
void ARedlineAstronautCharacter::PossessedBy(AController* NewController)
{
    Super::PossessedBy(NewController);
    if(auto* PC=Cast<APlayerController>(NewController))
    {PC->SetControlRotation(FRotator(bFirstPersonView ? 0 : -15,GetActorRotation().Yaw,0));PC->SetInputMode(FInputModeGameOnly());PC->bShowMouseCursor=false;}
}
TSharedRef<FJsonObject> ARedlineAstronautCharacter::PoseMessage(FVector Capsule,FQuat Q,double Half,double Time)
{
    auto J=MakeShared<FJsonObject>(),Header=MakeShared<FJsonObject>(),Stamp=MakeShared<FJsonObject>(),Pose=MakeShared<FJsonObject>(),P=MakeShared<FJsonObject>(),R=MakeShared<FJsonObject>();
    const FVector Map=URedlineCoords::UeToRosLocation(Capsule-FVector(0,0,Half));const FQuat Ros=URedlineCoords::UeToRosRotation(Q);
    const double Sec=FMath::FloorToDouble(Time);Stamp->SetNumberField(TEXT("sec"),Sec);Stamp->SetNumberField(TEXT("nanosec"),FMath::Clamp(FMath::FloorToDouble((Time-Sec)*1e9),0.,999999999.));
    Header->SetStringField(TEXT("frame_id"),TEXT("map"));Header->SetObjectField(TEXT("stamp"),Stamp);
    P->SetNumberField(TEXT("x"),Map.X);P->SetNumberField(TEXT("y"),Map.Y);P->SetNumberField(TEXT("z"),Map.Z);
    R->SetNumberField(TEXT("x"),Ros.X);R->SetNumberField(TEXT("y"),Ros.Y);R->SetNumberField(TEXT("z"),Ros.Z);R->SetNumberField(TEXT("w"),Ros.W);
    Pose->SetObjectField(TEXT("position"),P);Pose->SetObjectField(TEXT("orientation"),R);J->SetObjectField(TEXT("header"),Header);J->SetObjectField(TEXT("pose"),Pose);return J;
}
void ARedlineAstronautCharacter::QueryCell(FVector Map)
{
    if(!Bridge || bQueryPending)return;
    bQueryPending=true;LastQueryAt=FPlatformTime::Seconds();LastQueriedMap=Map;if(CellSpeedFactor>0)CellSpeedFactor=UnknownSpeedFactor;
    auto Args=MakeShared<FJsonObject>(),P=MakeShared<FJsonObject>();P->SetNumberField(TEXT("x"),Map.X);P->SetNumberField(TEXT("y"),Map.Y);P->SetNumberField(TEXT("z"),Map.Z);
    Args->SetStringField(TEXT("site_id"),TEXT("BXW"));Args->SetObjectField(TEXT("point"),P);
    TWeakObjectPtr<ARedlineAstronautCharacter> Weak(this);
    Bridge->CallService(TEXT("/redline/query_cell"),TEXT("redline_msgs/srv/QueryCell"),Args,
        [Weak,Map](bool OK,const TSharedPtr<FJsonObject>& Values,const FString& Error)
        {
            auto* Self=Weak.Get();if(!Self)return;Self->bQueryPending=false;
            bool Found=false;const TSharedPtr<FJsonObject>* Cell=nullptr;double Factor;
            const FVector Here=URedlineCoords::UeToRosLocation(Self->GetActorLocation());
            if(OK && Values && Values->TryGetBoolField(TEXT("found"),Found) && Found && Values->TryGetObjectField(TEXT("cell"),Cell) &&
               (*Cell)->TryGetNumberField(TEXT("speed_factor"),Factor) && FMath::IsFinite(Factor) && Factor>=0 && Factor<=1 && FVector::Dist2D(Here,Map)<3)
                Self->CellSpeedFactor=Factor;
        });
}
void ARedlineAstronautCharacter::OnState(const FString& Topic,const TSharedPtr<FJsonObject>& Json)
{
    if(Topic==TEXT("/redline/mission/state"))
    {
        double Phase;if(Json && Json->TryGetNumberField(TEXT("phase"),Phase) && Phase>=0 && Phase<=6 && Phase==FMath::FloorToDouble(Phase))
        {MissionPhase=static_cast<int32>(Phase);MissionReceipt=FPlatformTime::Seconds();}
        else MissionReceipt=-1;
        return;
    }
    if(!Bridge || !Bridge->IsOfflineReplay() || Topic!=TEXT("/crew/EV1/state"))return;
    FRedlineEVACrew Crew;FString Error;if(FRedlineEVACrew::Parse(Json,Crew,Error))SetActorLocation(URedlineCoords::RosToUeLocation(Crew.Position)+FVector(0,0,GetCapsuleComponent()->GetScaledCapsuleHalfHeight()));
}
void ARedlineAstronautCharacter::AdvanceMission()
{
    const double Now=FPlatformTime::Seconds();if(!Bridge || Now-LastInteractionAt<1 || !bMissionStateFresh)return;
    LastInteractionAt=Now;TWeakObjectPtr<ARedlineAstronautCharacter> Weak(this);FString Error;
    Bridge->DispatchMissionCommand(FGuid::NewGuid().ToString(),TEXT("/redline/mission/advance"),TEXT("std_srvs/srv/Trigger"),MakeShared<FJsonObject>(),
        {TEXT("/redline/mission/clock"),TEXT("/redline/mission/state"),TEXT("/crew/EV1/state")},
        [Weak](bool Transport,const TSharedPtr<FJsonObject>& Values,const FString& Why)
        {if(auto* Self=Weak.Get()){bool Success=false;if(Values)Values->TryGetBoolField(TEXT("success"),Success);
            Self->InteractionMessage=!Transport ? TEXT("Gorev baglantisi bekleniyor.") : Success ? TEXT("Onay alindi.") : TEXT("Su an kullanilamiyor. Hedefe yaklas ve tekrar dene.");}},Error);
    if(!Error.IsEmpty())InteractionMessage=TEXT("Gorev verileri yenilenince tekrar dene.");
}
void ARedlineAstronautCharacter::Tick(float Delta)
{
    Super::Tick(Delta);if(!Bridge || Bridge->IsOfflineReplay())return;
    const double Now=FPlatformTime::Seconds();auto* PC=Cast<APlayerController>(GetController());auto* View=GetWorld()->GetGameViewport();
    const bool Live=Bridge->IsConnected() && Bridge->bHasMissionClock && Bridge->StaleMonitor->IsFresh(TEXT("/redline/mission/clock"),Now);
    const bool Focused=PC && View && View->Viewport && View->Viewport->HasFocus();
    bMissionStateFresh=Bridge->IsConnected() && MissionReceipt>=0 && Now-MissionReceipt<3;
    if(!bPresentationLocked && !bMissionJournalOpen && Focused && PC->WasInputKeyJustPressed(EKeys::V))SetFirstPersonView(!bFirstPersonView);
    if(bIntroMode && !bPresentationLocked && !bMissionJournalOpen && Focused && PC->WasInputKeyJustPressed(EKeys::E))AdvanceMission();
    if(!bIntroMode && !bPresentationLocked && !bMissionJournalOpen && Focused && PC->WasInputKeyJustPressed(EKeys::E))
        for(TActorIterator<ARedlineCampaignConsole> It(GetWorld());It;++It){It->Interact();break;}
    FVector Direction=FVector::ZeroVector;
    bSprinting=false;
    if(!bPresentationLocked && !bMissionJournalOpen && Live && bMovementProfileReady && PC && (Focused || ProbeSeconds>0))
    {
        float MX=0,MY=0;if(Focused){PC->GetInputMouseDelta(MX,MY);AddControllerYawInput(MX*.5f);AddControllerPitchInput(-MY*.5f);}
        const FRotator Yaw(0,PC->GetControlRotation().Yaw,0);const FVector Forward=Yaw.Vector(),Right=FRotationMatrix(Yaw).GetUnitAxis(EAxis::Y);
        // A quick tap may press and release within one rendered frame. Retain a
        // short input pulse so both keyboard taps and held keys start walking.
        if(Focused)
        {
            if(PC->WasInputKeyJustPressed(EKeys::W) || PC->WasInputKeyJustPressed(EKeys::Up))ForwardPulse=Now+.12;
            if(PC->WasInputKeyJustPressed(EKeys::S) || PC->WasInputKeyJustPressed(EKeys::Down))BackPulse=Now+.12;
            if(PC->WasInputKeyJustPressed(EKeys::D) || PC->WasInputKeyJustPressed(EKeys::Right))RightPulse=Now+.12;
            if(PC->WasInputKeyJustPressed(EKeys::A) || PC->WasInputKeyJustPressed(EKeys::Left))LeftPulse=Now+.12;
            if(PC->WasInputKeyJustPressed(EKeys::LeftShift) || PC->WasInputKeyJustPressed(EKeys::RightShift))SprintPulse=Now+.2;
        }
        double F=Focused ? double(PC->IsInputKeyDown(EKeys::W) || PC->IsInputKeyDown(EKeys::Up) || Now<ForwardPulse)-double(PC->IsInputKeyDown(EKeys::S) || PC->IsInputKeyDown(EKeys::Down) || Now<BackPulse) : 0;
        double R=Focused ? double(PC->IsInputKeyDown(EKeys::D) || PC->IsInputKeyDown(EKeys::Right) || Now<RightPulse)-double(PC->IsInputKeyDown(EKeys::A) || PC->IsInputKeyDown(EKeys::Left) || Now<LeftPulse) : 0;
        if(ProbeSeconds>0)
        {
            if(ProbeStart<0)ProbeStart=Now;
            if(Now-ProbeStart<ProbeSeconds){F=1;R=0;}
            else ProbeSeconds=0; // End the diagnostic override; return to normal WASD.
        }
        Direction=(Forward*F+Right*R).GetClampedToMaxSize(1);
        const FVector Normal=GetCharacterMovement()->CurrentFloor.HitResult.ImpactNormal;
        const double Grade=Normal.Z>.1 ? -FVector::DotProduct(Normal,Direction.GetSafeNormal2D())/Normal.Z : 0;
        bSprinting=Focused && !Direction.IsNearlyZero() && SprintCapMps>0 && (PC->IsInputKeyDown(EKeys::LeftShift) || PC->IsInputKeyDown(EKeys::RightShift) || Now<SprintPulse);
        GetCharacterMovement()->MaxWalkSpeed=RequestedSpeed(WalkingSpeed(Grade),bSprinting,SprintMultiplier,SprintCapMps)*100;
        GetCharacterMovement()->MaxAcceleration=bSprinting ? 850 : 400;
        AddMovementInput(Direction,1);
    }
    else {GetCharacterMovement()->StopMovementImmediately();ForwardPulse=BackPulse=RightPulse=LeftPulse=SprintPulse=-1;}
    if(Locomotion)Locomotion->SetMeasuredSpeed(GetVelocity().Size2D());
    if(Now>=NextAnimationLog)
    {
        NextAnimationLog=Now+1;
        const FVector Foot=GetMesh()->GetBoneLocation(TEXT("foot_l"),EBoneSpaces::ComponentSpace);
        UE_LOG(LogRedlineEVA,Display,TEXT("EV1 runtime speed=%.3f cm/s focus=%d live=%d anim=%s weight=%.3f cadence=%.3f time=%.3f foot_l=(%.3f,%.3f,%.3f)"),GetVelocity().Size2D(),Focused,Live,
            Locomotion ? TEXT("idle_walk_blend") : TEXT("idle_fallback"),Locomotion ? Locomotion->GetWalkWeight() : 0,Locomotion ? Locomotion->GetCadence() : 0,Locomotion ? Locomotion->GetWalkTime() : -1,Foot.X,Foot.Y,Foot.Z);
    }
    if(!Live)return;
    const FVector Map=URedlineCoords::UeToRosLocation(GetActorLocation());
    if(Now-LastQueryAt>1 || FVector::Dist2D(Map,LastQueriedMap)>2)QueryCell(Map);
    if(Now-LastPoseAt>=.05)
    {
        LastPoseAt=Now-LastPoseAt>.25 ? Now : LastPoseAt+.05;const auto UTC=FDateTime::UtcNow();const double Stamp=Bridge->bHasPhysicsClock && Bridge->StaleMonitor->IsFresh(TEXT("/clock"),Now) ? Bridge->PhysicsClockSec : double(UTC.ToUnixTimestamp())+UTC.GetMillisecond()*.001;
        if(Bridge->Publish(TEXT("/crew/EV1/pose"),PoseMessage(GetActorLocation(),GetActorQuat(),GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),Stamp)))++PublishedPoses;
        if(!PoseLog.IsEmpty()){FVector Foot=URedlineCoords::UeToRosLocation(GetActorLocation()-FVector(0,0,GetCapsuleComponent()->GetScaledCapsuleHalfHeight()));FFileHelper::SaveStringToFile(FString::Printf(TEXT("%.3f,%.6f,%.6f,%.6f,%d\n"),double(UTC.ToUnixTimestamp())+UTC.GetMillisecond()*.001,Foot.X,Foot.Y,Foot.Z,PublishedPoses),*PoseLog,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_Append);}
    }
}
