# Video_Tunner

**Video_Tunner** es una aplicación portable para Windows 10/11 x64 orientada a la limpieza automática, inteligente, auditable y reversible de vídeo hablado.

Debe aceptar vídeo con audio embebido o vídeo + audio externo. Antes de cualquier transcripción o decisión temporal debe existir un **master audio** correctamente asociado a la línea temporal del vídeo. Los originales nunca se sobrescriben.

## Requisitos estructurales

### Portable real

Objetivo:

```text
ZIP → descomprimir → ejecutar
```

Sin instalador, permisos de administrador, Python preinstalado ni FFmpeg/ffprobe preinstalados. En modo portable herramientas, modelos, configuración, temporales, caches y logs deben resolverse desde el propio árbol de Video_Tunner.

### Dos modos de entrada

```text
A) vídeo + audio embebido → master audio
B) vídeo + audio externo → sync → master audio
```

El modo B deberá admitir auto-sync con confianza, offset manual/override y detección/corrección validada de drift. Si no existe referencia suficiente, Video_Tunner no debe adivinar la sincronización.

Ver `ROADMAP.md`.

## Estado actual

**Versión de desarrollo:** `0.1.0-dev`

- Fase 0 — Bootstrap: **implementada**.
- Fase 0.5 — Technology harvest: **cerrada**.
- Fase 1A.1 — Core portable: **PASS Windows**.
- Fase 1A.2 — Stack ML portable: **implementado en spike; validación Windows pendiente**.
- Fase 1B — Ingesta dual + sincronización A/V: **pendiente**.
- Fase 1C — Transcripción + VAD: **parcialmente implementada**; pendiente de master audio y validación del modelo objetivo.
- Release pública: **ninguna**.

Video_Tunner sigue siendo un producto/repo propio. `vcut`, `Cadence-Lab`, `ai-video-editor` y dependencias upstream se estudian mediante technology harvest selectivo y trazable.

## Portable Foundation

### Core validado

El run Windows `Portable Foundation Spike` #1 (`33600174568`) demostró:

- PyInstaller 6.22.2 `onedir`;
- `Video_Tunner.exe` con runtime Python empaquetado;
- FFmpeg/ffprobe propios en `Tools/ffmpeg/bin`;
- ejecución desde una ruta aislada con espacios;
- PATH sin Python ni FFmpeg externos;
- `doctor`, `probe`, `clean`, render y validación con ffprobe bundled;
- layout local `Models/Config/Temp/Cache/Logs/Output`;
- ZIP temporal core de `122677058` bytes;
- 0 artifacts almacenados.

### Árbol portable

```text
Video_Tunner/
├── Video_Tunner.exe
├── _internal/
├── Tools/
│   └── ffmpeg/
│       └── bin/
│           ├── ffmpeg.exe
│           └── ffprobe.exe
├── Models/
│   └── whisper/
├── Config/
├── Temp/
├── Cache/
├── Logs/
├── Output/
└── portable-manifest.json
```

### Stack ML

Perfil de spike fijado:

- `faster-whisper==1.2.1`;
- `ctranslate2==4.8.1`;
- `onnxruntime==1.29.0`;
- `tokenizers==0.23.1`;
- PyAV y restantes dependencias resueltas por faster-whisper;
- PyInstaller `6.22.2`.

Silero VAD utiliza el `silero_vad_v6.onnx` ya incluido por faster-whisper. No se añade standalone `silero-vad` + Torch/torchaudio.

### Modelos Whisper locales

Los modelos no se incrustan dentro del EXE ni de `_internal`:

```text
Models/whisper/<modelo>/
```

Ventajas:

- cambiar modelo sin recompilar;
- distribución del runtime separada del peso del modelo;
- estrategia offline explícita;
- fácil auditar qué modelo se usa.

Comandos:

```powershell
Video_Tunner.exe model status large-v3-turbo
Video_Tunner.exe model fetch large-v3-turbo
```

`model fetch` descarga primero a staging bajo `Temp/model-downloads` y usa cache bajo `Cache/huggingface`. Un modelo no se considera disponible hasta tener, como mínimo, `config.json`, `model.bin` y `tokenizer.json`.

En portable strict, `analyze` sólo acepta el modelo si está completo dentro de `Models/whisper`; no utiliza silenciosamente una cache global de Hugging Face.

