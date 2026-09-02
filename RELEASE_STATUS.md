# Release Status

## Estado actual

- Proyecto: Video_Tunner
- Versión de desarrollo: `0.1.0-dev`
- Release publicada: **no**
- ZIP portable final validado: **no**
- Windows 10/11 x64 validado manualmente por Guille: **no**
- Fase 0: bootstrap implementado
- Fase 0.5: technology harvest definido
- Fase 1A: **core portable Windows PASS; stack ML portable pendiente**
- Fase 1B: ingesta dual + sincronización A/V pendiente
- Fase 1C: transcript/candidates parcialmente implementados; master audio + runtime ML real pendientes

## Portable Foundation

Decisión provisional aceptada para continuar:

- PyInstaller 6.22.2 `onedir`;
- FFmpeg/ffprobe bundled;
- modo portable estricto sin PATH fallback;
- Silero VAD vía ONNX de faster-whisper, evitando standalone silero-vad/Torch.

### Evidencia core

GitHub Actions `Portable Foundation Spike` run #1 (`33600174568`) — **SUCCESS** el 2026-09-02.

Validado automáticamente:

- `Video_Tunner.exe` generado;
- ejecución desde carpeta aislada con espacios;
- Python ausente del PATH de prueba;
- FFmpeg externo ausente del PATH de prueba;
- FFmpeg/ffprobe resueltos desde `Tools/ffmpeg/bin`;
- `doctor`, `probe`, `clean` y render real PASS;
- render validado con ffprobe empaquetado;
- layout portable local PASS;
- ZIP temporal del core: `122677058` bytes;
- SHA-256 temporal: `5F3CFE09F017DE0421B906CE529822F830C8FFDE0731161AAFA42120464F4E97`;
- artifacts almacenados en Actions: 0.

Este PASS **no valida todavía el perfil ML frozen**. Permanecen pendientes CTranslate2, ONNX Runtime, asset Silero ONNX, carga local del modelo Whisper e inferencia real dentro del portable.

No existe todavía ningún paquete final que deba figurar en `SHA256SUMS.txt` ni ninguna versión sustituida para `Archive/`.

No publicar una GitHub Release sin autorización expresa del usuario.
