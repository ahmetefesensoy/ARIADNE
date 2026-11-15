#include "RedlineTaskFilm.h"
#include "RedlineSampleInteraction.h"
#include "RedlineAstronautCharacter.h"
#include "RedlineLocomotionInstance.h"
#include "RedlineRoverActor.h"
#include "RedlineCoords.h"
#include "RedlineTypes.h"
#include "RedlineMusicSubsystem.h"
#include "Engine/World.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/CanvasRenderTarget2D.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/RectLightComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "CanvasItem.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"

namespace TaskFilm
{
TSharedPtr<FJsonObject> O(const TSharedPtr<FJsonObject>& J,const TCHAR* K){const TSharedPtr<FJsonObject>* V;return J && J->TryGetObjectField(K,V) ? *V : nullptr;}
FString S(const TSharedPtr<FJsonObject>& J,const TCHAR* K){FString V;if(J)J->TryGetStringField(K,V);return V;}
FVector V(const TArray<TSharedPtr<FJsonValue>>& A){return A.Num()==3 ? FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber()) : FVector::ZeroVector;}
}
ARedlineTaskFilm::ARedlineTaskFilm(){PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickGroup=TG_PostUpdateWork;RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("FilmingFixture"));SetActorEnableCollision(false);}
UStaticMeshComponent* ARedlineTaskFilm::Prop(const FString& Path,FVector Position,FVector Scale)
{
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,*Path,nullptr,LOAD_NoWarn);if(!Mesh)return nullptr;
    auto* Part=NewObject<UStaticMeshComponent>(this);AddInstanceComponent(Part);Part->SetupAttachment(RootComponent);Part->RegisterComponent();Part->SetStaticMesh(Mesh);Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetWorldLocation(Position);Part->SetWorldScale3D(Scale);Props.Add(Part);return Part;
}
void ARedlineTaskFilm::BeginPlay()
{
    Super::BeginPlay();FParse::Value(FCommandLine::Get(),TEXT("RedlineTaskFilm="),Kind);
    if(Kind!=TEXT("collect") && Kind!=TEXT("xrf") && Kind!=TEXT("weather") && Kind!=TEXT("cache") && Kind!=TEXT("drill") && Kind!=TEXT("lab")){SetActorTickEnabled(false);return;}
    Camera=GetWorld()->SpawnActor<ACameraActor>();if(Camera)Camera->GetCameraComponent()->SetFieldOfView(52);
    // These clips start at a declared filming location. They do not represent
    // travelling there, charge EVA resources, or call mission/science services.
    FString Data;FParse::Value(FCommandLine::Get(),TEXT("RedlineFilmProduct="),Data);FString Raw;
    if(!Data.IsEmpty() && IFileManager::Get().FileSize(*Data)<128000 && FFileHelper::LoadFileToString(Raw,*Data)){Result=FRedlineJson::Parse(Raw);if(auto P=TaskFilm::O(Result,TEXT("product")))Result=P;ProductId=TaskFilm::S(Result,TEXT("product_id"));}
}
void ARedlineTaskFilm::PrepareDrill()
{
    using namespace TaskFilm;
    // Copy only the already assembled approved rover render parts. This is a
    // stationary SCENARIO shot fixture, not another ROS/Gazebo robot.
    for(TActorIterator<ARedlineRoverActor> It(GetWorld());It;++It)if(It->BaseFrame==TEXT("rover_1/base_link"))
    {
        TArray<AActor*> Visuals;It->GetAttachedActors(Visuals,true,true);Visuals.Add(*It);
        for(auto* Visual:Visuals){TArray<UStaticMeshComponent*> Meshes;Visual->GetComponents(Meshes);
        for(auto* Source:Meshes)if(Source->GetStaticMesh() && Source->GetStaticMesh()->GetPathName()!=TEXT("/Engine/BasicShapes/Cube.Cube"))
        {
            auto* Copy=Prop(Source->GetStaticMesh()->GetPathName(),Site-FVector(200,0,0));if(!Copy)continue;
            const FTransform Relative=Source->GetComponentTransform().GetRelativeTransform(It->GetActorTransform());
            Copy->SetWorldTransform(Relative*FTransform(FQuat::Identity,Site-FVector(200,0,0)));
            for(int32 M=0;M<Source->GetNumMaterials();++M)Copy->SetMaterial(M,Source->GetMaterial(M));
        }}break;
    }
    FString Raw;if(!FFileHelper::LoadFileToString(Raw,*(FPaths::ProjectContentDir()/TEXT("MissionProps/tool_drill_parts.json"))))return;
    auto J=FRedlineJson::Parse(Raw);const TArray<TSharedPtr<FJsonValue>>* Parts=nullptr;if(!J || !J->TryGetArrayField(TEXT("parts"),Parts))return;
    for(auto Value:*Parts)
    {
        auto P=Value->AsObject();auto* Part=Prop(S(P,TEXT("mesh_asset")),Site);if(!Part)continue;
        if(S(P,TEXT("name")).Contains(TEXT("_bit_LOD")))
        {
            const TArray<TSharedPtr<FJsonValue>>* Pivot=nullptr;if(!P->TryGetArrayField(TEXT("pivot_cm"),Pivot))continue;CapOrigin=V(*Pivot);
            BitPivot=NewObject<USceneComponent>(this);AddInstanceComponent(BitPivot);BitPivot->SetupAttachment(RootComponent);BitPivot->RegisterComponent();BitPivot->SetWorldLocation(Site+CapOrigin);
            Part->AttachToComponent(BitPivot,FAttachmentTransformRules::KeepWorldTransform);Part->SetRelativeLocation(-CapOrigin);
        }
    }
}
void ARedlineTaskFilm::PrepareLab()
{
    Prop(TEXT("/Game/MissionProps/lab_bench/SM_lab_bench.SM_lab_bench"),Site);
    Prop(TEXT("/Game/MissionProps/sample_case/SM_sample_case.SM_sample_case"),Site+FVector(0,0,85));
    LabTube=Prop(TEXT("/Game/MissionProps/sample_tube/SM_sample_tube.SM_sample_tube"),Site+FVector(20,0,86));
    // The lab's authored glass box occludes a plane behind the worktop. Put the
    // result monitor above its front edge and point its actual normal at the
    // filming camera; leave the approved source mesh and materials untouched.
    const FVector MonitorPosition=Site+FVector(40,-45,172);
    const FVector MonitorCamera=Site+FVector(230,-80,168);
    // Engine Plane UVs in this view run opposite to both camera axes. Two
    // negative in-plane scales rotate the display 180 degrees (no mirroring).
    auto* Plane=Prop(TEXT("/Engine/BasicShapes/Plane.Plane"),MonitorPosition,FVector(-1.25,-.78125,1));
    if(Plane)
    {
        const FVector Normal=(MonitorCamera-MonitorPosition).GetSafeNormal();
        const FVector Right=FVector::CrossProduct(FVector::UpVector,Normal).GetSafeNormal();
        Plane->SetWorldRotation(FRotationMatrix::MakeFromZX(Normal,Right).Rotator());ScreenMaterial=UMaterialInstanceDynamic::Create(LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Campaign/Materials/M_CampaignDisplay.M_CampaignDisplay")),this);Plane->SetMaterial(0,ScreenMaterial);
        Screen=UCanvasRenderTarget2D::CreateCanvasRenderTarget2D(this,UCanvasRenderTarget2D::StaticClass(),1280,800);Screen->OnCanvasRenderTargetUpdate.AddDynamic(this,&ARedlineTaskFilm::DrawLab);ScreenMaterial->SetTextureParameterValue(TEXT("DisplayMap"),Screen);ScreenMaterial->SetScalarParameterValue(TEXT("DataFresh"),1);Screen->UpdateResource();
    }
}
void ARedlineTaskFilm::Tick(float Dt)
{
    Super::Tick(Dt);auto* PC=GetWorld()->GetFirstPlayerController();if(!PC || !Camera)return;
    if(!Human)Human=Cast<ARedlineAstronautCharacter>(PC->GetPawn());if(!Human)return;
    if(Began<0)
    {
        FVector Ground;FVector Map(330,-430,-3580);if(!URedlineCoords::TraceTerrainHeight(this,Map,200,Ground))return;
        Site=URedlineCoords::RosToUeLocation(Ground);
        if(Kind==TEXT("lab") || Kind==TEXT("cache"))
        {
            // Lab work belongs to the dedicated approved habitat room beyond
            // the airlock, not a workbench placed on the open Martian surface.
            for(TActorIterator<AActor> It(GetWorld());It;++It)if(It->ActorHasTag(TEXT("prologue_room_lab")))
            {Site=It->GetActorLocation()+FVector(-160,0,2);bIndoor=true;break;}
            if(!bIndoor){SetActorTickEnabled(false);Phase=TEXT("Habitat laboratuvarı bulunamadı; dışarıda deney başlatılmadı.");return;}
        }
        Start=bIndoor ? Site+FVector(190,65,0) : Site-FVector(240,0,0);Began=FPlatformTime::Seconds();
        Human->bPresentationLocked=true;Human->bMissionJournalOpen=false;Human->SetFirstPersonView(false);Human->SetActorHiddenInGame(Kind==TEXT("drill"));Human->SetActorRotation(FRotator::ZeroRotator);
        Human->SetActorLocation(Start+FVector(0,0,Human->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()));
        if(bIndoor)Human->SetActorRotation(FRotator(0,180,0));
        // A soft filming fill is confined to this opt-in SCENARIO actor. It
        // makes glove/tool surfaces readable without changing the level's sun,
        // exposure, other session's materials or any live-game light.
        auto* Fill=NewObject<URectLightComponent>(this);AddInstanceComponent(Fill);Fill->SetupAttachment(RootComponent);Fill->RegisterComponent();
        Fill->SetIntensityUnits(ELightUnits::Lumens);Fill->SetIntensity(bIndoor ? 6000 : 45000);Fill->SetLightColor(FLinearColor(1,.89,.75));Fill->SetAttenuationRadius(bIndoor ? 450 : 1400);Fill->SetCastShadows(false);Fill->SetSourceWidth(220);Fill->SetSourceHeight(160);
        const FVector FillPosition=Site+(bIndoor ? FVector(230,-50,200) : FVector(300,-300,280));Fill->SetWorldLocationAndRotation(FillPosition,(Site+FVector(0,0,100)-FillPosition).Rotation());
        if(Kind==TEXT("drill"))PrepareDrill();if(bIndoor)PrepareLab();
        if(auto* Cue=LoadObject<USoundBase>(nullptr,TEXT("/Game/Prologue/Audio/VO_mission_science.VO_mission_science")))UGameplayStatics::PlaySound2D(this,Cue,.7f);
    }
    const double T=FPlatformTime::Seconds()-Began;
    if(Kind==TEXT("drill"))
    {
        const double Progress=FMath::Clamp((T-5)/14.,0.,1.);const double Lift=T<5 ? 30*(1-T/5) : T>22 ? (T-22)*5 : 0;const double Depth=5*Progress;
        for(const auto& Part:Props){if(Part->GetAttachParent()==BitPivot)continue;if(Part->GetStaticMesh()->GetPathName().Contains(TEXT("tool_drill_parts")))Part->SetWorldLocation(Site+FVector(0,0,Lift-Depth));}
        if(BitPivot)BitPivot->SetWorldLocationAndRotation(Site+CapOrigin+FVector(0,0,Lift-Depth),FRotator(0,T>5 && T<22 ? T*720 : 0,0));
        Phase=T<5 ? TEXT("Ön konum ve yüzeye yaklaşma") : T<18 ? TEXT("Dönme ve 50 mm besleme / senaryo") : T<22 ? TEXT("Numune kaydı / senaryo") : TEXT("Ucu geri çekme");
    }
    else if(Kind!=TEXT("lab"))
    {
        if(T<4)
        {
            const FVector End=bIndoor ? Site+FVector(85,65,0) : Site-FVector(75,0,0);
            const FVector P=FMath::Lerp(Start,End,T/4)+FVector(0,0,Human->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());Human->SetActorLocation(P,true);
            if(auto* Anim=Cast<URedlineLocomotionInstance>(Human->GetMesh()->GetAnimInstance()))Anim->SetMeasuredSpeed(42);
            Phase=TEXT("Çalışma alanına yaklaşma");
        }
        else
        {
            if(!bStartedWork)
            {
                Human->bPresentationLocked=false;WorkPose=GetWorld()->SpawnActor<ARedlineSampleInteraction>();WorkPose->bUseInspectionCamera=false;WorkPose->bUseActualWorkPoint=true;
                const FVector WorkPoint=bIndoor ? Site+FVector(20,35,91) : Site;
                if(!WorkPose->BeginInteraction(Human,URedlineCoords::UeToRosLocation(WorkPoint),bIndoor ? TEXT("lab") : Kind))return;Work.Begin(Kind);bStartedWork=true;
            }
            if(Work.IsActive())
            {
                const int32 Stage=Work.StageIndex();uint8 Button=Stage==0 ? 1 : (Kind==TEXT("xrf") || Stage==2) ? 4 : 2;
                // Explicit scripted input for this filming fixture. The normal
                // playable actor still requires the player's actual buttons.
                Work.Tick(FMath::Min(double(Dt),.05),0,true);Work.Tick(FMath::Min(double(Dt),.05),Button,true,true,true);
                WorkPose->SetProgress(.75f*Work.Progress(),Work.PhaseText());Phase=Work.PhaseText();
            }
            else
            {
                if(PreparedAt<0)PreparedAt=T;const double P=FMath::Clamp((T-PreparedAt)/8.,0.,1.);Phase=TEXT("Ölçüm / kayıt gösterimi · senaryo");WorkPose->SetProgress(.75+.25*P,Phase);
                if(P>=1 && !bEndedWork){WorkPose->EndInteraction(true);bEndedWork=true;Phase=TEXT("Uygulama gösterimi tamamlandı");}
            }
        }
    }
    else
    {
        Phase=T<4 ? TEXT("Habitat / bilim odası: numuneyi tezgâha getir") : T<10 ? TEXT("Kap kabulü ve elektrot hazırlığı / senaryo") : T<18 ? TEXT("pH ve iletkenlik analiz modeli") : TEXT("Numune kökenine bağlı kayıtlı sonuç");
        if(T<4)
        {
            Human->SetActorLocation(FMath::Lerp(Start,Site+FVector(85,65,0),T/4)+FVector(0,0,Human->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),true);
            if(auto* Anim=Cast<URedlineLocomotionInstance>(Human->GetMesh()->GetAnimInstance()))Anim->SetMeasuredSpeed(27);
        }
        else if(!bStartedWork)
        {
            Human->bPresentationLocked=false;WorkPose=GetWorld()->SpawnActor<ARedlineSampleInteraction>();WorkPose->bUseInspectionCamera=false;WorkPose->bUseActualWorkPoint=true;
            bStartedWork=WorkPose->BeginInteraction(Human,URedlineCoords::UeToRosLocation(Site+FVector(20,35,91)),TEXT("lab"));
            if(LabTube)LabTube->SetHiddenInGame(true);
        }
        if(bStartedWork && WorkPose)WorkPose->SetProgress(FMath::Clamp((T-4)/14.,0.,1.),Phase);
        if(Screen)Screen->UpdateResource();
    }
    FVector Look=Kind==TEXT("drill") || Kind==TEXT("lab") ? Site+FVector(Kind==TEXT("drill") ? -60 : -20,0,Kind==TEXT("lab") ? 145 : 70)
        : Human->GetActorLocation()-FVector(0,0,Human->GetCapsuleComponent()->GetScaledCapsuleHalfHeight())+FVector(0,0,85);
    const double Orbit=T*.018;const double Range=Kind==TEXT("drill") ? 390 : 440;
    FVector Position=Look+FVector(FMath::Cos(Orbit)*Range,FMath::Sin(Orbit)*Range-250,160);
    if(Kind!=TEXT("lab") && Kind!=TEXT("drill"))
    {
        const double Close=FMath::Clamp((T-3)/3.,0.,1.)*(1-FMath::Clamp((T-22)/4.,0.,1.));
        Look=FMath::Lerp(Look,Site+FVector(-25,0,45),Close);
        const double WorkRange=FMath::Lerp(440.,215.,Close);
        Position=Look+FVector(FMath::Cos(Orbit)*WorkRange,FMath::Sin(Orbit)*WorkRange-FMath::Lerp(250.,150.,Close),FMath::Lerp(160.,110.,Close));
    }
    if(bIndoor)
    {
        const double Close=Kind==TEXT("lab") ? FMath::Clamp((T-12)/4.,0.,1.) : 0;
        Look=FMath::Lerp(Site+FVector(15,35,118),Site+FVector(40,-45,172),Close);
        Position=FMath::Lerp(Site+FVector(270,-115,165),Site+FVector(230,-80,168),Close);
        Camera->GetCameraComponent()->SetFieldOfView(65);
    }
    Camera->SetActorLocationAndRotation(Position,(Look-Position).Rotation());PC->SetViewTarget(Camera);
}
void ARedlineTaskFilm::DrawCaption(UCanvas* C)
{
    if(!C)return;auto Text=[&](FString S,float X,float Y,float Scale,FLinearColor Color){FCanvasTextItem I(FVector2D(X,Y),FText::FromString(S),GEngine->GetSmallFont(),Color);I.Scale=FVector2D(Scale);C->DrawItem(I);};
    FCanvasTileItem Header(FVector2D(0,0),FVector2D(C->SizeX,68),FLinearColor(0,0,0,.88));Header.BlendMode=SE_BLEND_Translucent;C->DrawItem(Header);
    Text(Kind==TEXT("collect") ? TEXT("Saha / yüzey numunesi / tüpe aktarım / mühürleme") : Kind==TEXT("xrf") ? TEXT("Saha / el tipi XRF / yüzey teması / sayım") : Kind==TEXT("weather") ? TEXT("Saha / çevre istasyonu / taban / anten") : Kind==TEXT("cache") ? TEXT("Habitat bilim odası / numune teslimi") : Kind==TEXT("drill") ? TEXT("Sondaj / dönen Tripo uç / besleme") : TEXT("Habitat bilim odası / pH ve iletkenlik"),28,18,1.6,FLinearColor(.9,.85,.75));
    FCanvasTileItem Footer(FVector2D(0,C->SizeY-78),FVector2D(C->SizeX,78),FLinearColor(0,0,0,.85));Footer.BlendMode=SE_BLEND_Translucent;C->DrawItem(Footer);
    Text(Phase,28,C->SizeY-65,1.35,FLinearColor::White);Text(TEXT("UNREAL 3D UYGULAMA GÖSTERİMİ · Betikli oyuncu / SCENARIO · Canlı görev sonucu değildir"),28,C->SizeY-30,1.0,FLinearColor(.7,.65,.55));
}
void ARedlineTaskFilm::DrawLab(UCanvas* C,int32 W,int32 H)
{
    using namespace TaskFilm;if(!C)return;FCanvasTileItem BG(FVector2D::ZeroVector,FVector2D(W,H),FLinearColor(.01,.01,.008));C->DrawItem(BG);
    auto Text=[&](FString S,int32 Y){FCanvasTextItem I(FVector2D(40,Y),FText::FromString(S),GEngine->GetSmallFont(),FLinearColor(.9,.85,.75));I.Scale=FVector2D(1.8);C->DrawItem(I);};
    Text(TEXT("NUMUNE ANALİZİ / pH + İLETKENLİK"),30);auto Summary=O(Result,TEXT("summary"));if(!Summary)Summary=O(Result,TEXT("measurement"));auto Series=O(Summary,TEXT("series"));
    const TArray<TSharedPtr<FJsonValue>> *Times=nullptr,*PH=nullptr,*EC=nullptr;
    if(!Series || !Series->TryGetArrayField(TEXT("time_s"),Times) || !Series->TryGetArrayField(TEXT("ph"),PH) || !Series->TryGetArrayField(TEXT("conductivity_ms_cm"),EC) || Times->Num()<2 || PH->Num()!=Times->Num() || EC->Num()!=Times->Num()){Text(TEXT("Kayıtlı analiz ürünü yok; sonuç üretilmedi."),200);return;}
    Text(TEXT("pH / 0–14"),130);Text(TEXT("İletkenlik / mS cm-1"),420);const double MaxTime=Times->Last()->AsNumber();double MaxEC=.01;for(auto V:*EC)MaxEC=FMath::Max(MaxEC,V->AsNumber());
    for(int32 I=1;I<Times->Num();++I)
    {
        const float X=80+(*Times)[I-1]->AsNumber()/MaxTime*1080,X2=80+(*Times)[I]->AsNumber()/MaxTime*1080;
        FCanvasLineItem A(FVector2D(X,370-(*PH)[I-1]->AsNumber()/14*190),FVector2D(X2,370-(*PH)[I]->AsNumber()/14*190));A.SetColor(FLinearColor(.55,.72,.58));A.LineThickness=3;C->DrawItem(A);
        FCanvasLineItem B(FVector2D(X,650-(*EC)[I-1]->AsNumber()/MaxEC*170),FVector2D(X2,650-(*EC)[I]->AsNumber()/MaxEC*170));B.SetColor(FLinearColor(.85,.5,.2));B.LineThickness=3;C->DrawItem(B);
    }
    Text(TEXT("SIMULATED / WCL_SCENARIO · Gale ölçümü değildir"),700);Text(S(Summary,TEXT("sample_id")),750);
}
void ARedlineTaskFilm::EndPlay(const EEndPlayReason::Type Reason){if(WorkPose){WorkPose->EndInteraction(false);WorkPose->Destroy();}if(Human){Human->bPresentationLocked=false;Human->SetActorHiddenInGame(false);}if(Camera)Camera->Destroy();Super::EndPlay(Reason);}
