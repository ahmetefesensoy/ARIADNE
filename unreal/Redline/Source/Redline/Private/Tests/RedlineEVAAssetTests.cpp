#include "Misc/AutomationTest.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimSequence.h"
#include "Materials/Material.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineEVAAssets,"Redline.EVA.PersistentSkeletonAndMaterial",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineEVAAssets::RunTest(const FString& Parameters)
{
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/EVAFixtures/Astronaut/SK_Astronaut.SK_Astronaut"));
    if(!TestNotNull(TEXT("existing imported astronaut"),Mesh))return false;
    TestNotNull(TEXT("skeleton persists in a fresh process"),Mesh->GetSkeleton());
    TestTrue(TEXT("material slot persists in a fresh process"),Mesh->GetMaterials().Num()>0 && Mesh->GetMaterials()[0].MaterialInterface!=nullptr);
    for(const TCHAR* Path:{TEXT("/Game/EVAFixtures/Astronaut/AN_Idle.AN_Idle"),TEXT("/Game/EVAFixtures/Astronaut/AN_Walk.AN_Walk")})
    {
        auto* A=LoadObject<UAnimSequence>(nullptr,Path);
        if(TestNotNull(TEXT("imported locomotion animation"),A))
        {
            TestTrue(TEXT("same persisted skeleton, not merely nonzero duration"),A->GetSkeleton()!=nullptr && A->GetSkeleton()==Mesh->GetSkeleton());TestTrue(TEXT("nonempty clip"),A->GetPlayLength()>1);
            const auto& Ref=Mesh->GetRefSkeleton();auto* Model=A->GetDataModel();
            auto Pose=[&](FName Name,bool Animated)
            {
                FTransform Out=FTransform::Identity;int32 I=Ref.FindBoneIndex(Name);
                while(I!=INDEX_NONE){const FName Bone=Ref.GetBoneName(I);FTransform Local=Ref.GetRefBonePose()[I];if(Animated && Model->IsValidBoneTrackName(Bone))Local=Model->GetBoneTrackTransform(Bone,FFrameNumber(0));Out=Out*Local;I=Ref.GetParentIndex(I);}return Out;
            };
            const double ReferenceHeight=FVector::Dist(Pose(TEXT("head"),false).GetTranslation(),Pose(TEXT("foot_l"),false).GetTranslation());
            const double AnimationHeight=FVector::Dist(Pose(TEXT("head"),true).GetTranslation(),Pose(TEXT("foot_l"),true).GetTranslation());
            AddInfo(FString::Printf(TEXT("%s reference head-foot=%.3fcm animated=%.3fcm rootRef=%s rootAnim=%s"),*A->GetName(),ReferenceHeight,AnimationHeight,*Ref.GetRefBonePose()[0].ToString(),*Model->GetBoneTrackTransform(Ref.GetBoneName(0),FFrameNumber(0)).ToString()));
            TestTrue(TEXT("animation preserves human scale"),AnimationHeight>ReferenceHeight*.75 && AnimationHeight<ReferenceHeight*1.25);
        }
    }
    auto* Material=LoadObject<UMaterial>(nullptr,TEXT("/Game/EVAFixtures/M_EV1_Original.M_EV1_Original"));
    TestTrue(TEXT("material supports skeletal rendering"),Material && Material->bUsedWithSkeletalMesh);
    return true;
}
#endif
