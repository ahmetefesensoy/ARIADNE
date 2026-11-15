#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "RedlineFieldTablet.h"
#include "RedlineCampaignConsole.h"
#include "RedlineTypes.h"
#include "Misc/Base64.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineTabletImageTest,"Redline.Tablet.RealImageBounds",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineTabletImageTest::RunTest(const FString&)
{
    auto J=FRedlineJson::Parse(TEXT(R"({"header":{"frame_id":"rviz"},"format":"png","data":"bad"})"));TArray<uint8> Pixels;int32 W=0,H=0;
    TestFalse(TEXT("malformed compression rejected"),ARedlineFieldTablet::DecodeImage(J,Pixels,W,H));
    TArray<uint8> Raw;Raw.Init(60,128*64*4);auto Png=FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper")).CreateImageWrapper(EImageFormat::PNG);
    Png->SetRaw(Raw.GetData(),Raw.Num(),128,64,ERGBFormat::BGRA,8);const auto& Bytes=Png->GetCompressed();J->SetStringField(TEXT("data"),FBase64::Encode(Bytes.GetData(),Bytes.Num()));
    TestTrue(TEXT("actual PNG decoded"),ARedlineFieldTablet::DecodeImage(J,Pixels,W,H));TestEqual(TEXT("exact width"),W,128);TestEqual(TEXT("pixels preserved"),Pixels,Raw);
    J->GetObjectField(TEXT("header"))->SetStringField(TEXT("frame_id"),TEXT("desktop"));TestFalse(TEXT("desktop frame not accepted"),ARedlineFieldTablet::DecodeImage(J,Pixels,W,H));return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineTabletScienceTest,"Redline.Tablet.ScienceProductsAndMissingData",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineTabletScienceTest::RunTest(const FString&)
{
    auto J=FRedlineJson::Parse(TEXT(R"({"unit":"pH","labels":["pH"],"values":[7.7],"sigma":[0.12],"series":{"time_s":[0,60,120],"ph":[7,7.6,7.7]}})"));
    TestTrue(TEXT("explicit valid model pH accepted"),ARedlineCampaignConsole::ValidateScienceSummary(J,TEXT("WCL_SCENARIO")));
    J->GetObjectField(TEXT("series"))->SetArrayField(TEXT("ph"),{MakeShared<FJsonValueNumber>(7)});TestFalse(TEXT("mismatched time samples rejected"),ARedlineCampaignConsole::ValidateScienceSummary(J,TEXT("WCL_SCENARIO")));
    auto P=FRedlineJson::Parse(TEXT(R"({"instrument":"APXS","summary":{"unit":"mass_percent_SCENARIO","values":[40]}})"));TestFalse(TEXT("oxide product cannot masquerade as pH"),ARedlineCampaignConsole::IsPHProduct(P));return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineTabletAtlasTest,"Redline.Tablet.AtlasCoordinatesAndManifest",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineTabletAtlasTest::RunTest(const FString&)
{
    const FVector4 Bounds(-1500,-1500,1500,1500);
    TestTrue(TEXT("northwest is first image pixel"),ARedlineCampaignConsole::AtlasUV(FVector2D(-1500,1500),Bounds).Equals(FVector2D(0,0)));
    TestTrue(TEXT("southeast is last image edge"),ARedlineCampaignConsole::AtlasUV(FVector2D(1500,-1500),Bounds).Equals(FVector2D(1,1)));
    TestTrue(TEXT("ENU origin is image centre"),ARedlineCampaignConsole::AtlasUV(FVector2D(0,0),Bounds).Equals(FVector2D(.5,.5)));
    FString Raw;TestTrue(TEXT("staged real atlas manifest exists"),FFileHelper::LoadFileToString(Raw,*(FPaths::ProjectContentDir()/TEXT("Atlas/manifest.json"))));
    auto J=FRedlineJson::Parse(Raw);if(!J)return false;
    TestTrue(TEXT("actual BXW atlas contract accepted"),ARedlineCampaignConsole::ValidateAtlasManifest(J));
    J->SetBoolField(TEXT("north_up"),false);TestFalse(TEXT("flipped orientation rejected"),ARedlineCampaignConsole::ValidateAtlasManifest(J));J->SetBoolField(TEXT("north_up"),true);
    J->SetNumberField(TEXT("m_per_px"),4);TestFalse(TEXT("inconsistent pixel scale rejected"),ARedlineCampaignConsole::ValidateAtlasManifest(J));J->SetNumberField(TEXT("m_per_px"),1.46484375);
    J->GetObjectField(TEXT("layers"))->GetObjectField(TEXT("imagery"))->SetStringField(TEXT("file"),TEXT("../secret.png"));TestFalse(TEXT("path traversal rejected"),ARedlineCampaignConsole::ValidateAtlasManifest(J));return true;
}
#endif
