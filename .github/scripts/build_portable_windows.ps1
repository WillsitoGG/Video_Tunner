param(
    [string]$Python = "python",
    [string]$FfmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n9.0-latest-win64-gpl-9.0.zip",
    [ValidateSet("core", "analysis")]
    [string]$Profile = "core"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$work = Join-Path $root ".portable-build"
$dist = Join-Path $root "dist"
$ffmpegZip = Join-Path $work "ffmpeg.zip"
$ffmpegExtract = Join-Path $work "ffmpeg"
$deepfilterDownload = Join-Path $work "deep-filter.exe"

Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $dist -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $work | Out-Null

$extras = if ($Profile -eq "analysis") { "analysis,packaging" } else { "packaging" }
& $Python -m pip install --disable-pip-version-check -e "${root}[$extras]"
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar dependencias del perfil $Profile." }

$deepfilterContractJson = (& $Python -c "import json; from video_tunner.denoise_runtime import selected_denoiser_contract; print(json.dumps(selected_denoiser_contract()))" | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $deepfilterContractJson) { throw "No se pudo cargar el contrato DeepFilterNet seleccionado." }
$deepfilterContract = $deepfilterContractJson | ConvertFrom-Json
if ($deepfilterContract.integration_state.runtime_download_allowed -ne $false) { throw "El contrato no puede permitir descarga DeepFilterNet en runtime." }
if ($deepfilterContract.integration_state.denoise_authorized -ne $false -or $deepfilterContract.integration_state.renderer_authorized -ne $false) {
    throw "3.6g no puede autorizar denoise ni renderer."
}

Write-Host "Downloading immutable DeepFilterNet build-time asset..."
Invoke-WebRequest -Uri $deepfilterContract.asset_url -OutFile $deepfilterDownload
$deepfilterDownloadedSha256 = (Get-FileHash $deepfilterDownload -Algorithm SHA256).Hash.ToLowerInvariant()
$deepfilterDownloadedSize = (Get-Item $deepfilterDownload).Length
if ($deepfilterDownloadedSha256 -ne $deepfilterContract.asset_sha256) {
    throw "DeepFilterNet SHA256 no coincide con el contrato congelado."
}
if ($deepfilterDownloadedSize -ne [int64]$deepfilterContract.asset_size_bytes) {
    throw "DeepFilterNet size no coincide con el contrato congelado."
}
$deepfilterVersionOutput = (& $deepfilterDownload --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $deepfilterVersionOutput -notmatch [regex]::Escape($deepfilterContract.version)) {
    throw "DeepFilterNet --version no cumple el contrato congelado."
}
$deepfilterHelpOutput = (& $deepfilterDownload --help 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0 -or $deepfilterHelpOutput -notmatch "--compensate-delay" -or $deepfilterHelpOutput -notmatch "--output-dir") {
    throw "DeepFilterNet --help no cumple el contrato CLI congelado."
}

Write-Host "Downloading FFmpeg portable build..."
Invoke-WebRequest -Uri $FfmpegUrl -OutFile $ffmpegZip
$ffmpegArchiveSha256 = (Get-FileHash $ffmpegZip -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "FFMPEG_ARCHIVE_SHA256=$ffmpegArchiveSha256"
Expand-Archive -Path $ffmpegZip -DestinationPath $ffmpegExtract -Force

$ffmpegExe = Get-ChildItem $ffmpegExtract -Filter "ffmpeg.exe" -Recurse | Select-Object -First 1
$ffprobeExe = Get-ChildItem $ffmpegExtract -Filter "ffprobe.exe" -Recurse | Select-Object -First 1
if (-not $ffmpegExe -or -not $ffprobeExe) {
    throw "El paquete FFmpeg descargado no contiene ffmpeg.exe y ffprobe.exe."
}

$pyinstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--onedir",
    "--name", "Video_Tunner",
    "--paths", (Join-Path $root "Source"),
    "--contents-directory", "_internal"
)

if ($Profile -eq "analysis") {
    foreach ($package in @("faster_whisper", "ctranslate2", "onnxruntime", "tokenizers", "av")) {
        $pyinstallerArgs += @("--collect-all", $package)
    }
}

$pyinstallerArgs += (Join-Path $root "packaging\entrypoint.py")
& $Python -m PyInstaller @pyinstallerArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller no pudo generar el portable." }

$portable = Join-Path $dist "Video_Tunner"
$ffmpegBin = Join-Path $portable "Tools\ffmpeg\bin"
$deepfilterBin = Join-Path $portable "Tools\deepfilter\bin"
New-Item -ItemType Directory -Force -Path $ffmpegBin | Out-Null
New-Item -ItemType Directory -Force -Path $deepfilterBin | Out-Null
Copy-Item $ffmpegExe.FullName (Join-Path $ffmpegBin "ffmpeg.exe") -Force
Copy-Item $ffprobeExe.FullName (Join-Path $ffmpegBin "ffprobe.exe") -Force
$deepfilterPortable = Join-Path $deepfilterBin "deep-filter.exe"
Copy-Item $deepfilterDownload $deepfilterPortable -Force

$deepfilterCopiedSha256 = (Get-FileHash $deepfilterPortable -Algorithm SHA256).Hash.ToLowerInvariant()
$deepfilterCopiedSize = (Get-Item $deepfilterPortable).Length
if ($deepfilterCopiedSha256 -ne $deepfilterContract.asset_sha256 -or $deepfilterCopiedSize -ne [int64]$deepfilterContract.asset_size_bytes) {
    throw "La copia portable DeepFilterNet no conserva identidad exacta."
}
$deepfilterValidationJson = (& $Python -c "import json,sys; from pathlib import Path; from video_tunner.denoise_runtime import validate_selected_denoiser_binary; print(json.dumps(validate_selected_denoiser_binary(Path(sys.argv[1]), probe_cli=True)))" $deepfilterPortable | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $deepfilterValidationJson) { throw "El validador de producto rechazó DeepFilterNet portable." }
$deepfilterValidation = $deepfilterValidationJson | ConvertFrom-Json
if ($deepfilterValidation.valid -ne $true) { throw "DeepFilterNet portable no quedó validado." }

foreach ($folder in @("Models", "Temp", "Cache", "Config", "Logs", "Output")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $portable $folder) | Out-Null
}

