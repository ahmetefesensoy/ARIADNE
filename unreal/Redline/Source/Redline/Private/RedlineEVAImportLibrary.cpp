#include "RedlineEVAImportLibrary.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimSequence.h"
#include "Engine/StaticMesh.h"
#include "PhysicsEngine/BodySetup.h"
#if WITH_EDITOR
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#endif
bool URedlineEVAImportLibrary::PrepareInteriorQueryCollision(UStaticMesh* Mesh)
{
#if WITH_EDITOR
    if(!Mesh || Mesh->GetNumTriangles(0)<=0)return false;
    Mesh->CreateBodySetup();auto* Body=Mesh->GetBodySetup();if(!Body)return false;
    Body->CollisionTraceFlag=CTF_UseComplexAsSimple;
    Body->InvalidatePhysicsData();Body->CreatePhysicsMeshes();Mesh->MarkPackageDirty();return true;
#else
    return false;
#endif
}
bool URedlineEVAImportLibrary::NormalizeLocomotionRoot(USkeletalMesh* Mesh,UAnimSequence* A)
{
#if WITH_EDITOR
    if(!Mesh || !A || !Mesh->GetSkeleton() || Mesh->GetSkeleton()!=A->GetSkeleton())return false;
    const auto& Ref=Mesh->GetRefSkeleton();if(Ref.GetNum()==0)return false;
    const FName Root=Ref.GetBoneName(0);auto* Model=A->GetDataModel();
    if(!Model || !Model->IsValidBoneTrackName(Root))return false;
    TArray<FTransform> Keys;Model->GetBoneTrackTransforms(Root,Keys);if(Keys.IsEmpty())return false;
    const FVector BindScale=Ref.GetRefBonePose()[0].GetScale3D(),Original=Keys[0].GetScale3D();
    if(Original.GetAbsMin()<1e-6 || BindScale.GetAbsMin()<1e-6)return false;
    TArray<FVector> Position,Scale;TArray<FQuat> Rotation;
    const FVector Ratio=BindScale/Original;
    for(const FTransform& Key:Keys)
    {
        if(!Key.GetScale3D().Equals(Original,1e-4))return false; // never erase authored scale animation
        Position.Add(Key.GetTranslation()*Ratio);Rotation.Add(Key.GetRotation());Scale.Add(BindScale);
    }
    if(!A->GetController().SetBoneTrackKeys(Root,Position,Rotation,Scale,false))return false;
    A->bEnableRootMotion=false;A->bForceRootLock=true;A->RootMotionRootLock=ERootMotionRootLock::AnimFirstFrame;
    A->MarkPackageDirty();A->PostEditChange();return true;
#else
    return false;
#endif
}
bool URedlineEVAImportLibrary::MakeSeatedIdle(USkeletalMesh* Mesh,UAnimSequence* SourceIdle,UAnimSequence* A)
{
#if WITH_EDITOR
    if(!Mesh || !SourceIdle || !A || SourceIdle==A || !Mesh->GetSkeleton() ||
       Mesh->GetSkeleton()!=SourceIdle->GetSkeleton() || Mesh->GetSkeleton()!=A->GetSkeleton())return false;
    const auto& Ref=Mesh->GetRefSkeleton();auto* SourceModel=SourceIdle->GetDataModel();auto* Model=A->GetDataModel();
    if(!SourceModel || !Model || Model==SourceModel || Ref.GetNum()==0)return false;
    TArray<FName> SourceNames;SourceModel->GetBoneTrackNames(SourceNames);
    TMap<FName,TArray<FTransform>> SourceTracks;
    for(const FName& Name:SourceNames)
    {
        TArray<FTransform> Keys;SourceModel->GetBoneTrackTransforms(Name,Keys);if(Keys.IsEmpty())return false;
        for(const FTransform& Key:Keys)if(Key.ContainsNaN())return false;
        SourceTracks.Add(Name,MoveTemp(Keys));
    }
    const FName Root=Ref.GetBoneName(0);
    const auto* SourceRoot=SourceTracks.Find(Root);
    if(!SourceRoot || !(*SourceRoot)[0].GetScale3D().Equals(Ref.GetRefBonePose()[0].GetScale3D(),1e-3))return false;
    TArray<FTransform> Component;Component.SetNum(Ref.GetNum());
    for(int32 I=0;I<Ref.GetNum();++I){const int32 Parent=Ref.GetParentIndex(I);Component[I]=Parent==INDEX_NONE ? Ref.GetRefBonePose()[I] : Ref.GetRefBonePose()[I]*Component[Parent];}
    const int32 Pelvis=Ref.FindBoneIndex(TEXT("pelvis")),Calf=Ref.FindBoneIndex(TEXT("calf_l")),Foot=Ref.FindBoneIndex(TEXT("foot_l"));
    if(Pelvis<0 || Calf<0 || Foot<0)return false;
    const double Shin=FVector::Distance(Component[Calf].GetTranslation(),Component[Foot].GetTranslation());
    // Keep the bind-pose foot clearance; bend the legs without scaling bones.
    const double RootShift=Shin+Component[Foot].GetTranslation().Z-Component[Pelvis].GetTranslation().Z;
    TMap<FName,FVector> DesiredDirection;
    for(const FString Side:{FString(TEXT("l")),FString(TEXT("r"))})
    {
        DesiredDirection.Add(FName(TEXT("thigh_")+Side),FVector(1,0,0));
        DesiredDirection.Add(FName(TEXT("calf_")+Side),FVector(0,0,-1));
        DesiredDirection.Add(FName(TEXT("upperarm_")+Side),FVector(.2,Side==TEXT("l") ? -.15 : .15,-1).GetSafeNormal());
        DesiredDirection.Add(FName(TEXT("lowerarm_")+Side),FVector(1,0,-.15).GetSafeNormal());
    }
    TMap<FName,FName> Tip;
    Tip.Add(TEXT("thigh_l"),TEXT("calf_l"));Tip.Add(TEXT("thigh_r"),TEXT("calf_r"));
    Tip.Add(TEXT("calf_l"),TEXT("foot_l"));Tip.Add(TEXT("calf_r"),TEXT("foot_r"));
    Tip.Add(TEXT("upperarm_l"),TEXT("lowerarm_l"));Tip.Add(TEXT("upperarm_r"),TEXT("lowerarm_r"));
    Tip.Add(TEXT("lowerarm_l"),TEXT("hand_l"));Tip.Add(TEXT("lowerarm_r"),TEXT("hand_r"));
    // Validate the required rig before changing the derivative.
    for(const auto& Pair:DesiredDirection)
        if(Ref.FindBoneIndex(Pair.Key)<0 || Ref.FindBoneIndex(Tip.FindChecked(Pair.Key))<0 || !SourceTracks.Contains(Pair.Key))return false;
    auto& Controller=A->GetController();
    Controller.SetFrameRate(SourceModel->GetFrameRate(),false);
    Controller.SetNumberOfFrames(FFrameNumber(SourceModel->GetNumberOfFrames()),false);
    TArray<FName> TargetNames;Model->GetBoneTrackNames(TargetNames);
    for(const FName& Name:TargetNames)if(!SourceTracks.Contains(Name) && !Controller.RemoveBoneTrack(Name,false))return false;
    auto WriteKeys=[&](FName Name,const TArray<FTransform>& Keys,const FQuat* FixedRotation,double RootOffset)
    {
        if(!Model->IsValidBoneTrackName(Name) && !Controller.AddBoneCurve(Name,false))return false;
        TArray<FVector> Position,Scale;TArray<FQuat> Rotation;
        for(const FTransform& Key:Keys)
        {
            Position.Add(Key.GetTranslation()+FVector(0,0,RootOffset));Scale.Add(Key.GetScale3D());
            Rotation.Add(FixedRotation ? *FixedRotation : Key.GetRotation());
        }
        return Controller.SetBoneTrackKeys(Name,Position,Rotation,Scale,false);
    };
    // Rebuild every bone from the original clip, not from last import's derivative.
    // This also retains the original breathing/spine motion and frame count.
    for(const FName& Name:SourceNames)if(!WriteKeys(Name,SourceTracks.FindChecked(Name),nullptr,0))return false;
    TArray<FQuat> Rotations;Rotations.SetNum(Ref.GetNum());
    for(int32 I=0;I<Ref.GetNum();++I)
    {
        const FName Name=Ref.GetBoneName(I);const int32 Parent=Ref.GetParentIndex(I);
        const FQuat ParentQ=Parent<0 ? FQuat::Identity : Rotations[Parent];
        // UE transform Local*Parent composes quaternions ParentQ*LocalQ.
        Rotations[I]=ParentQ*Ref.GetRefBonePose()[I].GetRotation();
        if(const FVector* Desired=DesiredDirection.Find(Name))
        {
            const int32 T=Ref.FindBoneIndex(Tip.FindChecked(Name));if(T<0)return false;
            const FVector OriginalDirection=(Component[T].GetTranslation()-Component[I].GetTranslation()).GetSafeNormal();
            Rotations[I]=FQuat::FindBetweenNormals(OriginalDirection,*Desired)*Component[I].GetRotation();
            const FQuat Local=(ParentQ.Inverse()*Rotations[I]).GetNormalized();
            if(!WriteKeys(Name,SourceTracks.FindChecked(Name),&Local,0))return false;
        }
    }
    if(!WriteKeys(Root,SourceTracks.FindChecked(Root),nullptr,RootShift))return false;
    A->bEnableRootMotion=false;A->bForceRootLock=true;A->RootMotionRootLock=ERootMotionRootLock::AnimFirstFrame;
    A->MarkPackageDirty();A->PostEditChange();return true;
#else
    return false;
#endif
}
