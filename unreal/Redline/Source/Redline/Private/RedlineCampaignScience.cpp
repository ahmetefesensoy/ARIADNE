#include "RedlineCampaignConsole.h"
#include "RedlineTypes.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "CanvasItem.h"
#include "Dom/JsonObject.h"
#include "RedlineBridgeSubsystem.h"
#include "RedlineCoords.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Engine/Texture2D.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Engine/World.h"
#include "RedlineConsoleTheme.h"
namespace TabletScience
{
FString S(const TSharedPtr<FJsonObject>& J,const TCHAR* K){FString V;return J && J->TryGetStringField(K,V) ? V : TEXT("");}
double N(const TSharedPtr<FJsonObject>& J,const TCHAR* K,double Default=0){double V;return J && J->TryGetNumberField(K,V) && FMath::IsFinite(V) ? V : Default;}
TSharedPtr<FJsonObject> O(const TSharedPtr<FJsonObject>& J,const TCHAR* K){const TSharedPtr<FJsonObject>* P;return J && J->TryGetObjectField(K,P) ? *P : nullptr;}
const TArray<TSharedPtr<FJsonValue>>& A(const TSharedPtr<FJsonObject>& J,const TCHAR* K){static TArray<TSharedPtr<FJsonValue>> Empty;const TArray<TSharedPtr<FJsonValue>>* V;return J && J->TryGetArrayField(K,V) ? *V : Empty;}
bool Numbers(const TArray<TSharedPtr<FJsonValue>>& V,int32 Count,double Lo,double Hi){if(V.Num()!=Count)return false;for(auto X:V){double D;if(!X || !X->TryGetNumber(D) || !FMath::IsFinite(D) || D<Lo || D>Hi)return false;}return true;}
}
FString ARedlineCampaignConsole::PageTitle(int32 I)
{const TCHAR* Titles[]={TEXT("GÖREVLER"),TEXT("BİLİM / NUMUNE"),TEXT("ROBOTLAR"),TEXT("ÇEVRE"),TEXT("DRONE HARİTALAMA"),TEXT("DAN / SONDAJ"),TEXT("LABORATUVAR / pH"),TEXT("SAHA HARİTASI")};return Titles[FMath::Clamp(I,0,PageCount-1)];}
void ARedlineCampaignConsole::CyclePage(int32 D){Page=(Page+D+PageCount)%PageCount;}
void ARedlineCampaignConsole::StartLabAssay()
{
    using namespace TabletScience;if(!Fresh() || !Bridge)return;
    FString SampleId;for(auto V:A(State,TEXT("samples"))){auto Sample=V->AsObject();if(N(Sample,TEXT("state"))==7 && !S(Sample,TEXT("container_id")).IsEmpty()){SampleId=S(Sample,TEXT("sample_id"));break;}}
    if(SampleId.IsEmpty()){LabMessage=TEXT("Önce numuneyi laboratuvara teslim et.");return;}
    auto Args=MakeShared<FJsonObject>();const FString Id=FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphens);
    Args->SetStringField(TEXT("request_id"),Id);Args->SetStringField(TEXT("sample_id"),SampleId);Args->SetStringField(TEXT("method"),TEXT("WCL_SCENARIO"));Args->SetNumberField(TEXT("integration_s"),120);
    TWeakObjectPtr<ARedlineCampaignConsole> Weak(this);FString Error;
    Bridge->DispatchMissionCommand(Id,TEXT("/redline/science/analyze_sample"),TEXT("redline_msgs/srv/AnalyzeSample"),Args,{TEXT("/redline/campaign/state")},
        [Weak](bool OK,const TSharedPtr<FJsonObject>& Values,const FString&){if(auto* Self=Weak.Get())Self->LabMessage=OK ? S(Values,TEXT("reason")) : TEXT("Lab bağlantısı yok; sonucu kontrol et.");},Error);
    if(!Error.IsEmpty())LabMessage=Error;
}
bool ARedlineCampaignConsole::IsPHProduct(const TSharedPtr<FJsonObject>& P)
{using namespace TabletScience;const auto Summary=O(P,TEXT("summary"));return S(P,TEXT("instrument"))==TEXT("WCL_SCENARIO") && S(Summary,TEXT("unit"))==TEXT("pH");}
bool ARedlineCampaignConsole::ValidateScienceSummary(const TSharedPtr<FJsonObject>& J,const FString& Instrument)
{
    using namespace TabletScience;if(!J)return false;const auto& V=A(J,TEXT("values"));const auto& Sig=A(J,TEXT("sigma"));const auto& Labels=A(J,TEXT("labels"));
    if(V.Num()>64 || !Numbers(V,V.Num(),-1e6,1e6) || !Numbers(Sig,V.Num(),0,1e6) || Labels.Num()!=V.Num() || S(J,TEXT("unit")).Len()>128)return false;
    for(auto L:Labels){FString Value;if(!L || !L->TryGetString(Value) || Value.Len()>128)return false;}
    if(Instrument==TEXT("WCL_SCENARIO") && (S(J,TEXT("unit"))!=TEXT("pH") || !Numbers(V,V.Num(),0,14)))return false;
    auto G=O(J,TEXT("posterior_grid"));if(G){const int32 W=N(G,TEXT("width")),H=N(G,TEXT("height"));if(W<2 || H<2 || W>33 || H>33 || !Numbers(A(G,TEXT("values")),W*H,-100,100) || !Numbers(A(G,TEXT("sigma")),W*H,0,100))return false;}
    auto Series=O(J,TEXT("series"));if(Series){const auto& T=A(Series,TEXT("time_s"));if(T.Num()<2 || T.Num()>512 || !Numbers(T,T.Num(),0,1e9) || !Numbers(A(Series,TEXT("ph")),T.Num(),0,14))return false;if(Series->HasField(TEXT("conductivity_ms_cm")) && !Numbers(A(Series,TEXT("conductivity_ms_cm")),T.Num(),0,10000))return false;for(int32 I=1;I<T.Num();++I)if(T[I]->AsNumber()<=T[I-1]->AsNumber())return false;}
    return true;
}
TSharedPtr<FJsonObject> ARedlineCampaignConsole::SelectedProductForPage(int32 I)const
{
    using namespace TabletScience;const auto& Products=A(State,TEXT("products"));
    auto Matches=[&](const TSharedPtr<FJsonObject>& P){const FString K=S(P,TEXT("instrument"));return I==6 ? IsPHProduct(P) : I==5 ? (K==TEXT("DAN") || K==TEXT("DRILL")) : true;};
    if(Products.IsValidIndex(ProductSelection) && Matches(Products[ProductSelection]->AsObject()))return Products[ProductSelection]->AsObject();
    for(int32 Index=Products.Num()-1;Index>=0;--Index)if(Matches(Products[Index]->AsObject()))return Products[Index]->AsObject();return nullptr;
}
void ARedlineCampaignConsole::CycleProduct(int32 D,int32 I)
{
    using namespace TabletScience;const auto& Products=A(State,TEXT("products"));if(Products.IsEmpty())return;
    for(int32 Attempt=0;Attempt<Products.Num();++Attempt){ProductSelection=(ProductSelection+D+Products.Num())%Products.Num();const auto P=Products[ProductSelection]->AsObject();if(I!=6 || IsPHProduct(P))break;}
}
void ARedlineCampaignConsole::CaptureScoutEvidence(const TSharedPtr<FJsonObject>& J,double Now)
{
    using namespace TabletScience;const FString Source=S(J,TEXT("source")),Id=S(J,TEXT("evidence_id"));
    if(!Source.StartsWith(TEXT("scout")) || S(O(J,TEXT("header")),TEXT("frame_id"))!=TEXT("map") || Id.IsEmpty() || Id.Len()>256 || ScoutObservationIds.Contains(Id))return;
    auto Pose=O(O(J,TEXT("pose")),TEXT("pose"));FVector P;if(!FRedlineJson::Vector(O(Pose,TEXT("position")),P) || P.GetAbsMax()>1e7)return;
    FString Raw=S(J,TEXT("summary_json"));if(Raw.Len()>8192)return;auto Summary=FRedlineJson::Parse(Raw);
    if(ScoutObservations.Num()>=2048){ScoutObservationIds.Remove(ScoutObservations[0].Id);ScoutObservations.RemoveAt(0,1,EAllowShrinking::No);}
    ScoutObservations.Add({FVector2D(P),Id,int32(N(Summary,TEXT("passability"),-1)),int32(N(O(J,TEXT("provenance")),TEXT("status"),3))});ScoutObservationIds.Add(Id);ScoutObservationReceipt=Now;
}
// Atlas renderer: RedlineTabletAtlas.cpp
void ARedlineCampaignConsole::DrawTabletPage(UCanvas* C,int32 W,int32 H,int32 Index)
{
    using namespace TabletScience;Index=FMath::Clamp(Index,0,PageCount-1);
    if(Index<4){const int32 Prev=Page;Page=Index;DrawConsole(C,W,H);Page=Prev;return;}
    const float Scale=FMath::Min(W/1280.f,H/720.f);
    auto Rect=[&](float X,float Y,float Width,float Height,FLinearColor Color){FCanvasTileItem I(FVector2D(X*Scale,Y*Scale),FVector2D(Width*Scale,Height*Scale),Color);C->DrawItem(I);};
    auto Text=[&](FString V,float X,float Y,float Size=1.2f,FLinearColor Color=FLinearColor::White){FCanvasTextItem I(FVector2D(X*Scale,Y*Scale),FText::FromString(V),GEngine->GetSmallFont(),Color);I.Scale=FVector2D(Size*Scale,Size*Scale);C->DrawItem(I);};
    auto Line=[&](float X,float Y,float X2,float Y2,FLinearColor Color){FCanvasLineItem I(FVector2D(X*Scale,Y*Scale),FVector2D(X2*Scale,Y2*Scale));I.SetColor(Color);I.LineThickness=2;C->DrawItem(I);};
    const FLinearColor Cyan=RedlineConsoleTheme::Text,Amber=RedlineConsoleTheme::Warning;Rect(0,0,1280,720,RedlineConsoleTheme::Background);
    Text(PageTitle(Index),28,24,2.f);Text(Fresh() ? TEXT("Kayıt güncel") : TEXT("VERİ ESKİ / BAĞLANTI YOK"),28,64,1.2,RedlineConsoleTheme::Secondary);
    if(Index!=7)Text(TEXT("Tab sayfa · ←/→ ürün · E işlem · X iptal"),28,680,1,RedlineConsoleTheme::Secondary);
    if(Index==7){DrawSiteMap(C,W,H);return;}
    if(Index==4)
    {
        Text(FString::Printf(TEXT("Drone: %s · %d gözlem"),*S(O(State,TEXT("scout")),TEXT("phase")),ScoutObservations.Num()),28,112,1.4f,Cyan);
        TArray<FVector2D> Points=ScoutTrack;for(const auto& P:ScoutObservations)Points.Add(P.Point);FVector2D Lo,Hi;
        if(FitRobotMap(Points,FVector2D(1150,420),Lo,Hi))
        {
            auto P=[&](FVector2D V){return FVector2D(60+(V.X-Lo.X)/(Hi.X-Lo.X)*1150,175+(Hi.Y-V.Y)/(Hi.Y-Lo.Y)*420);};
            for(const auto& V:ScoutObservations){auto Q=P(V.Point);Rect(Q.X-2,Q.Y-2,4,4,V.Passability==0 ? Amber : Cyan);}
            for(int32 I=1;I<ScoutTrack.Num();++I){auto A=P(ScoutTrack[I-1]),B=P(ScoutTrack[I]);Line(A.X,A.Y,B.X,B.Y,FLinearColor::White);}
        }else Text(TEXT("Keşif kayıtları bekleniyor; harita uydurulmaz."),40,250,1.4f,Amber);
        Text(TEXT("Fizik izi: ROS/Gazebo · Gözlemler SIMULATED truth adaptörü · sensör algısı değildir"),28,624,1,Cyan);return;
    }
    if(Index==6){Text(TEXT("P · Kayıtlı numuneyi uzaktan analiz et / MODEL"),28,110,1.1f,Amber);Text(LabMessage.Left(130),28,140,1,Cyan);}
    auto Product=SelectedProductForPage(Index);if(!Product){Text(Index==6 ? TEXT("pH analizi yok. Laboratuvarda kayıtlı numune için P ile model analizi başlat.") : TEXT("Henüz DAN / sondaj sonucu yok. Görev sonucu bekleniyor."),28,190,1.3f,Amber);return;}
    auto Summary=O(Product,TEXT("summary"));Text(S(Product,TEXT("instrument"))+TEXT(" / ")+S(Product,TEXT("target_id")),28,Index==6 ? 174 : 112,1.4f,Cyan);
    if(Index==5)
    {
        auto G=O(Summary,TEXT("posterior_grid"));if(G)
        {
            const int32 Width=N(G,TEXT("width")),Height=N(G,TEXT("height"));const auto& Values=A(G,TEXT("values"));const auto& Sigma=A(G,TEXT("sigma"));
            Text(TEXT("WEH posterior (%)"),40,160,1.2f);Text(TEXT("Belirsizlik σ (%)"),650,160,1.2f);
            double Max=1,SigMax=.001;for(auto V:Values)Max=FMath::Max(Max,V->AsNumber());for(auto V:Sigma)SigMax=FMath::Max(SigMax,V->AsNumber());
            for(int32 R=0;R<Height;++R)for(int32 Col=0;Col<Width;++Col){int32 I=R*Width+Col;Rect(40+Col*410.f/Width,198+(Height-1-R)*410.f/Height,410.f/Width+.2f,410.f/Height+.2f,FLinearColor(.1+Values[I]->AsNumber()/Max*.8,.25,.2,1));Rect(650+Col*410.f/Width,198+(Height-1-R)*410.f/Height,410.f/Width+.2f,410.f/Height+.2f,FLinearColor(.1,Sigma[I]->AsNumber()/SigMax*.8,.55,1));}
        }
        else{auto D=O(Summary,TEXT("drill"));Text(FString::Printf(TEXT("İstenen %.1f mm / elde edilen %.1f mm"),N(D,TEXT("requested_depth_mm")),N(D,TEXT("achieved_depth_mm"))),28,220,1.5f);Text(TEXT("Fiziksel kuvvet/tork sensörü yok. Zaman eğrisi üretilmedi."),28,280,1.2f,Amber);}
    }
    else
    {
        auto Series=O(Summary,TEXT("series"));const auto& Times=A(Series,TEXT("time_s"));const auto& Values=A(Series,TEXT("ph"));
        Text(TEXT("pH (0–14)"),28,218,1,Cyan);
        if(Times.Num()>1 && Times.Num()==Values.Num())for(int32 I=1;I<Times.Num();++I)Line(70+Times[I-1]->AsNumber()/Times.Last()->AsNumber()*1100,400-Values[I-1]->AsNumber()/14*170,70+Times[I]->AsNumber()/Times.Last()->AsNumber()*1100,400-Values[I]->AsNumber()/14*170,Cyan);
        const auto& EC=A(Series,TEXT("conductivity_ms_cm"));double Maximum=.01;for(auto V:EC)Maximum=FMath::Max(Maximum,V->AsNumber());
        Text(FString::Printf(TEXT("İletkenlik mS/cm (0–%.2f)"),Maximum),28,430,1,Amber);
        if(Times.Num()>1 && EC.Num()==Times.Num())for(int32 I=1;I<Times.Num();++I)Line(70+Times[I-1]->AsNumber()/Times.Last()->AsNumber()*1100,590-EC[I-1]->AsNumber()/Maximum*130,70+Times[I]->AsNumber()/Times.Last()->AsNumber()*1100,590-EC[I]->AsNumber()/Maximum*130,Amber);
        Text(TEXT("Zaman (s) · SIMULATED / SCENARIO laboratuvar modeli"),28,610,1.2f,Amber);
        Text(TEXT("Gale ölçümü değildir; oksit bileşiminden pH çıkarılmaz."),28,642,1,Cyan);
    }
    Text(S(Product,TEXT("product_id")),28,Index==6 ? 202 : 154,.85f);
}
