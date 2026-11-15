#include "RedlineEVAData.h"
#include "RedlineTypes.h"
#include "RedlineCoords.h"
#include "Misc/Base64.h"
#include "Modules/ModuleManager.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"

namespace RedlineEVAJson
{
TSharedPtr<FJsonObject> Object(const TSharedPtr<FJsonObject>& J,const TCHAR* Key)
{ const TSharedPtr<FJsonObject>* P=nullptr;return J && J->TryGetObjectField(Key,P) ? *P : nullptr; }
bool Number(const TSharedPtr<FJsonObject>& J,const TCHAR* Key,double& V)
{ return J && J->TryGetNumberField(Key,V) && FMath::IsFinite(V); }
bool Header(const TSharedPtr<FJsonObject>& J)
{ auto H=Object(J,TEXT("header"));FString Frame;double Stamp;return H && H->TryGetStringField(TEXT("frame_id"),Frame) && Frame==TEXT("map") && FRedlineJson::Stamp(Object(H,TEXT("stamp")),Stamp); }
bool Rings(const TSharedPtr<FJsonObject>& J,const TCHAR* Key,TArray<TArray<FVector>>& Out,int32& Budget)
{
    const TArray<TSharedPtr<FJsonValue>>* Regions=nullptr;
    if(!J->TryGetArrayField(Key,Regions) || Regions->Num()>128)return false;
    for(const auto& Region:*Regions)
    {
        const TArray<TSharedPtr<FJsonValue>>* Points=nullptr;
        if(!Region || Region->Type!=EJson::Object || !Region->AsObject()->TryGetArrayField(TEXT("points"),Points) || Points->Num()<3)return false;
        Budget+=Points->Num();if(Budget>6000)return false;
        TArray<FVector> Ring;
        for(const auto& Point:*Points)
        { FVector P;if(!Point || Point->Type!=EJson::Object || !FRedlineJson::Vector(Point->AsObject(),P) || FMath::Max(FMath::Abs(P.X),FMath::Abs(P.Y))>1e6)return false;Ring.Add(P); }
        Out.Add(MoveTemp(Ring));
    }
    return true;
}
}

