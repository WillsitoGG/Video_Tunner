param(
    [string]$Fixture = (Join-Path $PWD "tests\fixtures\human_positive_closeout_ami_v1.json")
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $Fixture)) {
    throw "No existe el fixture de 2D.6: $Fixture"
}

$spec = Get-Content $Fixture -Raw | ConvertFrom-Json
if (-not $spec.audio_sources) {
    throw "El fixture 2D.6 no contiene audio_sources speaker-specific."
}

$root = Join-Path $env:RUNNER_TEMP "Video Tunner AMI Positive Closeout"
Remove-Item $root -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $root | Out-Null

$curl = Get-Command curl.exe -ErrorAction SilentlyContinue
if (-not $curl) { throw "curl.exe no está disponible en el runner Windows." }

$seenMeetings = @{}
foreach ($sourceProperty in $spec.audio_sources.PSObject.Properties) {
    $sourceId = [string]$sourceProperty.Name
    $source = $sourceProperty.Value
    $meeting = [string]$source.meeting
    $speaker = [string]$source.speaker
    $target = Join-Path $root ([string]$source.audio)

    if ([string]$source.source_kind -ne "individual_headset") {
        throw "2D.6 exige individual_headset; source=$sourceId kind=$($source.source_kind)"
    }
    if ($seenMeetings.ContainsKey($meeting)) {
        throw "El harness actual admite un único speaker-specific source por meeting; duplicado=$meeting"
    }
    $seenMeetings[$meeting] = $true

    Write-Host "AMI_CLOSEOUT_DOWNLOAD_SOURCE=$sourceId"
    Write-Host "AMI_CLOSEOUT_DOWNLOAD_MEETING=$meeting"
    Write-Host "AMI_CLOSEOUT_DOWNLOAD_SPEAKER=$speaker"
    Write-Host "AMI_CLOSEOUT_DOWNLOAD_CHANNEL=$($source.channel)"
    Write-Host "AMI_CLOSEOUT_DOWNLOAD_URL=$($source.url)"

    & $curl.Source `
        --location `
        --fail `
        --silent `
        --show-error `
        --retry 4 `
        --retry-all-errors `
        --retry-delay 5 `
        --connect-timeout 30 `
        --user-agent "Video_Tunner-CI/0.1 (+https://github.com/WillsitoGG/Video_Tunner)" `
        --output $target `
        ([string]$source.url)
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $target)) {
        throw "No se pudo descargar audio AMI speaker-specific para $sourceId."
    }

    $bytes = [long](Get-Item $target).Length
    $sha = (Get-FileHash $target -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($bytes -le 1000000L) {
        throw "Audio AMI inesperadamente pequeño para ${sourceId}: $bytes bytes."
    }

    $expectedBytes = $source.expected_bytes
    $expectedSha = [string]$source.expected_sha256
    if ($null -ne $expectedBytes -and [long]$expectedBytes -gt 0 -and $bytes -ne [long]$expectedBytes) {
        throw "AMI $sourceId bytes mismatch: actual=$bytes expected=$expectedBytes"
    }
    if ($expectedSha -and $sha -ne $expectedSha.ToUpperInvariant()) {
        throw "AMI $sourceId SHA-256 mismatch: actual=$sha expected=$expectedSha"
    }

    # Keep the existing meeting-level environment contract used by the closeout
    # validator. The fixture intentionally has one selected speaker per meeting.
    $envName = "AMI_CLOSEOUT_{0}_WAV" -f ($meeting.ToUpperInvariant() -replace '[^A-Z0-9]', '')
    if ($env:GITHUB_ENV) {
        "$envName=$target" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
    }

    Write-Host "AMI_CLOSEOUT_SOURCE=$sourceId"
    Write-Host "AMI_CLOSEOUT_BYTES=$bytes"
    Write-Host "AMI_CLOSEOUT_SHA256=$sha"
    Write-Host "AMI_CLOSEOUT_ENV=$envName"
}

Write-Host "AMI_CLOSEOUT_DOWNLOAD_GATE=PASS"
Write-Host "AMI speaker-specific audio remains ephemeral in RUNNER_TEMP and is never uploaded as an artifact."
