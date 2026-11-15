#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "Misc/AutomationTest.h"
#include "RedlineEVAImportLibrary.h"
#include "Engine/StaticMesh.h"
#include "PhysicsEngine/BodySetup.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/Package.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineInteriorQueries,"Redline.EVA.InteriorQueryCollision",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineInteriorQueries::RunTest(const FString& Parameters)
{
    auto* Source=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    if(!Source || !Source->GetBodySetup())return false;
    const auto Original=Source->GetBodySetup()->CollisionTraceFlag;
    TStrongObjectPtr<UStaticMesh> Copy(DuplicateObject<UStaticMesh>(Source,GetTransientPackage(),MakeUniqueObjectName(GetTransientPackage(),UStaticMesh::StaticClass(),TEXT("InteriorQueryTest"))));
    if(!TestTrue(TEXT("derived body setup is independent"),Copy->GetBodySetup()!=Source->GetBodySetup()))return false;
    TestTrue(TEXT("query collision cooks for derivative architecture"),URedlineEVAImportLibrary::PrepareInteriorQueryCollision(Copy.Get()));
    TestTrue(TEXT("open geometry uses triangle queries, not a portal-blocking convex hull"),Copy->GetBodySetup()->CollisionTraceFlag==CTF_UseComplexAsSimple);
    TestTrue(TEXT("repeated preparation is valid"),URedlineEVAImportLibrary::PrepareInteriorQueryCollision(Copy.Get()));
    TestEqual(TEXT("immutable source collision is untouched"),Source->GetBodySetup()->CollisionTraceFlag,Original);
    TestFalse(TEXT("missing mesh rejected"),URedlineEVAImportLibrary::PrepareInteriorQueryCollision(nullptr));
    return true;
}
#endif
