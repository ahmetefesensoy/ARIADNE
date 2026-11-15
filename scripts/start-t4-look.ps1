param(
    [Parameter(Mandatory)][uri]$RosbridgeUrl,
    [string]$EngineRoot = 'C:/Users/USER/Desktop/UE_5.8',
    [string]$BuildRoot = "$env:LOCALAPPDATA/Redline/T4Build/Redline"
)
$ErrorActionPreference = 'Stop'
if ($RosbridgeUrl.Scheme -notin @('ws','wss')) { throw 'RosbridgeUrl must use ws or wss' }
$project = Join-Path $BuildRoot 'Redline.uproject'
$map = '/Game/VisualShowcase/BXW_Atmosphere_Autonomy'
foreach ($required in @($project, (Join-Path $BuildRoot 'Content/VisualShowcase/BXW_Atmosphere_Autonomy.umap'))) {
    if (!(Test-Path -LiteralPath $required)) { throw "Missing preview input: $required" }
}
# Physical pose and wheel animation are display-only. ROS/Gazebo remains the
# sole control/physics authority. Keys 1/2/3 change the SCENARIO physics factor;
# they do not change mission/PET time or bypass the navigation command chain.
$arguments = @(
    ('"{0}"' -f $project), $map, '-game', '-windowed',
    '-ResX=1280', '-ResY=720', '-WinX=0', '-WinY=0', '-RedlineTimeControl',
    '-RedlinePresentationPoseTopic=/redline/presentation/rover_1/odom',
    ('-RedlineRosbridgeUrl={0}' -f $RosbridgeUrl.AbsoluteUri),
    '-ExecCmds="t.MaxFPS 60,r.ScreenPercentage 200,sg.ShadowQuality 3,sg.TextureQuality 3,sg.EffectsQuality 3,r.MaxAnisotropy 16,r.Streaming.PoolSize 4096,r.Tonemapper.Sharpen 0.3"'
)
$process = Start-Process -FilePath (Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor.exe') -ArgumentList $arguments -PassThru
Write-Output "Unreal preview PID: $($process.Id)"
