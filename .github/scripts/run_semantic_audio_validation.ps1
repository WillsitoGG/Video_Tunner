param(
    [string]$FixtureWav = $env:AMI_SEMANTIC_FIXTURE_WAV,
    [string]$ModelStage = $env:SPANISH_TARGET_MODEL_STAGE,
    [string]$PortableSource = (Join-Path $PWD "dist\Video_Tunner")
)

$ErrorActionPreference = "Stop"
if (-not $FixtureWav -or -not (Test-Path $FixtureWav)) {
    throw "No existe el WAV AMI para validación semántica: $FixtureWav"
}
if (-not $ModelStage -or -not (Test-Path $ModelStage)) {
    throw "No existe el staging fijado de large-v3-turbo: $ModelStage"
}
if (-not (Test-Path $PortableSource)) {
    throw "No existe el portable de análisis: $PortableSource"
}

$isolated = Join-Path $env:RUNNER_TEMP "Video Tunner Semantic Audio Portable"
$fixtureRoot = Join-Path $env:RUNNER_TEMP "Video Tunner Semantic Audio Cases"
Remove-Item $isolated -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $fixtureRoot -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item $PortableSource $isolated -Recurse
New-Item -ItemType Directory -Force -Path $fixtureRoot | Out-Null

$exe = Join-Path $isolated "Video_Tunner.exe"
$ffmpeg = Join-Path $isolated "Tools\ffmpeg\bin\ffmpeg.exe"
$ffprobe = Join-Path $isolated "Tools\ffmpeg\bin\ffprobe.exe"
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

if (Get-Command python -ErrorAction SilentlyContinue) { throw "Python sigue disponible en PATH durante la prueba portable." }
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) { throw "FFmpeg externo sigue disponible en PATH durante la prueba portable." }

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
if (-not $modelStatus.available) { throw "large-v3-turbo staged no está disponible en el portable." }

$cases = @(
    [ordered]@{
        id = "ami-retake-0036"
        source_start = 34.0
        duration = 18.0
        expected_kinds = @("possible_retake", "possible_repetition")
        expected_marker = $null
        expected_positive = $true
        expected_decision = "REVIEW"
        manual_reference = "we'll have a look at the uh th- have a look at the prototypes"
        note = "ASR may collapse the manual retake into an adjacent exact repetition; safety decision must remain REVIEW if timing is suspicious."
    },
    [ordered]@{
        id = "ami-i-mean-correction-0250"
        source_start = 168.0
        duration = 12.0
        expected_kinds = @("explicit_correction")
        expected_marker = "i mean"
        expected_positive = $true
        expected_decision = "REVIEW"
        manual_reference = "I just wondered - I mean h- how will people put these down I wonder"
        note = "large-v3-turbo may remove manual dashes/truncations; interrogative reframe evidence must survive."
    },
    [ordered]@{
        id = "ami-i-mean-discourse-0311"
        source_start = 189.0
        duration = 18.0
        expected_kinds = @("explicit_correction")
        expected_marker = "i mean"
        expected_positive = $false
        expected_decision = $null
        manual_reference = "particularly if they're gonna have it as a fashion item ... I mean ..."
        note = "Discourse I mean must not become an explicit_correction candidate. Other review-only semantic noise is logged separately."
    }
)

$failures = [System.Collections.Generic.List[string]]::new()
$results = [System.Collections.Generic.List[object]]::new()
$totalAnalyzeSeconds = 0.0

function Add-Failure {
    param([string]$Message)
    $failures.Add($Message)
    Write-Host "SEMANTIC_AUDIO_FAILURE=$Message"
}

