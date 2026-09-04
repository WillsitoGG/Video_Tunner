param(
    [string]$Fixture = (Join-Path $PWD "tests\fixtures\human_positive_closeout_ami_v2.json"),
    [string]$ModelStage = $env:SPANISH_TARGET_MODEL_STAGE,
    [string]$PortableSource = (Join-Path $PWD "dist\Video_Tunner")
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $Fixture)) { throw "No existe el fixture de 2D.6: $Fixture" }
if (-not $ModelStage -or -not (Test-Path $ModelStage)) {
    throw "No existe staging fijado de large-v3-turbo: $ModelStage"
}
if (-not (Test-Path $PortableSource)) { throw "No existe portable de análisis: $PortableSource" }

$spec = Get-Content $Fixture -Raw | ConvertFrom-Json
$isolated = Join-Path $env:RUNNER_TEMP "Video Tunner Human Positive Closeout Portable"
$caseRoot = Join-Path $env:RUNNER_TEMP "Video Tunner Human Positive Closeout Cases"
Remove-Item $isolated -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $caseRoot -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item $PortableSource $isolated -Recurse
New-Item -ItemType Directory -Force -Path $caseRoot | Out-Null

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

function Normalize-Phrase {
    param([AllowNull()][string]$Text)
    if (-not $Text) { return "" }
    $lower = $Text.ToLowerInvariant()
    $decomposed = $lower.Normalize([Text.NormalizationForm]::FormD)
    $builder = [Text.StringBuilder]::new()
    foreach ($char in $decomposed.ToCharArray()) {
        $category = [Globalization.CharUnicodeInfo]::GetUnicodeCategory($char)
        if ($category -ne [Globalization.UnicodeCategory]::NonSpacingMark) {
            [void]$builder.Append($char)
        }
    }
    $tokens = [System.Collections.Generic.List[string]]::new()
    foreach ($raw in @($builder.ToString() -split '\s+' | Where-Object { $_ })) {
        $token = ([string]$raw -replace '[^a-z0-9]+', '')
        if ($token) { $tokens.Add($token) }
    }
    return ($tokens -join ' ')
}

function Add-HardFailure {
    param([string]$Message)
    $script:hardFailures.Add($Message)
    Write-Host "HUMAN_POSITIVE_HARD_FAILURE=$Message"
}

$hardFailures = [System.Collections.Generic.List[string]]::new()
$results = [System.Collections.Generic.List[object]]::new()
$totalAnalyzeSeconds = 0.0

