#include "RedlineCampaignConsole.h"
#include "RedlineConsoleTheme.h"
#include "RedlineCoords.h"
#include "RedlineOverlay.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "CanvasItem.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"

namespace MissionBoard
{
FString S(const TSharedPtr<FJsonObject>& J,const TCHAR* K){FString V;return J && J->TryGetStringField(K,V) ? V : FString();}
double N(const TSharedPtr<FJsonObject>& J,const TCHAR* K,double Default=0){double V;return J && J->TryGetNumberField(K,V) && FMath::IsFinite(V) ? V : Default;}
TSharedPtr<FJsonObject> O(const TSharedPtr<FJsonObject>& J,const TCHAR* K){const TSharedPtr<FJsonObject>* V;return J && J->TryGetObjectField(K,V) ? *V : nullptr;}
const TArray<TSharedPtr<FJsonValue>>& A(const TSharedPtr<FJsonObject>& J,const TCHAR* K){static TArray<TSharedPtr<FJsonValue>> Empty;const TArray<TSharedPtr<FJsonValue>>* V;return J && J->TryGetArrayField(K,V) ? *V : Empty;}
FString Title(FString V){FString Prefix,Rest;return V.Split(TEXT(" / "),&Prefix,&Rest) ? Rest : V;}
struct Paint
{
    UCanvas* C;float Scale;
    void Rect(float X,float Y,float W,float H,FLinearColor Colour)const{FCanvasTileItem I(FVector2D(X,Y)*Scale,FVector2D(W,H)*Scale,Colour);I.BlendMode=SE_BLEND_Translucent;C->DrawItem(I);}
    void Text(FString V,float X,float Y,float Size=1.5,FLinearColor Colour=RedlineConsoleTheme::Text)const{FCanvasTextItem I(FVector2D(X,Y)*Scale,FText::FromString(V),GEngine->GetSmallFont(),Colour);I.Scale=FVector2D(Size*Scale,Size*Scale);C->DrawItem(I);}
    float Wrap(FString V,float X,float Y,float Width,float Size,int32 MaxLines,FLinearColor Colour=RedlineConsoleTheme::Text)const
    {
        TArray<FString> Words;V.ParseIntoArrayWS(Words);FString Row;int32 Line=0;
        for(const auto& Word:Words){FString Try=Row.IsEmpty() ? Word : Row+TEXT(" ")+Word;float W,H;C->StrLen(GEngine->GetSmallFont(),Try,W,H);
            if(W*Size>Width && !Row.IsEmpty()){Text(Row,X,Y+Line*Size*15,Size,Colour);Row=Word;if(++Line>=MaxLines)return Y+Line*Size*15;}else Row=Try;}
        if(!Row.IsEmpty()){Text(Row,X,Y+Line*Size*15,Size,Colour);++Line;}return Y+Line*Size*15;
    }
};
}

