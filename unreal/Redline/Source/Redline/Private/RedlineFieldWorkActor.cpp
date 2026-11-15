#include "RedlineFieldWorkActor.h"
#include "RedlineCampaignConsole.h"
#include "RedlineAstronautCharacter.h"
#include "RedlineSampleInteraction.h"
#include "RedlineCoords.h"
#include "RedlineConsoleTheme.h"
#include "Components/CapsuleComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "CanvasItem.h"
#include "InputCoreTypes.h"
#include "Dom/JsonObject.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

namespace FieldWorkActor
{
FString S(const TSharedPtr<FJsonObject>& J,const TCHAR* K){FString V;return J && J->TryGetStringField(K,V) ? V : FString();}
double N(const TSharedPtr<FJsonObject>& J,const TCHAR* K,double Default=0){double V;return J && J->TryGetNumberField(K,V) && FMath::IsFinite(V) ? V : Default;}
TSharedPtr<FJsonObject> O(const TSharedPtr<FJsonObject>& J,const TCHAR* K){const TSharedPtr<FJsonObject>* V;return J && J->TryGetObjectField(K,V) ? *V : nullptr;}
bool B(const TSharedPtr<FJsonObject>& J,const TCHAR* K){bool V=false;return J && J->TryGetBoolField(K,V) && V;}
bool Recorded(const TSharedPtr<FJsonObject>& J,const FString& Id)
{const TArray<TSharedPtr<FJsonValue>>* Values;if(!J || !J->TryGetArrayField(TEXT("completed"),Values))return false;for(const auto& Value:*Values){FString V;if(Value && Value->TryGetString(V) && V==Id)return true;}return false;}
}

ARedlineFieldWorkActor::ARedlineFieldWorkActor()
{PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickGroup=TG_PostUpdateWork;SetActorEnableCollision(false);}

bool ARedlineFieldWorkActor::BeginWork(ARedlineCampaignConsole* Campaign)
{
    using namespace FieldWorkActor;
    if(bWorking || !IsValid(Campaign) || !Campaign->Fresh() || Campaign->IsBusy() || Campaign->bLocalWorkOwnsPresentation)return false;
    auto* PC=GetWorld()->GetFirstPlayerController();auto* A=PC ? Cast<ARedlineAstronautCharacter>(PC->GetPawn()) : nullptr;
    if(!A || A->bPresentationLocked)return false;
    const FString Kind=Campaign->TaskKind();FRedlineFieldWork Candidate;if(!Candidate.Begin(Kind))return false;
    auto Task=Campaign->Task();auto Presentation=O(Task,TEXT("presentation"));
    if(S(Task,TEXT("actor"))!=TEXT("EV1") || S(Presentation,TEXT("state"))!=TEXT("active") || !B(Presentation,TEXT("enabled")) || B(Campaign->State,TEXT("sep_alert")))
    {Campaign->Notify(TEXT("Bu saha işlemi henüz açık değil; güncel görevi kontrol et."));return false;}
    const FVector Here=URedlineCoords::UeToRosLocation(A->GetActorLocation());FVector Target=Campaign->TaskMap();
    const double Radius=Campaign->InteractionRadius();
    if(!FMath::IsFinite(Radius) || Radius<=0 || Target.ContainsNaN() || FVector::Dist2D(Here,Target)>FMath::Min(Radius,1.25))
    {Campaign->Notify(TEXT("El işlemi için hedefin 1,25 m yakınına gel."));return false;}
    const FString NewRun=S(Campaign->State,TEXT("run_id")),NewTask=S(Task,TEXT("id"));
    if(NewRun.IsEmpty() || NewRun.Len()>100 || NewTask.IsEmpty() || NewTask.Len()>96)return false;
    // Query actual near-foot surface/bench, ignoring EV1's own capsule. Never
    // substitute a fixed height or move the human to meet a work target.
    const double HalfHeight=A->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    Target.Z=URedlineCoords::UeToRosLocation(A->GetActorLocation()-FVector(0,0,HalfHeight)).Z+.25;
    FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(RedlineManualWorkSurface),true,this);Query.AddIgnoredActor(A);Query.AddIgnoredActor(Campaign);
    if(Pose)Query.AddIgnoredActor(Pose);
    if(!GetWorld()->LineTraceSingleByChannel(Hit,URedlineCoords::RosToUeLocation(Target+FVector(0,0,2)),URedlineCoords::RosToUeLocation(Target-FVector(0,0,2)),ECC_Visibility,Query) || !Hit.bBlockingHit || Hit.ImpactPoint.ContainsNaN())
    {Campaign->Notify(TEXT("Gerçek çalışma yüzeyi bulunamadı; hedefe yaklaş."));return false;}
    WorkMap=URedlineCoords::UeToRosLocation(Hit.ImpactPoint);WorkWorld=Hit.ImpactPoint;
    if(!Pose)Pose=GetWorld()->SpawnActor<ARedlineSampleInteraction>();if(!Pose)return false;
    Pose->bUseInspectionCamera=true;Pose->bUseActualWorkPoint=true;
    if(!Pose->BeginInteraction(A,WorkMap,Kind))return false;
    Console=Campaign;Human=A;Work=MoveTemp(Candidate);RunId=NewRun;TaskId=NewTask;OriginalTaskIndex=int32(N(Campaign->State,TEXT("task_index"),-1));
    OperationId.Empty();bWorking=true;bDispatched=false;bSawRunning=false;bAligned=false;DispatchedAt=WaitStarted=-1;CameraYaw=CameraPitch=0;
    Campaign->bLocalWorkOwnsPresentation=true;Campaign->bConsoleOpen=false;
    if(Pose->InspectionCamera)
    {InitialCamera=(WorkWorld-Pose->InspectionCamera->GetComponentLocation()).Rotation();Pose->InspectionCamera->SetWorldRotation(InitialCamera);}
    Campaign->Notify(TEXT("El işlemi başladı: hedefe bak ve ekrandaki fare/E adımlarını uygula."));return true;
}