foreach ($case in @($spec.cases)) {
    $id = [string]$case.id
    $meeting = [string]$case.meeting
    $sourceId = [string]$case.audio_source_id
    $envName = "AMI_CLOSEOUT_{0}_WAV" -f ($sourceId.ToUpperInvariant() -replace '[^A-Z0-9]', '')
    $sourceWav = [Environment]::GetEnvironmentVariable($envName)
    if (-not $sourceWav -or -not (Test-Path $sourceWav)) {
        throw "No existe audio AMI para $id ($sourceId / $envName)."
    }

    $root = Join-Path $caseRoot $id
    $output = Join-Path $root "Output"
    New-Item -ItemType Directory -Force -Path $root | Out-Null
    New-Item -ItemType Directory -Force -Path $output | Out-Null
    $clip = Join-Path $root "$id.wav"
    $video = Join-Path $root "$id.mp4"

    & $ffmpeg -hide_banner -loglevel error -y `
        -ss ([string]$case.clip_start) -t ([string]$case.clip_duration) -i $sourceWav `
        -ac 1 -ar 16000 -c:a pcm_s16le $clip
    if ($LASTEXITCODE -ne 0) { throw "No se pudo extraer $id." }

    $duration = [double](& $ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 $clip)
    if ($duration -lt 5.0) { throw "Clip demasiado corto para ${id}: $duration" }
    & $ffmpeg -hide_banner -loglevel error -y `
        -f lavfi -i "color=c=black:s=320x240:r=25:d=$duration" `
        -i $clip -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac $video
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear vídeo de validación para $id." }

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
    if ($exitCode -ne 0) { throw "Analyze falló para $id con código $exitCode." }

    $transcriptPath = Join-Path $output "${id}_transcript.json"
    $analysisPath = Join-Path $output "${id}_analysis.json"
    foreach ($path in @($transcriptPath, $analysisPath)) {
        if (-not (Test-Path $path)) { throw "Falta output para ${id}: $path" }
    }
    $transcript = Get-Content $transcriptPath -Raw | ConvertFrom-Json
    $analysis = Get-Content $analysisPath -Raw | ConvertFrom-Json
    if ([int]$analysis.schema_version -lt 8) {
        Add-HardFailure "$id analysis schema < 8"
    }

    $wordTexts = [System.Collections.Generic.List[string]]::new()
    foreach ($segment in @($transcript.segments)) {
        foreach ($word in @($segment.words)) {
            if ([double]$word.end -lt [double]$word.start) {
                Add-HardFailure "$id has negative word timestamp duration"
            }
            $text = ([string]$word.text).Trim()
            if ($text) { $wordTexts.Add($text) }
        }
    }
    $transcriptText = ($wordTexts -join " ").Trim()
    if ($wordTexts.Count -eq 0) { Add-HardFailure "$id produced no word timestamps" }

    $candidates = @($analysis.candidates)
    $decisions = @($analysis.semantic_decisions)
    $joins = @($analysis.join_assessments)
    $acoustics = @($analysis.acoustic_join_assessments)
    $eligibilities = @($analysis.eligibility_assessments)
    $expectedText = Normalize-Phrase ([string]$case.reparandum_text)
    $repeatCandidates = @($candidates | Where-Object { [string]$_.kind -eq "possible_repetition" })
    $exactCandidates = @($repeatCandidates | Where-Object {
        (Normalize-Phrase ([string]$_.evidence.removed_text)) -eq $expectedText
    })

    $matched = $null
    if ($exactCandidates.Count -gt 0) {
        $matched = $exactCandidates | Sort-Object {
            [Math]::Abs([double]$_.start - ([double]$case.reparandum_start - [double]$case.clip_start))
        } | Select-Object -First 1
    } elseif ($repeatCandidates.Count -gt 0) {
        $matched = $repeatCandidates | Sort-Object {
            [Math]::Abs([double]$_.start - ([double]$case.reparandum_start - [double]$case.clip_start))
        } | Select-Object -First 1
    }

    $candidateFound = $null -ne $matched
    $textMatch = $false
    $timingAligned = $false
    $startDelta = $null
    $endDelta = $null
    $matchedRemovedText = $null
    $decisionValue = $null
    $decisionGuard = $null
    $joinStatus = $null
    $acousticStatus = $null
    $eligibilityStatus = $null
    $removedTextValid = $null
    $futurePromotion = $false

    if ($candidateFound) {
        $matchedRemovedText = [string]$matched.evidence.removed_text
        $textMatch = (Normalize-Phrase $matchedRemovedText) -eq $expectedText
        $manualLocalStart = [double]$case.reparandum_start - [double]$case.clip_start
        $manualLocalEnd = [double]$case.reparandum_end - [double]$case.clip_start
        $startDelta = [Math]::Abs([double]$matched.start - $manualLocalStart)
        $endDelta = [Math]::Abs([double]$matched.end - $manualLocalEnd)
        $timingAligned = $startDelta -le 0.75 -and $endDelta -le 0.75

        $decision = @($decisions | Where-Object { $_.candidate_id -eq $matched.id } | Select-Object -First 1)
        if ($decision.Count -gt 0) {
            $decisionValue = [string]$decision[0].decision
            $decisionGuard = [string]$decision[0].guard_status
        }
        $join = @($joins | Where-Object { $_.candidate_id -eq $matched.id } | Select-Object -First 1)
        if ($join.Count -gt 0) {
            $joinStatus = [string]$join[0].status
            $acoustic = @($acoustics | Where-Object { $_.join_assessment_id -eq $join[0].id } | Select-Object -First 1)
            if ($acoustic.Count -gt 0) { $acousticStatus = [string]$acoustic[0].status }
        }
        $eligibility = @($eligibilities | Where-Object { $_.candidate_id -eq $matched.id } | Select-Object -First 1)
        if ($eligibility.Count -gt 0) {
            $eligibilityStatus = [string]$eligibility[0].status
            $removedTextValid = [bool]$eligibility[0].removed_text_validation.valid
            $futurePromotion = [bool]$eligibility[0].future_promotion_candidate
        }
    }

    $safetyViolations = 0
    if ([int]$analysis.summary.automatic_edits -ne 0) { $safetyViolations += 1 }
    $safetyViolations += @($candidates | Where-Object { $_.auto_apply }).Count
    $safetyViolations += @($decisions | Where-Object { $_.executable -or $_.auto_apply }).Count
    $safetyViolations += @($joins | Where-Object { $_.safe_for_cut -or $_.executable -or $_.auto_apply }).Count
    $safetyViolations += @($acoustics | Where-Object { $_.safe_for_cut -or $_.executable -or $_.auto_apply }).Count
    $safetyViolations += @($eligibilities | Where-Object { $_.safe_for_cut -or $_.executable -or $_.auto_apply }).Count
    if ($safetyViolations -ne 0) { Add-HardFailure "$id safety violations=$safetyViolations" }

    $longCompatible = [string]$case.detector_expectation -eq "long_detector_compatible"
    $alignedHumanPositive = $longCompatible -and $candidateFound -and $textMatch -and $timingAligned
    $foundationHumanPositive = $alignedHumanPositive -and $eligibilityStatus -eq "foundation_guards_pass"

    Write-Host "HUMAN_POSITIVE_CASE=$id"
    Write-Host "HUMAN_POSITIVE_SOURCE=$sourceId"
    Write-Host "HUMAN_POSITIVE_MEETING=$meeting"
    Write-Host "HUMAN_POSITIVE_LABEL=$($case.human_label)"
    Write-Host "HUMAN_POSITIVE_DETECTOR_EXPECTATION=$($case.detector_expectation)"
    Write-Host "HUMAN_POSITIVE_MANUAL_REPARANDUM=$($case.reparandum_text)"
    Write-Host "HUMAN_POSITIVE_TRANSCRIPT=$transcriptText"
    Write-Host "HUMAN_POSITIVE_CANDIDATE_FOUND=$candidateFound"
    Write-Host "HUMAN_POSITIVE_MATCHED_REMOVED_TEXT=$matchedRemovedText"
    Write-Host "HUMAN_POSITIVE_TEXT_MATCH=$textMatch"
    Write-Host "HUMAN_POSITIVE_TIMING_ALIGNED=$timingAligned"
    Write-Host "HUMAN_POSITIVE_DECISION=$decisionValue"
    Write-Host "HUMAN_POSITIVE_JOIN_STATUS=$joinStatus"
    Write-Host "HUMAN_POSITIVE_ACOUSTIC_STATUS=$acousticStatus"
    Write-Host "HUMAN_POSITIVE_ELIGIBILITY_STATUS=$eligibilityStatus"
    Write-Host "HUMAN_POSITIVE_ANALYZE_SECONDS=$([Math]::Round($watch.Elapsed.TotalSeconds, 3))"

    $results.Add([ordered]@{
        id = $id
        audio_source_id = $sourceId
        meeting = $meeting
        human_label = [string]$case.human_label
        detector_expectation = [string]$case.detector_expectation
        reparandum_text = [string]$case.reparandum_text
        transcript = $transcriptText
        candidate_found = $candidateFound
        matched_removed_text = $matchedRemovedText
        removed_text_matches_human_label = $textMatch
        timing_aligned_to_human_label = $timingAligned
        start_delta_seconds = if ($null -eq $startDelta) { $null } else { [Math]::Round([double]$startDelta, 3) }
        end_delta_seconds = if ($null -eq $endDelta) { $null } else { [Math]::Round([double]$endDelta, 3) }
        semantic_decision = $decisionValue
        semantic_guard_status = $decisionGuard
        join_status = $joinStatus
        acoustic_status = $acousticStatus
        eligibility_status = $eligibilityStatus
        removed_text_validation = $removedTextValid
        future_promotion_candidate = $futurePromotion
        aligned_human_positive = $alignedHumanPositive
        foundation_human_positive = $foundationHumanPositive
        safety_violations = $safetyViolations
        automatic_edits = [int]$analysis.summary.automatic_edits
        analyze_seconds = [Math]::Round($watch.Elapsed.TotalSeconds, 3)
    })
}

