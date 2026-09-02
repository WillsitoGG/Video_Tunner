# Portable Foundation Spike — Fase 1A

## Estado

**CORE PORTABLE: PASS / ML PORTABLE: PENDIENTE**

Ejecución validada: GitHub Actions `Portable Foundation Spike` run #1, ID `33600174568`, 2026-09-02.

La ejecución fue deliberadamente única. El workflow se activó mediante un trigger temporal restringido a un único fichero marcador y, una vez iniciado el run, volvió a quedar `workflow_dispatch`-only. El marcador se eliminó sin generar una segunda ejecución.

## Decisiones

- Packaging inicial: PyInstaller 6.22.2 `onedir`.
- Runtime target: Windows 10/11 x64.
- FFmpeg/ffprobe: binarios empaquetados bajo `Tools/ffmpeg/bin`.
- Portable strict: no PATH fallback para herramientas/modelos.
- VAD: usar Silero ONNX incluido en faster-whisper; eliminar silero-vad standalone + Torch/torchaudio.

## Razón del cambio VAD

La distribución oficial de `silero-vad` 6.2.1 declara Torch y torchaudio como dependencias base. `faster-whisper` ya depende de ONNX Runtime y contiene `silero_vad_v6.onnx` junto con su implementación VAD. Mantener dos stacks sería redundante y perjudicaría tamaño/packaging.

## Workflow

`.github/workflows/portable-spike.yml`

Estado permanente tras la validación: `workflow_dispatch`-only; sin artifact upload.

## Resultado del run #1

- Job `windows-portable-core`: **SUCCESS**.
- Runner: Windows Server 2025 / windows-latest.
- Python de build: CPython 3.12.10.
- PyInstaller: 6.22.2.
- FFmpeg empaquetado: `n9.0.1-11-ge47273f4d9-20260901`.
- SHA-256 del ZIP upstream de FFmpeg usado por el build: `06910d03c4c4407a092336e1b9b4d200afa361979fdb2e5971c9e0f430a355de`.
- Tests source: 20 ejecutados, 18 PASS + 2 SKIP esperados por ausencia de FFmpeg en el PATH de la fase previa al packaging.
- `Video_Tunner.exe`: generado correctamente.
- `doctor` portable: PASS.
- Runtime root resuelto desde la carpeta portable.
- `Models/`, `Temp/`, `Cache/`, `Config/`, `Logs/`, `Output/` y `Tools/ffmpeg/bin`: resueltos bajo el runtime portable.
- Prueba aislada ejecutada desde una ruta con espacios: PASS.
- Python externo eliminado del PATH de prueba: PASS.
- FFmpeg externo eliminado del PATH de prueba: PASS.
- `probe` sobre fixture generado con FFmpeg empaquetado: PASS.
- `clean --mode conservative`: PASS.
- Render real: PASS.
- Vídeo sintético original: 3.0 s.
- Silencio eliminado: ~0.800042 s.
- Duración estimada: ~2.199958 s.
- Duración render validada con ffprobe empaquetado: ~2.219979 s.
- ZIP temporal del core portable: `122677058` bytes (~117 MiB).
- SHA-256 ZIP temporal: `5F3CFE09F017DE0421B906CE529822F830C8FFDE0731161AAFA42120464F4E97`.
- Artifacts almacenados por Actions: **0**.

## Acceptance criteria core

- [x] Windows x64 job PASS.
- [x] source tests PASS.
- [x] `Video_Tunner.exe` generated.
- [x] bundled `ffmpeg.exe` + `ffprobe.exe` found.
- [x] isolated directory with spaces PASS.
- [x] Python absent from test PATH.
- [x] external FFmpeg absent from test PATH.
- [x] portable `doctor` PASS.
- [x] portable `probe` PASS.
- [x] portable `clean` PASS.
- [x] rendered MP4 validates with bundled ffprobe.
- [x] temporary ZIP SHA-256 + size emitted to logs.
- [x] no ZIP uploaded as Actions artifact.

## No cubierto todavía

Este PASS demuestra la **base portable del core determinista**, no el pipeline ML completo.

Pendiente en el siguiente sub-spike:

- frozen import de `faster-whisper`;
- CTranslate2 DLLs;
- ONNX Runtime DLLs;
- asset `silero_vad_v6.onnx` dentro del bundle;
- carga de modelo Whisper desde `Models/` local;
- inferencia real de Whisper;
- inferencia real de Silero ONNX;
- funcionamiento offline una vez adquirido el modelo;
- CUDA, que seguirá siendo opt-in y posterior;
- audio externo/sincronización, que pertenece a Fase 1B.

## Conclusión

PyInstaller `onedir` queda **aceptado provisionalmente para continuar**: ha demostrado que el core actual puede ejecutarse como aplicación Windows autocontenida sin depender de Python ni FFmpeg del sistema. No se considera todavía cerrada toda la Fase 1A hasta validar el stack `faster-whisper` + CTranslate2 + ONNX Runtime + modelo local dentro del portable.
