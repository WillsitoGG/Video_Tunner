# Release Status

## Estado actual

- Proyecto: Video_Tunner
- Versión de desarrollo: `0.1.0-dev`
- Release publicada: **no**
- ZIP portable final validado: **no**
- Windows 10/11 x64 validado manualmente por Guille: **no**
- Fase 0: bootstrap implementado
- Fase 0.5: technology harvest definido
- Fase 1A: **Portable Foundation PASS en Windows (core + stack ML CPU)**
- Fase 1B: ingesta dual + sincronización A/V — siguiente
- Fase 1C: transcript/candidates parcialmente implementados; pendiente adaptación a master audio + validación del modelo objetivo

## Portable Foundation — core

GitHub Actions `Portable Foundation Spike` run #1 (`33600174568`) — **SUCCESS** el 2026-09-02.

Validado:

- PyInstaller 6.22.2 `onedir`;
- `Video_Tunner.exe`;
- bundled FFmpeg/ffprobe;
- carpeta aislada con espacios;
- PATH sin Python/FFmpeg externos;
- `doctor`, `probe`, `clean`, render y ffprobe PASS;
- ZIP temporal core: `122677058` bytes;
- SHA-256: `5F3CFE09F017DE0421B906CE529822F830C8FFDE0731161AAFA42120464F4E97`;
- artifacts: 0.

## Portable Foundation — stack ML

GitHub Actions `Portable ML Foundation Spike` run #1 (`33621357438`) — **SUCCESS** el 2026-09-02.

Stack frozen validado:

- faster-whisper 1.2.1;
- CTranslate2 4.8.1;
- ONNX Runtime 1.29.0;
- tokenizers 0.23.1;
- PyAV 18.1.0;
- Silero VAD V6 ONNX dentro de `_internal`;
- FFmpeg/ffprobe propios;
- PATH sin Python/FFmpeg externos.

Modelo/runtime:

- `model fetch tiny` descargó el modelo dentro de `Models/whisper/tiny`;
- se verificaron `config.json`, `model.bin`, `tokenizer.json`;
- después se activó `HF_HUB_OFFLINE=1`;
- `Video_Tunner.exe analyze` ejecutó Whisper + VAD frozen/offline;
- `word_count=22`;
- 3 candidates tipo pause;
- `automatic_edits=0`;
- transcript JSON/TXT/SRT + analysis JSON generados.

Bundle ML temporal, **sin modelo**:

- `212334854` bytes (~202.5 MiB);
- SHA-256 `F1208C6E830A60CB06C1AB7781C0D7D60161341AC5C9DEA3D12EFB3F2BE3AF05`;
- artifacts almacenados: 0.

PyInstaller `onedir` queda aceptado como base provisional. Existe margen de reducción porque `--collect-all onnxruntime` recoge herramientas opcionales; no se gastará otro run sólo para optimizar tamaño en esta fase.

## Qué sigue pendiente antes de una Release

- Fase 1B: ingesta vídeo + audio externo, master audio, auto-sync, offset manual y drift;
- adaptar `analyze` al master audio;
- validar calidad/rendimiento de `large-v3-turbo` con vídeo hablado real, especialmente español;
- semantic cleaner;
- UX;
- Release Hardening, licencias/notices y validación en Windows limpio real;
- decidir política final de adquisición/inclusión de modelos.

No existe todavía ningún paquete final que deba figurar en `SHA256SUMS.txt` ni ninguna versión sustituida para `Archive/`.

No publicar una GitHub Release sin autorización expresa del usuario.
