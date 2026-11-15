using UnrealBuildTool;
public class Redline : ModuleRules
{
    public Redline(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new [] {"Core", "CoreUObject", "Engine", "DeveloperSettings", "RedlineBridge"});
        PrivateDependencyModuleNames.AddRange(new [] {"Json", "InputCore", "PhysicsCore", "ImageWrapper", "MediaAssets", "MovieSceneCapture", "AudioMixer", "Slate", "SlateCore", "RenderCore", "RHI"});
    }
}
