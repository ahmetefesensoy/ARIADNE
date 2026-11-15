param(
    [string]$BuildRoot="$env:LOCALAPPDATA/Redline/FieldWorkBuild/Redline",
    [string]$OutputRoot="$env:LOCALAPPDATA/Redline/TaskClips",
    [string[]]$Kinds=@('collect','xrf','weather','drill','lab','cache'),
    [ValidateRange(10,60)][int]$Seconds=28
)
$ErrorActionPreference='Stop'
$repoRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$engine='C:/Users/USER/Desktop/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$clipRecords=@()
foreach($kind in $Kinds){
    if($kind -notin @('collect','xrf','weather','drill','lab','cache')){throw "Unsupported filming fixture: $kind"}
    $name=@{collect='03_numune';xrf='04_xrf';weather='05_istasyon';drill='06_sondaj';lab='07_laboratuvar_ph';cache='08_numune_teslimi'}[$kind]
    $product=Join-Path $repoRoot 'test-results/tablet-lab-flow/verification.json'
    $args=@(('"{0}/Redline.uproject"' -f $BuildRoot),'/Game/EVAFixtures/BXW_EVA_SurfaceV2','-game','-windowed','-ResX=1280','-ResY=720',
        '-RedlineCampaign','-RedlineSkipPrologue','-RedlineRosbridgeUrl=ws://127.0.0.1:1/',
        ('-RedlineEVARuntime="{0}/data/engines/BXW/eva-runtime-v1.json"' -f $repoRoot),
        ('-RedlineTaskFilm={0}' -f $kind),('-RedlineFilmProduct="{0}"' -f $product),
        ('-RedlineShotDir="{0}"' -f $OutputRoot),('-RedlineShotName={0}' -f $name),('-RedlineShotSeconds={0}' -f $Seconds),
        '-RedlineShotFps=24','-RedlineShotAutoStart','-RedlineShotDelay=1','-RedlineShotExitAfter',
        '-ExecCmds="t.MaxFPS 40,r.ScreenPercentage 100,stat none"')
    $started=[DateTimeOffset]::UtcNow
    $process=Start-Process -FilePath $engine -ArgumentList $args -PassThru -WindowStyle Hidden
    Write-Output "Filming $kind; own process $($process.Id)"
    while(!$process.WaitForExit(10000)){Write-Output "Filming $kind remains active"}
    $folder=Get-ChildItem -LiteralPath $OutputRoot -Directory | Where-Object Name -Like "$name-*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if(!$folder){throw "No actual clip created for $kind"}
    $manifest=Join-Path $folder.FullName 'manifest.json'
    $capture=Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
    if(!$capture.complete -or $capture.saved_frames -lt 2 -or $capture.failure){throw "Incomplete actual recording $kind"}
    $record=[ordered]@{kind=$kind;folder=$folder.FullName;created_at_utc=$started.ToString('o');process_exit=$process.ExitCode;capture_manifest_sha256=(Get-FileHash -LiteralPath $manifest).Hash;source='Actual Unreal viewport; scripted SCENARIO task demonstration, no ROS commands';actual_live_mission=$false;data_product_record=$product;data_product_sha256=(Get-FileHash -LiteralPath $product).Hash}
    $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $folder.FullName 'task-film.json') -Encoding utf8
    $clipRecords+=$record
    $clipRecords | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $repoRoot 'test-results/task-film-captures.json') -Encoding utf8
    Write-Output "Captured $kind : $($capture.saved_frames) real frames"
}
