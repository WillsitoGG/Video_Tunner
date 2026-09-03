param(
    [string]$Destination = (Join-Path $env:RUNNER_TEMP "Video Tunner AMI Semantic Fixture")
)

$ErrorActionPreference = "Stop"
$meeting = "ES2012d"
$uri = "https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/ES2012d/audio/ES2012d.Mix-Headset.wav"
$userAgent = "Video_Tunner-CI/0.1 (+https://github.com/WillsitoGG/Video_Tunner)"
$curl = Get-Command curl.exe -ErrorAction SilentlyContinue
if (-not $curl) {
    throw "curl.exe no está disponible en el runner Windows."
}

Remove-Item $Destination -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$target = Join-Path $Destination "ES2012d.Mix-Headset.wav"

& $curl.Source `
    --location `
    --fail `
    --silent `
    --show-error `
    --retry 4 `
    --retry-all-errors `
    --retry-delay 5 `
    --connect-timeout 30 `
    --user-agent $userAgent `
    --output $target `
    $uri
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo descargar el audio AMI $meeting."
}
if (-not (Test-Path $target)) {
    throw "La descarga AMI no produjo fichero."
}

$bytes = [long](Get-Item $target).Length
if ($bytes -lt 10000000L -or $bytes -gt 100000000L) {
    throw "Tamaño AMI inesperado: $bytes bytes."
}
$sha256 = (Get-FileHash $target -Algorithm SHA256).Hash.ToUpperInvariant()

if ($env:GITHUB_ENV) {
    "AMI_SEMANTIC_FIXTURE_WAV=$target" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
    "AMI_SEMANTIC_FIXTURE_SHA256=$sha256" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
    "AMI_SEMANTIC_FIXTURE_BYTES=$bytes" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
}

Write-Host "AMI_SEMANTIC_MEETING=$meeting"
Write-Host "AMI_SEMANTIC_SOURCE=$uri"
Write-Host "AMI_SEMANTIC_LICENSE=CC-BY-4.0"
Write-Host "AMI_SEMANTIC_FIXTURE_BYTES=$bytes"
Write-Host "AMI_SEMANTIC_FIXTURE_SHA256=$sha256"
Write-Host "AMI audio is downloaded only into RUNNER_TEMP and is not uploaded as an artifact."
