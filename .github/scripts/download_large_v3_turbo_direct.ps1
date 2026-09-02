param(
    [string]$Destination = (Join-Path $env:RUNNER_TEMP "Video Tunner Large V3 Turbo Model")
)

$ErrorActionPreference = "Stop"
$repo = "rtlingo/mobiuslabsgmbh-faster-whisper-large-v3-turbo"
$revision = "6bd64462dd562f8062828f585c3709aa52df0083"
$userAgent = "Video_Tunner-CI/0.1 (+https://github.com/WillsitoGG/Video_Tunner)"
$expectedModelBytes = 1617884929L
$expectedModelSha256 = "E76620F83D5F5B69EFD3D87E3DC180C1BD21DF9FBEBACFD4335E5E1EFCC018DA"

$files = @(
    @{ name = "config.json"; min_bytes = 1000L },
    @{ name = "preprocessor_config.json"; min_bytes = 100L },
    @{ name = "tokenizer.json"; min_bytes = 2000000L },
    @{ name = "vocabulary.json"; min_bytes = 500000L },
    @{ name = "model.bin"; min_bytes = 1500000000L }
)

$curl = Get-Command curl.exe -ErrorAction SilentlyContinue
if (-not $curl) {
    throw "curl.exe no está disponible en el runner Windows."
}

Remove-Item $Destination -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$watch = [Diagnostics.Stopwatch]::StartNew()

foreach ($item in $files) {
    $name = [string]$item.name
    $target = Join-Path $Destination $name
    $uri = "https://huggingface.co/$repo/resolve/$revision/$name?download=true"

    Write-Host "Downloading pinned model file: $name"
    & $curl.Source `
        --location `
        --fail `
        --silent `
        --show-error `
        --retry 5 `
        --retry-all-errors `
        --retry-delay 8 `
        --connect-timeout 30 `
        --continue-at - `
        --user-agent $userAgent `
        --output $target `
        $uri
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo descargar $name desde el snapshot fijado $repo@$revision."
    }
    if (-not (Test-Path $target)) {
        throw "La descarga de $name no produjo fichero."
    }
    $size = [long](Get-Item $target).Length
    if ($size -lt [long]$item.min_bytes) {
        throw "$name tiene un tamaño inesperado: $size bytes."
    }
    $hash = (Get-FileHash $target -Algorithm SHA256).Hash.ToUpperInvariant()
    Write-Host "TARGET_MODEL_FILE_${name}_BYTES=$size"
    Write-Host "TARGET_MODEL_FILE_${name}_SHA256=$hash"

    if ($name -eq "model.bin") {
        if ($size -ne $expectedModelBytes) {
            throw "model.bin no coincide con el tamaño fijado: actual=$size esperado=$expectedModelBytes."
        }
        if ($hash -ne $expectedModelSha256) {
            throw "model.bin no coincide con SHA-256 fijado: actual=$hash esperado=$expectedModelSha256."
        }
    }
}

$watch.Stop()
$totalBytes = [long](Get-ChildItem $Destination -File | Measure-Object -Property Length -Sum).Sum
$required = @("config.json", "model.bin", "preprocessor_config.json", "tokenizer.json", "vocabulary.json")
foreach ($name in $required) {
    if (-not (Test-Path (Join-Path $Destination $name))) {
        throw "Falta archivo obligatorio del modelo: $name"
    }
}

if ($env:GITHUB_ENV) {
    "SPANISH_TARGET_MODEL_STAGE=$Destination" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
    "TARGET_MODEL_SOURCE_REPO=$repo" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
    "TARGET_MODEL_SOURCE_REVISION=$revision" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
    "TARGET_MODEL_EXPECTED_SHA256=$expectedModelSha256" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
    "TARGET_MODEL_STAGE_BYTES=$totalBytes" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
    "TARGET_MODEL_DOWNLOAD_SECONDS=$($watch.Elapsed.TotalSeconds)" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
}

Write-Host "TARGET_MODEL_SOURCE_REPO=$repo"
Write-Host "TARGET_MODEL_SOURCE_REVISION=$revision"
Write-Host "TARGET_MODEL_EXPECTED_SHA256=$expectedModelSha256"
Write-Host "TARGET_MODEL_STAGE_BYTES=$totalBytes"
Write-Host "TARGET_MODEL_DOWNLOAD_SECONDS=$([Math]::Round($watch.Elapsed.TotalSeconds, 3))"
