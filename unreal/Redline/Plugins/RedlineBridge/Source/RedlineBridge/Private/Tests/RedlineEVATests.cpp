#include "Misc/AutomationTest.h"
#include "RedlineEVAData.h"
#include "RedlineTypes.h"
#include "Misc/Base64.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "Modules/ModuleManager.h"

#if WITH_DEV_AUTOMATION_TESTS
namespace
{
TSharedRef<FJsonObject> TilePacket()
{
    auto J=FRedlineJson::Parse(TEXT(R"({"header":{"frame_id":"map","stamp":{"sec":12,"nanosec":125000000}},"site_id":"BXW","name":"margin_min_EV1","unit":"min","resolution_m":4,"origin":{"x":10,"y":20,"z":0},"width":2,"height":2,"scale":1,"offset":-60,"nodata_byte":255})"));
    auto Image=FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper")).CreateImageWrapper(EImageFormat::PNG);
    const uint8 Pixels[]={0,128,255,1};Image->SetRaw(Pixels,4,2,2,ERGBFormat::Gray,8);
    const auto& PNG=Image->GetCompressed();J->SetStringField(TEXT("png"),FBase64::Encode(PNG.GetData(),PNG.Num()));return J.ToSharedRef();
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineEVATile,"Redline.EVA.FieldTileGeometry",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineEVATile::RunTest(const FString& Parameters)
{
    auto J=TilePacket();FRedlineFieldTile Tile;FString Error;double Value=123;
    TestTrue(TEXT("valid 8-bit base64 tile"),FRedlineFieldTile::Parse(J,Tile,Error));
    TestTrue(TEXT("south-west row"),Tile.Sample(FVector(12,22,0),Value));TestEqual(TEXT("scale and offset"),Value,-60.);
    TestTrue(TEXT("north-east row is not vertically flipped"),Tile.Sample(FVector(16,26,0),Value));TestEqual(TEXT("north-east code"),Value,-59.);
    TestFalse(TEXT("nodata is unknown"),Tile.Sample(FVector(12,26,0),Value));
    TestFalse(TEXT("east boundary is outside"),Tile.Sample(FVector(18,22,0),Value));
    J->SetNumberField(TEXT("width"),3);TestFalse(TEXT("decoded dimensions must agree"),FRedlineFieldTile::Parse(J,Tile,Error));
    TestEqual(TEXT("invalid packet cannot replace accepted data"),Tile.Width,2);
    J=TilePacket();J->SetStringField(TEXT("unit"),TEXT("m/s"));TestFalse(TEXT("wrong units rejected"),FRedlineFieldTile::Parse(J,Tile,Error));
    J=TilePacket();J->SetStringField(TEXT("png"),TEXT("bad!"));TestFalse(TEXT("invalid bytes rejected"),FRedlineFieldTile::Parse(J,Tile,Error));
    J=TilePacket();J->SetNumberField(TEXT("width"),2049);TestFalse(TEXT("bounded allocation"),FRedlineFieldTile::Parse(J,Tile,Error));
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineEVALineTest,"Redline.EVA.RedLineUnknownAndFrame",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineEVALineTest::RunTest(const FString& Parameters)
{
    auto J=FRedlineJson::Parse(TEXT(R"({"header":{"frame_id":"map","stamp":{"sec":1,"nanosec":0}},"site_id":"BXW","abort_regions":[{"points":[{"x":0,"y":0,"z":0},{"x":4,"y":0,"z":0},{"x":0,"y":4,"z":0}]}],"terminate_regions":[],"limiting_crew_id":"EV1","margin_now_min":123.5})"));
    FRedlineEVALine Line;FString Error;TestTrue(TEXT("line accepted"),FRedlineEVALine::Parse(J,Line,Error));TestEqual(TEXT("ROS margin is preserved"),Line.MarginMinutes,123.5);
    J->SetField(TEXT("margin_now_min"),MakeShared<FJsonValueNull>());TestTrue(TEXT("unknown margin is supported"),FRedlineEVALine::Parse(J,Line,Error));TestFalse(TEXT("unknown is not zero margin"),Line.bHasMargin);
    J->GetObjectField(TEXT("header"))->SetStringField(TEXT("frame_id"),TEXT("odom"));TestFalse(TEXT("odom line cannot be drawn as map"),FRedlineEVALine::Parse(J,Line,Error));return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineEVADoseTest,"Redline.EVA.RADSourceAndAlert",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineEVADoseTest::RunTest(const FString& Parameters)
{
    auto J=FRedlineJson::Parse(TEXT(R"({"header":{"frame_id":"map","stamp":{"sec":1,"nanosec":0}},"dose_rate_b_ugy_h":2.5,"background_b_ugy_h":1,"source_sol":4190,"source_file":"rad_source.tab","alert":true})"));
    FRedlineEVADose Dose;FString Error;TestTrue(TEXT("archive source and ROS alarm read"),FRedlineEVADose::Parse(J,Dose,Error));TestTrue(TEXT("ROS alarm is not recomputed in UE"),Dose.bAlert);TestEqual(TEXT("source sol"),Dose.SourceSol,4190);
    J->SetStringField(TEXT("alert_detector"),TEXT("E"));J->SetNumberField(TEXT("dose_rate_e_ugy_h"),8.3);J->SetNumberField(TEXT("background_e_ugy_h"),6.);
    TestTrue(TEXT("selected detector E is supported"),FRedlineEVADose::Parse(J,Dose,Error));TestEqual(TEXT("selected E value is not B value"),Dose.RateE,8.3);
    J->SetNumberField(TEXT("dose_rate_b_ugy_h"),-1);TestFalse(TEXT("invalid dose cannot clear alert"),FRedlineEVADose::Parse(J,Dose,Error));TestTrue(TEXT("prior alert retained"),Dose.bAlert);
    TestTrue(TEXT("stale active alarm remains visible and explicitly stale"),Dose.AlarmText(false).Contains(TEXT("ESKI")));Dose.bAlert=false;TestTrue(TEXT("ROS clear clears the label"),Dose.AlarmText(true).IsEmpty());return true;
}
#endif
