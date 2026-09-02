# Video_Tunner

**Video_Tunner** es una aplicación portable para Windows 10/11 x64 orientada a la limpieza automática, inteligente, auditable y reversible de vídeo hablado.

Debe aceptar vídeo con audio embebido o vídeo + audio externo. Antes de cualquier transcripción o decisión temporal debe existir un **master audio** correctamente asociado a la línea temporal del vídeo. Los originales nunca se sobrescriben.

## Requisitos estructurales

```text
ZIP → descomprimir → ejecutar
```

Sin instalador, permisos de administrador, Python preinstalado ni FFmpeg/ffprobe preinstalados. Herramientas, modelos, configuración, temporales, caches y logs deben resolverse desde el árbol portable.

Entradas:

```text
A) vídeo + audio embebido → master audio
B) vídeo + audio externo → sync → master audio
```

Sin referencia suficiente, Video_Tunner no debe inventar la sincronización.

## Estado actual

**Versión:** `0.1.0-dev`

- Fase 0 — Bootstrap: ✅
- Fase 0.5 — Technology harvest: ✅
- Fase 1A — Portable Foundation: ✅ core + stack ML frozen validados en Windows
- Fase 1B — Ingesta dual + sync/drift: 🟡 **foundation implementada y validada; hardening pendiente**
- Fase 1C — Transcripción/VAD sobre master audio: 🟡 código de análisis existente; adaptación pendiente
- Release pública: ninguna

Video_Tunner sigue siendo un producto/repo propio, no un fork.

## Portable Foundation

### Core — run `33600174568`

- PyInstaller 6.22.2 `onedir`;
- runtime Python + FFmpeg/ffprobe propios;
- ruta aislada con espacios;
- PATH sin Python/FFmpeg externos;
- `doctor`, `probe`, `clean`, render y ffprobe PASS;
- ZIP temporal: `122677058` bytes;
- 0 artifacts.

### ML — run `33621357438`

- faster-whisper 1.2.1;
- CTranslate2 4.8.1;
- ONNX Runtime 1.29.0;
- tokenizers 0.23.1;
- PyAV 18.1.0;
- Silero VAD V6 ONNX frozen;
- `tiny` adquirido bajo `Models/whisper/tiny`;
- `HF_HUB_OFFLINE=1` + Whisper/VAD frozen PASS;
- 22 palabras, 3 candidatos pause, 0 edits automáticos;
- runtime ML sin modelo: `212334854` bytes (~202.5 MiB);
- 0 artifacts.

Modelo objetivo de producto: **`large-v3-turbo`**. `tiny` sólo validó runtime.

## Fase 1B — sync foundation

Nuevo comando:

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

- offset positivo: el grabador externo empezó después del vídeo;
- offset negativo: empezó antes;
- `drift_ppm = (time_scale - 1) × 1e6`.

Auto-sync actual:

1. FFmpeg extrae referencia mono 8 kHz;
2. envolvente log-RMS a 50 Hz;
3. correlación ZNCC coarse;
4. 7 anchors fine multi-window;
5. ajuste lineal offset + drift;
6. outliers por MAD;
7. confidence según correlación, unicidad, residuos y nº de anchors;
8. aceptación sólo si pasa confidence, anchors, residual, drift y cobertura.

Si la evidencia es insuficiente, `ingest` genera `review_required` y **no materializa master**. El override manual es explícito. Nunca se mezcla audio de cámara para rellenar huecos sin indicarlo: los huecos externos manuales se rellenan con silencio.

Outputs:

```text
<video>_master_audio.flac
<video>_ingest.json
```

El informe registra SHA-256, fuentes, método, offset, confidence, anchors, drift, residuos, cobertura, warnings y master seleccionado.

### Validación Windows sync

Workflow manual: `.github/workflows/sync-spike.yml`.

Runs:

- `33633846344` — FAILURE: primera aserción de duración era incorrecta;
- `33634121264` — FAILURE útil: descubrió que el master quedaba `88.756 s` frente a vídeo `90.000 s`;
- `33634775313` — **SUCCESS** tras corregir timestamps/padding.

Run final:

- 33 tests PASS;
- offset esperado/estimado: `+1.500 s` / `+1.500 s`;
- confidence `1.000`;
- 7 anchors;
- drift `0 ppm`;
- vídeo `90.000 s`;
- master `90.000 s`;
- 0 artifacts.

El bug de duración queda cubierto por un test E2E de regresión de 4 s. Ver `Validation/sync-foundation-spike.md`.

## Modelos Whisper

Ruta:

```text
Models/whisper/<modelo>/
```

```powershell
Video_Tunner.exe model status large-v3-turbo
Video_Tunner.exe model fetch large-v3-turbo
```

En portable strict sólo se usa un modelo completo bajo `Models/whisper`; no hay fallback silencioso a caches globales.

## Pipeline

```text
sources
  ↓
ingest / sync
  ↓
MASTER AUDIO + video timeline
  ↓
transcripción + VAD + análisis
  ↓
candidates
  ↓
decisions
  ↓
Edit Plan
  ↓
render + audit
```

**Candidato ≠ decisión ≠ edición.**

## Funcionalidad existente

- CLI;
- FFmpeg/ffprobe + probe;
- Cleaner determinista de silencios;
- Edit Plan + render;
- faster-whisper word-level + TXT/JSON/SRT;
- Silero VAD ONNX;
- Candidate Analysis review-only;
- gestión local de modelos;
- runtime portable core/ML validado;
- ingesta embebida/externa;
- auto-sync offset + confidence + anchors + drift;
- override manual;
- master audio FLAC + informe auditable.

`analyze` todavía toma el audio embebido del vídeo; se migrará al master audio en Fase 1C después del hardening restante de sync.

## Desarrollo

```powershell
python -m pip install -e .
python -m pip install -e ".[analysis]"
```

Builds:

```powershell
.\.github\scripts\build_portable_windows.ps1 -Profile core
.\.github\scripts\build_portable_windows.ps1 -Profile analysis
```

## Siguiente trabajo

1. endurecer 1B con E2E de offset negativo, drift, baja señal, manual override y cobertura;
2. validar comportamiento con fuentes acústicamente distintas;
3. adaptar `analyze` a master audio;
4. validar `large-v3-turbo` en vídeo hablado real en español;
5. entrar en Fase 2 semántica.

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
