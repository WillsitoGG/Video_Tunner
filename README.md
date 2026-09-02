# Video_Tunner

**Video_Tunner** es una aplicación portable para Windows 10/11 x64 orientada a la limpieza automática, inteligente, auditable y reversible de vídeo hablado.

Debe aceptar vídeo con audio embebido o vídeo + audio externo. Antes de cualquier transcripción o decisión temporal debe existir un **master audio** correctamente asociado a la línea temporal del vídeo. Los originales nunca se sobrescriben.

## Requisitos estructurales

```text
ZIP → descomprimir → ejecutar
```

Sin instalador, permisos de administrador, Python preinstalado ni FFmpeg/ffprobe preinstalados. Herramientas, modelos, configuración, temporales, caches y logs se resuelven desde el árbol portable.

```text
A) vídeo + audio embebido → master audio
B) vídeo + audio externo → sync → master audio
```

Sin referencia suficiente, Video_Tunner no inventa la sincronización.

## Estado actual

**Versión:** `0.1.0-dev`

- Fase 0 — Bootstrap: ✅
- Fase 0.5 — Technology harvest: ✅
- Fase 1A — Portable Foundation: ✅
- Fase 1B — Ingesta dual + sync/drift: ✅
- Fase 1C — Transcripción/VAD sobre master audio: **🟡 integración técnica portable validada; falta `large-v3-turbo` + español real**
- Release pública: ninguna

Video_Tunner sigue siendo producto/repo propio, no un fork.

## Portable Foundation

### Core — run `33600174568`

- PyInstaller 6.22.2 `onedir`;
- runtime Python + FFmpeg/ffprobe propios;
- PATH sin Python/FFmpeg externos;
- `doctor`, `probe`, `clean`, render y ffprobe PASS;
- ZIP temporal: `122677058` bytes;
- 0 artifacts.

### ML — run `33621357438`

- faster-whisper 1.2.1;
- CTranslate2 4.8.1;
- ONNX Runtime 1.29.0;
- tokenizers 0.23.1;
- NumPy 2.5.2;
- PyAV 18.1.0;
- Silero VAD V6 ONNX frozen;
- modelo local bajo `Models/whisper/<modelo>`;
- frozen/offline Whisper + VAD PASS;
- 0 artifacts.

Modelo objetivo de producto: **`large-v3-turbo`**. `tiny` sólo se utiliza como fixture barato de runtime/CI.

## Fase 1B — ingesta y sincronización

```powershell
video-tunner ingest "video.mp4" --output-dir Output
video-tunner ingest "video.mp4" --audio "grabador.wav" --output-dir Output
video-tunner ingest "video.mp4" --audio "grabador.wav" --offset 1.25 --output-dir Output
video-tunner ingest "video.mp4" --audio "grabador.wav" --offset -2.0 --drift-ppm 120 --output-dir Output
```

Convención temporal:

```text
video_time = offset_seconds + time_scale * external_time
```

Auto-sync: envolvente log-RMS → ZNCC coarse → anchors fine → ajuste offset/drift → confidence/residual/coverage. Si la evidencia no supera los thresholds, `ingest` devuelve `review_required` y no genera master.

Outputs:

```text
<video>_master_audio.flac
<video>_ingest.json
```

Hardening Windows run `33639009841`: 37 tests PASS, offset negativo, drift real, low-signal failure-safe, override manual y coverage parcial. Ver `Validation/sync-foundation-spike.md` y `Validation/sync-hardening.md`.

## Fase 1C — análisis sobre master audio

`analyze` ya no asume que debe leer el audio embebido del MP4.

Puede:

```powershell
# Audio embebido: ingest + master + analyze
video-tunner analyze "video.mp4" --model large-v3-turbo --language es --output-dir Output

# Audio externo: auto-sync + master + analyze
video-tunner analyze "video.mp4" --audio "micro.wav" --model large-v3-turbo --language es --output-dir Output

# Audio externo con override manual
video-tunner analyze "video.mp4" --audio "micro.wav" --offset 1.25 --model large-v3-turbo --language es --output-dir Output

# Reutilizar un master ya resuelto y acreditado
video-tunner analyze "video.mp4" --master-audio "video_master_audio.flac" --ingest-report "video_ingest.json" --model large-v3-turbo --language es --output-dir Output
```

Reglas:

- Whisper y Silero VAD reciben **exactamente el mismo master**;
- el master cubre la timeline completa del vídeo;
- todos los timestamps de transcript/VAD/candidates están en tiempo de vídeo;
- un master pre-resuelto exige su `ingest.json`;
- se verifica SHA-256 del vídeo fuente antes de reutilizarlo;
- si ingest devuelve `review_required`, Whisper/VAD no arrancan;
- `analysis.json` schema v2 registra provenance de master e ingest;
- candidates siguen `undecided` y `auto_apply=false`.

### Evidencia portable — run `33640872486`

**SUCCESS a la primera**:

- 41 source tests PASS;
- build frozen analysis PASS;
- NumPy + stack ML + Silero ONNX operativos sin Python/FFmpeg externos en PATH;
- inferencia posterior con `HF_HUB_OFFLINE=1`;
- embedded con audio retrasado: **89 palabras**, 11 pause candidates, vídeo/master `45.6 / 45.6 s`;
- external auto-sync: **88 palabras**, 9 pause candidates;
- offset real `+0.500 s` → estimado **`+0.49581 s`** (~4.19 ms de error);
- confidence `1.0`;
- drift estimado `192.308 ppm`;
- vídeo/master external `44.58275 / 44.58275 s`;
- automatic edits: `0`;
- artifacts: `0`.

Ver `Validation/master-audio-analysis-spike.md`.

## Pipeline

```text
sources
  ↓
ingest / sync
  ↓
MASTER AUDIO + video timeline
  ↓
Whisper word-level + Silero VAD
  ↓
candidates auditables
  ↓
KEEP / TRIM / CUT / REVIEW
  ↓
protección semántica
  ↓
Edit Plan
  ↓
render + audit
```

**Candidato ≠ decisión ≠ edición.**

## Modelos Whisper

```text
Models/whisper/<modelo>/
```

```powershell
Video_Tunner.exe model status large-v3-turbo
Video_Tunner.exe model fetch large-v3-turbo
```

En portable strict no existe fallback silencioso a caches globales.

## Siguiente trabajo

1. validar `large-v3-turbo` con contenido hablado real en español;
2. medir precisión cualitativa/word timestamps, velocidad, RAM y tamaño del modelo;
3. revisar parámetros Whisper/VAD y thresholds de sync sobre contenido real;
4. cerrar Fase 1C;
5. entrar en Fase 2: retomas, repeticiones, errores, fillers contextuales y protección semántica.

## Principios

- portable por diseño;
- local-first;
- originales intactos;
- sync fiable antes de IA temporal;
- Conservador por defecto;
- ante duda: KEEP/REVIEW;
- GitHub como source of truth;
- CI deliberada y sin artifacts pesados ordinarios.

Consulta `AGENTS.md`, `ROADMAP.md`, `UPSTREAM_SOURCES.md` y `Validation/`.