$env:PATH = $originalPath
$longResults = @($results | Where-Object { $_.detector_expectation -eq "long_detector_compatible" })
$shortResults = @($results | Where-Object { $_.detector_expectation -eq "short_known_limitation" })
$alignedLong = @($longResults | Where-Object { $_.aligned_human_positive })
$foundationLong = @($longResults | Where-Object { $_.foundation_human_positive })
$foundationSources = @($foundationLong | ForEach-Object { $_.audio_source_id } | Sort-Object -Unique)

$minimumEvaluated = if ($spec.close_out_policy.minimum_evaluated_long_cases) {
    [int]$spec.close_out_policy.minimum_evaluated_long_cases
} else { 2 }
$minimumAligned = if ($spec.close_out_policy.minimum_aligned_human_positives) {
    [int]$spec.close_out_policy.minimum_aligned_human_positives
} else { 2 }
$minimumFoundation = if ($spec.close_out_policy.minimum_foundation_human_positives) {
    [int]$spec.close_out_policy.minimum_foundation_human_positives
} else { 1 }
$minimumFoundationSources = if ($spec.close_out_policy.minimum_foundation_sources) {
    [int]$spec.close_out_policy.minimum_foundation_sources
} else { 1 }

$evidenceGate = $hardFailures.Count -eq 0 -and $results.Count -eq @($spec.cases).Count
$closeOutReady = (
    $evidenceGate -and
    $longResults.Count -ge $minimumEvaluated -and
    $alignedLong.Count -ge $minimumAligned -and
    $foundationLong.Count -ge $minimumFoundation -and
    $foundationSources.Count -ge $minimumFoundationSources
)
$closeOutDecision = if ($closeOutReady) { "CLOSE_OUT_READY" } else { "INSUFFICIENT" }