void ARedlineCampaignConsole::DrawMissionBoard(UCanvas* C,int32 Width,int32 Height)
{
    using namespace RedlineConsoleTheme;using namespace MissionBoard;
    const float Scale=FMath::Min(Width/1280.f,Height/720.f);Paint D{C,Scale};D.Rect(0,0,1280,720,Background);
    D.Text(TEXT("REDLINE"),40,28,1.3,Secondary);D.Text(TEXT("Boxwork / Sefer kaydı"),184,27,1.3,Secondary);
    D.Text(Fresh() ? TEXT("BAĞLI") : TEXT("BAĞLANTI BEKLENİYOR"),1024,28,1.1,Fresh() ? Complete : Warning);D.Rect(40,68,1200,1,Rule);
    const auto CurrentTask=Task();const int32 Current=N(State,TEXT("task_index")),Total=N(State,TEXT("task_count"));
    if(!State){D.Text(TEXT("Görev kaydı bekleniyor"),40,144,2.4);D.Text(TEXT("Bağlantı kurulduğunda etkin adım ve yer bilgisi burada görünür."),40,200,1.5,Secondary);return;}
    const bool Done=Current>=Total,Busy=IsBusy();
    D.Text(Done ? TEXT("EVA TAMAMLANDI") : FString::Printf(TEXT("ETKİN ADIM   %02d / %02d"),Current+1,Total),40,104,1.2,Done ? Complete : Copper);
    D.Wrap(Done ? TEXT("Kayıt kapandı.") : Title(TaskTitle()),40,142,750,2.8,2);
    D.Wrap(TaskInstruction(),40,226,750,1.55,3,Secondary);
    const auto Presentation=O(CurrentTask,TEXT("presentation"));const FString Kind=TaskKind(),Actor=S(CurrentTask,TEXT("actor"));
    bool Enabled=false;const bool HasGate=Presentation && Presentation->TryGetBoolField(TEXT("enabled"),Enabled);const FString Blocked=S(Presentation,TEXT("blocked_reason"));
    const bool Remote=Actor==TEXT("rover_1");double Distance=-1;
    if(auto* PC=GetWorld()->GetFirstPlayerController())if(APawn* Pawn=PC->GetPawn())Distance=FVector::Dist2D(URedlineCoords::UeToRosLocation(Pawn->GetActorLocation()),TaskMap());
    const bool Arrived=Distance>=0 && Distance<=InteractionRadius();
    D.Rect(40,340,752,136,Surface);
    FString Status=Done ? TEXT("Ürünler ve kararlar kaydedildi") : !Fresh() ? TEXT("Durum eski. İşlem gönderilemiyor.") : Blocked==TEXT("sep_alert") ? TEXT("Alarm · Bilim beklemede") : Busy ? TEXT("İşlem sürüyor") : Blocked==TEXT("crew_pose_stale") ? TEXT("Konum doğrulaması bekleniyor") : Remote && Enabled ? TEXT("Uzaktan işlem hazır") : Remote ? TEXT("Robot işlemi beklemede") : Arrived ? TEXT("Görev yerindesin") : TEXT("Görev yerine ilerle");
    D.Text(Status,60,360,1.8,Busy ? Copper : Text);
    D.Text(Remote ? Actor+TEXT("  /  ROS otonom kontrol") : Distance<0 ? TEXT("Konum bekleniyor") : FString::Printf(TEXT("%s  /  %.0f m"),*S(CurrentTask,TEXT("target_id")),Distance),60,400,1.3,Secondary);
    if(Busy){D.Rect(60,444,712,3,Rule);D.Rect(60,444,712*N(State,TEXT("progress")),3,Copper);D.Text(FString::Printf(TEXT("%.0f%%"),100*N(State,TEXT("progress"))),700,360,1.4,Copper);}
    else if(!Done)D.Text(!Fresh() ? TEXT("Bağlantının yenilenmesini bekle") : HasGate && !Enabled ? Blocked==TEXT("approach_site") ? TEXT("Varıştan sonra E ile başlat") : TEXT("ROS onayını bekle") : Kind==TEXT("decision") ? TEXT("1  Sırt rotası     2  Çukur rotası") : Kind==TEXT("assessment") ? TEXT("1  Örüntü destekleniyor     2  Ek veri gerekli") : (Remote || Arrived) ? TEXT("E  İşlemi başlat") : TEXT("Varıştan sonra E ile başlat"),60,438,1.25,Fresh() ? Text : Secondary);
    if(!LastCommandMessage.IsEmpty())D.Wrap(LastCommandMessage,40,504,752,1.2,2,Warning);
    D.Text(TEXT("SONRAKİ ADIMLAR"),848,104,1.1,Secondary);
    const auto& Tasks=A(State,TEXT("tasks"));const int32 First=FMath::Max(0,FMath::Min(Current,Tasks.Num()-5));
    for(int32 I=First;I<FMath::Min(Tasks.Num(),First+5);++I)
    {
        const auto T=Tasks[I]->AsObject();const float Y=146+(I-First)*84;const bool Active=I==Current,CompleteTask=I<Current;
        D.Text(FString::Printf(TEXT("%02d"),I+1),848,Y,1.4,Active ? Copper : Secondary);
        D.Wrap(Title(S(T,TEXT("title"))),892,Y,330,1.45,2,Active ? Text : Secondary);
        D.Text(CompleteTask ? TEXT("Kaydedildi") : Active ? Busy ? TEXT("Yürütülüyor") : TEXT("Etkin") : TEXT("Önceki sonucun ardından açılır"),892,Y+43,1.05,CompleteTask ? Complete : Active ? Copper : Muted);
    }
    D.Rect(40,584,1200,1,Rule);ARedlineOverlay* Overlay=nullptr;for(TActorIterator<ARedlineOverlay> It(GetWorld());It;++It){Overlay=*It;break;}
    D.Text(TEXT("GÖREV SÜRESİ"),40,608,1.05,Secondary);D.Text(FString::Printf(TEXT("%.1f dk"),N(State,TEXT("pet_s"))/60.),40,632,1.9);
    D.Text(TEXT("DÖNÜŞ PAYI"),264,608,1.05,Secondary);D.Text(Overlay && Overlay->Fresh(Overlay->LineReceipt) && Overlay->Line.bHasMargin ? FString::Printf(TEXT("%.1f dk"),Overlay->Line.MarginMinutes) : TEXT("—"),264,632,1.9);
    D.Text(TEXT("BİLİM KAYDI"),520,608,1.05,Secondary);D.Text(FString::Printf(TEXT("%d ürün  /  %d numune"),A(State,TEXT("products")).Num(),A(State,TEXT("samples")).Num()),520,638,1.3);
    D.Text(TEXT("Tab  Bilim ve harita"),984,610,1.1,Secondary);D.Text(TEXT("M / Esc  Kapat"),984,642,1.1,Secondary);
    if(!Fresh())D.Text(TEXT("GÖRÜNEN SON KAYIT · GÜNCEL DEĞİL"),40,690,1.05,Warning);
}

