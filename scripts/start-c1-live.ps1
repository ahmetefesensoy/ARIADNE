# Live storm chapter (C1) with the real Unreal EV1: one command for the backend, the game and F10 recording.
# The mission clock starts when the backend is up; the real sol 4190 alarm arrives 11.8 min later (x1, D018).
# Walk out toward the red line before then; when the alarm banner appears the line pulls in: walk home.
# Usage (PowerShell 7):  pwsh scripts/start-c1-live.ps1  [-Workspace <WSL path>] [-Port 9190] [-WithPrologue]
# Evidence: test-results/c1-bxw-<run>/ (capture.json, c1_summary.json); F10 clips: test-results/c1-live-unreal/shots.
param(
    [string]$Workspace='.cache/redline/ros/ws-5dacf41d08de2c4c-hupd88fp',
    [ValidateRange(1024,65535)][int]$Port=9190,
    [switch]$WithPrologue,
    [switch]$BackendOnly,
    # C1_SHOT: the real alarm arrives 2.0 min after start instead of 11.8 (film take).
    [ValidateSet('C1_SOL4190_CHAPTER','C1_SHOT')][string]$Scenario='C1_SOL4190_CHAPTER'
)
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$log=Join-Path $repo 'test-results/c1-live-unreal/backend.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
$ip=((wsl.exe --exec hostname -I) -split '\s+' | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' } | Select-Object -First 1)
if(!$ip){throw 'Could not read the WSL IP address'}
$ws=$Workspace
if(!$ws.StartsWith('/')){$ws=((wsl.exe --exec printenv HOME) | Select-Object -First 1).Trim()+'/'+$ws}
if($ws -notmatch '^/[A-Za-z0-9._/-]+$'){throw "Workspace must be a plain WSL path: $ws"}
# A separate hidden process: the backend outlives this script and the terminal it ran in.
$backend=Start-Process -FilePath wsl.exe -WindowStyle Hidden -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.err" `
    -ArgumentList @('--cd',"`"$repo`"",'--exec','env',"C1_ROSBRIDGE_PORT=$Port","C1_SCENARIO=config/scenarios/$Scenario.yaml",'bash','scripts/run-c1-live.sh',$ws)
Write-Output "C1 backend starting (PID $($backend.Id)); log: $log"
$deadline=(Get-Date).AddSeconds(150)
while($true){
    $client=[Net.Sockets.TcpClient]::new()
    try{ if($client.ConnectAsync($ip,$Port).Wait(700) -and $client.Connected){break} } catch {} finally { $client.Dispose() }
    if($backend.HasExited){Get-Content $log,"$log.err" -Tail 20; throw 'C1 backend stopped before rosbridge came up'}
    if((Get-Date) -gt $deadline){throw "rosbridge did not open on $($ip):$Port"}
    Start-Sleep -Milliseconds 800
}
$alarm=(Get-Date).AddMinutes($(if($Scenario -eq 'C1_SHOT'){2.0}else{11.8}))
Write-Output ("Backend up at {0:HH:mm:ss}. Real alarm expected about {1:HH:mm:ss} (PET 11.8 min)." -f (Get-Date),$alarm)
if($BackendOnly){Write-Output "Backend only: connect the game with -RosbridgeUrl ws://$($ip):$Port/ (PID $($backend.Id))."; return}
Write-Output 'Walk out toward the red line now. Press F10 about one minute before the alarm (one clip is at most 120 s).'
$eva=@{RosbridgeUrl="ws://$($ip):$Port/"; SkipIntro=$true; ShotDirectory=(Join-Path $repo 'test-results/c1-live-unreal/shots'); ShotName='c1_storm'; ShotSeconds=120}
if(!$WithPrologue){$eva.SkipPrologue=$true}
& (Join-Path $PSScriptRoot 'start-t5-eva.ps1') @eva
Write-Output "The backend keeps capturing for 25 min after start, then writes c1_summary.json (PID $($backend.Id); log $log)."