$summary = [ordered]@{
    schema_version = 2
    phase = "2D.6"
    fixture_schema_version = [int]$spec.schema_version
    source = "AMI manually annotated exact repetitions"
    model = "large-v3-turbo"
    device = "cpu"
    compute_type = "int8"
    cases = $results.Count
    long_detector_compatible_cases = $longResults.Count
    short_known_limitation_cases = $shortResults.Count
    aligned_long_human_positives = $alignedLong.Count
    foundation_long_human_positives = $foundationLong.Count
    foundation_sources = $foundationSources.Count
    close_out_policy = [ordered]@{
        minimum_evaluated_long_cases = $minimumEvaluated
        minimum_aligned_human_positives = $minimumAligned
        minimum_foundation_human_positives = $minimumFoundation
        minimum_foundation_sources = $minimumFoundationSources
    }
    hard_failures = $hardFailures.Count
    total_analyze_seconds = [Math]::Round($totalAnalyzeSeconds, 3)
    safe_for_cut = 0
    executable = 0
    auto_apply = 0
    automatic_edits = 0
    evidence_gate = if ($evidenceGate) { "PASS" } else { "FAIL" }
    close_out_decision = $closeOutDecision
    results = $results
    hard_failure_messages = $hardFailures
}
Write-Host "HUMAN_POSITIVE_CLOSEOUT_SUMMARY=$($summary | ConvertTo-Json -Compress -Depth 10)"
Write-Host "HUMAN_POSITIVE_EVIDENCE_GATE=$(if ($evidenceGate) { 'PASS' } else { 'FAIL' })"
Write-Host "HUMAN_POSITIVE_CLOSE_OUT_DECISION=$closeOutDecision"
Write-Host "No model, AMI audio, generated video or output artifact is uploaded by this workflow."

if (-not $evidenceGate) {
    throw "2D.6 evidence-integrity gate failed: $($hardFailures -join '; ')"
}
