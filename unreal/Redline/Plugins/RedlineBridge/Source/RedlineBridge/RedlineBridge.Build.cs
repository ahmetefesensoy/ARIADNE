using UnrealBuildTool;
public class RedlineBridge : ModuleRules
{
    public RedlineBridge(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new [] {"Core", "CoreUObject", "Engine", "Json", "DeveloperSettings"});
        PrivateDependencyModuleNames.AddRange(new [] {"WebSockets", "JsonUtilities", "ImageWrapper", "InputCore"});
    }
}
