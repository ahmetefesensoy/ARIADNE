param(
    [Parameter(Mandatory)][uri]$RosbridgeUrl,
    [ValidateRange(0,120)][double]$ProbeSeconds=0,
    [switch]$SkipIntro,
    [switch]$SkipPrologue,
    [switch]$Campaign,
    [switch]$OpenBoard,
    [string]$ShotDirectory,
    [string]$ShotName='redline_oynanis',
    [ValidateRange(1,120)][double]$ShotSeconds=90,
    [string]$Map='/Game/EVAFixtures/BXW_EVA_SurfaceV2',
    [string]$EngineRoot='C:/Users/USER/Desktop/UE_5.8',
    [string]$BuildRoot="$env:LOCALAPPDATA/Redline/T4Build/Redline"
)
$ErrorActionPreference='Stop'
$repoRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$profile=Join-Path $repoRoot 'data/engines/BXW/eva-runtime-v1.json'
$project=Join-Path $BuildRoot 'Redline.uproject'
if($RosbridgeUrl.Scheme -notin @('ws','wss')){throw 'RosbridgeUrl must use ws or wss'}
if($Map -notmatch '^/Game/[A-Za-z0-9_/]+$'){throw 'Map must be a /Game package path'}
foreach($path in @($profile,$project,(Join-Path $BuildRoot ('Content/'+$Map.Substring(6)+'.umap')))){if(!(Test-Path -LiteralPath $path)){throw "Missing EVA input: $path"}}
$arguments=@(
    ('"{0}"' -f $project),$Map,'-game','-windowed','-ResX=1280','-ResY=720','-WinX=0','-WinY=0',
    ('-RedlineRosbridgeUrl={0}' -f $RosbridgeUrl.AbsoluteUri),
    ('-RedlineEVARuntime="{0}"' -f $profile),
    ('-RedlineEVAPoseLog="{0}/Redline/t5-eva-live-pose.csv"' -f $env:LOCALAPPDATA),
    '-ExecCmds="t.MaxFPS 60,r.ScreenPercentage 150,sg.ShadowQuality 3,sg.TextureQuality 3,r.MaxAnisotropy 16,r.Streaming.PoolSize 4096"'
)
if($ProbeSeconds -gt 0){$arguments+=('-RedlineEVAProbeSeconds={0}' -f $ProbeSeconds.ToString([Globalization.CultureInfo]::InvariantCulture))}
if($Campaign){$arguments+='-RedlineCampaign'}
elseif(!$SkipIntro -and $ProbeSeconds -eq 0){$arguments+='-RedlineEVAIntro'}
if($SkipPrologue){$arguments+='-RedlineSkipPrologue'}
if($OpenBoard){$arguments+='-RedlineOpenBoard'}
if($ShotDirectory){
    if($ShotName -notmatch '^[A-Za-z0-9_-]{1,64}$'){throw 'ShotName must contain 1-64 letters, numbers, underscores or hyphens'}
    $shotRoot=[IO.Path]::GetFullPath($ShotDirectory)
    New-Item -ItemType Directory -Force -Path $shotRoot | Out-Null
    $arguments+=('-RedlineShotDir="{0}"' -f $shotRoot)
    $arguments+=('-RedlineShotName={0}' -f $ShotName)
    $arguments+=('-RedlineShotSeconds={0}' -f $ShotSeconds.ToString([Globalization.CultureInfo]::InvariantCulture))
}
$process=Start-Process -FilePath (Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor.exe') -ArgumentList $arguments -PassThru
Write-Output "EV1 game PID: $($process.Id)"