foreach ($case in $cases) {
    $caseId = [string]$case.id
    $caseRoot = Join-Path $fixtureRoot $caseId
    $output = Join-Path $caseRoot "Output"
    New-Item -ItemType Directory -Force -Path $caseRoot | Out-Null
    New-Item -ItemType Directory -Force -Path $output | Out-Null

    $clipWav = Join-Path $caseRoot "$caseId.wav"
    & $ffmpeg -hide_banner -loglevel error -y `
        -ss ([string]$case.source_start) -t ([string]$case.duration) -i $FixtureWav `
        -ac 1 -ar 16000 -c:a pcm_s16le $clipWav
    if ($LASTEXITCODE -ne 0) { throw "No se pudo recortar audio para $caseId." }

    $duration = [double](& $ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 $clipWav)
    if ($duration -lt 5.0) { throw "Clip AMI demasiado corto para ${caseId}: $duration" }

    $video = Join-Path $caseRoot "$caseId.mp4"
    & $ffmpeg -hide_banner -loglevel error -y `
        -f lavfi -i "color=c=black:s=320x240:r=25:d=$duration" `
        -i $clipWav -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac $video
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear vídeo de validación para $caseId." }

    $watch = [Diagnostics.Stopwatch]::StartNew()
    $stdout = (& $exe analyze $video `
        --model large-v3-turbo `
        --language en `
        --device cpu `
        --compute-type int8 `
        --output-dir $output 2>&1 | Out-String)
    $exitCode = $LASTEXITCODE
    $watch.Stop()
    $totalAnalyzeSeconds += $watch.Elapsed.TotalSeconds
    Write-Host $stdout
    if ($exitCode -ne 0) { throw "Analyze falló para $caseId con código $exitCode." }

    $transcriptPath = Join-Path $output "${caseId}_transcript.json"
    $analysisPath = Join-Path $output "${caseId}_analysis.json"
    foreach ($path in @($transcriptPath, $analysisPath)) {
        if (-not (Test-Path $path)) { throw "Falta output para ${caseId}: $path" }
    }

    $transcript = Get-Content $transcriptPath -Raw | ConvertFrom-Json
    $analysis = Get-Content $analysisPath -Raw | ConvertFrom-Json
    $wordTexts = [System.Collections.Generic.List[string]]::new()
    $wordTimingRows = [System.Collections.Generic.List[object]]::new()
    $wordCount = 0
    foreach ($segment in @($transcript.segments)) {
        foreach ($word in @($segment.words)) {
            $text = ([string]$word.text).Trim()
            if ($text) { $wordTexts.Add($text) }
            $wordTimingRows.Add([ordered]@{
                text = $text
                start = [Math]::Round([double]$word.start, 3)
                end = [Math]::Round([double]$word.end, 3)
                duration = [Math]::Round(([double]$word.end - [double]$word.start), 3)
            })
            $wordCount += 1
            if ([double]$word.end -lt [double]$word.start) {
                Add-Failure "$caseId has negative word timestamp duration"
            }
        }
    }
    $transcriptText = ($wordTexts -join " ").Trim()
    $candidates = @($analysis.candidates)
    $decisions = @($analysis.semantic_decisions)
    $matching = @($candidates | Where-Object {
        $case.expected_kinds -contains [string]$_.kind -and (
            -not $case.expected_marker -or $_.evidence.marker_normalized -eq [string]$case.expected_marker
        )
    })

    Write-Host "SEMANTIC_AUDIO_CASE=$caseId"
    Write-Host "SEMANTIC_AUDIO_SOURCE_WINDOW=$($case.source_start)+$($case.duration)"
    Write-Host "SEMANTIC_AUDIO_MANUAL_REFERENCE=$($case.manual_reference)"
    Write-Host "SEMANTIC_AUDIO_NOTE=$($case.note)"
    Write-Host "SEMANTIC_AUDIO_TRANSCRIPT=$transcriptText"
    Write-Host "SEMANTIC_AUDIO_WORD_COUNT=$wordCount"
    Write-Host "SEMANTIC_AUDIO_WORDS=$($wordTimingRows | ConvertTo-Json -Compress -Depth 5)"
    Write-Host "SEMANTIC_AUDIO_CANDIDATES=$($candidates | ConvertTo-Json -Compress -Depth 8)"
    Write-Host "SEMANTIC_AUDIO_DECISIONS=$($decisions | ConvertTo-Json -Compress -Depth 8)"
    Write-Host "SEMANTIC_AUDIO_ANALYZE_SECONDS=$([Math]::Round($watch.Elapsed.TotalSeconds, 3))"

    if ($wordCount -le 0) { Add-Failure "$caseId produced no word timestamps" }
    if ([int]$analysis.summary.automatic_edits -ne 0) { Add-Failure "$caseId automatic_edits != 0" }
    if (@($decisions | Where-Object { $_.executable }).Count -ne 0) { Add-Failure "$caseId emitted executable semantic decision" }
    if (@($decisions | Where-Object { $_.auto_apply }).Count -ne 0) { Add-Failure "$caseId emitted auto_apply semantic decision" }

    $matchedDecisionValue = $null
    $matchedKind = $null
    if ([bool]$case.expected_positive) {
        if ($matching.Count -eq 0) {
            Add-Failure "$caseId missing expected semantic event ($($case.expected_kinds -join '|'))"
        } else {
            $matchedCandidate = $matching[0]
            $matchedKind = [string]$matchedCandidate.kind
            $matchedDecision = @($decisions | Where-Object { $_.candidate_id -eq $matchedCandidate.id } | Select-Object -First 1)
            if ($matchedDecision.Count -eq 0) {
                Add-Failure "$caseId expected candidate has no semantic decision"
            } else {
                $matchedDecisionValue = [string]$matchedDecision[0].decision
                if ($case.expected_decision -and $matchedDecisionValue -ne [string]$case.expected_decision) {
                    Add-Failure "$caseId expected $($case.expected_decision) but got $matchedDecisionValue"
                }
            }
        }
    } else {
        if ($matching.Count -ne 0) {
            Add-Failure "$caseId produced unexpected semantic event ($($case.expected_kinds -join '|'))"
        }
    }

    $results.Add([ordered]@{
        id = $caseId
        expected_positive = [bool]$case.expected_positive
        expected_kinds = @($case.expected_kinds)
        expected_decision = $case.expected_decision
        transcript = $transcriptText
        word_count = $wordCount
        candidate_count = $candidates.Count
        matching_candidate_count = $matching.Count
        matched_kind = $matchedKind
        matched_decision = $matchedDecisionValue
        automatic_edits = [int]$analysis.summary.automatic_edits
        executable_decisions = @($decisions | Where-Object { $_.executable }).Count
        auto_apply_decisions = @($decisions | Where-Object { $_.auto_apply }).Count
        analyze_seconds = [Math]::Round($watch.Elapsed.TotalSeconds, 3)
    })
}

$env:PATH = $originalPath
$summary = [ordered]@{
    schema_version = 2
    source = "AMI Meeting Corpus ES2012d Mix-Headset"
    model = "large-v3-turbo"
    device = "cpu"
    compute_type = "int8"
    cases = $results.Count
    failures = $failures.Count
    total_analyze_seconds = [Math]::Round($totalAnalyzeSeconds, 3)
    automatic_edits = 0
    executable_decisions = 0
    auto_apply_decisions = 0
    results = $results
}
Write-Host "SEMANTIC_AUDIO_SUMMARY=$($summary | ConvertTo-Json -Compress -Depth 8)"
Write-Host "No model, AMI audio, generated video or output artifact is uploaded by this workflow."

if ($failures.Count -ne 0) {
    throw "Audio-backed semantic gate failed: $($failures -join '; ')"
}
Write-Host "SEMANTIC_AUDIO_GATE=PASS"
