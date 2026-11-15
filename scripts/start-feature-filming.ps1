param(
    [Parameter(Mandatory)][uri]$RosbridgeUrl,
    [ValidateSet('human','drone','rover','task')][string]$View='human',
    [string]$Name='02_drone_live',
    [string]$BuildRoot="$env:LOCALAPPDATA/Redline/FieldWorkBuild/Redline",
    [string]$OutputRoot="$env:LOCALAPPDATA/Redline/LiveClips",
    [ValidateRange(1,120)][int]$Seconds=120,
    [switch]$AutoRecord,
    [switch]$Hidden,
    [string]$Rocks
)
$ErrorActionPreference='Stop'
if($RosbridgeUrl.Scheme -notin @('ws','wss')){throw 'A live ws/wss ROS bridge is required'}
if($Name -notmatch '^[A-Za-z0-9_-]{1,64}$'){throw 'Invalid shot name'}
$repoRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$project=Join-Path $BuildRoot 'Redline.uproject'
if(!(Test-Path -LiteralPath $project)){throw 'Build the exact source snapshot first'}
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$arguments=@(('"{0}"' -f $project),'/Game/EVAFixtures/BXW_EVA_SurfaceV2','-game','-windowed','-ResX=1280','-ResY=720','-WinX=0','-WinY=0',
    '-RedlineCampaign','-RedlineSkipPrologue','-RedlineFilming',('-RedlineFilmView={0}' -f $View),
    ('-RedlineRosbridgeUrl={0}' -f $RosbridgeUrl.AbsoluteUri),
    ('-RedlineEVARuntime="{0}/data/engines/BXW/eva-runtime-v1.json"' -f $repoRoot),
    ('-RedlineShotDir="{0}"' -f $OutputRoot),('-RedlineShotName={0}' -f $Name),('-RedlineShotSeconds={0}' -f $Seconds),'-RedlineShotFps=24',
    '-ExecCmds="t.MaxFPS 40,r.ScreenPercentage 100,stat none"')
if($AutoRecord){$arguments+=@('-RedlineShotAutoStart','-RedlineShotDelay=5')}
if($Rocks){if(!(Test-Path -LiteralPath $Rocks)){throw 'Matched Gazebo rock receipt missing'};$arguments+=('-RedlineFilmRocks="{0}"' -f [IO.Path]::GetFullPath($Rocks))}
# F5/F6/F7 switch only the presentation camera. Recording never auto-quits this
# live game. Hidden keeps unattended filming out of the user's active window.
$startOptions=@{FilePath='C:/Users/USER/Desktop/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe';ArgumentList=$arguments;PassThru=$true}
if($Hidden){$startOptions.WindowStyle='Hidden';$arguments+='-RedlineReadOnlyFilm';$startOptions.ArgumentList=$arguments}
$process=Start-Process @startOptions
[ordered]@{pid=$process.Id;rosbridge=$RosbridgeUrl.AbsoluteUri;view=$View;name=$Name;started_at_utc=[DateTimeOffset]::UtcNow.ToString('o');robot_authority='ROS/Gazebo';human_pose_fixture=$false;manual_recording_key='F10'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $repoRoot 'test-results/live-feature-game.json') -Encoding utf8
Write-Output "Interactive live game PID $($process.Id); F10 record, F5 rover, F6 drone, F7 human"
