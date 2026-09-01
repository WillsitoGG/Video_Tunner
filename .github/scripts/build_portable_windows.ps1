param(
    [string]$Python = "python",
    [string]$FfmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n9.0-latest-win64-gpl.zip"
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

& $Python -m pip install --disable-pip-version-check -e "${root}[packaging]"
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar dependencias de packaging." }

Write-Host "Downloading FFmpeg portable build..."
Invoke-WebRequest -Uri $FfmpegUrl -OutFile $ffmpegZip
Expand-Archive -Path $ffmpegZip -DestinationPath $ffmpegExtract -Force

$ffmpegExe = Get-ChildItem $ffmpegExtract -Filter "ffmpeg.exe" -Recurse | Select-Object -First 1
$ffprobeExe = Get-ChildItem $ffmpegExtract -Filter "ffprobe.exe" -Recurse | Select-Object -First 1
if (-not $ffmpegExe -or -not $ffprobeExe) {
    throw "El paquete FFmpeg descargado no contiene ffmpeg.exe y ffprobe.exe."
}

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --name Video_Tunner `
    --paths (Join-Path $root "Source") `
    --contents-directory "_internal" `
    (Join-Path $root "packaging\entrypoint.py")
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
$manifest = [ordered]@{
    schema_version = 1
    profile = "portable-core-spike"
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    pyinstaller = "6.22.2"
    python_build = (& $Python --version 2>&1 | Out-String).Trim()
    ffmpeg_source = $FfmpegUrl
    ffmpeg = $ffmpegVersion
    ffprobe = $ffprobeVersion
    analysis_stack_included = $false
    note = "Spike build only. FFmpeg URL floats within the n9.0 latest branch; final release must pin an immutable asset/digest."
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 (Join-Path $portable "portable-manifest.json")

Write-Host "Portable generated at: $portable"
& (Join-Path $portable "Video_Tunner.exe") doctor
if ($LASTEXITCODE -ne 0) { throw "El ejecutable portable no supera doctor." }