bool ARedlineFieldWorkActor::Focused() const
{auto* View=GetWorld() ? GetWorld()->GetGameViewport() : nullptr;return View && View->Viewport && View->Viewport->HasFocus();}

void ARedlineFieldWorkActor::Finish(bool Success,const FString& Message)
{
    if(!bWorking)return;bWorking=false;Work.Cancel();
    if(Pose && Pose->IsInteracting())Pose->EndInteraction(Success);
    if(auto* C=Console.Get()){C->bLocalWorkOwnsPresentation=false;if(!Message.IsEmpty())C->Notify(Message);}
    Console.Reset();Human.Reset();bDispatched=false;bSawRunning=false;
}

void ARedlineFieldWorkActor::CancelWork()
{
    if(!bWorking)return;
    if(auto* C=Console.Get();C && bDispatched && C->Fresh() && C->IsBusy())C->SendCommand(TEXT("CANCEL"));
    Finish(false,bDispatched ? TEXT("İşlem görünümü kapandı. İptal/ürün sonucunu ROS kaydından kontrol et.") : TEXT("El hazırlığı iptal edildi; bilim işlemi başlatılmadı."));
}

void ARedlineFieldWorkActor::Tick(float Delta)
{
    Super::Tick(Delta);if(!bWorking)return;using namespace FieldWorkActor;
    auto* C=Console.Get();auto* A=Human.Get();auto* PC=GetWorld()->GetFirstPlayerController();
    if(!C || !A || !PC || !Pose || !Pose->IsInteracting()){Finish(false,TEXT("Saha işlemi görünümü durdu; görev kaydını kontrol et."));return;}
    if(!C->Fresh()){Finish(false,bDispatched ? TEXT("Bağlantı eski: işlem sonucu bilinmiyor. Komut tekrar gönderilmedi.") : TEXT("Bağlantı eski; el hazırlığı durdu."));return;}
    if(S(C->State,TEXT("run_id"))!=RunId){Finish(false,TEXT("Görev oturumu değişti; saha işlemi kapandı."));return;}
    const FString CurrentId=S(C->Task(),TEXT("id"));const int32 CurrentIndex=int32(N(C->State,TEXT("task_index"),-1));
    if(CurrentId!=TaskId || CurrentIndex!=OriginalTaskIndex)
    {
        const bool Success=bDispatched && CurrentIndex>OriginalTaskIndex && Recorded(C->State,TaskId);
        Finish(Success,Success ? TEXT("İşlem ROS ürünü ve görev kaydıyla tamamlandı.") : TEXT("Etkin görev değişti; yerel hazırlık kapandı."));return;
    }
    if(B(C->State,TEXT("sep_alert"))){CancelWork();return;}
    const bool Focus=Focused();
    if(Focus && (PC->WasInputKeyJustPressed(EKeys::Escape) || PC->WasInputKeyJustPressed(EKeys::X))){CancelWork();return;}
    const double Now=FPlatformTime::Seconds();
    if(bDispatched)
    {
        const FString State=S(C->State,TEXT("state"));const FString Request=S(C->State,TEXT("operation_id"));
        if(C->IsBusy())
        {
            if(OperationId.IsEmpty())OperationId=Request;
            if(Request.IsEmpty() || Request!=OperationId){Finish(false,TEXT("Başka bir işlem etkin; sonuçları görev kaydından kontrol et."));return;}
            bSawRunning=true;Pose->SetProgress(.75f+.25f*float(FMath::Clamp(N(C->State,TEXT("progress")),0.,1.)),S(C->State,TEXT("operation_phase")));return;
        }
        if(State==TEXT("failed")){Finish(false,TEXT("ROS işlemi tamamlayamadı. Görev açık; hata mesajını kontrol et."));return;}
        // Acceptance or time alone is never presented as success.
        if(Now-DispatchedAt>5 && !bSawRunning){Finish(false,TEXT("Komutun yürütme kaydı gelmedi. Durumu kontrol et; otomatik tekrar yok."));return;}
        if(bSawRunning && Now-DispatchedAt>900){Finish(false,TEXT("İşlem sonucu bekleme süresi doldu. Sonuç bilinmiyor; ROS kaydını kontrol et."));return;}
        return;
    }
    if(C->IsBusy()){Finish(false,TEXT("Başka bir ROS işlemi başladı; el hazırlığı kapandı."));return;}
    if(!B(O(C->Task(),TEXT("presentation")),TEXT("enabled"))){Finish(false,TEXT("Saha işlemi artık açık değil; güncel görevi kontrol et."));return;}
    if(FVector::Dist2D(URedlineCoords::UeToRosLocation(A->GetActorLocation()),WorkMap)>FMath::Min(C->InteractionRadius(),1.25))
    {Finish(false,TEXT("Çalışma alanından uzaklaşıldı; hazırlık iptal edildi."));return;}
    if(Focus && Pose->InspectionCamera)
    {
        float MouseX=0,MouseY=0;PC->GetInputMouseDelta(MouseX,MouseY);
        if(FMath::IsFinite(MouseX) && FMath::IsFinite(MouseY))
        {CameraYaw=FMath::Clamp(CameraYaw+FMath::Clamp(double(MouseX),-30.,30.)*.18,-25.,25.);CameraPitch=FMath::Clamp(CameraPitch-FMath::Clamp(double(MouseY),-30.,30.)*.18,-25.,25.);}
        Pose->InspectionCamera->SetWorldRotation(FRotator(InitialCamera.Pitch+CameraPitch,InitialCamera.Yaw+CameraYaw,InitialCamera.Roll));
    }
    if(Pose->InspectionCamera)
    {const FVector Direction=(WorkWorld-Pose->InspectionCamera->GetComponentLocation()).GetSafeNormal();bAligned=FVector::DotProduct(Pose->InspectionCamera->GetForwardVector(),Direction)>.90;}
    else bAligned=false;
    uint8 Buttons=0;if(Focus){if(PC->WasInputKeyJustPressed(EKeys::LeftMouseButton))LeftPulse=Now+.12;if(PC->WasInputKeyJustPressed(EKeys::RightMouseButton))RightPulse=Now+.12;if(PC->WasInputKeyJustPressed(EKeys::E))InteractPulse=Now+.12;if(PC->IsInputKeyDown(EKeys::LeftMouseButton) || Now<LeftPulse)Buttons|=1;if(PC->IsInputKeyDown(EKeys::RightMouseButton) || Now<RightPulse)Buttons|=2;if(PC->IsInputKeyDown(EKeys::E) || Now<InteractPulse)Buttons|=4;}
    const int32 PreviousStage=Work.StageIndex();
    Work.Tick(Delta,Buttons,bAligned,Focus,Focus && PC->WasInputKeyJustPressed(EKeys::E));Pose->SetProgress(.75f*float(Work.Progress()),Work.PhaseText());
    if(Work.StageIndex()!=PreviousStage)
        if(auto* Cue=LoadObject<USoundBase>(nullptr,TEXT("/Game/Prologue/Audio/SFX_ready_chime.SFX_ready_chime")))UGameplayStatics::PlaySoundAtLocation(this,Cue,WorkWorld,.28f,1.1f);
    if(Work.ConsumePrepared())
    {
        bDispatched=true;DispatchedAt=Now;Pose->SetProgress(.75f,TEXT("ROS işlemi bekleniyor"));C->SendCommand(TEXT("START"));
    }
}

