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
- Fase 2C — Validación semántica real: 🟡 **benchmark + retake humano + correcciones humanas bilingües validadas; ampliar evidencia/audio real pendiente**
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

## Fase 2C — Semantic Validation — EN CURSO

El harness de `Source/video_tunner/semantic_validation.py` mide TP/FP/FN, precision/recall/F1 y seguridad de decisiones sin promover edits.

### Foundation

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

### Primer retake humano

AMI Meeting Corpus ES2012d añadido como positivo humano.

Run `33743638690`:

```text
65 tests PASS
22 casos / 12 eventos
FP 0 / FN 0
possible_retake → REVIEW
unsafe proposals 0
artifacts 0
```

### Correcciones humanas bilingües

Se añadió `tests/fixtures/semantic_human_corrections_v1.json` con un par positivo/negativo en cada idioma:

- AMI, inglés: `I mean` como reparación real vs. `I mean` discursivo;
- CORMA, español: `Perdón` tras fragmento abandonado vs. `perdón eh` como disculpa/inciso.

Baseline `33750475437`:

```text
69 tests PASS en 6.718 s
26 casos / 14 eventos
14 TP / 2 FP / 0 FN
precision 87.50%
recall 100%
F1 93.33%
unsafe proposals 0
executable 0
auto_apply 0
```

El gate falló sólo por precision. Los dos FP eran exactamente los usos humanos ambiguos de marcador.

Tuneo Conservador basado en esa evidencia:

- `I mean / quiero decir` requiere frontera explícita de reparación o sustitución numérica;
- `perdón / perdona / sorry` no se trata como correction candidate en patrones de disculpa/hesitación sin intento interrumpido;
- tras fragmento truncado sí permanece `explicit_correction → REVIEW`;
- modo Agresivo conserva detección más amplia.

Run final `33750836791` — **SUCCESS**:

```text
74 tests PASS en 6.729 s
26 casos
14 eventos esperados / 14 candidates
FP 0
FN 0
precision 100%
recall 100%
F1 100%
decision mismatches 0
unsafe proposals 0
missing safe proposals 0
executable decisions 0
auto_apply decisions 0
artifacts 0
```

`video-tunner doctor` y E2E FFmpeg/sync PASS.

Composición humana actual:

```text
4 human_speech_reference  # SpanishPod negativos ya acreditados con audio/Whisper
3 human_speech_positive   # AMI retake + AMI correction + CORMA correction
2 human_speech_negative   # AMI discourse + CORMA apology
```

**El 100% sólo corresponde al corpus etiquetado actual.** El harness semántico usa timings deterministas; aún no demuestra que Whisper preserve siempre las señales de truncamiento/puntuación de transcripts manuales.

Provenance: `Validation/phase2c-semantic-validation-sources.md`.

## Siguiente trabajo

1. ampliar humanos positivos/negativos, especialmente español;
2. validar cómo sobreviven las señales de reparación a audio real → `large-v3-turbo`;
3. resolver scope seguro `intento incorrecto → corrección válida`;
4. validar fillers contextuales;
5. añadir límites de frase y join safety;
6. mantener `executable=false` hasta evidencia suficiente;
7. sólo después considerar promotion al Edit Plan.

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