El spike Windows usará `tiny` exclusivamente para demostrar empaquetado e inferencia real a bajo coste. El modelo objetivo de producto sigue siendo **`large-v3-turbo`**.

## Pipeline objetivo

```text
vídeo + audio embebido
          O
vídeo + audio externo
          ↓
       ingest/sync
          ↓
      MASTER AUDIO
          ↓
transcripción + VAD + análisis
          ↓
 candidatos auditables
          ↓
 KEEP / TRIM / CUT / REVIEW
          ↓
 protección semántica
          ↓
       Edit Plan
          ↓
 render + auditoría
```

Candidato ≠ decisión ≠ edición.

## Funcionalidad existente

- CLI;
- FFmpeg/ffprobe + probe;
- Cleaner determinista de silencios;
- Edit Plan;
- render H.264/AAC sin sobrescribir original;
- extracción WAV mono 16 kHz PCM16;
- estructuras de transcripción word-level;
- TXT/JSON/SRT;
- Candidate Analysis review-only;
- SHA-256 del source;
- tests unitarios y E2E sintéticos;
- runtime core portable Windows validado.

Implementado y pendiente de la validación ML Windows:

- faster-whisper frozen;
- CTranslate2/ONNX Runtime frozen;
- Silero VAD ONNX frozen;
- adquisición de modelos en el árbol portable;
- inferencia Whisper/VAD offline tras adquirir el modelo.

## Desarrollo local

```powershell
python -m pip install -e .
python -m pip install -e ".[analysis]"
```

Build core:

```powershell
.\.github\scripts\build_portable_windows.ps1 -Profile core
```

Build analysis:

```powershell
.\.github\scripts\build_portable_windows.ps1 -Profile analysis
```

### Comandos

```powershell
video-tunner doctor
video-tunner probe "video.mp4"
video-tunner model status large-v3-turbo
video-tunner model fetch large-v3-turbo
video-tunner plan "video.mp4" --mode conservative --output edit_plan.json
video-tunner clean "video.mp4" --mode conservative --output-dir Output
video-tunner analyze "video.mp4" --model large-v3-turbo --language es --output-dir Output
video-tunner render "video.mp4" edit_plan.json "video_clean.mp4"
```

`analyze` todavía consume el audio embebido del vídeo; se adaptará al concepto de `master audio` en Fase 1B/1C.

## Validación ML portable

Workflow manual: `.github/workflows/portable-ml-spike.yml`.

La prueba debe:

1. construir el perfil `analysis` en Windows;
2. comprobar imports reales de faster-whisper, CTranslate2, ONNX Runtime, tokenizers y PyAV;
3. localizar `silero_vad_v6.onnx` dentro del frozen bundle;
4. ejecutarse en PATH sin Python/FFmpeg externos;
5. descargar `tiny` dentro de `Models/whisper`;
6. crear un vídeo hablado temporal con un fixture upstream pequeño;
7. activar `HF_HUB_OFFLINE=1`;
8. ejecutar `analyze` desde `Video_Tunner.exe`;
9. producir transcript con palabras y analysis JSON;
10. registrar tamaño/SHA del ZIP temporal;
11. no almacenar el ZIP como artifact.

Esto valida runtime/packaging, no calidad de `tiny` ni de `large-v3-turbo`.

## Próximos pasos

1. Ejecutar/corregir una única validación Windows del perfil ML.
2. Si pasa, cerrar Fase 1A.
3. Implementar Fase 1B: vídeo + audio externo, master audio, auto-sync, offset manual y drift.
4. Adaptar `analyze` al master audio.
5. Validar `large-v3-turbo` + VAD sobre vídeo hablado real en español.
6. Sólo después construir retomas/repeticiones y la capa semántica.

## Principios

- portable por diseño;
- procesamiento local por defecto;
- originales intactos;
- línea temporal A/V fiable antes de IA;
- candidato ≠ decisión ≠ edición;
- modo Conservador por defecto;
- ante duda semántica o de sync, conservar/revisar;
- GitHub como fuente de verdad;
- CI deliberada y sin artifacts pesados ordinarios.

Consulta `AGENTS.md`, `ROADMAP.md`, `UPSTREAM_SOURCES.md` y `Validation/` para contexto técnico y evidencia.