$ffmpegVersion = (& (Join-Path $ffmpegBin "ffmpeg.exe") -version | Select-Object -First 1)
$ffprobeVersion = (& (Join-Path $ffmpegBin "ffprobe.exe") -version | Select-Object -First 1)
$resolvedPackages = @{}
foreach ($package in @("faster-whisper", "ctranslate2", "onnxruntime", "tokenizers", "av", "huggingface-hub")) {
    $version = (& $Python -c "import importlib.metadata as m; print(m.version('$package'))" 2>$null)
    if ($LASTEXITCODE -eq 0) { $resolvedPackages[$package] = ($version | Out-String).Trim() }
}

$manifest = [ordered]@{
    schema_version = 3
    profile = "portable-$Profile-spike"
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    pyinstaller = "6.22.2"
    python_build = (& $Python --version 2>&1 | Out-String).Trim()
    ffmpeg_source = $FfmpegUrl
    ffmpeg_archive_sha256 = $ffmpegArchiveSha256
    ffmpeg = $ffmpegVersion
    ffprobe = $ffprobeVersion
    selected_denoiser = [ordered]@{
        candidate_id = $deepfilterContract.candidate_id
        implementation = $deepfilterContract.implementation
        version = $deepfilterContract.version
        asset_name = $deepfilterContract.asset_name
        asset_source = $deepfilterContract.asset_url
        asset_sha256 = $deepfilterCopiedSha256
        asset_size_bytes = $deepfilterCopiedSize
        runtime_relative_path = $deepfilterContract.runtime_relative_path
        arguments = @($deepfilterContract.arguments)
        explicit_model_argument = $deepfilterContract.explicit_model_argument
        selected_for_integration_review_only = $true
        runtime_download_allowed = $false
        product_default = "preserve"
        denoise_authorized = $false
        renderer_authorized = $false
        auto_apply = $false
    }
    analysis_stack_included = ($Profile -eq "analysis")
    resolved_packages = $resolvedPackages
    models_bundled = @()
    note = "Spike build. The selected DeepFilterNet binary is bundled immutably for offline integration review only; denoise/render remain unauthorized. Whisper models are still managed separately and final release provenance remains a Phase 5 concern."
}
$manifest | ConvertTo-Json -Depth 7 | Set-Content -Encoding UTF8 (Join-Path $portable "portable-manifest.json")

Write-Host "Portable generated at: $portable"
& (Join-Path $portable "Video_Tunner.exe") doctor
if ($LASTEXITCODE -ne 0) { throw "El ejecutable portable no supera doctor." }
