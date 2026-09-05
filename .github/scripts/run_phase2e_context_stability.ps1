param(
    [string]$Fixture = (Join-Path $PWD "tests\fixtures\phase2e_human_render_closeout_ami_v1.json"),
    [string]$ModelStage = $env:SPANISH_TARGET_MODEL_STAGE,
    [string]$PortableSource = (Join-Path $PWD "dist\Video_Tunner")
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $Fixture)) { throw "No existe fixture Phase 2E.5: $Fixture" }
if (-not $ModelStage -or -not (Test-Path $ModelStage)) { throw "No existe staging fijado de large-v3-turbo: $ModelStage" }
if (-not (Test-Path $PortableSource)) { throw "No existe portable de análisis: $PortableSource" }

$spec = Get-Content $Fixture -Raw | ConvertFrom-Json
$isolated = Join-Path $env:RUNNER_TEMP "Video Tunner Phase2E Context Portable"
$caseRoot = Join-Path $env:RUNNER_TEMP "Video Tunner Phase2E Context Cases"
$diagRoot = Join-Path $env:RUNNER_TEMP "Video Tunner Phase2E Context Diagnostics"
Remove-Item $isolated -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $caseRoot -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $diagRoot -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item $PortableSource $isolated -Recurse
New-Item -ItemType Directory -Force -Path $caseRoot | Out-Null
New-Item -ItemType Directory -Force -Path $diagRoot | Out-Null

$exe = Join-Path $isolated "Video_Tunner.exe"
$ffmpeg = Join-Path $isolated "Tools\ffmpeg\bin\ffmpeg.exe"
$ffprobe = Join-Path $isolated "Tools\ffmpeg\bin\ffprobe.exe"
$hostPython = (Get-Command python -ErrorAction Stop).Source
foreach ($path in @($exe, $ffmpeg, $ffprobe)) {
    if (-not (Test-Path $path)) { throw "Falta herramienta portable: $path" }
}

$modelDestination = Join-Path $isolated "Models\whisper\large-v3-turbo"
Remove-Item $modelDestination -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $modelDestination | Out-Null
Copy-Item (Join-Path $ModelStage "*") $modelDestination -Recurse -Force

$originalPath = $env:PATH
$env:VIDEO_TUNNER_PORTABLE_STRICT = "1"
Remove-Item Env:VIDEO_TUNNER_FFMPEG_DIR -ErrorAction SilentlyContinue
Remove-Item Env:VIDEO_TUNNER_MODEL_DIR -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:HF_HOME = Join-Path $isolated "Cache\huggingface-home"
$env:HUGGINGFACE_HUB_CACHE = Join-Path $isolated "Cache\huggingface-hub"
$env:HF_HUB_OFFLINE = "1"
$env:HF_HUB_DISABLE_XET = "1"
$env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"

$results = [System.Collections.Generic.List[object]]::new()
foreach ($case in @($spec.cases)) {
    $id = [string]$case.id
    $sourceId = [string]$case.audio_source_id
    $envName = "AMI_CLOSEOUT_{0}_WAV" -f ($sourceId.ToUpperInvariant() -replace '[^A-Z0-9]', '')
    $sourceWav = [Environment]::GetEnvironmentVariable($envName)
    if (-not $sourceWav -or -not (Test-Path $sourceWav)) { throw "No existe audio AMI para $id ($envName)." }

    $root = Join-Path $caseRoot $id
    $analysisOutput = Join-Path $root "Analysis"
    New-Item -ItemType Directory -Force -Path $root | Out-Null
    New-Item -ItemType Directory -Force -Path $analysisOutput | Out-Null
    $clipWav = Join-Path $root "$id.wav"
    $video = Join-Path $root "$id.mp4"

    & $ffmpeg -hide_banner -loglevel error -y `
        -ss ([string]$case.render_clip_start) -t ([string]$case.render_clip_duration) -i $sourceWav `
        -ac 1 -ar 16000 -c:a pcm_s16le $clipWav
    if ($LASTEXITCODE -ne 0) { throw "No se pudo extraer $id." }
    $duration = [double](& $ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 $clipWav)
    & $ffmpeg -hide_banner -loglevel error -y `
        -f lavfi -i "color=c=black:s=320x240:r=25:d=$duration" `
        -i $clipWav -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac $video
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear vídeo para $id." }

    $stdout = (& $exe analyze $video `
        --model large-v3-turbo `
        --language en `
        --device cpu `
        --compute-type int8 `
        --output-dir $analysisOutput 2>&1 | Out-String)
    Write-Host $stdout
    if ($LASTEXITCODE -ne 0) { throw "Analyze falló para $id." }

    $analysisPath = Join-Path $analysisOutput "${id}_analysis.json"
    $diagPath = Join-Path $diagRoot "${id}.json"
    & $hostPython .\.github\scripts\summarize_phase2e_context_case.py `
        $analysisPath `
        --expected-text ([string]$case.reparandum_text) `
        --case-id $id `
        --output $diagPath | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "No se pudo resumir $id." }
    $diag = Get-Content $diagPath -Raw | ConvertFrom-Json
    $results.Add($diag)
    Write-Host "PHASE2E_CONTEXT_CASE=$id"
    Write-Host "PHASE2E_CONTEXT_CLASSIFICATION=$($diag.classification)"
    Write-Host "PHASE2E_CONTEXT_JOIN_STATUS=$($diag.join.status)"
    Write-Host "PHASE2E_CONTEXT_ELIGIBILITY_STATUS=$($diag.eligibility.status)"
    Write-Host "PHASE2E_CONTEXT_PROMOTION_STATUS=$($diag.promotion.status)"
}

$eligible = @($results | Where-Object { $_.classification -eq "promotion_eligible" }).Count
$joinBlocked = @($results | Where-Object { $_.classification -eq "context_blocked_at_join" }).Count
$acousticBlocked = @($results | Where-Object { $_.classification -eq "context_blocked_at_acoustic" }).Count
$manifest = [ordered]@{
    schema_version = 1
    record_type = "phase2e_context_stability_diagnostic"
    source_fixture = [IO.Path]::GetFileName($Fixture)
    case_count = $results.Count
    promotion_eligible_count = $eligible
    context_blocked_at_join_count = $joinBlocked
    context_blocked_at_acoustic_count = $acousticBlocked
    cases = @($results)
}
$manifest | ConvertTo-Json -Depth 30 | Set-Content -Path (Join-Path $diagRoot "manifest.json") -Encoding utf8
Write-Host "PHASE2E_CONTEXT_CASES=$($results.Count)"
Write-Host "PHASE2E_CONTEXT_PROMOTION_ELIGIBLE=$eligible"
Write-Host "PHASE2E_CONTEXT_BLOCKED_JOIN=$joinBlocked"
Write-Host "PHASE2E_CONTEXT_BLOCKED_ACOUSTIC=$acousticBlocked"
Write-Host "PHASE2E_CONTEXT_DIAGNOSTIC=COMPLETE"

$env:PATH = $originalPath
