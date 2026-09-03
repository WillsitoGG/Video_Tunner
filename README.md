# Video_Tunner

**Video_Tunner** es una aplicación portable para Windows 10/11 x64 orientada a la limpieza automática, inteligente, auditable y reversible de vídeo hablado.

Acepta vídeo con audio embebido o vídeo + audio externo. Antes de transcripción, VAD o decisiones temporales debe existir un **master audio** correctamente asociado a la timeline del vídeo. Los originales nunca se sobrescriben.

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
- Fase 1C — Transcripción/VAD sobre master + `large-v3-turbo` español real: ✅
- Fase 2A — Semantic Candidates v1: ✅
- Fase 2B — Semantic Decisions + Protection v1: ✅
- Fase 2C.1 — Benchmark semántico: ✅
- Fase 2C.2 — Positivos/negativos humanos bilingües: ✅
- Fase 2C.3 — Audio humano real → `large-v3-turbo` → semantic gate: ✅
- Fase 2D — Correction scope + fillers contextuales + join safety: 🟡 **siguiente bloque**
- Release pública: ninguna

Video_Tunner es producto/repo propio, no un fork.

## Arquitectura

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

Invariantes:

```text
candidate != semantic decision != edit
PROPOSED_CUT != executable CUT
executable = false
auto_apply = false
automatic_edits = 0
```

## Portable / ML validado

- Core portable `33600174568`: PASS; PyInstaller onedir + FFmpeg/ffprobe bundled; artifacts 0.
- ML frozen `33621357438`: PASS; faster-whisper/CTranslate2/ONNX/Silero local/offline; artifacts 0.
- Sync hardening `33639009841`: PASS; offset +/-, drift, confidence, fallback/manual, coverage.
- Master analysis `33640872486`: PASS; Whisper y VAD usan el mismo master.
- Target Spanish `33656235038`: PASS; WER `1.64%`, RTF `0.4854`, word timestamps PASS, automatic edits 0.

Modelo objetivo: **`large-v3-turbo`**. `tiny` se reserva para fixtures baratos.

## Ingesta / sincronización

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

Auto-sync: log-RMS → ZNCC coarse → anchors → offset/drift → residual/confidence/coverage. Evidencia insuficiente => `review_required`, sin master.

Outputs:

```text
<video>_master_audio.flac
<video>_ingest.json
```

## Análisis

```powershell
video-tunner analyze "video.mp4" --model large-v3-turbo --language es --output-dir Output
video-tunner analyze "video.mp4" --audio "micro.wav" --model large-v3-turbo --language es --output-dir Output
video-tunner analyze "video.mp4" --master-audio "video_master_audio.flac" --ingest-report "video_ingest.json" --model large-v3-turbo --language es --output-dir Output
```

`analysis.json` actual usa schema v3 y separa:

```text
candidates[]
semantic_decisions[]
```

Safety flags:

```text
semantic_protection_enabled = true
semantic_decisions_are_not_edits = true
semantic_decisions_executable = false
```

## Fase 2A — Semantic Candidates v1

Clases:

```text
possible_repetition
possible_retake
explicit_correction
```

Todo candidate sigue siendo review-only y registra span, `removed_text`, contexto, timestamps/evidence y confidence.

Run `33659725847`: 48 tests PASS, artifacts 0.

## Fase 2B — Semantic Decisions + Protection v1

Decisiones posibles:

```text
KEEP
REVIEW
PROPOSED_TRIM
PROPOSED_CUT
```

Guardas: span integrity, cifras/importes/porcentajes/unidades, negaciones, persona/sujeto, tiempo/aspecto, causalidad/contraste y señal heurística de entidades.

Run `33741195594`: 55 tests PASS, doctor PASS, artifacts 0.

## Fase 2C — Semantic Validation

El harness de `Source/video_tunner/semantic_validation.py` mide TP/FP/FN, precision/recall/F1 y seguridad de decisiones sin promover edits.

### 2C.1 — Foundation

Baseline `33742519997`:

```text
60 tests PASS
FP 2 / FN 0
precision 84.62%
recall 100%
F1 91.67%
unsafe proposals 0
```

Tras tuneo guiado por esos FP, `33743029443`:

```text
64 tests PASS
21 casos / 11 eventos
FP 0 / FN 0
precision = recall = F1 = 100% en ese corpus
unsafe proposals 0
executable 0
auto_apply 0
artifacts 0
```

### 2C.2 — Evidencia humana bilingüe

AMI y CORMA aportan positivos/negativos humanos para retakes, autocorrecciones y usos ambiguos de `I mean` / `perdón`.

Run final `33750836791`:

```text
74 tests PASS en 6.729 s
26 casos / 14 eventos
FP 0 / FN 0
precision = recall = F1 = 100% en el corpus etiquetado actual
unsafe proposals 0
decision mismatches 0
missing safe proposals 0
executable 0
auto_apply 0
artifacts 0
```

El **100% sólo acredita ese corpus etiquetado**; no debe generalizarse a habla arbitraria.

### 2C.3 — Audio humano real → `large-v3-turbo` → semántica

Se validó audio real de AMI ES2012d mediante el **portable frozen**, modelo fijado `large-v3-turbo`, word timestamps reales, candidate generation y semantic decisions.

Validación ligera previa `33754755238`:

```text
76/76 tests PASS en 5.561 s
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

Baseline audio real válido detectó dos efectos ASR que no aparecen en transcripts manuales:

1. Whisper puede omitir una vacilación y convertir un retake en una repetición textual exacta.
2. Whisper puede eliminar el guion/truncamiento alrededor de `I mean`, conservando sólo una reformulación contextual.

Hardening guiado por esa evidencia:

- repetición exacta con timing anómalamente comprimido => fail-safe `REVIEW`;
- `I mean / quiero decir` puede usar `question_reframe_cue` como evidencia conservadora cuando la señal de truncamiento desaparece;
- un `I mean` discursivo sigue sin convertirse en `explicit_correction`.

Run final pesado `33755013415` — **SUCCESS**:

```text
3 casos de audio humano real
0 failures
53.810 s de análisis total
automatic_edits 0
executable decisions 0
auto_apply decisions 0
artifacts 0
SEMANTIC_AUDIO_GATE=PASS
```

Resultados:

```text
retake real      → possible_repetition → REVIEW
I mean correction → explicit_correction → REVIEW
I mean discourse  → 0 explicit_correction
```

En el retake real, la primera repetición quedó en `0.112 s/token`, por debajo del umbral conservador `0.120 s/token`, por lo que no llega a `PROPOSED_CUT`.

AMI se descarga sólo a `RUNNER_TEMP`; audio/modelo/outputs no se suben como artifacts. Evidencia detallada: `Validation/phase2c-audio-backed-validation.md`.

## Siguiente trabajo — Fase 2D

1. definir y medir **correction scope**: qué span anterior corresponde realmente al intento incorrecto;
2. mantener marker-only si el scope no puede demostrarse con seguridad;
3. distinguir fillers contextuales eliminables de discurso natural/semántico;
4. añadir límites de frase y join safety;
5. mantener `executable=false` y `auto_apply=false` durante 2D;
6. sólo después considerar promoción al Edit Plan.

## Principios

- portable por diseño;
- local-first;
- originales intactos;
- sync fiable antes de IA temporal;
- Conservador por defecto;
- ante duda: KEEP/REVIEW;
- GitHub como source of truth;
- CI deliberada y sin artifacts pesados ordinarios.

Consulta `AGENTS.md`, `ROADMAP.md`, `RELEASE_STATUS.md`, `UPSTREAM_SOURCES.md` y `Validation/`.