void ARedlineCampaignConsole::DrawMissionPrompt(UCanvas* C)
{
    if(!C || bConsoleOpen || bTabletOpen)return;using namespace MissionBoard;using namespace RedlineConsoleTheme;
    const float Scale=FMath::Min(C->SizeX/1280.f,C->SizeY/720.f);Paint D{C,Scale};const float Y=C->SizeY/Scale-148;
    const bool Remote=S(Task(),TEXT("actor"))==TEXT("rover_1");double Distance=-1;
    const auto Gate=O(Task(),TEXT("presentation"));bool Enabled=false;if(Gate)Gate->TryGetBoolField(TEXT("enabled"),Enabled);
    if(auto* PC=GetWorld()->GetFirstPlayerController())if(APawn* Pawn=PC->GetPawn())Distance=FVector::Dist2D(URedlineCoords::UeToRosLocation(Pawn->GetActorLocation()),TaskMap());
    const bool Arrived=Distance>=0 && Distance<=InteractionRadius();D.Rect(24,Y,656,94,Background);
    D.Text(Fresh() ? Title(TaskTitle()) : TEXT("Görev verisi bekleniyor"),40,Y+12,1.55);
    FString Hint=!Fresh() ? TEXT("Bağlantının yenilenmesini bekle") : IsBusy() ? TEXT("İşlem sürüyor · X iptal iste") : Remote ? TEXT("E  Uzaktan başlat") : Arrived ? TEXT("E  İşlemi başlat") : FString::Printf(TEXT("%s · %.0f m · Hedefe ilerle"),*S(Task(),TEXT("target_id")),Distance);
    if(Gate && !Enabled && S(Gate,TEXT("blocked_reason"))!=TEXT("approach_site") && !IsBusy())Hint=S(Gate,TEXT("blocked_reason"))==TEXT("sep_alert") ? TEXT("Alarm · Bilim beklemede") : TEXT("ROS onayı bekleniyor");
    else if(TaskKind()==TEXT("decision") || TaskKind()==TEXT("assessment"))Hint=TEXT("M  Verileri aç ve karar ver");
    D.Text(Hint,40,Y+48,1.15,IsBusy() ? Copper : Secondary);
    if(IsBusy()){D.Rect(40,Y+80,624,2,Rule);D.Rect(40,Y+80,624*N(State,TEXT("progress")),2,Copper);}
    if(!LastCommandMessage.IsEmpty() && MessageAgeSec()<6)D.Wrap(LastCommandMessage,40,Y-48,650,1.05,2,Warning);
}
