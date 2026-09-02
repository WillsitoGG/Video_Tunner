# Release Status

## Estado actual

- Proyecto: Video_Tunner
- Versión de desarrollo: `0.1.0-dev`
- Release publicada: **no**
- ZIP portable final validado: **no**
- Windows 10/11 x64 validado manualmente por Guille: **no**
- Fase 0: bootstrap implementado
- Fase 0.5: technology harvest definido
- Fase 1A.1: **core portable Windows PASS**
- Fase 1A.2: **perfil ML portable implementado; ejecución Windows real pendiente**
- Fase 1B: ingesta dual + sincronización A/V pendiente
- Fase 1C: transcript/candidates parcialmente implementados; master audio + validación del modelo objetivo pendientes

## Portable Foundation — core

Decisión provisional aceptada para continuar:

- PyInstaller 6.22.2 `onedir`;
- FFmpeg/ffprobe bundled;
- modo portable estricto sin PATH fallback;
- Silero VAD vía ONNX de faster-whisper, evitando standalone silero-vad/Torch.

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

## Portable Foundation — stack ML

Preparado en rama `phase1a-ml-portable`:

- `faster-whisper==1.2.1`;
- `ctranslate2==4.8.1`;
- `onnxruntime==1.29.0`;
- `tokenizers==0.23.1`;
- PyAV/faster-whisper dependencies recogidas por PyInstaller;
- asset `silero_vad_v6.onnx` verificado por `doctor`;
- modelos bajo `Models/whisper/<modelo>`;
- `model status` / `model fetch`;
- staging de descarga en `Temp/` y cache de descarga en `Cache/`;
- inferencia portable exige modelo local completo y no usa silenciosamente caches externas;
- workflow `portable-ml-spike.yml` preparado para una única validación Windows deliberada con modelo `tiny`, seguida de inferencia con `HF_HUB_OFFLINE=1`.

El modelo `tiny` es sólo una prueba de packaging/runtime. El objetivo de calidad de producto sigue siendo `large-v3-turbo`, a validar separadamente sobre material hablado real.

No considerar Fase 1A cerrada hasta que el perfil ML frozen pase la ejecución Windows y queden registrados tamaño, SHA-256 y dependencias resueltas.

No existe todavía ningún paquete final que deba figurar en `SHA256SUMS.txt` ni ninguna versión sustituida para `Archive/`.

No publicar una GitHub Release sin autorización expresa del usuario.