bool FRedlineFieldTile::Parse(const TSharedPtr<FJsonObject>& J,FRedlineFieldTile& Out,FString& Error)
{
    using namespace RedlineEVAJson;
    FRedlineFieldTile V;FString Site,Name,Unit;double W,H,N;
    if(!Header(J) || !J->TryGetStringField(TEXT("site_id"),Site) || Site!=TEXT("BXW") ||
       !J->TryGetStringField(TEXT("name"),Name) || !Name.StartsWith(TEXT("margin_min")) ||
       !J->TryGetStringField(TEXT("unit"),Unit) || Unit!=TEXT("min") ||
       !Number(J,TEXT("width"),W) || !Number(J,TEXT("height"),H) || W<1 || H<1 || W>2048 || H>2048 || W!=FMath::FloorToDouble(W) || H!=FMath::FloorToDouble(H) ||
       !Number(J,TEXT("resolution_m"),V.Resolution) || V.Resolution<=0 || V.Resolution>100 ||
       !Number(J,TEXT("scale"),V.Scale) || V.Scale<=0 || !Number(J,TEXT("offset"),V.Offset) ||
       !Number(J,TEXT("nodata_byte"),N) || N<0 || N>255 || N!=FMath::FloorToDouble(N) ||
       !FRedlineJson::Vector(Object(J,TEXT("origin")),V.Origin))
    { Error=TEXT("Invalid BXW map-frame margin tile metadata");return false; }
    TArray<uint8> PNG;FString Encoded;
    if(J->TryGetStringField(TEXT("png"),Encoded))
    { if(Encoded.Len()>410000 || !FBase64::Decode(Encoded,PNG)){Error=TEXT("Invalid PNG base64");return false;} }
    else
    {
        const TArray<TSharedPtr<FJsonValue>>* Bytes=nullptr;
        if(!J->TryGetArrayField(TEXT("png"),Bytes) || Bytes->Num()>307200){Error=TEXT("PNG must be base64 or a bounded byte array");return false;}
        for(const auto& Byte:*Bytes){double B;if(!Byte || !Byte->TryGetNumber(B) || !FMath::IsFinite(B) || B<0 || B>255 || B!=FMath::FloorToDouble(B)){Error=TEXT("Invalid PNG byte");return false;}PNG.Add(static_cast<uint8>(B));}
    }
    if(PNG.IsEmpty() || PNG.Num()>307200){Error=TEXT("PNG exceeds 300 KiB contract");return false;}
    auto Image=FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper")).CreateImageWrapper(EImageFormat::PNG);
    TArray64<uint8> Raw;
    if(!Image || !Image->SetCompressed(PNG.GetData(),PNG.Num()) || Image->GetWidth()!=W || Image->GetHeight()!=H || Image->GetBitDepth()!=8 ||
       !Image->GetRaw(ERGBFormat::Gray,8,Raw) || Raw.Num()!=static_cast<int64>(W*H))
    {Error=TEXT("PNG dimensions/8-bit grayscale decoding do not match metadata");return false;}
    V.Width=static_cast<int32>(W);V.Height=static_cast<int32>(H);V.Nodata=static_cast<uint8>(N);
    V.Pixels.Append(Raw.GetData(),static_cast<int32>(Raw.Num()));Out=MoveTemp(V);return true;
}
bool FRedlineFieldTile::Sample(FVector P,double& Value) const
{
    const int32 I=URedlineCoords::MapToCellIndex(P,Origin,Resolution,Width,Height);
    if(!Pixels.IsValidIndex(I) || Pixels[I]==Nodata)return false;
    Value=Pixels[I]*Scale+Offset;return true;
}
bool FRedlineEVALine::Parse(const TSharedPtr<FJsonObject>& J,FRedlineEVALine& Out,FString& Error)
{
    using namespace RedlineEVAJson;FRedlineEVALine V;FString Site;int32 Budget=0;
    if(!Header(J) || !J->TryGetStringField(TEXT("site_id"),Site) || Site!=TEXT("BXW") ||
       !J->TryGetStringField(TEXT("limiting_crew_id"),V.LimitingCrew) ||
       !Rings(J,TEXT("abort_regions"),V.Abort,Budget) || !Rings(J,TEXT("terminate_regions"),V.Terminate,Budget))
    {Error=TEXT("Invalid map-frame RedLine geometry");return false;}
    V.bHasMargin=Number(J,TEXT("margin_now_min"),V.MarginMinutes);
    // rosbridge represents the unknown (NaN) margin with JSON null.
    if(!V.bHasMargin){const auto* M=J->Values.Find(TEXT("margin_now_min"));if(!M || (*M)->Type!=EJson::Null){Error=TEXT("Invalid margin");return false;}}
    Out=MoveTemp(V);return true;
}
bool FRedlineEVACrew::Parse(const TSharedPtr<FJsonObject>& J,FRedlineEVACrew& Out,FString& Error)
{
    using namespace RedlineEVAJson;FRedlineEVACrew V;FString Id;auto C=Object(J,TEXT("consumables"));FQuat Q;
    auto Pose=Object(Object(J,TEXT("pose")),TEXT("pose"));
    if(!Header(J) || !J->TryGetStringField(TEXT("crew_id"),Id) || Id!=TEXT("EV1") ||
       !FRedlineJson::Vector(Object(Pose,TEXT("position")),V.Position) || !FRedlineJson::Quaternion(Object(Pose,TEXT("orientation")),Q) ||
       !Number(C,TEXT("o2_kg"),V.OxygenKg) || V.OxygenKg<0 || !Number(C,TEXT("water_kg"),V.WaterKg) || V.WaterKg<0 ||
       !Number(C,TEXT("battery_wh"),V.BatteryWh) || V.BatteryWh<0)
    {Error=TEXT("Invalid EV1 crew state/consumables");return false;}
    Out=V;return true;
}
bool FRedlineEVADose::Parse(const TSharedPtr<FJsonObject>& J,FRedlineEVADose& Out,FString& Error)
{
    using namespace RedlineEVAJson;FRedlineEVADose V;double Sol;
    if(!Header(J) || !Number(J,TEXT("dose_rate_b_ugy_h"),V.RateB) || V.RateB<0 ||
       !Number(J,TEXT("background_b_ugy_h"),V.BackgroundB) || V.BackgroundB<0 ||
       !J->TryGetBoolField(TEXT("alert"),V.bAlert) || !Number(J,TEXT("source_sol"),Sol) || Sol<0 || Sol!=FMath::FloorToDouble(Sol) || Sol>100000 ||
       !J->TryGetStringField(TEXT("source_file"),V.SourceFile) || V.SourceFile.IsEmpty())
    {Error=TEXT("Invalid RAD source/values");return false;}
    J->TryGetStringField(TEXT("alert_detector"),V.Detector);
    if(V.Detector!=TEXT("B") && V.Detector!=TEXT("E")){Error=TEXT("Unknown RAD detector");return false;}
    if(V.Detector==TEXT("E") && (!Number(J,TEXT("dose_rate_e_ugy_h"),V.RateE) || V.RateE<0 ||
       !Number(J,TEXT("background_e_ugy_h"),V.BackgroundE) || V.BackgroundE<0)){Error=TEXT("Missing selected RAD E channel");return false;}
    V.SourceSol=static_cast<int32>(Sol);Out=MoveTemp(V);return true;
}
FString FRedlineEVADose::AlarmText(bool bFresh) const
{return !bAlert ? FString() : bFresh ? TEXT("SEP ALARMI - SIGINAGA DON") : TEXT("SEP ALARMI - SIGINAGA DON | RAD VERI ESKI");}
