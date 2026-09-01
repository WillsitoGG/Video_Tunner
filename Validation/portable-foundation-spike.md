# Portable Foundation Spike — Fase 1A

## Estado

**IMPLEMENTADO / PENDIENTE DE EJECUCIÓN WINDOWS REAL**

Este documento registra qué pretende demostrar el primer spike portable. No es evidencia de PASS hasta que exista una ejecución Windows real con todos los checks verdes.

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

Manual-only; no artifact upload.

## Acceptance criteria core

- [ ] Windows x64 job PASS.
- [ ] source tests PASS.
- [ ] `Video_Tunner.exe` generated.
- [ ] bundled `ffmpeg.exe` + `ffprobe.exe` found.
- [ ] isolated directory with spaces PASS.
- [ ] Python absent from test PATH.
- [ ] external FFmpeg absent from test PATH.
- [ ] portable `doctor` PASS.
- [ ] portable `probe` PASS.
- [ ] portable `clean` PASS.
- [ ] rendered MP4 validates with bundled ffprobe.
- [ ] temporary ZIP SHA-256 + size emitted to logs.
- [ ] no ZIP uploaded as Actions artifact.

## Not covered by first run

- faster-whisper frozen import;
- CTranslate2 DLLs;
- ONNX Runtime DLLs;
- Silero ONNX asset collection;
- real Whisper model;
- CUDA;
- external audio/sync.

Those are the next sub-spike after core portable PASS.
