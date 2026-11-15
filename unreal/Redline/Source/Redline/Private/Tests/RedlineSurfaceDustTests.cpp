#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Tests/AutomationCommon.h"
#include "RedlineSurfaceDust.h"
#include "RedlineSettings.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineSurfaceDustGateTest,"Redline.SurfaceDust.MotionAndAltitudeGates",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineSurfaceDustGateTest::RunTest(const FString& Parameters)
{
    using K=ERedlineDustSource;
    TestTrue(TEXT("walking grounded boot emits"),ARedlineSurfaceDust::CanEmit(K::Boot,70,96,true,true));
    TestFalse(TEXT("stationary boot emits nothing"),ARedlineSurfaceDust::CanEmit(K::Boot,0,96,true,true));
    TestFalse(TEXT("jumping boot emits nothing"),ARedlineSurfaceDust::CanEmit(K::Boot,70,96,true,false));
    TestTrue(TEXT("rover contact movement emits"),ARedlineSurfaceDust::CanEmit(K::Rover,40,110,true,false));
    TestFalse(TEXT("stale robot emits nothing"),ARedlineSurfaceDust::CanEmit(K::Rover,40,110,false,false));
    TestFalse(TEXT("teleport speed emits nothing"),ARedlineSurfaceDust::CanEmit(K::Rover,900,110,true,false));
    TestTrue(TEXT("fresh low hovering rotor emits"),ARedlineSurfaceDust::CanEmit(K::Rotor,0,180,true,false));
    TestFalse(TEXT("parked rotor emits nothing"),ARedlineSurfaceDust::CanEmit(K::Rotor,0,12,true,false));
    TestFalse(TEXT("high aircraft produces no ground fog"),ARedlineSurfaceDust::CanEmit(K::Rotor,200,1500,true,false));
    TestFalse(TEXT("invalid sample cannot enter renderer"),ARedlineSurfaceDust::CanEmit(K::Rotor,NAN,100,true,false));
    for(int32 I=0;I<=100;++I)
    {
        const float Value=ARedlineSurfaceDust::OpacityAt(I/100.f,1,5);
        TestTrue(TEXT("opacity remains below 0.14 even with excessive gain"),Value>=0 && Value<=.14f);
    }
    TestEqual(TEXT("puff starts invisible"),ARedlineSurfaceDust::OpacityAt(0,1,1),0.f);
    TestEqual(TEXT("expired puff invisible"),ARedlineSurfaceDust::OpacityAt(1,1,1),0.f);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineSurfaceDustPoolTest,"Redline.SurfaceDust.BoundedPoolAndExpiry",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineSurfaceDustPoolTest::RunTest(const FString& Parameters)
{
    TGuardValue<bool> NoConnection(GetMutableDefault<URedlineSettings>()->bAutoConnect,false);FTestWorldWrapper Fixture;
    if(!Fixture.CreateTestWorld(EWorldType::Game)){Fixture.ForwardErrorMessages(this);return false;}
    auto* Dust=Fixture.GetTestWorld()->SpawnActor<ARedlineSurfaceDust>();if(!Dust)return false;
    // Geometry/state test does not require the generated material or a live ROS graph.
    Dust->Puffs.SetNum(ARedlineSurfaceDust::PoolCapacity);
    const FTransform Before=Dust->GetActorTransform();
    for(int32 I=0;I<500;++I)Dust->SpawnPuff(FVector(1,2,-359500),FVector(30,0,0),ERedlineDustSource::Rover,.7f);
    TestEqual(TEXT("pool never grows under repeated emissions"),Dust->Puffs.Num(),ARedlineSurfaceDust::PoolCapacity);
    TestEqual(TEXT("live puffs bounded"),Dust->GetActiveParticleCount(),ARedlineSurfaceDust::PoolCapacity);
    Dust->AdvanceParticles(2,FVector(0,0,-359000));TestEqual(TEXT("all particles expire"),Dust->GetActiveParticleCount(),0);
    TestTrue(TEXT("particle update does not move an actor or physics root"),Dust->GetActorTransform().Equals(Before));
    Fixture.ForwardErrorMessages(this);return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineSurfaceDustTerrainTest,"Redline.SurfaceDust.TerrainOnlyContact",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineSurfaceDustTerrainTest::RunTest(const FString& Parameters)
{
    auto* Component=NewObject<UStaticMeshComponent>();
    auto* Terrain=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/T4Fixtures/Terrain/SM_BXW_ops_00_00_LOD0.SM_BXW_ops_00_00_LOD0"));
    auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    if(!TestNotNull(TEXT("actual imported terrain asset"),Terrain) || !TestNotNull(TEXT("engine building proxy"),Cube))return false;
    Component->SetStaticMesh(Cube);TestFalse(TEXT("building floor cannot raise surface dust"),ARedlineSurfaceDust::IsTerrainComponent(Component));
    Component->SetStaticMesh(Terrain);TestTrue(TEXT("verified imported terrain is the permitted surface"),ARedlineSurfaceDust::IsTerrainComponent(Component));
    TestFalse(TEXT("missing hit component cannot create dust"),ARedlineSurfaceDust::IsTerrainComponent(nullptr));
    return true;
}
#endif