void ARedlineFieldWorkActor::DrawWork(UCanvas* Canvas)
{
    if(!bWorking || !Canvas)return;using namespace RedlineConsoleTheme;
    const float Scale=FMath::Min(Canvas->SizeX/1280.f,Canvas->SizeY/720.f);const float X=40*Scale,Y=Canvas->SizeY-174*Scale,W=1200*Scale;
    auto Rect=[&](float PX,float PY,float Width,float Height,FLinearColor Color){FCanvasTileItem Item(FVector2D(PX,PY),FVector2D(Width,Height),Color);Item.BlendMode=SE_BLEND_Translucent;Canvas->DrawItem(Item);};
    auto TextAt=[&](const FString& Value,float PX,float PY,float Size,FLinearColor Color){FCanvasTextItem Item(FVector2D(PX,PY),FText::FromString(Value),GEngine->GetSmallFont(),Color);Item.Scale=FVector2D(Size*Scale);Canvas->DrawItem(Item);};
    Rect(X,Y,W,144*Scale,FLinearColor(.012,.011,.009,.94));
    TextAt(bDispatched ? TEXT("ÖLÇÜM / KAYIT · ROS") : TEXT("EL İŞLEMİ · SAHA HAZIRLIĞI"),X+20*Scale,Y+14*Scale,1.1,Secondary);
    const auto* C=Console.Get();const double Progress=bDispatched && C ? FieldWorkActor::N(C->State,TEXT("progress")) : Work.Progress();
    TextAt(bDispatched ? Pose ? Pose->GetInteractionPhase() : TEXT("Sonuç bekleniyor") : Work.PhaseText(),X+20*Scale,Y+43*Scale,1.7,Text);
    TextAt(bDispatched ? TEXT("Ürün ve numune kaydı gelmeden görev tamamlanmaz.  X / Esc: görünümü kapat ve iptal iste") : Work.Prompt()+TEXT("   ·   X / Esc: iptal"),X+20*Scale,Y+83*Scale,1.1,Secondary);
    Rect(X+20*Scale,Y+121*Scale,W-40*Scale,3*Scale,Rule);Rect(X+20*Scale,Y+121*Scale,(W-40*Scale)*FMath::Clamp(Progress,0.,1.),3*Scale,Copper);
    FVector2D Screen;auto* PC=GetWorld()->GetFirstPlayerController();
    if(!bDispatched && PC && PC->ProjectWorldLocationToScreen(WorkWorld,Screen))
    {const FLinearColor Color=bAligned ? Text : Warning;const float R=8*Scale;Rect(Screen.X-R,Screen.Y-1,R*2,2,Color);Rect(Screen.X-1,Screen.Y-R,2,R*2,Color);}
}

void ARedlineFieldWorkActor::EndPlay(const EEndPlayReason::Type Reason)
{
    // Ending presentation never invents an action cancellation/result.
    Finish(false,FString());if(Pose){Pose->Destroy();Pose=nullptr;}Super::EndPlay(Reason);
}
