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
$isolated = Join-Path $env:RUNNER_TEMP "Video Tunner Phase2E Human Render Portable"
$caseRoot = Join-Path $env:RUNNER_TEMP "Video Tunner Phase2E Human Render Cases"
$bundleRoot = Join-Path $env:RUNNER_TEMP "Video Tunner Phase2E Human Review Bundle"
Remove-Item $isolated -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $caseRoot -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $bundleRoot -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item $PortableSource $isolated -Recurse
New-Item -ItemType Directory -Force -Path $caseRoot | Out-Null
New-Item -ItemType Directory -Force -Path $bundleRoot | Out-Null

$exe = Join-Path $isolated "Video_Tunner.exe"
$ffmpeg = Join-Path $isolated "Tools\ffmpeg\bin\ffmpeg.exe"
$ffprobe = Join-Path $isolated "Tools\ffmpeg\bin\ffprobe.exe"
foreach ($path in @($exe, $ffmpeg, $ffprobe)) {
    if (-not (Test-Path $path)) { throw "Falta herramienta portable: $path" }
}
$hostPython = (Get-Command python -ErrorAction Stop).Source

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
if (-not $doctor.analysis_dependencies.silero_onnx.available) { throw "Silero ONNX no está disponible en el portable." }
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
        if ($category -ne [Globalization.UnicodeCategory]::NonSpacingMark) { [void]$builder.Append($char) }
    }
    $tokens = [System.Collections.Generic.List[string]]::new()
    foreach ($raw in @($builder.ToString() -split '\s+' | Where-Object { $_ })) {
        $token = ([string]$raw -replace '[^a-z0-9]+', '')
        if ($token) { $tokens.Add($token) }
    }
    return ($tokens -join ' ')
}

$manifestCases = [System.Collections.Generic.List[object]]::new()
$technicalPassCount = 0
$sourceIds = [System.Collections.Generic.HashSet[string]]::new()

