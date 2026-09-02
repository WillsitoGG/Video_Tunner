param(
    [string]$Destination = (Join-Path $env:RUNNER_TEMP "Video Tunner Spanish Fixture")
)

$ErrorActionPreference = "Stop"
$headers = @{
    "User-Agent" = "Video_Tunner-CI/0.1 (+https://github.com/WillsitoGG/Video_Tunner)"
}

$sources = @(
    @{
        id = "A0006"
        file = "SpanishPod_newbie_lesson_A0006_dialogue.ogg"
        uri = "https://upload.wikimedia.org/wikipedia/commons/0/0a/SpanishPod_newbie_lesson_A0006_dialogue.ogg"
    },
    @{
        id = "A0007"
        file = "SpanishPod_newbie_lesson_A0007_dialogue.ogg"
        uri = "https://upload.wikimedia.org/wikipedia/commons/4/4c/SpanishPod_newbie_lesson_A0007_dialogue.ogg"
    },
    @{
        id = "A0013"
        file = "SpanishPod_newbie_lesson_A0013_dialogue.ogg"
        uri = "https://upload.wikimedia.org/wikipedia/commons/6/67/SpanishPod_newbie_lesson_A0013_dialogue.ogg"
    },
    @{
        id = "A0116"
        file = "SpanishPod_newbie_lesson_A0116_dialogue.ogg"
        uri = "https://upload.wikimedia.org/wikipedia/commons/5/54/SpanishPod_newbie_lesson_A0116_dialogue.ogg"
    }
)

function Get-WithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$OutFile
    )

    $delays = @(0, 3, 8, 15)
    $lastError = $null
    for ($attempt = 0; $attempt -lt $delays.Count; $attempt++) {
        if ($delays[$attempt] -gt 0) {
            Start-Sleep -Seconds $delays[$attempt]
        }
        try {
            Remove-Item $OutFile -Force -ErrorAction SilentlyContinue
            Invoke-WebRequest -Uri $Uri -Headers $headers -OutFile $OutFile -TimeoutSec 45
            if (-not (Test-Path $OutFile)) {
                throw "La descarga no creó fichero."
            }
            $size = (Get-Item $OutFile).Length
            if ($size -lt 20000) {
                throw "Fichero descargado sospechosamente pequeño: $size bytes."
            }
            return
        } catch {
            $lastError = $_
            Write-Warning "Descarga fallida intento $($attempt + 1)/$($delays.Count): $Uri — $($_.Exception.Message)"
        }
    }
    throw "No se pudo descargar $Uri tras $($delays.Count) intentos. Último error: $lastError"
}

Remove-Item $Destination -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $Destination | Out-Null

foreach ($item in $sources) {
    $target = Join-Path $Destination $item.file
    Get-WithRetry -Uri $item.uri -OutFile $target
    $hash = (Get-FileHash $target -Algorithm SHA256).Hash
    $bytes = (Get-Item $target).Length
    Write-Host "$($item.id)_SHA256=$hash"
    Write-Host "$($item.id)_BYTES=$bytes"
    Start-Sleep -Seconds 2
}

if ($env:GITHUB_ENV) {
    "SPANISH_MODEL_FIXTURE_ROOT=$Destination" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
}

Write-Host "SPANISH_FIXTURE_DOWNLOADS_READY=$Destination"
