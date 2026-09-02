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

Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $dist -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $work | Out-Null

$extras = if ($Profile -eq "analysis") { "analysis,packaging" } else { "packaging" }
& $Python -m pip install --disable-pip-version-check -e "${root}[$extras]"
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar dependencias del perfil $Profile." }

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
New-Item -ItemType Directory -Force -Path $ffmpegBin | Out-Null
Copy-Item $ffmpegExe.FullName (Join-Path $ffmpegBin "ffmpeg.exe") -Force
Copy-Item $ffprobeExe.FullName (Join-Path $ffmpegBin "ffprobe.exe") -Force

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
    schema_version = 2
    profile = "portable-$Profile-spike"
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    pyinstaller = "6.22.2"
    python_build = (& $Python --version 2>&1 | Out-String).Trim()
    ffmpeg_source = $FfmpegUrl
    ffmpeg_archive_sha256 = $ffmpegArchiveSha256
    ffmpeg = $ffmpegVersion
    ffprobe = $ffprobeVersion
    analysis_stack_included = ($Profile -eq "analysis")
    resolved_packages = $resolvedPackages
    models_bundled = @()
    note = "Spike build. Models are acquired into Models/ at runtime; final release must pin immutable dependency and FFmpeg provenance."
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $portable "portable-manifest.json")

Write-Host "Portable generated at: $portable"
& (Join-Path $portable "Video_Tunner.exe") doctor
if ($LASTEXITCODE -ne 0) { throw "El ejecutable portable no supera doctor." }