foreach ($case in @($spec.cases)) {
    $id = [string]$case.id
    $sourceId = [string]$case.audio_source_id
    [void]$sourceIds.Add($sourceId)
    $envName = "AMI_CLOSEOUT_{0}_WAV" -f ($sourceId.ToUpperInvariant() -replace '[^A-Z0-9]', '')
    $sourceWav = [Environment]::GetEnvironmentVariable($envName)
    if (-not $sourceWav -or -not (Test-Path $sourceWav)) { throw "No existe audio AMI para $id ($envName)." }

    $root = Join-Path $caseRoot $id
    $analysisOutput = Join-Path $root "Analysis"
    $reviewDir = Join-Path $bundleRoot $id
    New-Item -ItemType Directory -Force -Path $root | Out-Null
    New-Item -ItemType Directory -Force -Path $analysisOutput | Out-Null
    New-Item -ItemType Directory -Force -Path $reviewDir | Out-Null

    $clipWav = Join-Path $root "$id.wav"
    $inputVideo = Join-Path $root "$id.mp4"
    $renderedVideo = Join-Path $root "${id}_rendered.mp4"

    & $ffmpeg -hide_banner -loglevel error -y `
        -ss ([string]$case.clip_start) -t ([string]$case.clip_duration) -i $sourceWav `
        -ac 1 -ar 16000 -c:a pcm_s16le $clipWav
    if ($LASTEXITCODE -ne 0) { throw "No se pudo extraer $id." }
    $duration = [double](& $ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 $clipWav)
    if ($duration -lt 5.0) { throw "Clip demasiado corto para ${id}: $duration" }

    & $ffmpeg -hide_banner -loglevel error -y `
        -f lavfi -i "color=c=black:s=320x240:r=25:d=$duration" `
        -i $clipWav -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac $inputVideo
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear vídeo de validación para $id." }

    $analyzeStdout = (& $exe analyze $inputVideo `
        --model large-v3-turbo `
        --language en `
        --device cpu `
        --compute-type int8 `
        --output-dir $analysisOutput 2>&1 | Out-String)
    Write-Host $analyzeStdout
    if ($LASTEXITCODE -ne 0) { throw "Analyze falló para $id." }

    $analysisPath = Join-Path $analysisOutput "${id}_analysis.json"
    if (-not (Test-Path $analysisPath)) { throw "Falta analysis.json para $id." }
    $analysis = Get-Content $analysisPath -Raw | ConvertFrom-Json
    if ([int]$analysis.schema_version -lt 9) { throw "$id analysis schema < 9" }
    if ([int]$analysis.summary.automatic_edits -ne 0) { throw "$id produjo automatic_edits antes de autorización." }

    $expectedText = Normalize-Phrase ([string]$case.reparandum_text)
    $promotionMatches = @($analysis.promotion_assessments | Where-Object {
        [string]$_.status -eq "eligible_for_promotion_review" -and
        [string]$_.candidate_kind -eq [string]$case.expected_candidate_kind -and
        (Normalize-Phrase ([string]$_.target_preview.text)) -eq $expectedText
    })
    if ($promotionMatches.Count -ne 1) {
        throw "$id esperaba exactamente 1 promotion assessment elegible para '$($case.reparandum_text)' y obtuvo $($promotionMatches.Count)."
    }
    $promotion = $promotionMatches[0]

    $approvalPath = Join-Path $root "promotion_approval.json"
    $proposalPath = Join-Path $root "approved_edit_plan_proposal.json"
    $authorizationPath = Join-Path $root "semantic_execution_authorization.json"
    $planPath = Join-Path $root "semantic_edit_plan.json"
    $technicalPath = Join-Path $reviewDir "technical_verification.json"
    $decisionTemplatePath = Join-Path $reviewDir "human_review_decisions.json"

    & $exe approval create $analysisPath `
        --promotion-assessment ([string]$promotion.id) `
        --decision approve `
        --actor "AMI-manual-human-label" `
        --reason "Controlled Phase 2E.5 validation: AMI manual disfluency annotation labels this exact reparandum as the removable first occurrence; not a production-user approval." `
        --output $approvalPath | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Approval falló para $id." }

    & $exe proposal build $analysisPath --approval $approvalPath --output $proposalPath | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Proposal falló para $id." }

    & $exe execution authorize $analysisPath $proposalPath `
        --decision approve `
        --actor "phase2e-validation-harness" `
        --reason "Controlled benchmark execution under project-owner direction on a licensed ephemeral AMI clip; this authorization is validation-only and not reusable for production media." `
        --output $authorizationPath | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Execution authorization falló para $id." }

    & $exe execution materialize $analysisPath $proposalPath $authorizationPath --output $planPath | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Plan materialization falló para $id." }

    & $exe execution render $inputVideo $analysisPath $proposalPath $authorizationPath $planPath $renderedVideo | Out-Host
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $renderedVideo)) { throw "Semantic render falló para $id." }

    $sourceShaAfter = (Get-FileHash $inputVideo -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($sourceShaAfter -ne ([string]$analysis.source.sha256).ToLowerInvariant()) { throw "$id source SHA cambió tras render." }

    $env:PYTHONPATH = "$PWD\Source"
    & $hostPython .\.github\scripts\build_phase2e_review_bundle_case.py `
        --source $inputVideo `
        --output $renderedVideo `
        --analysis $analysisPath `
        --proposal $proposalPath `
        --authorization $authorizationPath `
        --plan $planPath `
        --technical-report $technicalPath `
        --decision-template $decisionTemplatePath `
        --portable-ffmpeg-dir (Split-Path $ffmpeg -Parent) | Out-Host
    $technicalExit = $LASTEXITCODE
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    if ($technicalExit -ne 0) { throw "Technical post-render verification falló para $id." }

    $technical = Get-Content $technicalPath -Raw | ConvertFrom-Json
    if (-not [bool]$technical.technical_pass) { throw "$id technical_pass=false." }
    $technicalPassCount += 1

    $originalReview = Join-Path $reviewDir "original.wav"
    $renderedReview = Join-Path $reviewDir "rendered.wav"
    & $ffmpeg -hide_banner -loglevel error -y -i $inputVideo -map 0:a:0 -vn -ac 1 -ar 16000 -c:a pcm_s16le $originalReview
    if ($LASTEXITCODE -ne 0) { throw "No se pudo generar original.wav para $id." }
    & $ffmpeg -hide_banner -loglevel error -y -i $renderedVideo -map 0:a:0 -vn -ac 1 -ar 16000 -c:a pcm_s16le $renderedReview
    if ($LASTEXITCODE -ne 0) { throw "No se pudo generar rendered.wav para $id." }

    Copy-Item $planPath (Join-Path $reviewDir "semantic_edit_plan.json") -Force

    $manifestCases.Add([ordered]@{
        id = $id
        audio_source_id = $sourceId
        human_label = [string]$case.human_label
        expected_removed_text = [string]$case.reparandum_text
        promotion_assessment_id = [string]$promotion.id
        technical_pass = [bool]$technical.technical_pass
        technical_status = [string]$technical.status
        technical_report_sha256 = (Get-FileHash $technicalPath -Algorithm SHA256).Hash.ToLowerInvariant()
        rendered_output_sha256 = [string]$technical.output.sha256
        plan_fingerprint = [string]$technical.execution_chain.plan_fingerprint
        join_count = [int]$technical.summary.join_audit_count
        join_statuses = @($technical.post_render_join_audits | ForEach-Object { [string]$_.status })
        original_review_file = "$id/original.wav"
        rendered_review_file = "$id/rendered.wav"
        decision_template_file = "$id/human_review_decisions.json"
    })

    Write-Host "PHASE2E_HUMAN_RENDER_CASE=$id"
    Write-Host "PHASE2E_HUMAN_RENDER_TEXT=$($case.reparandum_text)"
    Write-Host "PHASE2E_HUMAN_RENDER_TECHNICAL_PASS=$($technical.technical_pass)"
    Write-Host "PHASE2E_HUMAN_RENDER_JOIN_STATUSES=$(@($technical.post_render_join_audits | ForEach-Object { $_.status }) -join ',')"
}

$policy = $spec.closeout_policy
$preHumanGate = (
    $manifestCases.Count -ge [int]$policy.minimum_rendered_human_cases -and
    $sourceIds.Count -ge [int]$policy.minimum_distinct_audio_sources -and
    $technicalPassCount -eq $manifestCases.Count
)

$manifest = [ordered]@{
    schema_version = 1
    record_type = "phase2e_human_render_review_bundle"
    source_fixture = [IO.Path]::GetFileName($Fixture)
    license = [string]$spec.license
    corpus = "AMI Meeting Corpus"
    selection_locked_before_listening = $true
    closeout_policy = $policy
    pre_human_gate = if ($preHumanGate) { "PASS" } else { "FAIL" }
    case_count = $manifestCases.Count
    distinct_audio_source_count = $sourceIds.Count
    technical_pass_count = $technicalPassCount
    human_perceptual_reviews_completed = 0
    phase2e_closeout_ready = $false
    cases = @($manifestCases)
}
$manifestPath = Join-Path $bundleRoot "manifest.json"
$manifest | ConvertTo-Json -Depth 20 | Set-Content -Path $manifestPath -Encoding utf8

$readme = @"
Video_Tunner — Phase 2E.5 Human Render Review Bundle
====================================================

Purpose
-------
Listen to exactly 3 precommitted real-human AMI semantic joins. The cases were selected because they already reached foundation_guards_pass in Phase 2D.6, before any Phase 2E.5 listening result.

Close-out policy (precommitted)
-------------------------------
- at least 3 rendered human cases
- at least 2 distinct speaker-specific AMI sources
- 100% technical post-render PASS
- 100% human perceptual PASS
- 0 safety violations
- any human FAIL keeps Phase 2E open and triggers join-treatment/hardening; thresholds are not relaxed after listening

How to review
-------------
For each case folder:
1. Listen to original.wav.
2. Listen to rendered.wav, preferably with headphones.
3. Open human_review_decisions.json.
4. For every join replace PENDING with PASS or FAIL and write a concrete reason.

PASS requires all of the following:
- no audible click/pop;
- no clipped phoneme or word;
- no unnatural timing/rhythm jump;
- no meaning loss caused by the join.

The technical report is not a substitute for this listening step.

License / provenance
--------------------
AMI Meeting Corpus, CC BY 4.0. Only short review clips are included; full AMI source WAVs, model files, generated portable ZIPs and analysis working directories are not uploaded.
"@
$readme | Set-Content -Path (Join-Path $bundleRoot "README.txt") -Encoding utf8

if (-not $preHumanGate) { throw "Phase 2E.5 pre-human technical corpus gate FAIL." }
Write-Host "PHASE2E_HUMAN_RENDER_PRE_HUMAN_GATE=PASS"
Write-Host "PHASE2E_HUMAN_RENDER_CASES=$($manifestCases.Count)"
Write-Host "PHASE2E_HUMAN_RENDER_SOURCES=$($sourceIds.Count)"
Write-Host "PHASE2E_HUMAN_RENDER_TECHNICAL_PASS=$technicalPassCount"
Write-Host "PHASE2E_HUMAN_PERCEPTUAL_PENDING=$($manifestCases.Count)"
Write-Host "PHASE2E_CLOSE_OUT_DECISION=PENDING_HUMAN_LISTENING"

$env:PATH = $originalPath
