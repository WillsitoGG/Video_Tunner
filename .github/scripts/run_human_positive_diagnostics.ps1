param(
    [string]$Fixture = (Join-Path $PWD "tests\fixtures\human_positive_closeout_ami_v2.json"),
    [string]$CaseRoot = (Join-Path $env:RUNNER_TEMP "Video Tunner Human Positive Closeout Cases")
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $Fixture)) { throw "No existe fixture 2D.6: $Fixture" }
if (-not (Test-Path $CaseRoot)) { throw "No existe case root 2D.6: $CaseRoot" }

$spec = Get-Content $Fixture -Raw | ConvertFrom-Json
$minimumRepeatTokens = [int]$spec.detector_contract.minimum_exact_repeat_tokens

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

function Get-NormalizedTokens {
    param([AllowNull()][string]$Text)
    $normal = Normalize-Phrase $Text
    if (-not $normal) { return @() }
    return @($normal -split ' ' | Where-Object { $_ })
}

function Count-TokenSequence {
    param(
        [object[]]$Haystack,
        [object[]]$Needle
    )
    if ($Needle.Count -eq 0 -or $Haystack.Count -lt $Needle.Count) { return 0 }
    $count = 0
    for ($i = 0; $i -le $Haystack.Count - $Needle.Count; $i++) {
        $match = $true
        for ($j = 0; $j -lt $Needle.Count; $j++) {
            if ([string]$Haystack[$i + $j] -ne [string]$Needle[$j]) {
                $match = $false
                break
            }
        }
        if ($match) { $count += 1 }
    }
    return $count
}

function Get-LongestRepeatedExpectedPrefix {
    param(
        [object[]]$TranscriptTokens,
        [object[]]$ExpectedTokens
    )
    for ($size = $ExpectedTokens.Count; $size -ge 1; $size--) {
        $prefix = @($ExpectedTokens[0..($size - 1)])
        $occurrences = Count-TokenSequence -Haystack $TranscriptTokens -Needle $prefix
        if ($occurrences -ge 2) {
            return [ordered]@{
                token_count = $size
                text = ($prefix -join ' ')
                occurrences = $occurrences
            }
        }
    }
    return [ordered]@{ token_count = 0; text = ""; occurrences = 0 }
}

function Get-TranscriptText {
    param($Transcript)
    $words = [System.Collections.Generic.List[string]]::new()
    foreach ($segment in @($Transcript.segments)) {
        foreach ($word in @($segment.words)) {
            $text = ([string]$word.text).Trim()
            if ($text) { $words.Add($text) }
        }
    }
    return ($words -join ' ').Trim()
}

$results = [System.Collections.Generic.List[object]]::new()
$statusCounts = @{}

