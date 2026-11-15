#include "RedlineFieldTablet.h"
#include "RedlineAstronautCharacter.h"
#include "RedlineCampaignConsole.h"
#include "RedlineBridgeSubsystem.h"
#include "RedlineTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/CanvasRenderTarget2D.h"
#include "Engine/Texture2D.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/SkeletalMesh.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "CanvasItem.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/Base64.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "InputCoreTypes.h"
#include "Math/RotationMatrix.h"
#include "RedlineConsoleTheme.h"

DEFINE_LOG_CATEGORY_STATIC(LogRedlineTablet,Log,All);
ARedlineFieldTablet::ARedlineFieldTablet()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickGroup=TG_PostUpdateWork;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("TabletRoot"));
    Shell=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("TripoTablet"));Shell->SetupAttachment(RootComponent);
    Screen=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LiveDisplay"));Screen->SetupAttachment(RootComponent);
    Arms=CreateDefaultSubobject<UPoseableMeshComponent>(TEXT("TabletGripVisual"));Arms->SetupAttachment(RootComponent);
    for(auto* Part:{Shell.Get(),Screen.Get()}){Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetCastShadow(false);Part->SetHiddenInGame(true);}
    Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);Arms->SetHiddenInGame(true);
    SetActorEnableCollision(false);
}
void ARedlineFieldTablet::BeginPlay()
{
    Super::BeginPlay();if(auto* GI=GetGameInstance())Bridge=GI->GetSubsystem<URedlineBridgeSubsystem>();
    FString Text;if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("Campaign/tablet.json"))))return;
    auto J=FRedlineJson::Parse(Text);FString Path;if(!J || !J->TryGetStringField(TEXT("mesh_asset"),Path))return;
    Shell->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,*Path));Screen->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Plane.Plane")));
    Screen->SetRelativeLocation(FVector(0,0,1.15));Screen->SetRelativeScale3D(FVector(.252,.158,1));
    ScreenMaterial=UMaterialInstanceDynamic::Create(LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Campaign/Materials/M_CampaignDisplay.M_CampaignDisplay")),this);
    if(!Shell->GetStaticMesh() || !ScreenMaterial)return;
    Screen->SetMaterial(0,ScreenMaterial);Display=UCanvasRenderTarget2D::CreateCanvasRenderTarget2D(this,UCanvasRenderTarget2D::StaticClass(),1280,800);
    Display->OnCanvasRenderTargetUpdate.AddDynamic(this,&ARedlineFieldTablet::Render);ScreenMaterial->SetTextureParameterValue(TEXT("DisplayMap"),Display);ScreenMaterial->SetScalarParameterValue(TEXT("DataFresh"),1);
    if(Bridge){Handle=Bridge->OnTopic.AddUObject(this,&ARedlineFieldTablet::Receive);Bridge->Subscribe(TEXT("/redline/rviz/image/compressed"),TEXT("sensor_msgs/msg/CompressedImage"),250,2);Bridge->Subscribe(TEXT("/redline/rviz/status"),TEXT("std_msgs/msg/String"),250,2);}
    bReady=true;UE_LOG(LogRedlineTablet,Display,TEXT("Tripo field tablet ready; T raise, Tab pages, Z zoom; actual RViz stream only"));
}
bool ARedlineFieldTablet::DecodeImage(const TSharedPtr<FJsonObject>& J,TArray<uint8>& Pixels,int32& Width,int32& Height)
{
    FString Format,Data,Frame;const TSharedPtr<FJsonObject>* Header;
    if(!J || !J->TryGetStringField(TEXT("format"),Format) || (Format!=TEXT("png") && Format!=TEXT("jpeg")) || !J->TryGetObjectField(TEXT("header"),Header) ||
       !(*Header)->TryGetStringField(TEXT("frame_id"),Frame) || Frame!=TEXT("rviz") || !J->TryGetStringField(TEXT("data"),Data) || Data.Len()>1400000)return false;
    TArray<uint8> Compressed;if(!FBase64::Decode(Data,Compressed) || Compressed.Num()<16 || Compressed.Num()>1048576)return false;
    auto Wrapper=FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper")).CreateImageWrapper(Format==TEXT("png") ? EImageFormat::PNG : EImageFormat::JPEG);
    if(!Wrapper || !Wrapper->SetCompressed(Compressed.GetData(),Compressed.Num()))return false;
    Width=Wrapper->GetWidth();Height=Wrapper->GetHeight();if(Width<64 || Height<64 || Width>2048 || Height>2048)return false;
    return Wrapper->GetRaw(ERGBFormat::BGRA,8,Pixels) && Pixels.Num()==Width*Height*4;
}
void ARedlineFieldTablet::Receive(const FString& Topic,const TSharedPtr<FJsonObject>& J)
{
    if(Topic==TEXT("/redline/rviz/status"))
    {
        FString Text;if(!J || !J->TryGetStringField(TEXT("data"),Text) || Text.Len()>4096)return;auto S=FRedlineJson::Parse(Text);FString Schema,Source,Id;double Seq;
        if(!S || !S->TryGetStringField(TEXT("schema"),Schema) || Schema!=TEXT("redline.rviz.stream.v1") || !S->TryGetStringField(TEXT("source"),Source) || Source!=TEXT("rviz2/private-xvfb") || !S->TryGetStringField(TEXT("stream_id"),Id) || Id.Len()>128 || !S->TryGetNumberField(TEXT("sequence"),Seq) || !FMath::IsFinite(Seq) || Seq<0)return;
        if(StreamId!=Id){RvizImage=nullptr;ImageAt=-1;ImageStamp=-1;Sequence=-1;StreamId=Id;}
        if(Seq<Sequence)return;Sequence=Seq;Status=S;StatusAt=FPlatformTime::Seconds();return;
    }
    const TSharedPtr<FJsonObject>* H;const TSharedPtr<FJsonObject>* StampObject;double Stamp;
    if(!J || !J->TryGetObjectField(TEXT("header"),H) || !(*H)->TryGetObjectField(TEXT("stamp"),StampObject) || !FRedlineJson::Stamp(*StampObject,Stamp) || Stamp<=ImageStamp)return;
    TArray<uint8> Pixels;int32 W,Ht;if(!DecodeImage(J,Pixels,W,Ht))return;
    if(!RvizImage || RvizImage->GetSizeX()!=W || RvizImage->GetSizeY()!=Ht)
    {
        RvizImage=UTexture2D::CreateTransient(W,Ht,PF_B8G8R8A8);if(!RvizImage)return;RvizImage->SRGB=true;
        void* Dest=RvizImage->GetPlatformData()->Mips[0].BulkData.Lock(LOCK_READ_WRITE);
        FMemory::Memcpy(Dest,Pixels.GetData(),Pixels.Num());RvizImage->GetPlatformData()->Mips[0].BulkData.Unlock();RvizImage->UpdateResource();
    }
    else
    {
        auto* Data=static_cast<uint8*>(FMemory::Malloc(Pixels.Num()));FMemory::Memcpy(Data,Pixels.GetData(),Pixels.Num());
        auto* Region=new FUpdateTextureRegion2D(0,0,0,0,W,Ht);
        RvizImage->UpdateTextureRegions(0,1,Region,W*4,4,Data,[](uint8* Bytes,const FUpdateTextureRegion2D* Area){FMemory::Free(Bytes);delete Area;});
    }
    ImageStamp=Stamp;ImageAt=FPlatformTime::Seconds();++AcceptedFrames;
    if(AcceptedFrames%20==1)UE_LOG(LogRedlineTablet,Display,TEXT("Actual RViz frame %d %dx%d physics %.3f"),AcceptedFrames,W,Ht,Stamp);
}
bool ARedlineFieldTablet::StreamFresh()const
{
    const double Now=FPlatformTime::Seconds();bool Capture=false,Source=false;
    return Bridge && Bridge->IsConnected() && RvizImage && Status && Status->TryGetBoolField(TEXT("capture_fresh"),Capture) && Status->TryGetBoolField(TEXT("source_fresh"),Source) && Capture && Source && Now-ImageAt<2 && Now-StatusAt<2;
}
bool ARedlineFieldTablet::Open()
{
    if(!bReady || bOpen || bOwnLock)return false;for(TActorIterator<ARedlineAstronautCharacter> It(GetWorld());It;++It){Human=*It;break;}
    for(TActorIterator<ARedlineCampaignConsole> It(GetWorld());It;++It){Console=*It;break;}
    auto* A=Human.Get();if(!A || !Console.IsValid() || A->bPresentationLocked)return false;
    auto* Mesh=A->GetMesh();if(!Mesh->GetSkeletalMeshAsset())return false;
    Arms->SetSkinnedAssetAndUpdate(Mesh->GetSkeletalMeshAsset());Arms->CopyPoseFromSkeletalComponent(Mesh);
    for(int32 I=0;I<Mesh->GetNumMaterials();++I)Arms->SetMaterial(I,Mesh->GetMaterial(I));
    bOldHidden=Mesh->bHiddenInGame;bOldOwnerNoSee=Mesh->bOwnerNoSee;Mesh->SetHiddenInGame(true);
    bOldFirstPerson=A->bFirstPersonView;A->SetFirstPersonView(true);bZoom=true;
    A->bPresentationLocked=true;bOwnLock=true;A->GetCharacterMovement()->StopMovementImmediately();
    Console->bTabletOpen=true;Console->bConsoleOpen=false;bOpen=true;Shell->SetHiddenInGame(false);Screen->SetHiddenInGame(false);Arms->SetHiddenInGame(false);return true;
}
void ARedlineFieldTablet::Close(bool Immediate)
{
    bOpen=false;if(Immediate)Raise=0;
    if(!Immediate && Raise>0)return;
    if(auto* A=Human.Get();A && bOwnLock){A->bPresentationLocked=false;A->SetFirstPersonView(bOldFirstPerson);A->GetMesh()->SetHiddenInGame(bOldHidden);A->GetMesh()->SetOwnerNoSee(bOldOwnerNoSee);}
    bOwnLock=false;if(Console.IsValid())Console->bTabletOpen=false;Arms->SetHiddenInGame(true);
    if(Immediate){Shell->SetHiddenInGame(true);Screen->SetHiddenInGame(true);}
}
void ARedlineFieldTablet::SolveArm(FName UpperName,FName LowerName,FName HandName,FVector Target,FVector Pole)
{
    const FVector U=Arms->GetBoneLocation(UpperName,EBoneSpaces::ComponentSpace),L=Arms->GetBoneLocation(LowerName,EBoneSpaces::ComponentSpace),H=Arms->GetBoneLocation(HandName,EBoneSpaces::ComponentSpace);
    const double A=(L-U).Size(),B=(H-L).Size();if(A<1 || B<1)return;
    FVector D=(Target-U).GetSafeNormal();double Len=FMath::Clamp((Target-U).Size(),FMath::Abs(A-B)+.1,A+B-.1);
    const double Along=(A*A+Len*Len-B*B)/(2*Len);FVector Bend=(Pole-D*FVector::DotProduct(Pole,D)).GetSafeNormal();
    FVector Joint=U+D*Along+Bend*FMath::Sqrt(FMath::Max(0.,A*A-Along*Along));
    FQuat Q=FQuat::FindBetweenNormals((L-U).GetSafeNormal(),(Joint-U).GetSafeNormal())*Arms->GetBoneRotationByName(UpperName,EBoneSpaces::ComponentSpace).Quaternion();
    Arms->SetBoneRotationByName(UpperName,Q.Rotator(),EBoneSpaces::ComponentSpace);Arms->RefreshBoneTransforms();
    FVector NewL=Arms->GetBoneLocation(LowerName,EBoneSpaces::ComponentSpace),NewH=Arms->GetBoneLocation(HandName,EBoneSpaces::ComponentSpace);
    Q=FQuat::FindBetweenNormals((NewH-NewL).GetSafeNormal(),(Target-NewL).GetSafeNormal())*Arms->GetBoneRotationByName(LowerName,EBoneSpaces::ComponentSpace).Quaternion();Arms->SetBoneRotationByName(LowerName,Q.Rotator(),EBoneSpaces::ComponentSpace);
}
void ARedlineFieldTablet::UpdateGrip()
{
    auto* A=Human.Get();if(!A || !bOwnLock || Raise<=0)return;Arms->SetWorldTransform(A->GetMesh()->GetComponentTransform());Arms->CopyPoseFromSkeletalComponent(A->GetMesh());
    const FTransform Inverse=Arms->GetComponentTransform().Inverse();
    SolveArm(TEXT("upperarm_l"),TEXT("lowerarm_l"),TEXT("hand_l"),Inverse.TransformPosition(GetActorTransform().TransformPosition(FVector(-20,12,-4))),FVector(0,1,-1));
    SolveArm(TEXT("upperarm_r"),TEXT("lowerarm_r"),TEXT("hand_r"),Inverse.TransformPosition(GetActorTransform().TransformPosition(FVector(20,12,-4))),FVector(0,-1,-1));
    if(A->bFirstPersonView)Arms->SetBoneScaleByName(TEXT("head"),FVector::ZeroVector,EBoneSpaces::ComponentSpace);
    Arms->RefreshBoneTransforms();
}
void ARedlineFieldTablet::Tick(float Dt)
{
    Super::Tick(Dt);auto* PC=GetWorld()->GetFirstPlayerController();auto* View=GetWorld()->GetGameViewport();if(!PC || !PC->PlayerCameraManager)return;
    const bool Focus=View && View->Viewport && View->Viewport->HasFocus();
    if(Focus && PC->WasInputKeyJustPressed(EKeys::T)){if(bOpen)Close();else Open();}
    if(bOpen && (!Bridge || !Bridge->IsConnected()))Close();
    if(bOpen && Focus)
    {
        if(PC->WasInputKeyJustPressed(EKeys::Escape) || PC->WasInputKeyJustPressed(EKeys::M) || PC->WasInputKeyJustPressed(EKeys::J))Close();
        if(PC->WasInputKeyJustPressed(EKeys::Z))bZoom=!bZoom;
        if(PC->WasInputKeyJustPressed(EKeys::Tab))Page=(Page+1)%(1+ARedlineCampaignConsole::TabletPageCount());
        if(Console.IsValid())
        {
            if(Page==8)
            {
                if(PC->WasInputKeyJustPressed(EKeys::L))Console->CycleAtlasLayer();
                if(PC->WasInputKeyJustPressed(EKeys::Right))Console->CycleAtlasStation(1);
                if(PC->WasInputKeyJustPressed(EKeys::Left))Console->CycleAtlasStation(-1);
                if(PC->WasInputKeyJustPressed(EKeys::Up))Console->CycleAtlasTask(-1);
                if(PC->WasInputKeyJustPressed(EKeys::Down))Console->CycleAtlasTask(1);
            }
            if(PC->WasInputKeyJustPressed(EKeys::P))Console->StartLabAssay();
            if(Page!=8 && PC->WasInputKeyJustPressed(EKeys::Right))Console->CycleProduct(1,Page-1);
            if(Page!=8 && PC->WasInputKeyJustPressed(EKeys::Left))Console->CycleProduct(-1,Page-1);
            if(PC->WasInputKeyJustPressed(EKeys::One))Console->SendCommand(Console->TaskKind()==TEXT("decision") ? TEXT("CHOOSE_RIDGE") : TEXT("SUPPORT_PATTERN"));
            if(PC->WasInputKeyJustPressed(EKeys::Two))Console->SendCommand(Console->TaskKind()==TEXT("decision") ? TEXT("CHOOSE_HOLLOW") : TEXT("NEED_MORE_DATA"));
            if(PC->WasInputKeyJustPressed(EKeys::X))Console->SendCommand(TEXT("CANCEL"));
            if(PC->WasInputKeyJustPressed(EKeys::E))
            {if(Console->TaskKind()==TEXT("collect") || Console->TaskKind()==TEXT("xrf") || Console->TaskKind()==TEXT("cache") || Console->TaskKind()==TEXT("weather"))Close(true);Console->Interact();}
        }
    }
    Raise=FMath::FInterpConstantTo(Raise,bOpen ? 1.f : 0.f,Dt,3.f);
    if(Raise<=0){if(bOwnLock)Close(true);Shell->SetHiddenInGame(true);Screen->SetHiddenInGame(true);return;}
    const FVector Forward=PC->PlayerCameraManager->GetCameraRotation().Vector(),Right=FRotationMatrix(PC->PlayerCameraManager->GetCameraRotation()).GetUnitAxis(EAxis::Y),Up=FRotationMatrix(PC->PlayerCameraManager->GetCameraRotation()).GetUnitAxis(EAxis::Z);
    SetActorLocationAndRotation(PC->PlayerCameraManager->GetCameraLocation()+Forward*(bZoom ? 30 : 44)-Up*(7+(1-Raise)*45),FRotationMatrix::MakeFromXZ(Right,-Forward).Rotator());UpdateGrip();
    if(Display && FPlatformTime::Seconds()-LastRender>.2){LastRender=FPlatformTime::Seconds();Display->UpdateResource();}
}
void ARedlineFieldTablet::Render(UCanvas* C,int32 W,int32 H)
{
    if(!C)return;
    if(Page>0 && Console.IsValid()){Console->DrawTabletPage(C,W,H,Page-1);return;}
    FCanvasTileItem BG(FVector2D(0,0),FVector2D(W,H),RedlineConsoleTheme::Background);C->DrawItem(BG);
    auto Text=[&](FString S,float X,float Y,FLinearColor Color){FCanvasTextItem I(FVector2D(X,Y),FText::FromString(S),GEngine->GetSmallFont(),Color);I.Scale=FVector2D(1.5,1.5);C->DrawItem(I);};
    const bool Fresh=StreamFresh();Text(TEXT("ROS / Navigasyon görüntüsü"),24,15,RedlineConsoleTheme::Text);
    if(Fresh){FCanvasTileItem I(FVector2D(0,60),RvizImage->GetResource(),FVector2D(W,H-110),FLinearColor::White);C->DrawItem(I);}
    else Text(TEXT("Görüntü bekleniyor. Son kare güncel değil."),24,H*.5,RedlineConsoleTheme::Warning);
    Text(TEXT("T kapat · Tab sayfalar · Z yakınlaştır · E işlem · X iptal"),24,H-38,RedlineConsoleTheme::Secondary);
}
void ARedlineFieldTablet::EndPlay(const EEndPlayReason::Type Reason)
{Close(true);if(Bridge)Bridge->OnTopic.Remove(Handle);Super::EndPlay(Reason);}
