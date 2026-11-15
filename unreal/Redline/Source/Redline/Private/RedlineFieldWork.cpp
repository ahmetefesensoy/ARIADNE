#include "RedlineFieldWork.h"

bool FRedlineFieldWork::Begin(const FString& InKind)
{
    if(IsActive() || IsPrepared() || (InKind!=TEXT("collect") && InKind!=TEXT("xrf") && InKind!=TEXT("weather") && InKind!=TEXT("cache")))return false;
    WorkKind=InKind;Stage=0;HeldSeconds=0;bInteractArmed=false;bPreparedConsumed=false;bLastAligned=false;bLastFocused=true;
    CurrentState=ERedlineFieldWorkState::Active;return true;
}
int32 FRedlineFieldWork::StageCount() const{return WorkKind==TEXT("xrf") ? 2 : 3;}
double FRedlineFieldWork::HoldDuration() const
{
    if(WorkKind==TEXT("collect"))return Stage==0 ? 1.5 : Stage==1 ? 1.2 : .8;
    if(WorkKind==TEXT("xrf"))return Stage==0 ? 1. : 0.;
    if(WorkKind==TEXT("weather"))return Stage==0 ? 1.2 : Stage==1 ? 1. : 0.;
    if(WorkKind==TEXT("cache"))return Stage==0 ? 1. : Stage==1 ? .8 : 0.;
    return 0.;
}
uint8 FRedlineFieldWork::RequiredButton() const
{
    if(Stage==0)return uint8(ERedlineFieldWorkButtons::Left);
    if(WorkKind==TEXT("xrf") || Stage==2)return uint8(ERedlineFieldWorkButtons::Interact);
    return uint8(ERedlineFieldWorkButtons::Right);
}
bool FRedlineFieldWork::IsConfirmation() const{return HoldDuration()==0.;}
void FRedlineFieldWork::Advance()
{
    ++Stage;HeldSeconds=0;bInteractArmed=false;
    if(Stage>=StageCount())CurrentState=ERedlineFieldWorkState::Prepared;
}
void FRedlineFieldWork::Tick(double Dt,uint8 Buttons,bool bAligned,bool bFocused,bool bEPressed)
{
    // Large stalls are not preparation time; never catch up from wall time.
    if(!IsActive() || !FMath::IsFinite(Dt) || Dt<=0 || Dt>.1 || (Buttons & ~uint8(7))!=0)return;
    bLastAligned=bAligned;bLastFocused=bFocused;
    if(!bAligned || !bFocused){bInteractArmed=false;return;}
    const uint8 E=uint8(ERedlineFieldWorkButtons::Interact);
    if((Buttons&E)==0)bInteractArmed=true;
    const uint8 Required=RequiredButton();
    // Require exactly the intended button. Holding every button cannot skip a
    // work sequence, and a stage change consumes no leftover time/input.
    if(Buttons!=Required || (Required==E && !bInteractArmed))return;
    if(IsConfirmation())
    {
        if(bEPressed)Advance();
        return;
    }
    HeldSeconds=FMath::Min(HoldDuration(),HeldSeconds+Dt);
    if(HeldSeconds+1e-9>=HoldDuration())Advance();
}
void FRedlineFieldWork::Cancel()
{
    if(CurrentState==ERedlineFieldWorkState::Idle || CurrentState==ERedlineFieldWorkState::Cancelled)return;
    CurrentState=ERedlineFieldWorkState::Cancelled;HeldSeconds=0;bInteractArmed=false;
}
bool FRedlineFieldWork::ConsumePrepared()
{if(!IsPrepared() || bPreparedConsumed)return false;bPreparedConsumed=true;return true;}
double FRedlineFieldWork::StageProgress() const
{
    if(IsPrepared())return 1.;if(!IsActive() || HoldDuration()<=0)return 0.;
    return FMath::Clamp(HeldSeconds/HoldDuration(),0.,1.);
}
double FRedlineFieldWork::Progress() const
{return IsPrepared() ? 1. : IsActive() ? FMath::Clamp((Stage+StageProgress())/StageCount(),0.,1.) : 0.;}
FString FRedlineFieldWork::PhaseText() const
{
    if(CurrentState==ERedlineFieldWorkState::Idle)return TEXT("Saha işlemi bekleniyor");
    if(CurrentState==ERedlineFieldWorkState::Cancelled)return TEXT("Hazırlık iptal edildi");
    if(IsPrepared())return TEXT("Hazırlık tamam · ROS işlemi bekleniyor");
    if(!bLastFocused)return TEXT("Oyun odağı bekleniyor");
    if(!bLastAligned)return TEXT("Çalışma alanına hizalan");
    if(WorkKind==TEXT("collect"))return Stage==0 ? TEXT("Yüzeyden numuneyi al") : Stage==1 ? TEXT("Numuneyi tüpe aktar") : TEXT("Tüpü mühürle");
    if(WorkKind==TEXT("xrf"))return Stage==0 ? TEXT("Aleti yüzeye hizala ve temas ettir") : TEXT("Ölçüm temasını onayla");
    if(WorkKind==TEXT("weather"))return Stage==0 ? TEXT("İstasyon tabanını yerleştir") : Stage==1 ? TEXT("İstasyon direğini aç") : TEXT("İstasyon yerleşimini onayla");
    return Stage==0 ? TEXT("Numune kabını yuvaya yerleştir") : Stage==1 ? TEXT("Kabı yuvaya kilitle") : TEXT("Teslim kaydını onayla");
}
FString FRedlineFieldWork::Prompt() const
{
    if(!IsActive())return IsPrepared() ? TEXT("Bu hazırlık görev sonucu değildir; ROS kaydını bekle.") : FString();
    if(!bLastFocused)return TEXT("Hazırlığa devam etmek için oyuna dön.");
    if(!bLastAligned)return TEXT("Hedefe yaklaş ve çalışma alanına bak.");
    const uint8 Button=RequiredButton();
    if(Button==uint8(ERedlineFieldWorkButtons::Left))return TEXT("Sol fareyi basılı tut · Bırakırsan ilerleme korunur");
    if(Button==uint8(ERedlineFieldWorkButtons::Right))return TEXT("Sağ fareyi basılı tut · Bırakırsan ilerleme korunur");
    if(!bInteractArmed)return TEXT("E tuşunu bırak, sonra yeniden bas.");
    return IsConfirmation() ? TEXT("E · Onayla") : TEXT("E tuşunu basılı tut · Tüpü mühürle");
}
