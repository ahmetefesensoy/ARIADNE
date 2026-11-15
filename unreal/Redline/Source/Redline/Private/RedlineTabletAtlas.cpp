#include "RedlineCampaignConsole.h"
#include "RedlineTypes.h"
#include "RedlineCoords.h"
#include "RedlineOverlay.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Texture2D.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "CanvasItem.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "RedlineConsoleTheme.h"

namespace TabletAtlas
{
const TCHAR* Keys[]={TEXT("imagery"),TEXT("hillshade"),TEXT("slope_class"),TEXT("science_units"),TEXT("return_time"),TEXT("stations")};
const TCHAR* Titles[]={TEXT("HiRISE renkli görüntü"),TEXT("Kabartma"),TEXT("Eğim sınıfları"),TEXT("TPI sırt / çukur"),TEXT("Başlangıç dönüş süresi"),TEXT("İstasyonlar")};
FString S(const TSharedPtr<FJsonObject>& J,const TCHAR* K){FString V;return J && J->TryGetStringField(K,V) ? V : TEXT("");}
TSharedPtr<FJsonObject> O(const TSharedPtr<FJsonObject>& J,const TCHAR* K){const TSharedPtr<FJsonObject>* V;return J && J->TryGetObjectField(K,V) ? *V : nullptr;}
const TArray<TSharedPtr<FJsonValue>>& A(const TSharedPtr<FJsonObject>& J,const TCHAR* K){static TArray<TSharedPtr<FJsonValue>> Empty;const TArray<TSharedPtr<FJsonValue>>* V;return J && J->TryGetArrayField(K,V) ? *V : Empty;}
bool N(const TSharedPtr<FJsonObject>& J,const TCHAR* K,double& V){return J && J->TryGetNumberField(K,V) && FMath::IsFinite(V);}
bool XY(const TArray<TSharedPtr<FJsonValue>>& V,FVector2D& P){double X,Y;if(V.Num()!=2 || !V[0]->TryGetNumber(X) || !V[1]->TryGetNumber(Y) || !FMath::IsFinite(X) || !FMath::IsFinite(Y))return false;P=FVector2D(X,Y);return true;}
FString Endpoint(const FString& Action)
{
    if(Action==TEXT("ContactScience"))return TEXT("/rover_1/contact_science");
    if(Action==TEXT("RemoteLibs"))return TEXT("/rover_1/remote_libs");
    if(Action==TEXT("NeutronSurvey"))return TEXT("/rover_1/neutron_survey");
    if(Action==TEXT("Drill"))return TEXT("/rover_1/drill");
    if(Action==TEXT("CollectSample"))return TEXT("/redline/science/collect_sample");
    if(Action==TEXT("CacheSample"))return TEXT("/redline/science/cache_sample");
    if(Action==TEXT("DeployStation"))return TEXT("/redline/science/deploy_station");
    if(Action==TEXT("ExecuteScout"))return TEXT("/scout_1/execute_scout");
    if(Action==TEXT("lab_analysis"))return TEXT("/redline/science/analyze_sample");
    return TEXT("Henüz çalışan kampanya uç noktası yok");
}
FString Animation(const FString& Action)
{
    if(Action==TEXT("ContactScience"))return TEXT("Yüzeye uzan / temas / sayım");
    if(Action==TEXT("RemoteLibs"))return TEXT("Direği hedefle / 5 lazer noktası");
    if(Action==TEXT("NeutronSurvey"))return TEXT("Dur / sayım / GP haritası");
    if(Action==TEXT("Drill"))return TEXT("Ucu indir / dön / FDIR geri çekme");
    if(Action==TEXT("CollectSample"))return TEXT("Eğil / numuneyi tüpe aktar");
    if(Action==TEXT("CacheSample"))return TEXT("Tüpü laboratuvar kabına aktar");
    if(Action==TEXT("ExecuteScout"))return TEXT("Kalk / tara / dön / in");
    if(Action==TEXT("DeployStation"))return TEXT("İstasyonu yerleştir / anteni aç");
    if(Action==TEXT("lab_analysis"))return TEXT("Hazırla / analiz / sonuç");
    return TEXT("Görev kartındaki sunum planı");
}
FString Instrument(const FString& Asset,const FString& Actor)
{
    const FString Id=FPaths::GetCleanFilename(Asset);
    if(Id==TEXT("tool_apxs"))return Actor==TEXT("EV1") ? TEXT("El tipi XRF") : TEXT("Rover APXS başlığı");
    if(Id==TEXT("tool_libs"))return TEXT("Rover LIBS başlığı");if(Id==TEXT("tool_neutron"))return TEXT("DAN nötron dedektörü");
    if(Id==TEXT("tool_drill"))return TEXT("Rover sondaj ucu");if(Id==TEXT("sample_tube"))return TEXT("Numune tüpü");
    if(Id==TEXT("sample_case"))return TEXT("Numune kabı");if(Id==TEXT("science_station"))return TEXT("Taşınabilir çevre istasyonu");
    if(Id==TEXT("lab_bench"))return TEXT("Laboratuvar analiz tezgâhı");if(Id==TEXT("scout_1"))return TEXT("Öncü drone");
    if(Id==TEXT("tool_multispectral"))return TEXT("Çok bantlı kamera");if(Id==TEXT("station_marker"))return TEXT("Saha notu ve işaretleyici");return TEXT("Bilim aleti");
}
UTexture2D* LoadPNG(const FString& Path)
{
    const int64 Size=IFileManager::Get().FileSize(*Path);if(Size<32 || Size>16*1024*1024)return nullptr;
    TArray<uint8> Bytes;if(!FFileHelper::LoadFileToArray(Bytes,*Path))return nullptr;
    auto Decoder=FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper")).CreateImageWrapper(EImageFormat::PNG);
    if(!Decoder || !Decoder->SetCompressed(Bytes.GetData(),Bytes.Num()) || Decoder->GetWidth()!=2048 || Decoder->GetHeight()!=2048)return nullptr;
    TArray<uint8> Raw;if(!Decoder->GetRaw(ERGBFormat::BGRA,8,Raw) || Raw.Num()!=2048*2048*4)return nullptr;
    auto* Texture=UTexture2D::CreateTransient(2048,2048,PF_B8G8R8A8);if(!Texture)return nullptr;Texture->SRGB=true;
    void* Dest=Texture->GetPlatformData()->Mips[0].BulkData.Lock(LOCK_READ_WRITE);FMemory::Memcpy(Dest,Raw.GetData(),Raw.Num());Texture->GetPlatformData()->Mips[0].BulkData.Unlock();Texture->UpdateResource();return Texture;
}
}

