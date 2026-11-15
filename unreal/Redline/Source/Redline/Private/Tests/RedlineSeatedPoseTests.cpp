#include "Misc/AutomationTest.h"
#include "RedlineEVAImportLibrary.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "UObject/Package.h"
#include "UObject/StrongObjectPtr.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
namespace RedlineSeatedPoseTests
{
using FTracks=TMap<FName,TArray<FTransform>>;

FTracks Snapshot(const IAnimationDataModel& Model)
{
    TArray<FName> Names;Model.GetBoneTrackNames(Names);FTracks Tracks;
    for(const FName& Name:Names)
    {
        TArray<FTransform> Keys;Model.GetBoneTrackTransforms(Name,Keys);Tracks.Add(Name,MoveTemp(Keys));
    }
    return Tracks;
}

bool SameTracks(const FTracks& A,const FTracks& B)
{
    if(A.Num()!=B.Num())return false;
    for(const auto& Pair:A)
    {
        const auto* Other=B.Find(Pair.Key);if(!Other || Pair.Value.Num()!=Other->Num())return false;
        for(int32 I=0;I<Pair.Value.Num();++I)if(!Pair.Value[I].Equals((*Other)[I],1e-7))return false;
    }
    return true;
}

TArray<FTransform> ComponentPose(const FReferenceSkeleton& Ref,const IAnimationDataModel* Model,int32 Frame)
{
    TArray<FTransform> Component;Component.SetNum(Ref.GetNum());
    for(int32 I=0;I<Ref.GetNum();++I)
    {
        const FName Name=Ref.GetBoneName(I);FTransform Local=Ref.GetRefBonePose()[I];
        if(Model && Model->IsValidBoneTrackName(Name))Local=Model->GetBoneTrackTransform(Name,FFrameNumber(Frame));
        const int32 Parent=Ref.GetParentIndex(I);Component[I]=Parent<0 ? Local : Local*Component[Parent];
    }
    return Component;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineSeatedPoseIdempotent,"Redline.Prologue.SeatedPoseIdempotent",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineSeatedPoseIdempotent::RunTest(const FString& Parameters)
{
    using namespace RedlineSeatedPoseTests;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/EVAFixtures/Astronaut/SK_Astronaut.SK_Astronaut"));
    auto* Source=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/EVAFixtures/Astronaut/AN_Idle.AN_Idle"));
    if(!TestNotNull(TEXT("approved mesh"),Mesh) || !TestNotNull(TEXT("immutable standing idle"),Source))return false;
    const auto* SourceModel=Source->GetDataModel();if(!TestNotNull(TEXT("source animation model"),SourceModel))return false;
    const FTracks SourceBefore=Snapshot(*SourceModel);const double OriginalLength=Source->GetPlayLength();
    const int32 OriginalFrames=SourceModel->GetNumberOfFrames();const FFrameRate OriginalRate=SourceModel->GetFrameRate();
    const bool SourceWasDirty=Source->GetOutermost()->IsDirty();
    TStrongObjectPtr<UAnimSequence> Derived(DuplicateObject<UAnimSequence>(Source,GetTransientPackage(),MakeUniqueObjectName(GetTransientPackage(),UAnimSequence::StaticClass(),TEXT("SeatedIdempotence"))));
    if(!TestNotNull(TEXT("transient derivative"),Derived.Get()))return false;
    if(!TestTrue(TEXT("first derivation"),URedlineEVAImportLibrary::MakeSeatedIdle(Mesh,Source,Derived.Get())))return false;
    const FTracks First=Snapshot(*Derived->GetDataModel());
    TestTrue(TEXT("original duration retained"),FMath::IsNearlyEqual(static_cast<double>(Derived->GetPlayLength()),OriginalLength,1e-6));
    TestEqual(TEXT("original frame count retained"),Derived->GetDataModel()->GetNumberOfFrames(),OriginalFrames);
    TestTrue(TEXT("original frame rate retained"),Derived->GetDataModel()->GetFrameRate()==OriginalRate);
    if(!TestTrue(TEXT("second derivation into same target"),URedlineEVAImportLibrary::MakeSeatedIdle(Mesh,Source,Derived.Get())))return false;
    TestTrue(TEXT("all bone keys identical after rerun; root cannot drift"),SameTracks(First,Snapshot(*Derived->GetDataModel())));
    TestTrue(TEXT("rerun preserves clip duration"),FMath::IsNearlyEqual(static_cast<double>(Derived->GetPlayLength()),OriginalLength,1e-6));
    TestFalse(TEXT("in-place conversion rejected"),URedlineEVAImportLibrary::MakeSeatedIdle(Mesh,Source,Source));
    TestTrue(TEXT("all source keys remain unchanged"),SameTracks(SourceBefore,Snapshot(*Source->GetDataModel())));
    TestEqual(TEXT("source dirty flag remains unchanged"),Source->GetOutermost()->IsDirty(),SourceWasDirty);
    const auto& Ref=Mesh->GetRefSkeleton();const auto Bind=ComponentPose(Ref,nullptr,0);
    const int32 Pelvis=Ref.FindBoneIndex(TEXT("pelvis")),Calf=Ref.FindBoneIndex(TEXT("calf_l")),Foot=Ref.FindBoneIndex(TEXT("foot_l"));
    if(!TestTrue(TEXT("seated rig landmarks exist"),Pelvis>=0 && Calf>=0 && Foot>=0))return false;
    const double ExpectedShift=FVector::Distance(Bind[Calf].GetTranslation(),Bind[Foot].GetTranslation())+Bind[Foot].GetTranslation().Z-Bind[Pelvis].GetTranslation().Z;
    const FName Root=Ref.GetBoneName(0);const auto* OriginalRoot=SourceBefore.Find(Root);const auto* SeatedRoot=First.Find(Root);
    if(!TestTrue(TEXT("root tracks retained"),OriginalRoot && SeatedRoot && OriginalRoot->Num()==SeatedRoot->Num()))return false;
    for(int32 I=0;I<OriginalRoot->Num();++I)
    {
        const FTransform& Standing=(*OriginalRoot)[I];const FTransform& Sitting=(*SeatedRoot)[I];
        if(!TestTrue(FString::Printf(TEXT("root key %d has exactly one lowering offset"),I),(Sitting.GetTranslation()-Standing.GetTranslation()).Equals(FVector(0,0,ExpectedShift),1e-4)))break;
        if(!TestTrue(TEXT("authored root orientation and scale preserved"),Sitting.GetRotation().Equals(Standing.GetRotation(),1e-6) && Sitting.GetScale3D().Equals(Standing.GetScale3D(),1e-6)))break;
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRedlineSeatedPoseGeometry,"Redline.Prologue.SeatedPoseGeometry",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FRedlineSeatedPoseGeometry::RunTest(const FString& Parameters)
{
    using namespace RedlineSeatedPoseTests;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/EVAFixtures/Astronaut/SK_Astronaut.SK_Astronaut"));
    auto* Source=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/EVAFixtures/Astronaut/AN_Idle.AN_Idle"));
    if(!TestNotNull(TEXT("approved mesh"),Mesh) || !TestNotNull(TEXT("standing source"),Source))return false;
    TStrongObjectPtr<UAnimSequence> Derived(DuplicateObject<UAnimSequence>(Source,GetTransientPackage(),MakeUniqueObjectName(GetTransientPackage(),UAnimSequence::StaticClass(),TEXT("SeatedGeometry"))));
    if(!TestTrue(TEXT("derive seated clip"),URedlineEVAImportLibrary::MakeSeatedIdle(Mesh,Source,Derived.Get())))return false;
    const auto& Ref=Mesh->GetRefSkeleton();const auto Bind=ComponentPose(Ref,nullptr,0);const auto* Model=Derived->GetDataModel();
    const int32 Head=Ref.FindBoneIndex(TEXT("head")),Pelvis=Ref.FindBoneIndex(TEXT("pelvis"));
    if(!TestTrue(TEXT("body landmarks exist"),Head>=0 && Pelvis>=0))return false;
    for(int32 Frame:{0,Model->GetNumberOfFrames()/2,Model->GetNumberOfFrames()})
    {
        const auto Sitting=ComponentPose(Ref,Model,Frame);const auto Standing=ComponentPose(Ref,Source->GetDataModel(),Frame);
        for(const TCHAR* Side:{TEXT("l"),TEXT("r")})
        {
            const int32 Thigh=Ref.FindBoneIndex(FName(*(FString(TEXT("thigh_"))+Side)));
            const int32 Calf=Ref.FindBoneIndex(FName(*(FString(TEXT("calf_"))+Side)));
            const int32 Foot=Ref.FindBoneIndex(FName(*(FString(TEXT("foot_"))+Side)));
            if(!TestTrue(TEXT("leg landmarks exist"),Thigh>=0 && Calf>=0 && Foot>=0))return false;
            const FVector UpperLeg=Sitting[Calf].GetTranslation()-Sitting[Thigh].GetTranslation();
            const FVector LowerLeg=Sitting[Foot].GetTranslation()-Sitting[Calf].GetTranslation();
            const double BindThigh=FVector::Dist(Bind[Calf].GetTranslation(),Bind[Thigh].GetTranslation());
            const double BindShin=FVector::Dist(Bind[Foot].GetTranslation(),Bind[Calf].GetTranslation());
            const FString Sample=FString::Printf(TEXT("frame %d %s"),Frame,Side);
            // FK checks expose quaternion multiplication errors even when every local quaternion is normalized.
            TestTrue(Sample+TEXT(" thigh points forward"),FVector::DotProduct(UpperLeg.GetSafeNormal(),FVector::ForwardVector)>.95);
            TestTrue(Sample+TEXT(" shin points down"),FVector::DotProduct(LowerLeg.GetSafeNormal(),-FVector::UpVector)>.95);
            TestTrue(Sample+TEXT(" thigh length preserved"),FMath::IsNearlyEqual(UpperLeg.Length(),BindThigh,BindThigh*.01));
            TestTrue(Sample+TEXT(" shin length preserved"),FMath::IsNearlyEqual(LowerLeg.Length(),BindShin,BindShin*.01));
            TestTrue(Sample+TEXT(" foot stays near bind floor height"),FMath::Abs(Sitting[Foot].GetTranslation().Z-Bind[Foot].GetTranslation().Z)<10.0);
            const double StandingHeight=Standing[Head].GetTranslation().Z-Standing[Foot].GetTranslation().Z;
            const double SeatedHeight=Sitting[Head].GetTranslation().Z-Sitting[Foot].GetTranslation().Z;
            AddInfo(FString::Printf(TEXT("%s standing head-foot %.3fcm seated %.3fcm foot floor delta %.3fcm"),*Sample,StandingHeight,SeatedHeight,Sitting[Foot].GetTranslation().Z-Bind[Foot].GetTranslation().Z));
            TestTrue(Sample+TEXT(" human seated height below standing height"),SeatedHeight>StandingHeight*.5 && SeatedHeight<StandingHeight*.9);
        }
        for(const auto& Pair:Snapshot(*Model))
            for(const FTransform& Key:Pair.Value)
                if(!Key.GetRotation().IsNormalized()){AddError(TEXT("seated animation contains a non-unit quaternion"));return false;}
        TestTrue(TEXT("pelvis lowers by a human seated amount"),Standing[Pelvis].GetTranslation().Z-Sitting[Pelvis].GetTranslation().Z>20.0 && Standing[Pelvis].GetTranslation().Z-Sitting[Pelvis].GetTranslation().Z<70.0);
    }
    return true;
}
#endif
