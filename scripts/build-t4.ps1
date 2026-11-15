param(
    [string]$EngineRoot = 'C:/Users/USER/Desktop/UE_5.8',
    [string]$BuildRoot = "$env:LOCALAPPDATA/Redline/T4Build/Redline"
)
$ErrorActionPreference = 'Stop'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$sourceRoot = Join-Path $repoRoot 'unreal/Redline'
$resolvedBuild = [System.IO.Path]::GetFullPath($BuildRoot)
if ($resolvedBuild -match '[^\x00-\x7F]' -or $resolvedBuild.StartsWith($sourceRoot)) { throw 'BuildRoot must be ASCII and outside source tree' }
$inputs = Get-ChildItem -LiteralPath $sourceRoot -File -Recurse | Where-Object {
    $_.FullName -notmatch '[\\/](Binaries|Intermediate|Saved|DerivedDataCache|Content)[\\/]'
} | Sort-Object FullName
$records = @()
foreach ($inputFile in $inputs) {
    $relative = [System.IO.Path]::GetRelativePath($sourceRoot,$inputFile.FullName)
    $target = Join-Path $resolvedBuild $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath $inputFile.FullName -Destination $target -Force
    $hash = (Get-FileHash -LiteralPath $inputFile.FullName -Algorithm SHA256).Hash
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $hash) { throw "Snapshot hash mismatch: $relative" }
    $records += [ordered]@{path=$relative;sha256=$hash;bytes=$inputFile.Length}
}
# A reused compiler cache is allowed only when its complete input file set is exact.
$snapshotInputs = @(Get-ChildItem -LiteralPath $resolvedBuild -File -Recurse | Where-Object {
    $_.FullName -notmatch '[\\/](Binaries|Intermediate|Saved|DerivedDataCache|Content)[\\/]'
} | ForEach-Object { [System.IO.Path]::GetRelativePath($resolvedBuild,$_.FullName) } | Sort-Object)
$expectedInputs = @($records | ForEach-Object path | Sort-Object)
if (Compare-Object $snapshotInputs $expectedInputs) { throw 'ASCII snapshot has additional or missing build inputs. Select a fresh BuildRoot.' }
$provenance = [ordered]@{ created_at_utc=[DateTime]::UtcNow.ToString('o'); source=$sourceRoot; workspace=$resolvedBuild; source_snapshot_verified=$true; files=$records; build_exit_code=$null }
$reportPath = Join-Path $repoRoot 'test-results/t4-build-source.json'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $reportPath) | Out-Null
$provenance | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding utf8
$project = Join-Path $resolvedBuild 'Redline.uproject'
& (Join-Path $EngineRoot 'Engine/Build/BatchFiles/Build.bat') RedlineEditor Win64 Development "-Project=$project" -WaitMutex -NoHotReloadFromIDE -NoUBA
$provenance.build_exit_code=$LASTEXITCODE
$provenance | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "T4 Unreal build failed: $LASTEXITCODE" }
foreach ($inputFile in $inputs) {
    $relative=[System.IO.Path]::GetRelativePath($sourceRoot,$inputFile.FullName)
    if ((Get-FileHash -LiteralPath $inputFile.FullName -Algorithm SHA256).Hash -ne ($records | Where-Object path -EQ $relative).sha256) { throw "Source changed during build: $relative" }
}
# Copy only compiled output back to the repository project, preserving the same source hashes.
foreach ($binaryRoot in @('Binaries','Plugins/RedlineBridge/Binaries')) {
    $built = Join-Path $resolvedBuild $binaryRoot
    if (Test-Path -LiteralPath $built) {
        $destination=Join-Path $sourceRoot $binaryRoot
        New-Item -ItemType Directory -Force -Path $destination | Out-Null
        Get-ChildItem -LiteralPath $built | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $destination -Recurse -Force }
    }
}
Write-Output "T4 project: $project"