foreach ($case in @($spec.cases)) {
    $id = [string]$case.id
    $output = Join-Path (Join-Path $CaseRoot $id) "Output"
    $transcriptPath = Join-Path $output "${id}_transcript.json"
    $analysisPath = Join-Path $output "${id}_analysis.json"
    foreach ($path in @($transcriptPath, $analysisPath)) {
        if (-not (Test-Path $path)) { throw "Falta output 2D.6 para diagnóstico: $path" }
    }

    $transcript = Get-Content $transcriptPath -Raw | ConvertFrom-Json
    $analysis = Get-Content $analysisPath -Raw | ConvertFrom-Json
    $transcriptText = Get-TranscriptText $transcript
    $transcriptTokens = @(Get-NormalizedTokens $transcriptText)
    $expectedTokens = @(Get-NormalizedTokens ([string]$case.reparandum_text))
    $fullOccurrences = Count-TokenSequence -Haystack $transcriptTokens -Needle $expectedTokens
    $longestPrefix = Get-LongestRepeatedExpectedPrefix -TranscriptTokens $transcriptTokens -ExpectedTokens $expectedTokens

    $repeatCandidates = @($analysis.candidates | Where-Object { [string]$_.kind -eq 'possible_repetition' })
    $exactCandidates = @($repeatCandidates | Where-Object {
        (Normalize-Phrase ([string]$_.evidence.removed_text)) -eq (Normalize-Phrase ([string]$case.reparandum_text))
    })
    $prefixCandidates = @($repeatCandidates | Where-Object {
        $candidateTokens = @(Get-NormalizedTokens ([string]$_.evidence.removed_text))
        if ($candidateTokens.Count -eq 0 -or $candidateTokens.Count -gt $expectedTokens.Count) { return $false }
        for ($i = 0; $i -lt $candidateTokens.Count; $i++) {
            if ([string]$candidateTokens[$i] -ne [string]$expectedTokens[$i]) { return $false }
        }
        return $true
    })

    $manualLocalStart = [double]$case.reparandum_start - [double]$case.clip_start
    $matched = $null
    if ($exactCandidates.Count -gt 0) {
        $matched = $exactCandidates | Sort-Object {
            [Math]::Abs([double]$_.start - $manualLocalStart)
        } | Select-Object -First 1
    } elseif ($prefixCandidates.Count -gt 0) {
        $matched = $prefixCandidates | Sort-Object `
            @{ Expression = { -1 * @(Get-NormalizedTokens ([string]$_.evidence.removed_text)).Count } }, `
            @{ Expression = { [Math]::Abs([double]$_.start - $manualLocalStart) } } |
            Select-Object -First 1
    }

    $candidatePrefixTokens = 0
    $matchedRemovedText = $null
    $timingAligned = $false
    $eligibilityStatus = $null
    if ($null -ne $matched) {
        $matchedRemovedText = [string]$matched.evidence.removed_text
        $candidatePrefixTokens = @(Get-NormalizedTokens $matchedRemovedText).Count
        $manualLocalEnd = [double]$case.reparandum_end - [double]$case.clip_start
        $startDelta = [Math]::Abs([double]$matched.start - $manualLocalStart)
        $endDelta = [Math]::Abs([double]$matched.end - $manualLocalEnd)
        $timingAligned = $startDelta -le 0.75 -and $endDelta -le 0.75
        $eligibility = @($analysis.eligibility_assessments | Where-Object { $_.candidate_id -eq $matched.id } | Select-Object -First 1)
        if ($eligibility.Count -gt 0) { $eligibilityStatus = [string]$eligibility[0].status }
    }

    $diagnosticStatus = $null
    if ([string]$case.detector_expectation -eq 'short_known_limitation') {
        $diagnosticStatus = 'known_short_detector_limitation'
    } elseif ($fullOccurrences -lt 2) {
        if ([int]$longestPrefix.token_count -ge $minimumRepeatTokens) {
            $diagnosticStatus = 'asr_partial_repeat_preserved'
        } else {
            $diagnosticStatus = 'asr_repeat_not_preserved'
        }
    } elseif ($repeatCandidates.Count -eq 0) {
        $diagnosticStatus = 'detector_miss_on_preserved_repeat'
    } elseif ($exactCandidates.Count -eq 0) {
        $diagnosticStatus = 'candidate_span_mismatch'
    } elseif (-not $timingAligned) {
        $diagnosticStatus = 'timing_mismatch'
    } elseif ($eligibilityStatus -eq 'foundation_guards_pass') {
        $diagnosticStatus = 'foundation_guards_pass'
    } elseif ($eligibilityStatus) {
        $diagnosticStatus = "downstream_blocked:$eligibilityStatus"
    } else {
        $diagnosticStatus = 'missing_downstream_evidence'
    }

    if (-not $statusCounts.ContainsKey($diagnosticStatus)) { $statusCounts[$diagnosticStatus] = 0 }
    $statusCounts[$diagnosticStatus] += 1

    $result = [ordered]@{
        id = $id
        audio_source_id = [string]$case.audio_source_id
        detector_expectation = [string]$case.detector_expectation
        human_reparandum = [string]$case.reparandum_text
        expected_tokens = $expectedTokens.Count
        asr_full_phrase_occurrences = $fullOccurrences
        asr_longest_repeated_prefix_tokens = [int]$longestPrefix.token_count
        asr_longest_repeated_prefix = [string]$longestPrefix.text
        asr_longest_repeated_prefix_occurrences = [int]$longestPrefix.occurrences
        repeat_candidates = $repeatCandidates.Count
        exact_human_span_candidates = $exactCandidates.Count
        candidate_prefix_tokens = $candidatePrefixTokens
        matched_removed_text = $matchedRemovedText
        timing_aligned = $timingAligned
        eligibility_status = $eligibilityStatus
        diagnostic_status = $diagnosticStatus
    }
    $results.Add($result)

    Write-Host "HUMAN_POSITIVE_DIAGNOSTIC_CASE=$id"
    Write-Host "HUMAN_POSITIVE_DIAGNOSTIC_STATUS=$diagnosticStatus"
    Write-Host "HUMAN_POSITIVE_ASR_FULL_OCCURRENCES=$fullOccurrences"
    Write-Host "HUMAN_POSITIVE_ASR_REPEAT_PREFIX_TOKENS=$($longestPrefix.token_count)"
    Write-Host "HUMAN_POSITIVE_ASR_REPEAT_PREFIX=$($longestPrefix.text)"
    Write-Host "HUMAN_POSITIVE_CANDIDATE_PREFIX_TOKENS=$candidatePrefixTokens"
}

$orderedCounts = [ordered]@{}
foreach ($key in @($statusCounts.Keys | Sort-Object)) { $orderedCounts[$key] = $statusCounts[$key] }
$summary = [ordered]@{
    schema_version = 2
    phase = '2D.6-diagnostics'
    fixture_schema_version = [int]$spec.schema_version
    cases = $results.Count
    minimum_repeat_tokens = $minimumRepeatTokens
    by_diagnostic_status = $orderedCounts
    results = $results
}
Write-Host "HUMAN_POSITIVE_DIAGNOSTIC_SUMMARY=$($summary | ConvertTo-Json -Compress -Depth 10)"
