param(
    [string]$FixtureRoot = $env:SPANISH_MODEL_FIXTURE_ROOT,
    [string]$ModelStage = $env:SPANISH_TARGET_MODEL_STAGE,
    [string]$PortableSource = (Join-Path $PWD "dist\Video_Tunner"),
    [string]$Reference = (Join-Path $PWD "Validation\spanish-large-v3-turbo-reference.txt"),
    [string]$Evaluator = (Join-Path $PWD ".github\scripts\evaluate_asr_reference.py"),
    [string]$BuildPython = (Get-Command python).Source
)

$ErrorActionPreference = "Stop"
if (-not $FixtureRoot -or -not (Test-Path $FixtureRoot)) {
    throw "No existe el directorio de fixture español: $FixtureRoot"
}
if (-not $ModelStage -or -not (Test-Path $ModelStage)) {
    throw "No existe el staging fijado de large-v3-turbo: $ModelStage"
}
if (-not (Test-Path $PortableSource)) {
    throw "No existe el portable de análisis: $PortableSource"
}

$isolated = Join-Path $env:RUNNER_TEMP "Video Tunner Spanish Target Portable"
Remove-Item $isolated -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item $PortableSource $isolated -Recurse

$exe = Join-Path $isolated "Video_Tunner.exe"
$ffmpeg = Join-Path $isolated "Tools\ffmpeg\bin\ffmpeg.exe"
$ffprobe = Join-Path $isolated "Tools\ffmpeg\bin\ffprobe.exe"

foreach ($id in @("A0006", "A0007", "A0013", "A0116")) {
    $ogg = Get-ChildItem $FixtureRoot -Filter "SpanishPod_newbie_lesson_${id}_dialogue.ogg" | Select-Object -First 1
    if (-not $ogg) { throw "Falta el diálogo descargado $id." }
    $wav = Join-Path $FixtureRoot "$id.wav"
    & $ffmpeg -hide_banner -loglevel error -y -i $ogg.FullName -ac 1 -ar 16000 -c:a pcm_s16le $wav
    if ($LASTEXITCODE -ne 0) { throw "No se pudo normalizar $id." }
}

$silence = Join-Path $FixtureRoot "silence.wav"
& $ffmpeg -hide_banner -loglevel error -y `
    -f lavfi -i "anullsrc=r=16000:cl=mono" -t 0.6 -c:a pcm_s16le $silence
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear la pausa determinista." }

Push-Location $FixtureRoot
try {
    @"
file 'A0006.wav'
file 'silence.wav'
file 'A0007.wav'
file 'silence.wav'
file 'A0013.wav'
file 'silence.wav'
file 'A0116.wav'
"@ | Set-Content -Encoding ascii "concat.txt"
    & $ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "concat.txt" `
        -ac 1 -ar 16000 -c:a pcm_s16le "spanish-real-speech.wav"
    if ($LASTEXITCODE -ne 0) { throw "No se pudo concatenar el fixture español." }
} finally {
    Pop-Location
}

$spoken = Join-Path $FixtureRoot "spanish-real-speech.wav"
$duration = [double](& $ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 $spoken)
if ($duration -lt 35.0 -or $duration -gt 60.0) {
    throw "Duración inesperada del fixture: $duration"
}

$video = Join-Path $FixtureRoot "spanish real speech.mp4"
& $ffmpeg -hide_banner -loglevel error -y `
    -f lavfi -i "color=c=black:s=320x240:r=25:d=$duration" `
    -i $spoken -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac $video
if ($LASTEXITCODE -ne 0) { throw "No se pudo construir el vídeo español de validación." }

Write-Host "SPANISH_FIXTURE_DURATION_SECONDS=$duration"
Write-Host "SPANISH_FIXTURE_SHA256=$((Get-FileHash $spoken -Algorithm SHA256).Hash)"

$modelDestination = Join-Path $isolated "Models\whisper\large-v3-turbo"
Remove-Item $modelDestination -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $modelDestination | Out-Null
Copy-Item (Join-Path $ModelStage "*") $modelDestination -Recurse -Force

$output = Join-Path $isolated "Output\large v3 turbo spanish"
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

if (Get-Command python -ErrorAction SilentlyContinue) { throw "Python sigue disponible en PATH." }
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) { throw "FFmpeg externo sigue disponible en PATH." }

$doctor = (& $exe doctor | Out-String | ConvertFrom-Json)
foreach ($module in @("faster_whisper", "ctranslate2", "onnxruntime", "tokenizers", "numpy", "av")) {
    if ($doctor.analysis_dependencies.$module.status -ne "available") {
        throw "Dependencia frozen no operativa: $module"
    }
}
if (-not $doctor.analysis_dependencies.silero_onnx.available) {
    throw "Silero ONNX no está disponible en el portable."
}

$modelStatus = (& $exe model status large-v3-turbo | Out-String | ConvertFrom-Json)
if (-not $modelStatus.available) { throw "large-v3-turbo staged no es reconocido como modelo local completo." }
if (-not $modelStatus.path.StartsWith((Join-Path $isolated "Models"))) {
    throw "El modelo quedó fuera del árbol portable."
}
$modelBytes = [long](Get-ChildItem $modelStatus.path -File -Recurse | Measure-Object -Property Length -Sum).Sum
if ($env:TARGET_MODEL_STAGE_BYTES -and $modelBytes -ne [long]$env:TARGET_MODEL_STAGE_BYTES) {
    throw "El tamaño del modelo cambió al copiarlo al portable: stage=$env:TARGET_MODEL_STAGE_BYTES portable=$modelBytes"
}

