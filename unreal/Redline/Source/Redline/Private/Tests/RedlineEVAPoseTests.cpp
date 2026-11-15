#include "Misc/AutomationTest.h"
#include "RedlineAstronautCharacter.h"
#include "RedlineTypes.h"
#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineEVAPoseTest,"Redline.EVA.AstronautFootPose",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineEVAPoseTest::RunTest(const FString& Parameters)
{
    auto J=ARedlineAstronautCharacter::PoseMessage(FVector(1000,-2000,-359800+94),FRotator(0,-90,0).Quaternion(),94,12.125);
    FVector Position;FQuat Rotation;double Stamp;
    TestTrue(TEXT("finite ROS foot pose"),FRedlineJson::Vector(J->GetObjectField(TEXT("pose"))->GetObjectField(TEXT("position")),Position));
    TestTrue(TEXT("centimetres, handedness and capsule foot origin"),Position.Equals(FVector(10,20,-3598),1e-9));
    TestTrue(TEXT("unit quaternion"),FRedlineJson::Quaternion(J->GetObjectField(TEXT("pose"))->GetObjectField(TEXT("orientation")),Rotation));
    TestTrue(TEXT("UE yaw -90 becomes ROS yaw +90"),Rotation.RotateVector(FVector::ForwardVector).Equals(FVector::RightVector,1e-6));
    TestTrue(TEXT("publication/source stamp retained, not PET"),FRedlineJson::Stamp(J->GetObjectField(TEXT("header"))->GetObjectField(TEXT("stamp")),Stamp));TestEqual(TEXT("stamp"),Stamp,12.125);return true;
}
#endif
