param([ValidateSet('storm','intro')][string]$Kind='storm')
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$build="$env:LOCALAPPDATA/Redline/FieldWorkBuild/Redline"
$out="$env:LOCALAPPDATA/Redline/StoryClips"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$name=if($Kind -eq 'storm'){'10_firtina_kayit_oynatimi'}else{'01_acilis_yeni_ses'}
$args=@(('"{0}/Redline.uproject"' -f $build),'/Game/EVAFixtures/BXW_EVA_SurfaceV2','-game','-windowed','-ResX=1280','-ResY=720','-RedlineCampaign','-RedlineReadOnlyFilm',('-RedlineEVARuntime="{0}/data/engines/BXW/eva-runtime-v1.json"' -f $repo),('-RedlineShotDir="{0}"' -f $out),('-RedlineShotName={0}' -f $name),'-RedlineShotAutoStart','-RedlineShotDelay=1','-RedlineShotFps=24','-RedlineShotExitAfter','-ExecCmds="t.MaxFPS 40,r.ScreenPercentage 100"')
if($Kind -eq 'storm'){$args+=@('-RedlineSkipPrologue',('-RedlineFeed="{0}/test-results/storm-video/ue_feed.jsonl"' -f $repo),'-RedlineShotSeconds=90')}
else{$args+=@('-RedlineRosbridgeUrl=ws://127.0.0.1:1/','-RedlineShotSeconds=64')}
$process=Start-Process -FilePath 'C:/Users/USER/Desktop/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
Write-Output "Raw $Kind capture PID $($process.Id)"
while(!$process.WaitForExit(10000)){Write-Output "Raw $Kind remains active"}
Write-Output "Raw capture process exit $($process.ExitCode)"
