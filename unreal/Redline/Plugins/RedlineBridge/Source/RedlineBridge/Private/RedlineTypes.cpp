#include "RedlineTypes.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
TSharedPtr<FJsonObject> FRedlineJson::Parse(const FString& Text)
{
    TSharedPtr<FJsonObject> Object;
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Object);
    return Object;
}
FString FRedlineJson::Write(const TSharedRef<FJsonObject>& Json)
{
    FString Text; FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text)); return Text;
}
bool FRedlineJson::Vector(const TSharedPtr<FJsonObject>& Json, FVector& Out)
{
    double X,Y,Z;
    if (!Json || !Json->TryGetNumberField(TEXT("x"),X) || !Json->TryGetNumberField(TEXT("y"),Y) || !Json->TryGetNumberField(TEXT("z"),Z) || !FMath::IsFinite(X) || !FMath::IsFinite(Y) || !FMath::IsFinite(Z)) return false;
    Out=FVector(X,Y,Z); return true;
}
bool FRedlineJson::Quaternion(const TSharedPtr<FJsonObject>& Json, FQuat& Out)
{
    double X,Y,Z,W;
    if (!Json || !Json->TryGetNumberField(TEXT("x"),X) || !Json->TryGetNumberField(TEXT("y"),Y) || !Json->TryGetNumberField(TEXT("z"),Z) || !Json->TryGetNumberField(TEXT("w"),W)) return false;
    FQuat Q(X,Y,Z,W);
    if (Q.ContainsNaN() || !FMath::IsFinite(Q.SizeSquared()) || FMath::Abs(Q.SizeSquared()-1.0)>0.01) return false;
    Out=Q.GetNormalized(); return true;
}
bool FRedlineJson::Transform(const TSharedPtr<FJsonObject>& Json, FTransform& Out)
{
    if (!Json) return false;
    const TSharedPtr<FJsonObject>* Translation; const TSharedPtr<FJsonObject>* Rotation;
    FVector P; FQuat Q;
    if (!Json->TryGetObjectField(TEXT("translation"),Translation) || !Json->TryGetObjectField(TEXT("rotation"),Rotation) || !Vector(*Translation,P) || !Quaternion(*Rotation,Q)) return false;
    Out=FTransform(Q,P); return true;
}
bool FRedlineJson::Stamp(const TSharedPtr<FJsonObject>& Json, double& Out)
{
    double Sec,Nanosec;
    if (!Json || !Json->TryGetNumberField(TEXT("sec"),Sec) || !Json->TryGetNumberField(TEXT("nanosec"),Nanosec) || !FMath::IsFinite(Sec) || !FMath::IsFinite(Nanosec) || Sec<0 || Nanosec<0 || Nanosec>=1e9 || Sec!=FMath::FloorToDouble(Sec) || Nanosec!=FMath::FloorToDouble(Nanosec)) return false;
    Out=Sec+Nanosec/1e9; return true;
}
bool FRedlineOdometry::Parse(const TSharedPtr<FJsonObject>& Json, FRedlineOdometry& Out, FString& Error)
{
    const TSharedPtr<FJsonObject>* Header; const TSharedPtr<FJsonObject>* StampObject; const TSharedPtr<FJsonObject>* PoseCov; const TSharedPtr<FJsonObject>* Pose; const TSharedPtr<FJsonObject>* Position; const TSharedPtr<FJsonObject>* Orientation;
    FRedlineOdometry Value;
    if (!Json || !Json->TryGetObjectField(TEXT("header"),Header) || !(*Header)->TryGetStringField(TEXT("frame_id"),Value.FrameId) || !(*Header)->TryGetObjectField(TEXT("stamp"),StampObject) || !FRedlineJson::Stamp(*StampObject,Value.PhysicsStampSec) || !Json->TryGetStringField(TEXT("child_frame_id"),Value.ChildFrameId) || !Json->TryGetObjectField(TEXT("pose"),PoseCov) || !(*PoseCov)->TryGetObjectField(TEXT("pose"),Pose) || !(*Pose)->TryGetObjectField(TEXT("position"),Position) || !(*Pose)->TryGetObjectField(TEXT("orientation"),Orientation) || !FRedlineJson::Vector(*Position,Value.PositionMetres) || !FRedlineJson::Quaternion(*Orientation,Value.Orientation) || Value.FrameId.IsEmpty() || Value.ChildFrameId.IsEmpty())
    { Error=TEXT("Invalid odometry: header/frame/stamp/finite pose/unit quaternion required"); return false; }
    Out=MoveTemp(Value); return true;
}
