# Video_Tunner

**Video_Tunner** es una aplicación portable para Windows 10/11 x64 orientada a la limpieza automática, inteligente, auditable y reversible de vídeo hablado.

Debe aceptar vídeo con audio embebido o vídeo + audio externo. Antes de cualquier transcripción o decisión temporal debe existir un **master audio** correctamente asociado a la línea temporal del vídeo. Los originales nunca se sobrescriben.

## Requisitos estructurales

### Portable real

```text
ZIP → descomprimir → ejecutar
```

Sin instalador, permisos de administrador, Python preinstalado ni FFmpeg/ffprobe preinstalados. Herramientas, modelos, configuración, temporales, caches y logs deben resolverse desde el propio árbol portable.

### Dos modos de entrada

```text
A) vídeo + audio embebido → master audio
B) vídeo + audio externo → sync → master audio
```

El modo B deberá admitir auto-sync con confidence, offset manual/override y detección/corrección validada de drift. Sin referencia suficiente, Video_Tunner no debe inventar la sincronización.

## Estado actual

**Versión:** `0.1.0-dev`

- Fase 0 — Bootstrap: ✅
- Fase 0.5 — Technology harvest: ✅
- Fase 1A — Portable Foundation: **✅ core + stack ML frozen validados en Windows**
- Fase 1B — Ingesta dual + sync/drift: **🔜 siguiente**
- Fase 1C — Transcripción/VAD sobre master audio: 🟡 parte ya implementada
- Release pública: ninguna

Video_Tunner sigue siendo un producto/repo propio. Los proyectos open source se aprovechan selectivamente y con trazabilidad; no se ha convertido en fork.

## Portable Foundation validada

### Core

Run `33600174568`:

- PyInstaller 6.22.2 `onedir`;
- `Video_Tunner.exe` con runtime Python empaquetado;
- FFmpeg/ffprobe propios;
- ejecución desde ruta aislada con espacios;
- PATH sin Python ni FFmpeg externos;
- `doctor`, `probe`, `clean`, render y ffprobe PASS;
- ZIP temporal core: `122677058` bytes (~117 MiB);
- 0 artifacts almacenados.

### Stack ML

Run `33621357438`:

- `faster-whisper 1.2.1`;
- `CTranslate2 4.8.1`;
- `ONNX Runtime 1.29.0`;
- `tokenizers 0.23.1`;
- `PyAV 18.1.0`;
- Silero VAD V6 ONNX dentro del frozen bundle;
- imports y DLLs nativas PASS;
- modelo `tiny` descargado dentro de `Models/whisper/tiny`;
- inferencia posterior con `HF_HUB_OFFLINE=1` PASS;
- 22 palabras transcritas;
- 3 candidatos `pause`;
- 0 ediciones automáticas;
- ZIP runtime ML sin modelo: `212334854` bytes (~202.5 MiB);
- 0 artifacts almacenados.

Esto demuestra **viabilidad portable real del runtime ML CPU**. No valida todavía la calidad de `large-v3-turbo`, que se probará sobre master audio real.

## Árbol portable

```text
Video_Tunner/
├── Video_Tunner.exe
├── _internal/
├── Tools/
│   └── ffmpeg/bin/
│       ├── ffmpeg.exe
│       └── ffprobe.exe
├── Models/
│   └── whisper/
├── Config/
├── Temp/
├── Cache/
├── Logs/
├── Output/
└── portable-manifest.json
```

## Modelos Whisper

Los modelos no se incrustan dentro del EXE:

```text
Models/whisper/<modelo>/
```

Comandos:

```powershell
Video_Tunner.exe model status large-v3-turbo
Video_Tunner.exe model fetch large-v3-turbo
```

`model fetch` usa staging bajo `Temp/model-downloads` y cache bajo `Cache/huggingface`. Un modelo no se considera disponible hasta encontrar al menos `config.json`, `model.bin` y `tokenizer.json`.

En portable strict, `analyze` sólo usa el modelo si está completo bajo `Models/whisper`; no recurre silenciosamente a caches globales. La primera adquisición puede necesitar red; después la inferencia debe poder funcionar offline.

Modelo objetivo de producto: **`large-v3-turbo`**. `tiny` fue únicamente el fixture de validación del runtime portable.

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

**Candidato ≠ decisión ≠ edición.**

## Funcionalidad existente

- CLI;
- FFmpeg/ffprobe + probe;
- Cleaner determinista de silencios;
- Edit Plan + render;
- WAV mono 16 kHz PCM16;
- faster-whisper word-level;
- TXT/JSON/SRT;
- Silero VAD ONNX;
- Candidate Analysis review-only;
- SHA-256 del source;
- gestión local de modelos;
- runtime portable core y ML Windows validados.

El `analyze` actual todavía parte del audio embebido del vídeo. Fase 1B/1C lo migrará a la abstracción de **master audio**.

## Desarrollo

```powershell
python -m pip install -e .
python -m pip install -e ".[analysis]"
```

Build core:

```powershell
.\.github\scripts\build_portable_windows.ps1 -Profile core
```

Build ML:

```powershell
.\.github\scripts\build_portable_windows.ps1 -Profile analysis
```

Comandos principales:

```powershell
video-tunner doctor
video-tunner probe "video.mp4"
video-tunner model status large-v3-turbo
video-tunner model fetch large-v3-turbo
video-tunner clean "video.mp4" --mode conservative --output-dir Output
video-tunner analyze "video.mp4" --model large-v3-turbo --language es --output-dir Output
video-tunner render "video.mp4" edit_plan.json "video_clean.mp4"
```

## Siguiente paso: Fase 1B

Ahora toca construir la base de ingesta/sincronización antes de ampliar la IA:

1. contrato de entrada vídeo + audio embebido/externo;
2. selección explícita de master audio;
3. auto-sync por correlación con offset y confidence;
4. offset manual/override;
5. anchors multi-window y drift;
6. corrección validada;
7. metadata auditable de sync;
8. tests sintéticos con offsets/drift conocidos.

Después se adaptará `analyze` al master audio y se validará `large-v3-turbo` con vídeo hablado real en español.

## Principios

- portable por diseño;
- procesamiento local por defecto;
- originales intactos;
- sync fiable antes de IA temporal;
- modo Conservador por defecto;
- ante duda semántica o de sync, conservar/revisar;
- GitHub como fuente de verdad;
- CI deliberada y sin artifacts pesados ordinarios.

Consulta `AGENTS.md`, `ROADMAP.md`, `UPSTREAM_SOURCES.md` y `Validation/` para el contexto técnico y la evidencia.
