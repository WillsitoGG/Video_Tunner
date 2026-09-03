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
- Fase 1C — Transcripción/VAD sobre master audio + `large-v3-turbo` español real: ✅
- Fase 2A — Semantic Candidates v1: ✅
- Fase 2B — Semantic Decisions + Protection v1: ✅
- Fase 2C — Validación semántica real: 🟡 **benchmark foundation v1 completada; positivos humanos espontáneos pendientes**
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

## Fase 1C — análisis sobre master audio — COMPLETADA

`analyze` ya no asume que debe leer el audio embebido del MP4.

Puede:

```powershell
video-tunner analyze "video.mp4" --model large-v3-turbo --language es --output-dir Output
video-tunner analyze "video.mp4" --audio "micro.wav" --model large-v3-turbo --language es --output-dir Output
video-tunner analyze "video.mp4" --audio "micro.wav" --offset 1.25 --model large-v3-turbo --language es --output-dir Output
video-tunner analyze "video.mp4" --master-audio "video_master_audio.flac" --ingest-report "video_ingest.json" --model large-v3-turbo --language es --output-dir Output
```

Reglas:

- Whisper y Silero VAD reciben **exactamente el mismo master**;
- el master cubre la timeline completa del vídeo;
- todos los timestamps están en tiempo de vídeo;
- un master pre-resuelto exige su `ingest.json`;
- se verifica SHA-256 del vídeo fuente;
- `review_required` detiene Whisper/VAD;
- `analysis.json` actual usa schema v3;
- candidates nunca son edits.

Target Spanish run `33656235038`: WER `1.64%`, RTF `0.4854`, word timestamps PASS, automatic edits `0`, artifacts `0`.

## Fase 2A — Semantic Candidates v1 — COMPLETADA

Clases iniciales:

```text
possible_repetition
possible_retake
explicit_correction
```

Cada candidato registra `removed_text`, contexto, word indices/timestamps, evidence y confidence, y permanece:

```text
suggested_decision = REVIEW
decision = undecided
auto_apply = false
span_safe_for_auto_apply = false
```

Run `33659725847`: 48 tests PASS, artifacts `0`.

## Fase 2B — Semantic Decisions + Protection v1 — COMPLETADA

```text
candidate
   ↓
semantic decision + protection
   ↓
KEEP / REVIEW / PROPOSED_TRIM / PROPOSED_CUT
```

Contrato:

```text
candidate != semantic decision != edit
PROPOSED_CUT != executable CUT
executable = false
auto_apply = false
```

Guardas v1: integridad de span, cifras/importes/porcentajes/unidades, negaciones, persona/sujeto, tiempo/aspecto, causalidad/contraste y señal heurística de entidades.

Run `33741195594`: 55 tests PASS, `doctor` PASS, artifacts `0`, automatic edits `0`.

## Fase 2C — Semantic Validation Foundation v1 — COMPLETADA COMO BASE

Se añade un benchmark etiquetado y reproducible que mide detección y seguridad por separado:

```text
Source/video_tunner/semantic_validation.py
tests/fixtures/semantic_corpus_v1.json
tests/test_semantic_validation.py
```

Corpus final:

```text
21 casos
11 positivos construidos
6 negativos construidos
4 controles derivados de habla humana real ya validada
11 eventos esperados
```

Baseline run `33742519997`:

```text
60 tests PASS
FP = 2
FN = 0
precision = 84.62%
recall = 100%
F1 = 91.67%
unsafe proposals = 0
```

Los dos FP eran reutilización legítima de opener y `quiero decir` literal. Se tunearon únicamente esas dos fuentes de ruido en modo Conservador.

Validación final run `33743029443`:

```text
64 tests PASS en 6.588 s
FP = 0
FN = 0
precision = 100%
recall = 100%
F1 = 100%
unsafe proposals = 0
executable decisions = 0
auto_apply decisions = 0
artifacts = 0
```

Los cuatro controles humanos reutilizan contenido SpanishPod ya validado con audio + `large-v3-turbo` en `33656235038`, evitando repetir una CI ML pesada sin necesidad.

**Limitación:** el 100% corresponde únicamente a este corpus v1. Todavía faltan positivos humanos espontáneos con retomas/autocorrecciones reales; por tanto Fase 2C completa sigue EN CURSO y no se habilita ningún edit semántico automático.

Ver `Validation/phase2c-semantic-validation.md`.

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
acoustic + semantic candidates auditables
  ↓
semantic decisions + protection
  ↓
future approved Edit Plan
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

## Siguiente trabajo dentro de Fase 2C

1. incorporar positivos humanos reales con retomas, reinicios y autocorrecciones;
2. medirlos con el mismo harness sin relajar thresholds para esconder fallos;
3. resolver scope seguro `intento incorrecto → corrección válida`;
4. validar fillers contextuales;
5. añadir límites de frase y join safety;
6. mantener todas las semantic decisions no ejecutables hasta demostrar qué clases pueden promoverse con seguridad.

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
