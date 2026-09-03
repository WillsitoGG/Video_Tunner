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
- Fase 2D.1 — Correction scope foundation v1: ✅
- Fase 2D.2 — Fillers contextuales foundation v1: ✅
- Fase 2D.3.1 — Sentence/join context foundation v1: ✅
- Fase 2D.3.2 — Acoustic join validation: 🟡 **siguiente**
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
correction scope evidence + filler assessments
  ↓
join assessments (timeline/lexical/boundary evidence)
  ↓
semantic decisions + protection
  ↓
future approved Edit Plan
  ↓
render + audit
```

Invariantes:

```text
candidate != correction scope != filler assessment != join assessment != semantic decision != edit
PROPOSED_CUT != executable CUT
bounded scope != safe cut
filler assessment != safe cut
join context != acoustically safe join
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

`analysis.json` actual usa **schema v6** y separa:

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
semantic_decisions[]
```

Safety flags relevantes:

```text
semantic_protection_enabled = true
semantic_decisions_are_not_edits = true
semantic_decisions_executable = false
correction_scopes_are_not_edits = true
correction_scopes_executable = false
correction_scopes_safe_for_cut = false
filler_assessments_are_not_edits = true
filler_assessments_executable = false
filler_assessments_safe_for_cut = false
join_assessments_are_not_edits = true
join_assessments_executable = false
join_assessments_safe_for_cut = false
join_acoustic_validation_enabled = false
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

Tras tuneo guiado por FP medidos, run `33743029443`:

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

Run final `33750836791`: 74 tests PASS; corpus gate PASS; artifacts 0.

El **100% sólo acredita ese corpus etiquetado**; no debe generalizarse a habla arbitraria.

### 2C.3 — Audio humano real → `large-v3-turbo` → semántica

Run final pesado `33755013415`:

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

Hallazgos: Whisper puede omitir vacilaciones, fabricar una repetición textual exacta y eliminar truncamientos alrededor de autocorrecciones. Timing anómalamente comprimido => `REVIEW`.

Evidencia: `Validation/phase2c-audio-backed-validation.md`.

## Fase 2D.1 — Correction Scope Foundation v1

`bounded` significa que existe un boundary local determinista suficiente para describir un `attempt_span`; **no** significa que el span sea seguro de cortar.

Run final `33758185755`: 88/88 PASS; schema v4; E2E FFmpeg/sync + doctor PASS; artifacts 0.

Evidencia: `Validation/phase2d-correction-scope.md`.

## Fase 2D.2 — Fillers Contextuales Foundation v1

`possible_filler` y la valoración contextual quedan separados. Estados v1:

```text
isolated_hesitation
hesitation_cluster
protected_repair_context
boundary_hesitation
uncertain_asr
invalid
```

Incluso `isolated_hesitation` continúa `safe_for_cut=false`.

Runs:

```text
33771489008  101/101 PASS en 7.030 s — benchmark/context foundation
33771792867  101/101 PASS en 5.031 s — schema v5 + pipeline integration
```

Limitación: el audio real de 2C.3 demostró que Whisper puede omitir un filler; esta capa no inventa tokens ausentes del transcript.

Evidencia: `Validation/phase2d-contextual-fillers.md`.

## Fase 2D.3.1 — Sentence/Join Context Foundation v1

Nueva capa no ejecutable:

```text
candidate / bounded correction scope / filler assessment
→ join assessment
→ future acoustic join validation
```

Estados v1:

```text
join_context_only
sentence_boundary_risk
segment_boundary_risk
critical_lexical_context_risk
repair_or_protected_context_risk
transcript_edge
invalid_or_unbounded_target
```

El join assessment:

- valida el target span antes de evaluarlo;
- registra contexto bilateral y gaps temporales;
- protege fronteras de frase/segmento;
- protege cifras, unidades, negación, persona, tiempo y causalidad;
- trata retakes/corrections y fillers protegidos como riesgo;
- deja scopes ambiguos y spans corruptos sin target ejecutable;
- **no** evalúa todavía continuidad de waveform.

Benchmark `tests/fixtures/join_safety_v1.json`: 15 casos, incluido el retake humano AMI.

Runs:

```text
33772715214  112/112 PASS en 6.670 s — foundation
33773287106  117/117 PASS en 6.891 s — benchmark + schema v6 integration
```

E2E FFmpeg/sync y doctor PASS; artifacts 0.

Evidencia: `Validation/phase2d-join-safety.md`.

## Siguiente trabajo — Fase 2D.3.2 Acoustic Join Validation

1. medir sobre **master audio** los dos bordes reales de un join hipotético;
2. detectar discontinuidades de nivel/waveform y contexto acústico insuficiente;
3. construir fixtures sintéticos positivos/negativos y, cuando aporte evidencia nueva, audio humano real;
4. mantener separada la evidencia acústica de la semántica/timeline;
5. no convertir un join acústicamente limpio en permiso semántico de corte;
6. mantener `safe_for_cut=false`, `executable=false`, `auto_apply=false` hasta superar todo 2D.

## Principios

- portable por diseño;
- local-first;
- originales intactos;
- sync fiable antes de IA temporal;
- conservador por defecto;
- ante duda: KEEP/REVIEW;
- GitHub como source of truth;
- CI deliberada y sin artifacts pesados ordinarios.

Consulta `AGENTS.md`, `ROADMAP.md`, `RELEASE_STATUS.md`, `UPSTREAM_SOURCES.md` y `Validation/`.