bool ARedlineCampaignConsole::ValidateAtlasManifest(const TSharedPtr<FJsonObject>& J)
{
    using namespace TabletAtlas;bool North=false;double Size,MPP;
    if(S(J,TEXT("schema"))!=TEXT("redline.tablet_atlas.v1") || S(J,TEXT("site_id"))!=TEXT("BXW") || S(J,TEXT("frame"))!=TEXT("map") || S(J,TEXT("units"))!=TEXT("m") || !J->TryGetBoolField(TEXT("north_up"),North) || !North || !N(J,TEXT("size_px"),Size) || Size!=2048 || !N(J,TEXT("m_per_px"),MPP) || MPP<=0)return false;
    const auto& B=A(J,TEXT("bounds_map_m"));if(B.Num()!=4)return false;double V[4];
    for(int32 I=0;I<4;++I)if(!B[I]->TryGetNumber(V[I]) || !FMath::IsFinite(V[I]) || FMath::Abs(V[I])>1e7)return false;
    if(V[2]<=V[0] || V[3]<=V[1] || FMath::Abs((V[2]-V[0])-Size*MPP)>.01 || FMath::Abs((V[3]-V[1])-Size*MPP)>.01)return false;
    auto Layers=O(J,TEXT("layers"));for(const auto* Key:Keys){auto Layer=O(Layers,Key);if(S(Layer,TEXT("file"))!=FString(Key)+TEXT(".png") || (S(Layer,TEXT("status"))!=TEXT("DERIVED") && S(Layer,TEXT("status"))!=TEXT("SCENARIO")))return false;}
    const auto& Stations=A(J,TEXT("stations"));if(Stations.IsEmpty() || Stations.Num()>32)return false;
    TSet<FString> Ids;
    for(auto Value:Stations)
    {
        if(!Value || Value->Type!=EJson::Object)return false;auto St=Value->AsObject();const FString Id=S(St,TEXT("id"));FVector2D P;
        if(Id.IsEmpty() || Id.Len()>64 || Ids.Contains(Id) || S(O(St,TEXT("name")),TEXT("tr")).Len()>128 || !XY(A(St,TEXT("xy_m")),P) || P.X<V[0] || P.X>V[2] || P.Y<V[1] || P.Y>V[3])return false;Ids.Add(Id);
        const auto& Tasks=A(St,TEXT("tasks"));if(Tasks.Num()>32)return false;
        for(auto T:Tasks){if(!T || T->Type!=EJson::Object)return false;auto Task=T->AsObject();if(!Task || S(Task,TEXT("id")).IsEmpty() || S(Task,TEXT("id")).Len()>64 || S(Task,TEXT("action")).Len()>64 || S(Task,TEXT("asset")).Len()>256 || S(O(Task,TEXT("purpose")),TEXT("tr")).Len()>2048)return false;}
    }
    return true;
}
FVector2D ARedlineCampaignConsole::AtlasUV(FVector2D Map,FVector4 Bounds)
{return FVector2D((Map.X-Bounds.X)/(Bounds.Z-Bounds.X),(Bounds.W-Map.Y)/(Bounds.W-Bounds.Y));}
void ARedlineCampaignConsole::LoadAtlas()
{
    using namespace TabletAtlas;bAtlasTried=true;const FString Dir=FPaths::ProjectContentDir()/TEXT("Atlas");FString Raw;
    if(IFileManager::Get().FileSize(*(Dir/TEXT("manifest.json")))>128000 || !FFileHelper::LoadFileToString(Raw,*(Dir/TEXT("manifest.json"))))return;
    auto Manifest=FRedlineJson::Parse(Raw);if(!ValidateAtlasManifest(Manifest))return;
    const auto& B=A(Manifest,TEXT("bounds_map_m"));AtlasBounds=FVector4(B[0]->AsNumber(),B[1]->AsNumber(),B[2]->AsNumber(),B[3]->AsNumber());
    for(const auto* Key:Keys)AtlasLayers.Add(LoadPNG(Dir/(FString(Key)+TEXT(".png"))));
    AtlasTexture=AtlasLayers[0];
    for(auto Value:A(Manifest,TEXT("stations")))
    {
        auto J=Value->AsObject();FAtlasStation St;St.Id=S(J,TEXT("id"));St.Role=S(J,TEXT("role"));St.Name=S(O(J,TEXT("name")),TEXT("tr"));XY(A(J,TEXT("xy_m")),St.Map);N(J,TEXT("t_eps_min"),St.TEpsMin);
        for(auto V:A(J,TEXT("tasks"))){auto T=V->AsObject();St.Tasks.Add({S(T,TEXT("id")),S(T,TEXT("action")),S(T,TEXT("actor")),S(T,TEXT("asset")),S(O(T,TEXT("purpose")),TEXT("tr")),S(T,TEXT("data_status"))});}
        AtlasStations.Add(MoveTemp(St));
    }
}
void ARedlineCampaignConsole::CycleAtlasLayer(){if(!bAtlasTried)LoadAtlas();AtlasLayer=(AtlasLayer+1)%6;}
void ARedlineCampaignConsole::CycleAtlasStation(int32 Delta){if(!bAtlasTried)LoadAtlas();if(!AtlasStations.IsEmpty()){AtlasStation=(AtlasStation+Delta+AtlasStations.Num())%AtlasStations.Num();AtlasTask=0;}}
void ARedlineCampaignConsole::CycleAtlasTask(int32 Delta){if(AtlasStations.IsValidIndex(AtlasStation)){const auto Count=AtlasStations[AtlasStation].Tasks.Num();if(Count)AtlasTask=(AtlasTask+Delta+Count)%Count;}}
void ARedlineCampaignConsole::DrawSiteMap(UCanvas* C,int32 W,int32 H)
{
    using namespace TabletAtlas;if(!bAtlasTried)LoadAtlas();const float Scale=FMath::Min(W/1280.f,H/720.f);
    auto Text=[&](FString V,float X,float Y,float Size=1.f,FLinearColor Color=FLinearColor::White){FCanvasTextItem I(FVector2D(X*Scale,Y*Scale),FText::FromString(V),GEngine->GetSmallFont(),Color);I.Scale=FVector2D(Size*Scale,Size*Scale);C->DrawItem(I);};
    auto Rect=[&](float X,float Y,float A,float B,FLinearColor Color){FCanvasTileItem I(FVector2D(X*Scale,Y*Scale),FVector2D(A*Scale,B*Scale),Color);I.BlendMode=SE_BLEND_Translucent;C->DrawItem(I);};
    const FLinearColor Cyan=RedlineConsoleTheme::Text,Amber=RedlineConsoleTheme::Warning;const float MX=28,MY=126,MS=520;
    auto Point=[&](FVector2D P){return FVector2D(MX,MY)+AtlasUV(P,AtlasBounds)*MS;};
    auto Inside=[&](FVector2D P){const auto Q=AtlasUV(P,AtlasBounds);return Q.X>=0 && Q.X<=1 && Q.Y>=0 && Q.Y<=1;};
    auto Line=[&](FVector2D P,FVector2D Q,FLinearColor Color){if(!Inside(P) || !Inside(Q))return;FCanvasLineItem I(Point(P)*Scale,Point(Q)*Scale);I.LineThickness=1.5;I.SetColor(Color);C->DrawItem(I);};
    auto Image=[&](UTexture2D* Texture,bool Alpha){if(Texture && Texture->GetResource()){FCanvasTileItem I(FVector2D(MX,MY)*Scale,Texture->GetResource(),FVector2D(MS,MS)*Scale,FLinearColor::White);I.BlendMode=Alpha ? SE_BLEND_Translucent : SE_BLEND_Opaque;C->DrawItem(I);}};
    Text(TEXT("L katman · ←/→ istasyon · ↑/↓ görev kartı"),28,90,1.1f,Cyan);
    if(!AtlasTexture){Text(TEXT("Atlas doğrulanamadı / dosyalar eksik."),MX,MY+180,1.3f,Amber);return;}
    Image(AtlasTexture,false);if(AtlasLayer && AtlasLayers.IsValidIndex(AtlasLayer))Image(AtlasLayers[AtlasLayer],AtlasLayer>1);
    Text(Titles[AtlasLayer],MX,MY+MS+8,1.f,Cyan);bool LiveLine=false;
    for(TActorIterator<ARedlineOverlay> It(GetWorld());It;++It)if(It->Fresh(It->LineReceipt))
    {for(const auto& Region:It->Line.Abort)for(int32 I=1;I<Region.Num();++I)Line(FVector2D(Region[I-1]),FVector2D(Region[I]),FLinearColor(1,.1,.1));LiveLine=true;break;}
    for(const auto& P:ScoutObservations)if(Inside(P.Point)){auto Q=Point(P.Point);Rect(Q.X-1,Q.Y-1,2,2,P.Passability==0 ? Amber : Cyan);}
    for(int32 I=1;I<ScoutTrack.Num();++I)Line(ScoutTrack[I-1],ScoutTrack[I],FLinearColor::White);
    for(int32 I=0;I<AtlasStations.Num();++I){const auto& St=AtlasStations[I];auto P=Point(St.Map);FLinearColor Color=St.Role==TEXT("control") ? FLinearColor(.27,.63,1) : St.Role==TEXT("test") ? Amber : FLinearColor::White;Rect(P.X-4,P.Y-4,8,8,Color);Text(St.Id,P.X+6,P.Y-10,.8f,Color);if(I==AtlasStation){Rect(P.X-7,P.Y-7,14,2,Cyan);Rect(P.X-7,P.Y+5,14,2,Cyan);}}
    auto Marker=[&](FVector2D P,FString Label,FLinearColor Color){if(Inside(P)){auto Q=Point(P);Rect(Q.X-3,Q.Y-3,6,6,Color);Text(Label,Q.X+5,Q.Y+4,.75f,Color);}};
    if(RobotFresh(RoverReceipt))Marker(FVector2D(RoverMap),TEXT("rover_1"),FLinearColor(.35,1,.45));
    if(auto* PC=GetWorld()->GetFirstPlayerController())if(APawn* Pawn=PC->GetPawn())Marker(FVector2D(URedlineCoords::UeToRosLocation(Pawn->GetActorLocation())),TEXT("EV1"),FLinearColor::White);
    for(auto Value:A(State,TEXT("products"))){auto Product=Value->AsObject();const auto& P=A(Product,TEXT("target_point_m"));if(P.Num()==3)Marker(FVector2D(P[0]->AsNumber(),P[1]->AsNumber()),S(Product,TEXT("instrument"))==TEXT("WCL_SCENARIO") ? TEXT("pH / numune") : TEXT("ürün"),Cyan);}
    Text(LiveLine ? TEXT("Kırmızı: canlı ROS sınırı") : TEXT("Canlı ROS sınırı yok / eski"),MX,MY+MS+30,.9f,LiveLine ? Cyan : Amber);
    if(!AtlasStations.IsValidIndex(AtlasStation))return;const auto& St=AtlasStations[AtlasStation];float Y=126;
    auto Wrap=[&](FString V,FLinearColor Color){TArray<FString> Words;V.ParseIntoArrayWS(Words);FString Row;for(const FString& Word:Words){if(Row.Len()+Word.Len()>77){Text(Row,580,Y,1.f,Color);Y+=22;Row.Empty();}Row+=Word+TEXT(" ");}if(!Row.IsEmpty()){Text(Row,580,Y,1.f,Color);Y+=22;}};
    Wrap(St.Id+TEXT(" / ")+St.Name,Cyan);
    const FString SiteRole=St.Role==TEXT("control") ? TEXT("Kontrol istasyonu") : St.Role==TEXT("test") ? TEXT("Test istasyonu") : TEXT("Destek noktası");
    Wrap(FString::Printf(TEXT("%s · Riskli dönüş: %.1f dk · Alarm sınırı: 20 dk"),*SiteRole,St.TEpsMin),St.TEpsMin>20 ? Amber : Cyan);
    Wrap(TEXT("Statik dönüş süresi EVA başlangıcına aittir."),Amber);Y+=12;
    if(St.Tasks.IsValidIndex(AtlasTask))
    {
        const auto& Task=St.Tasks[AtlasTask];Wrap(FString::Printf(TEXT("%d / %d   ·   %s"),AtlasTask+1,St.Tasks.Num(),*Task.Actor),Cyan);Wrap(Task.Purpose,FLinearColor::White);Y+=10;
        Wrap(TEXT("Alet: ")+Instrument(Task.Asset,Task.Actor),Cyan);Wrap(TEXT("İşlem planı: ")+Animation(Task.Action),FLinearColor::White);
        const FString Source=Task.Status==TEXT("ARCHIVE") ? TEXT("Arşiv başvurusu") : Task.Status==TEXT("DERIVED") ? TEXT("Arşivden türetilmiş model") : TEXT("Simülasyon / senaryo");
        Wrap(Source+TEXT(" · Sonuç etiketi ölçüm ürününde."),RedlineConsoleTheme::Secondary);
    }
    Y=FMath::Max(Y+14,550.f);Wrap(TEXT("Atlas görev planıdır. E yalnız etkin kampanya görevini çalıştırır; bu kart istasyonu değiştirmez."),Amber);
    Wrap(TEXT("Uzak yolculuk kapalı: ROS süre, sarf ve alarm kabulü bekleniyor."),Amber);
    Text(TEXT("Tab  Diğer sayfalar    ·    M / T  Kapat"),580,686,1.f,RedlineConsoleTheme::Secondary);
}
