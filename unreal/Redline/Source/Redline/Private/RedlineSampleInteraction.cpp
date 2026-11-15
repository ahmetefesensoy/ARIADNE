#include "RedlineSampleInteraction.h"
#include "RedlineAstronautCharacter.h"
#include "RedlineCoords.h"
#include "Components/SceneComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"
#include "RedlineTypes.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace RedlineSamplePerformance
{
double Smooth(double Start,double End,double Value)
{const double T=FMath::Clamp((Value-Start)/(End-Start),0.,1.);return T*T*(3-2*T);}
}

ARedlineSampleInteraction::ARedlineSampleInteraction()
{
    PrimaryActorTick.bCanEverTick=true;RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("SamplePerformanceRoot"));
    PerformanceBody=CreateDefaultSubobject<UPoseableMeshComponent>(TEXT("FeedbackDrivenAstronaut"));PerformanceBody->SetupAttachment(RootComponent);
    PerformanceBody->SetCollisionEnabled(ECollisionEnabled::NoCollision);PerformanceBody->SetGenerateOverlapEvents(false);PerformanceBody->SetReceivesDecals(false);PerformanceBody->SetHiddenInGame(true);
    SampleVisual=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("VisualSampleTube"));SampleVisual->SetupAttachment(RootComponent);
    SampleCapPivot=CreateDefaultSubobject<USceneComponent>(TEXT("ActualTubeCapPivot"));SampleCapPivot->SetupAttachment(SampleVisual);
    SampleCap=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ActualTubeCap"));SampleCap->SetupAttachment(SampleCapPivot);
    SampleCap->SetCollisionEnabled(ECollisionEnabled::NoCollision);SampleCap->SetHiddenInGame(true);SampleCap->SetReceivesDecals(false);
    StationRoot=CreateDefaultSubobject<USceneComponent>(TEXT("DeployedStationRoot"));StationRoot->SetupAttachment(RootComponent);
    HandTool=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SampleToolHandle"));HandTool->SetupAttachment(RootComponent);
    ToolHead=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SampleScoopHead"));ToolHead->SetupAttachment(RootComponent);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if(Cylinder.Succeeded()){SampleVisual->SetStaticMesh(Cylinder.Object);HandTool->SetStaticMesh(Cylinder.Object);}
    if(Cube.Succeeded())ToolHead->SetStaticMesh(Cube.Object);
    for(auto* Prop:{SampleVisual.Get(),HandTool.Get(),ToolHead.Get()})
    {Prop->SetSimulatePhysics(false);Prop->SetCollisionEnabled(ECollisionEnabled::NoCollision);Prop->SetGenerateOverlapEvents(false);Prop->SetHiddenInGame(true);Prop->SetReceivesDecals(false);}
    SampleVisual->SetRelativeScale3D(FVector(.035,.035,.16));
    HandTool->SetRelativeScale3D(FVector(.025,.025,.28));ToolHead->SetRelativeScale3D(FVector(.13,.08,.025));
    InspectionCamera=CreateDefaultSubobject<UCameraComponent>(TEXT("SampleInspectionCamera"));InspectionCamera->SetupAttachment(RootComponent);InspectionCamera->SetFieldOfView(62);
}