$stdoutPath = Join-Path $env:RUNNER_TEMP "large-v3-turbo-analyze.stdout.txt"
$stderrPath = Join-Path $env:RUNNER_TEMP "large-v3-turbo-analyze.stderr.txt"
$psi = [Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $exe
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
foreach ($argument in @(
    "analyze", $video,
    "--model", "large-v3-turbo",
    "--language", "es",
    "--device", "cpu",
    "--compute-type", "int8",
    "--output-dir", $output
)) {
    [void]$psi.ArgumentList.Add($argument)
}

$process = [Diagnostics.Process]::new()
$process.StartInfo = $psi
$watch = [Diagnostics.Stopwatch]::StartNew()
if (-not $process.Start()) { throw "No se pudo iniciar Video_Tunner.exe." }
$stdoutTask = $process.StandardOutput.ReadToEndAsync()
$stderrTask = $process.StandardError.ReadToEndAsync()
$peakWorkingSet = 0L
while (-not $process.HasExited) {
    try {
        $process.Refresh()
        $peakWorkingSet = [Math]::Max($peakWorkingSet, [long]$process.WorkingSet64)
    } catch {}
    Start-Sleep -Milliseconds 100
}
$process.WaitForExit()
$watch.Stop()
$stdout = $stdoutTask.GetAwaiter().GetResult()
$stderr = $stderrTask.GetAwaiter().GetResult()
Set-Content -Encoding UTF8 $stdoutPath $stdout
Set-Content -Encoding UTF8 $stderrPath $stderr
try {
    $process.Refresh()
    $peakWorkingSet = [Math]::Max($peakWorkingSet, [long]$process.PeakWorkingSet64)
} catch {}
if ($process.ExitCode -ne 0) {
    Write-Host $stdout
    Write-Host $stderr
    throw "Analyze large-v3-turbo devolvió $($process.ExitCode)."
}

$transcriptPath = Join-Path $output "spanish real speech_transcript.json"
$analysisPath = Join-Path $output "spanish real speech_analysis.json"
$masterPath = Join-Path $output "spanish real speech_master_audio.flac"
foreach ($path in @($transcriptPath, $analysisPath, $masterPath)) {
    if (-not (Test-Path $path)) { throw "Falta output de validación: $path" }
}

$videoDuration = [double](& $ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 $video)
$masterDuration = [double](& $ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 $masterPath)
if ([Math]::Abs($videoDuration - $masterDuration) -gt 0.10) {
    throw "Master/video divergen: video=$videoDuration master=$masterDuration"
}

# Product validation is complete. Restore only the harness PATH for the evaluator.
$env:PATH = $originalPath
$evaluationText = (& $BuildPython $Evaluator `
    $transcriptPath $Reference --timeline-duration $videoDuration --max-wer 0.15 --min-word-ratio 0.80 | Out-String)
$evaluationExit = $LASTEXITCODE
Write-Host $evaluationText
if ($evaluationExit -ne 0) { throw "La evaluación ASR no supera los criterios fijados." }
$evaluation = $evaluationText | ConvertFrom-Json

$analysis = Get-Content $analysisPath -Raw | ConvertFrom-Json
if ($analysis.summary.automatic_edits -ne 0) { throw "Analyze creó edits automáticos." }
if (-not $analysis.safety.master_audio_is_timeline_source) {
    throw "Master audio no figura como timeline source."
}

$elapsedSeconds = $watch.Elapsed.TotalSeconds
$rtf = $elapsedSeconds / $videoDuration
$peakMiB = $peakWorkingSet / 1MB
$modelMiB = [double]$modelBytes / 1MB

Write-Host "TARGET_MODEL=large-v3-turbo"
Write-Host "TARGET_MODEL_SOURCE_REPO=$env:TARGET_MODEL_SOURCE_REPO"
Write-Host "TARGET_MODEL_SOURCE_REVISION=$env:TARGET_MODEL_SOURCE_REVISION"
Write-Host "SPANISH_REFERENCE_WORDS=$($evaluation.reference_word_count)"
Write-Host "SPANISH_HYPOTHESIS_WORDS=$($evaluation.hypothesis_word_count)"
Write-Host "SPANISH_WER=$($evaluation.wer)"
Write-Host "SPANISH_WORD_TIMESTAMP_MEDIAN_SECONDS=$($evaluation.median_word_duration_seconds)"
Write-Host "SPANISH_ANALYZE_SECONDS=$([Math]::Round($elapsedSeconds, 3))"
Write-Host "SPANISH_REAL_TIME_FACTOR=$([Math]::Round($rtf, 4))"
Write-Host "SPANISH_PEAK_WORKING_SET_MIB=$([Math]::Round($peakMiB, 1))"
Write-Host "TARGET_MODEL_BYTES=$modelBytes"
Write-Host "TARGET_MODEL_MIB=$([Math]::Round($modelMiB, 1))"
Write-Host "TARGET_MODEL_DIRECT_DOWNLOAD_SECONDS=$env:TARGET_MODEL_DOWNLOAD_SECONDS"
Write-Host "SPANISH_CANDIDATES=$($analysis.summary.candidate_count)"
Write-Host "SPANISH_AUTOMATIC_EDITS=$($analysis.summary.automatic_edits)"
Write-Host "SPANISH_VIDEO_DURATION=$videoDuration"
Write-Host "SPANISH_MASTER_DURATION=$masterDuration"
Write-Host "No models, audio, video or ZIP artifacts are uploaded by this workflow."
