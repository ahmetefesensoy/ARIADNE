param([string]$Voice='Microsoft Tolga')
$ErrorActionPreference='Stop'
$repoRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$folder=Join-Path $repoRoot 'assets/narrative/prologue_v1'
$scriptFile=Join-Path $folder 'script.json'
$scriptData=Get-Content -LiteralPath $scriptFile -Raw -Encoding utf8 | ConvertFrom-Json
Add-Type -AssemblyName System.Speech
$synth=[System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
    $voices=@($synth.GetInstalledVoices() | ForEach-Object {$_.VoiceInfo.Name})
    if($Voice -notin $voices){throw "Requested installed voice is unavailable: $Voice"}
    $synth.SelectVoice($Voice)
    $synth.Rate=-1
    $synth.Volume=85
    $files=@()
    foreach($shot in (@($scriptData.shots)+@($scriptData.mission_intros))){
        $path=Join-Path $folder $shot.voice
        $synth.SetOutputToWaveFile($path)
        $synth.Speak([string]$shot.subtitle)
        $synth.SetOutputToNull()
        $files+=[ordered]@{id=$shot.id;file=$shot.voice;sha256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
    }
    [ordered]@{created_at_utc=[DateTime]::UtcNow.ToString('o');status='SCENARIO';method='local Windows System.Speech text-to-speech';voice=$Voice;language='tr-TR';synthetic_voice=$true;human_voice_actor=$false;credits_spent=0;script_sha256=(Get-FileHash -LiteralPath $scriptFile).Hash.ToLowerInvariant();files=$files} |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $folder 'voice_provenance.json') -Encoding utf8
    Write-Output "Prepared $($files.Count) local Turkish narration clips."
}
finally {$synth.Dispose()}