bool ARedlineSampleInteraction::BeginInteraction(ARedlineAstronautCharacter* Astronaut,FVector TargetMap,const FString& Kind)
{
    if(bActive || !IsValid(Astronaut) || TargetMap.ContainsNaN() || Kind.IsEmpty() || Astronaut->bPresentationLocked)return false;
    auto* Mesh=Astronaut->GetMesh();auto* Asset=Mesh ? Mesh->GetSkeletalMeshAsset() : nullptr;
    if(!Asset)return false;
    for(const TCHAR* Bone:{TEXT("hand_r"),TEXT("pelvis"),TEXT("thigh_l"),TEXT("calf_l"),TEXT("foot_l"),TEXT("thigh_r"),TEXT("calf_r"),TEXT("foot_r"),TEXT("upperarm_r"),TEXT("lowerarm_r")})
        if(Asset->GetRefSkeleton().FindBoneIndex(Bone)<0)return false;
    Human=Astronaut;SourceBody=Mesh;InteractionKind=Kind;FeedbackPhase=TEXT("PREPARING");FeedbackProgress=0;PerformanceSeconds=0;bTransferred=false;
    bPreviousLocked=Astronaut->bPresentationLocked;bPreviousMeshHidden=Mesh->bHiddenInGame;bPreviousMeshVisible=Mesh->IsVisible();bPreviousOwnerNoSee=Mesh->bOwnerNoSee;
    SetActorTransform(Mesh->GetComponentTransform());
    // Only the duplicate visual faces the work point. EV1's real capsule,
    // orientation, published map pose and root animation stay untouched.
    const FVector TargetWorld=URedlineCoords::RosToUeLocation(TargetMap);
    FVector Toward=(TargetWorld-Astronaut->GetActorLocation()).GetSafeNormal2D();
    if(Toward.IsNearlyZero())Toward=Astronaut->GetActorForwardVector();
    SetActorRotation(Toward.Rotation());
    PerformanceBody->SetSkinnedAssetAndUpdate(Asset);PerformanceBody->CopyPoseFromSkeletalComponent(Mesh);
    if(PerformanceBody->BoneSpaceTransforms.Num()!=Asset->GetRefSkeleton().GetNum())return false;
    for(int32 I=0;I<Mesh->GetNumMaterials();++I)PerformanceBody->SetMaterial(I,Mesh->GetMaterial(I));
    BaseLocalPose=PerformanceBody->BoneSpaceTransforms;PerformanceBody->RefreshBoneTransforms();BaseComponentPose=ComponentPose();
    const int32 Foot=Asset->GetRefSkeleton().FindBoneIndex(TEXT("foot_r"));
    const double FootZ=Foot>=0 ? BaseComponentPose[Foot].GetTranslation().Z : 10;
    WorkPointComponent=FVector(62,-15,FootZ+12);
    WorkWorld=TargetWorld;
    if(bUseActualWorkPoint)WorkPointComponent=GetActorTransform().InverseTransformPosition(TargetWorld)+FVector(0,0,Kind==TEXT("weather") ? 35 : 4);
    auto* Paint=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Prologue/Materials/M_AirlockPaint.M_AirlockPaint"));
    if(Kind!=TEXT("xrf"))
    {HandTool->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cylinder.Cylinder")));HandTool->SetRelativeScale3D(FVector(.025,.025,.28));}
    auto* Frame=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Prologue/Materials/M_GraphiteFrame.M_GraphiteFrame"));
    if(Paint)SampleVisual->SetMaterial(0,Paint);if(Frame){HandTool->SetMaterial(0,Frame);ToolHead->SetMaterial(0,Frame);}
    Astronaut->bPresentationLocked=true;Astronaut->GetCharacterMovement()->StopMovementImmediately();Mesh->SetHiddenInGame(true);PerformanceBody->SetOwnerNoSee(false);PerformanceBody->SetHiddenInGame(false);PerformanceBody->SetVisibility(true);
    for(auto* Prop:{SampleVisual.Get(),HandTool.Get(),ToolHead.Get()})Prop->SetHiddenInGame(false);
    // Approved source meshes retain their authored centimetre scale. These
    // are presentation props; ROS sample custody and results remain separate.
    if(auto* Tube=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/MissionProps/sample_tube/SM_sample_tube.SM_sample_tube"),nullptr,LOAD_NoWarn))
    {SampleVisual->SetStaticMesh(Tube);SampleVisual->SetRelativeScale3D(FVector::OneVector);SampleVisual->EmptyOverrideMaterials();}
    SampleVisual->SetHiddenInGame(Kind!=TEXT("collect") && Kind!=TEXT("cache") && Kind!=TEXT("lab"));
    if(Kind==TEXT("xrf"))
    {
        if(auto* Tool=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/MissionProps/tool_apxs/SM_tool_apxs.SM_tool_apxs"),nullptr,LOAD_NoWarn))
        {HandTool->SetStaticMesh(Tool);HandTool->SetRelativeScale3D(FVector::OneVector);HandTool->EmptyOverrideMaterials();ToolHead->SetHiddenInGame(true);}
    }
    LoadInteractionParts();
    SampleCap->SetHiddenInGame((Kind!=TEXT("collect") && Kind!=TEXT("cache") && Kind!=TEXT("lab")) || !SampleCap->GetStaticMesh());
    if(Kind==TEXT("lab")){HandTool->SetHiddenInGame(true);ToolHead->SetHiddenInGame(true);}
    for(const auto& Part:StationMeshes)Part->SetHiddenInGame(Kind!=TEXT("weather"));
    if(Kind==TEXT("weather")){HandTool->SetHiddenInGame(true);ToolHead->SetHiddenInGame(true);StationRoot->SetWorldLocationAndRotation(WorkWorld,GetActorRotation());}
    Player=Cast<APlayerController>(Astronaut->GetController());
    if(bUseInspectionCamera && Player.IsValid())
    {
        PreviousView=Player->GetViewTarget();const FVector Look=GetActorTransform().TransformPosition(FVector(30,0,75));
        FVector Position=GetActorTransform().TransformPosition(FVector(220,-190,155));
        FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(RedlineSampleCamera),false,this);Query.AddIgnoredActor(Astronaut);
        if(GetWorld()->LineTraceSingleByChannel(Hit,Look,Position,ECC_Camera,Query))Position=Hit.ImpactPoint+(Look-Hit.ImpactPoint).GetSafeNormal()*18;
        InspectionCamera->SetWorldLocationAndRotation(Position,(Look-Position).Rotation());Player->SetViewTarget(this);
    }
    bActive=true;ApplyPerformance();return true;
}

TArray<FTransform> ARedlineSampleInteraction::ComponentPose() const
{
    TArray<FTransform> Result;const auto* Asset=PerformanceBody->GetSkinnedAsset();if(!Asset)return Result;
    const auto& Ref=Asset->GetRefSkeleton();const auto& Local=PerformanceBody->BoneSpaceTransforms;Result.SetNum(Local.Num());
    for(int32 I=0;I<Local.Num();++I){const int32 Parent=Ref.GetParentIndex(I);Result[I]=Parent<0 ? Local[I] : Local[I]*Result[Parent];}
    return Result;
}

void ARedlineSampleInteraction::SetComponentRotation(int32 Bone,const FQuat& Rotation)
{
    if(!PerformanceBody->BoneSpaceTransforms.IsValidIndex(Bone))return;
    const auto& Ref=PerformanceBody->GetSkinnedAsset()->GetRefSkeleton();const int32 Parent=Ref.GetParentIndex(Bone);
    const auto Pose=ComponentPose();const FQuat ParentRotation=Parent<0 ? FQuat::Identity : Pose[Parent].GetRotation();
    PerformanceBody->BoneSpaceTransforms[Bone].SetRotation((ParentRotation.Inverse()*Rotation).GetNormalized());
}

void ARedlineSampleInteraction::SolveLimb(FName UpperName,FName LowerName,FName TipName,FVector Target,FVector Pole)
{
    const auto& Ref=PerformanceBody->GetSkinnedAsset()->GetRefSkeleton();
    const int32 Upper=Ref.FindBoneIndex(UpperName),Lower=Ref.FindBoneIndex(LowerName),Tip=Ref.FindBoneIndex(TipName);
    if(Upper<0 || Lower<0 || Tip<0)return;
    auto Pose=ComponentPose();const FVector Start=Pose[Upper].GetTranslation();
    const double A=FVector::Distance(BaseComponentPose[Upper].GetTranslation(),BaseComponentPose[Lower].GetTranslation());
    const double B=FVector::Distance(BaseComponentPose[Lower].GetTranslation(),BaseComponentPose[Tip].GetTranslation());
    if(A<.01 || B<.01)return;
    FVector Direction=(Target-Start).GetSafeNormal();if(Direction.IsNearlyZero())Direction=FVector(0,0,-1);
    const double Distance=FMath::Clamp(FVector::Distance(Start,Target),FMath::Abs(A-B)+.01,A+B-.01);
    const double Along=(A*A+Distance*Distance-B*B)/(2*Distance),Height=FMath::Sqrt(FMath::Max(0.,A*A-Along*Along));
    FVector Bend=(Pole-Direction*FVector::DotProduct(Pole,Direction)).GetSafeNormal();if(Bend.IsNearlyZero())Bend=FVector::YAxisVector;
    const FVector Joint=Start+Direction*Along+Bend*Height,End=Start+Direction*Distance;
    const FVector UpperBind=(BaseComponentPose[Lower].GetTranslation()-BaseComponentPose[Upper].GetTranslation()).GetSafeNormal();
    SetComponentRotation(Upper,FQuat::FindBetweenNormals(UpperBind,(Joint-Start).GetSafeNormal())*BaseComponentPose[Upper].GetRotation());
    Pose=ComponentPose();const FVector LowerBind=(BaseComponentPose[Tip].GetTranslation()-BaseComponentPose[Lower].GetTranslation()).GetSafeNormal();
    SetComponentRotation(Lower,FQuat::FindBetweenNormals(LowerBind,(End-Pose[Lower].GetTranslation()).GetSafeNormal())*BaseComponentPose[Lower].GetRotation());
    SetComponentRotation(Tip,BaseComponentPose[Tip].GetRotation());
}

void ARedlineSampleInteraction::ApplyPerformance()
{
    if(!bActive || BaseLocalPose.IsEmpty() || !PerformanceBody->GetSkinnedAsset())return;
    using namespace RedlineSamplePerformance;const double P=FeedbackProgress;
    const bool Bench=InteractionKind==TEXT("lab");
    const double Crouch=Bench ? 0 : Smooth(0,.32,P)*(1-Smooth(.67,.96,P));
    PerformanceBody->BoneSpaceTransforms=BaseLocalPose;
    PerformanceBody->BoneSpaceTransforms[0].AddToTranslation(FVector(0,0,-40*Crouch));
    const auto& Ref=PerformanceBody->GetSkinnedAsset()->GetRefSkeleton();
    for(const TCHAR* Side:{TEXT("l"),TEXT("r")})
    {
        const FName Thigh(FString(TEXT("thigh_"))+Side),Calf(FString(TEXT("calf_"))+Side),Foot(FString(TEXT("foot_"))+Side);
        const int32 Index=Ref.FindBoneIndex(Foot);if(Index>=0)SolveLimb(Thigh,Calf,Foot,BaseComponentPose[Index].GetTranslation(),FVector(1,0,0));
    }
    const int32 Spine=Ref.FindBoneIndex(TEXT("spine_01"));
    if(Spine>=0)SetComponentRotation(Spine,FQuat(FVector(0,1,0),FMath::DegreesToRadians(16*Crouch))*BaseComponentPose[Spine].GetRotation());
    const int32 RightHand=Ref.FindBoneIndex(TEXT("hand_r")),LeftHand=Ref.FindBoneIndex(TEXT("hand_l"));
    const double Reach=Smooth(.10,.36,P)*(1-Smooth(.75,1.,P));
    FVector RightTarget=BaseComponentPose[RightHand].GetTranslation();
    RightTarget=FMath::Lerp(RightTarget,WorkPointComponent+FVector(0,0,4*FMath::Sin(PerformanceSeconds*4))*(Bench ? .1 : Crouch),Reach);
    if(P>=.60){bTransferred=true;RightTarget=FMath::Lerp(RightTarget,FVector(30,-25,90),Smooth(.62,.91,P));}
    SolveLimb(TEXT("upperarm_r"),TEXT("lowerarm_r"),TEXT("hand_r"),RightTarget,FVector(0,-1,.2));
    if(LeftHand>=0)SolveLimb(TEXT("upperarm_l"),TEXT("lowerarm_l"),TEXT("hand_l"),FMath::Lerp(BaseComponentPose[LeftHand].GetTranslation(),Bench ? WorkPointComponent+FVector(0,16,10) : FVector(35,26,59),Bench ? Reach : Crouch),FVector(0,1,.2));
    PerformanceBody->MarkRefreshTransformDirty();PerformanceBody->RefreshBoneTransforms();
    FTransform Palm=PerformanceBody->GetSocketTransform(TEXT("hand_r"),RTS_World);
    // The imported rig's root bind scale is ~102.78. Socket offsets below are
    // centimetres, not bone units; avoid multiplying a 5 cm handle offset by it.
    Palm.SetScale3D(FVector::OneVector);
    const FVector ToolPoint=Palm.TransformPosition(FVector(0,0,-5));
    HandTool->SetWorldLocationAndRotation(ToolPoint,Palm.GetRotation());
    ToolHead->SetWorldLocationAndRotation(ToolPoint+Palm.GetRotation().RotateVector(FVector(0,0,-17)),Palm.GetRotation());
    if(bTransferred)SampleVisual->SetWorldLocationAndRotation(Palm.TransformPosition(FVector(0,3,-8)),Palm.GetRotation());
    else SampleVisual->SetRelativeLocationAndRotation(WorkPointComponent,FRotator::ZeroRotator);
    const double Open=Smooth(0,.12,P)*(1-Smooth(.55,.75,P));
    SampleCapPivot->SetRelativeLocationAndRotation(CapBind+FVector(0,0,5*Open),FRotator(25*Open,120*Open,0));
    if(InteractionKind==TEXT("weather"))
    {
        const double Place=Smooth(0,.25,P),Unfold=Smooth(.25,.60,P);StationRoot->SetWorldLocation(WorkWorld+FVector(0,0,18*(1-Place)));
        for(int32 I=0;I<StationPivots.Num();++I)
        {
            const FString Name=StationNames[I].ToString();FRotator Rotation=FRotator::ZeroRotator;
            if(Name.Contains(TEXT("antenna")))Rotation.Pitch=-75*(1-Unfold);
            if(Name.Contains(TEXT("leg_")))Rotation.Roll=30*(1-Unfold);
            StationPivots[I]->SetRelativeLocationAndRotation(StationBinds[I],Rotation);
        }
    }
}

void ARedlineSampleInteraction::LoadInteractionParts()
{
    if(bPartsLoaded){if(TubeBodyMesh){SampleVisual->SetStaticMesh(TubeBodyMesh);SampleVisual->SetRelativeScale3D(FVector::OneVector);SampleVisual->EmptyOverrideMaterials();}return;}
    bPartsLoaded=true;FString Raw;const FString Dir=FPaths::ProjectContentDir()/TEXT("MissionProps");
    if(FFileHelper::LoadFileToString(Raw,*(Dir/TEXT("sample_tube_parts.json"))) && Raw.Len()<64000)
    {
        auto J=FRedlineJson::Parse(Raw);FString Body,Cap;const TArray<TSharedPtr<FJsonValue>>* Pivot;
        if(J && J->TryGetStringField(TEXT("body_asset"),Body) && J->TryGetStringField(TEXT("cap_asset"),Cap) && J->TryGetArrayField(TEXT("cap_origin_cm"),Pivot) && Pivot->Num()==3)
        {
            auto* BodyMesh=LoadObject<UStaticMesh>(nullptr,*Body,nullptr,LOAD_NoWarn);auto* CapMesh=LoadObject<UStaticMesh>(nullptr,*Cap,nullptr,LOAD_NoWarn);
            if(BodyMesh && CapMesh){TubeBodyMesh=BodyMesh;SampleVisual->SetStaticMesh(BodyMesh);SampleVisual->SetRelativeScale3D(FVector::OneVector);SampleVisual->EmptyOverrideMaterials();SampleCap->SetStaticMesh(CapMesh);CapBind=FVector((*Pivot)[0]->AsNumber(),(*Pivot)[1]->AsNumber(),(*Pivot)[2]->AsNumber());SampleCap->SetRelativeLocation(-CapBind);}
        }
    }
    Raw.Empty();if(!FFileHelper::LoadFileToString(Raw,*(Dir/TEXT("science_station_parts.json"))) || Raw.Len()>64000)return;
    auto J=FRedlineJson::Parse(Raw);const TArray<TSharedPtr<FJsonValue>>* Parts;if(!J || !J->TryGetArrayField(TEXT("parts"),Parts) || Parts->Num()>32)return;
    for(auto V:*Parts)
    {
        auto P=V->AsObject();FString Path,Name;const TArray<TSharedPtr<FJsonValue>>* Pivot;
        if(!P || !P->TryGetStringField(TEXT("mesh_asset"),Path) || !P->TryGetStringField(TEXT("name"),Name) || !P->TryGetArrayField(TEXT("pivot_cm"),Pivot) || Pivot->Num()!=3)continue;
        auto* Mesh=LoadObject<UStaticMesh>(nullptr,*Path,nullptr,LOAD_NoWarn);if(!Mesh)continue;
        const FVector Origin((*Pivot)[0]->AsNumber(),(*Pivot)[1]->AsNumber(),(*Pivot)[2]->AsNumber());
        auto* Joint=NewObject<USceneComponent>(this);AddInstanceComponent(Joint);Joint->SetupAttachment(StationRoot);Joint->RegisterComponent();Joint->SetRelativeLocation(Origin);
        auto* Part=NewObject<UStaticMeshComponent>(this);AddInstanceComponent(Part);Part->SetupAttachment(Joint);Part->RegisterComponent();Part->SetStaticMesh(Mesh);Part->SetRelativeLocation(-Origin);Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetHiddenInGame(true);Part->SetReceivesDecals(false);
        StationPivots.Add(Joint);StationMeshes.Add(Part);StationNames.Add(FName(Name));StationBinds.Add(Origin);
    }
}

void ARedlineSampleInteraction::CommitStationVisual()
{
    if(StationMeshes.IsEmpty())return;auto* Installed=GetWorld()->SpawnActor<AActor>();if(!Installed)return;
    auto* Base=NewObject<USceneComponent>(Installed);Installed->SetRootComponent(Base);Installed->AddInstanceComponent(Base);Base->RegisterComponent();Installed->Tags.Add(TEXT("SCENARIO_DeployedScienceStation"));Installed->SetActorEnableCollision(false);
    for(const auto& Source:StationMeshes)
    {
        auto* Part=NewObject<UStaticMeshComponent>(Installed);Installed->AddInstanceComponent(Part);Part->SetupAttachment(Base);Part->RegisterComponent();Part->SetStaticMesh(Source->GetStaticMesh());Part->SetWorldTransform(Source->GetComponentTransform());Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetReceivesDecals(false);
    }
}

void ARedlineSampleInteraction::SetProgress(float Progress,const FString& Phase)
{
    if(!bActive || !FMath::IsFinite(Progress) || Progress<FeedbackProgress)return;
    FeedbackProgress=FMath::Max(FeedbackProgress,FMath::Clamp(Progress,0.f,1.f));FeedbackPhase=Phase.Left(128);ApplyPerformance();
    // Feedback of 1 is still not a result: only EndInteraction releases control.
}

void ARedlineSampleInteraction::EndInteraction(bool Success)
{
    if(!bActive)return;bActive=false;FeedbackPhase=Success ? TEXT("RESULT_SUCCEEDED") : TEXT("RESULT_STOPPED");
    if(Success && InteractionKind==TEXT("weather"))CommitStationVisual();
    SampleCap->SetHiddenInGame(true);for(const auto& Part:StationMeshes)Part->SetHiddenInGame(true);
    for(auto* Prop:{SampleVisual.Get(),HandTool.Get(),ToolHead.Get()})Prop->SetHiddenInGame(true);
    PerformanceBody->SetHiddenInGame(true);
    if(SourceBody.IsValid()){SourceBody->SetHiddenInGame(bPreviousMeshHidden);SourceBody->SetVisibility(bPreviousMeshVisible);SourceBody->SetOwnerNoSee(bPreviousOwnerNoSee);}
    if(Human.IsValid())Human->bPresentationLocked=bPreviousLocked;
    if(!bEnding && Player.IsValid()){if(PreviousView.IsValid())Player->SetViewTarget(PreviousView.Get());else if(Human.IsValid())Player->SetViewTarget(Human.Get());}
    Human.Reset();SourceBody.Reset();Player.Reset();PreviousView.Reset();
}

void ARedlineSampleInteraction::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);if(!bActive)return;
    if(!Human.IsValid() || !SourceBody.IsValid()){EndInteraction(false);return;}
    PerformanceSeconds+=FMath::Max(0.f,DeltaSeconds);ApplyPerformance();
}
void ARedlineSampleInteraction::EndPlay(const EEndPlayReason::Type Reason)
{bEnding=true;EndInteraction(false);Super::EndPlay(Reason);}
