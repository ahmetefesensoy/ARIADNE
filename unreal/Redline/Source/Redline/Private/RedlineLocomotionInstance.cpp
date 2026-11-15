#include "RedlineLocomotionInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimationPoseData.h"
#include "AnimationRuntime.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

void FRedlineLocomotionState::Advance(float MeasuredSpeedCmS,float DeltaSeconds,double IdleLength,double WalkLength)
{
    if(!FMath::IsFinite(DeltaSeconds) || DeltaSeconds<=0)return;
    // Limit a single visible transition step after a hitch. Do not seek the
    // gait clock when a movement state changes or when the player taps a key.
    const double Dt=FMath::Min(double(DeltaSeconds),.1);
    const double Speed=FMath::IsFinite(MeasuredSpeedCmS) ? FMath::Clamp(double(MeasuredSpeedCmS),0.,500.) : 0.;
    const double Fraction=FMath::Clamp(Speed/30.,0.,1.);
    const double TargetWeight=Fraction*Fraction*(3.-2.*Fraction);
    const double Blend=1.-FMath::Exp(-Dt/.10);
    WalkWeight=FMath::Clamp(float(FMath::Lerp(double(WalkWeight),TargetWeight,Blend)),0.f,1.f);
    // 65 cm/s is the existing preview clip's authored cadence reference. It
    // is a visual assumption, not a calibrated gait or a running animation.
    const double TargetCadence=Speed/65.;
    Cadence=FMath::Clamp(float(FMath::Lerp(double(Cadence),TargetCadence,Blend)),0.f,500.f/65.f);
    if(FMath::IsFinite(IdleLength) && IdleLength>0)IdleTime=FMath::Fmod(IdleTime+Dt,IdleLength);
    if(FMath::IsFinite(WalkLength) && WalkLength>0)WalkTime=FMath::Fmod(WalkTime+Dt*Cadence,WalkLength);
}

struct FRedlineLocomotionProxy : FAnimInstanceProxy
{
    explicit FRedlineLocomotionProxy(UAnimInstance* Instance):FAnimInstanceProxy(Instance){}
    UAnimSequence* Idle=nullptr;
    UAnimSequence* Walk=nullptr;
    float Speed=0;
    FRedlineLocomotionState State;

    virtual void InitializeObjects(UAnimInstance* Instance) override
    {
        FAnimInstanceProxy::InitializeObjects(Instance);
        // Read UObjects/game state only here on the game thread. Evaluation
        // uses this proxy's snapshot, while the instance retains both assets.
        // Engine calls this again before evaluation after clearing pointers.
        const auto* Locomotion=CastChecked<URedlineLocomotionInstance>(Instance);
        Idle=Locomotion->Idle;Walk=Locomotion->Walk;Speed=Locomotion->MeasuredSpeed;
    }
    virtual void ClearObjects() override
    {FAnimInstanceProxy::ClearObjects();Idle=nullptr;Walk=nullptr;}
    virtual void UpdateAnimationNode(const FAnimationUpdateContext& Context) override
    {
        State.Advance(Speed,Context.GetDeltaTime(),Idle ? Idle->GetPlayLength() : 0,Walk ? Walk->GetPlayLength() : 0);
    }
    virtual bool Evaluate(FPoseContext& Output) override
    {
        Output.ResetToRefPose();
        if(!Idle || !Walk)return true;
        FPoseContext IdlePose(Output),WalkPose(Output);
        IdlePose.ResetToRefPose();WalkPose.ResetToRefPose();
        FAnimationPoseData IdleData(IdlePose),WalkData(WalkPose),ResultData(Output);
        Idle->GetAnimationPose(IdleData,FAnimExtractContext(State.IdleTime,false));
        Walk->GetAnimationPose(WalkData,FAnimExtractContext(State.WalkTime,false));
        FAnimationRuntime::BlendTwoPosesTogether(IdleData,WalkData,1.f-State.WalkWeight,ResultData);
        Output.Pose.NormalizeRotations();
        return true;
    }
};

URedlineLocomotionInstance::URedlineLocomotionInstance()
{RootMotionMode=ERootMotionMode::NoRootMotionExtraction;}
bool URedlineLocomotionInstance::Configure(UAnimSequence* InIdle,UAnimSequence* InWalk)
{
    const auto* Mesh=GetSkelMeshComponent() ? GetSkelMeshComponent()->GetSkeletalMeshAsset() : nullptr;
    if(!Mesh || !InIdle || !InWalk || InIdle->GetSkeleton()!=Mesh->GetSkeleton() || InWalk->GetSkeleton()!=Mesh->GetSkeleton() ||
        InIdle->IsValidAdditive() || InWalk->IsValidAdditive() || InIdle->GetPlayLength()<=0 || InWalk->GetPlayLength()<=0)return false;
    Idle=InIdle;Walk=InWalk;return true;
}
void URedlineLocomotionInstance::SetMeasuredSpeed(float SpeedCmS)
{check(IsInGameThread());MeasuredSpeed=FMath::IsFinite(SpeedCmS) ? FMath::Clamp(SpeedCmS,0.f,500.f) : 0.f;}
float URedlineLocomotionInstance::GetWalkWeight() const
{return GetProxyOnGameThread<FRedlineLocomotionProxy>().State.WalkWeight;}
float URedlineLocomotionInstance::GetCadence() const
{return GetProxyOnGameThread<FRedlineLocomotionProxy>().State.Cadence;}
double URedlineLocomotionInstance::GetWalkTime() const
{return GetProxyOnGameThread<FRedlineLocomotionProxy>().State.WalkTime;}
FAnimInstanceProxy* URedlineLocomotionInstance::CreateAnimInstanceProxy()
{return new FRedlineLocomotionProxy(this);}
void URedlineLocomotionInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy)
{delete static_cast<FRedlineLocomotionProxy*>(Proxy);}
