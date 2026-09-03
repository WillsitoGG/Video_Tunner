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
- Fase 2D.3.2 — Acoustic join validation foundation v1: ✅
- Fase 2D.3.3 — Human-audio acoustic evidence v1: ✅
- Fase 2D.4 — Combined Eligibility / Promotion Policy Foundation: 🟡 **siguiente**
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
acoustic join assessments (master-audio waveform evidence)
  ↓
semantic decisions + protection
  ↓
future combined eligibility policy
  ↓
future approved Edit Plan
  ↓
render + audit
```

Invariantes:

```text
candidate != correction scope != filler assessment != join assessment != acoustic join assessment != semantic decision != edit
PROPOSED_CUT != executable CUT
bounded scope != safe cut
filler assessment != safe cut
join context != acoustically safe join
acoustic_context_only != semantic permission to cut
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

## Análisis

`analysis.json` actual usa **schema v7** y separa:

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
acoustic_join_assessments[]
semantic_decisions[]
```

Safety flags relevantes:

```text
semantic_decisions_executable = false
correction_scopes_safe_for_cut = false
filler_assessments_safe_for_cut = false
join_assessments_safe_for_cut = false
acoustic_join_assessments_are_not_edits = true
acoustic_join_assessments_executable = false
acoustic_join_assessments_safe_for_cut = false
join_acoustic_validation_enabled = true
join_acoustic_validation_is_not_cut_authorization = true
```

## Evidencia de Fase 2

```text
33659725847  Semantic Candidates PASS
33741195594  Semantic Decisions/Protection PASS
33750836791  Human correction corpus PASS
33755013415  3 casos AMI audio-backed semantic gate PASS
33758185755  88/88 — correction scope, schema v4
33771792867  101/101 — contextual fillers, schema v5
33773287106  117/117 — join context, schema v6
33781903986  131/131 — acoustic join, schema v7
33782959293  134/134 — human acoustic gate PASS
```

Todas las capas siguen sin producir edits automáticos.

## Fase 2D.3.2 — Acoustic Join Validation Foundation v1

La capa acústica usa el **mismo master audio acreditado** que Whisper/VAD.

```text
master audio
→ un único decode FFmpeg a PCM16 mono / 16 kHz temporal
→ NumPy memmap
→ ventanas locales de 80 ms por lado
→ RMS / edge RMS / peak / sample jump / jump ratio
```

Sólo se mide `join_context_only`; un join ya bloqueado por contexto permanece `blocked_by_context`.

Thresholds v1:

```text
silence                  -42.0 dBFS
max RMS delta             12.0 dB
max boundary sample jump   0.35
max boundary jump ratio    1.25
```

Detalle: `Validation/phase2d-acoustic-join.md`.

## Fase 2D.3.3 — Human-audio Acoustic Evidence v1

Run `33782959293` reutiliza endpoints reales de `large-v3-turbo` del run `33755013415` y mide el WAV AMI original CC BY 4.0, sin volver a ejecutar el modelo.

```text
134/134 tests PASS en 6.803 s
3 casos humanos
1 medición acústica real
2 bloqueos contextuales preservados
HUMAN_ACOUSTIC_GATE=PASS
artifacts 0
```

Control humano medido:

```text
status               acoustic_context_only
RMS delta            4.9369 dB
boundary sample jump 0.030243
boundary jump ratio  0.340433
safe_for_cut          false
```

Los casos de retake y correction ambigua permanecieron `blocked_by_context`, por lo que la acústica no puede rescatar un join previamente bloqueado.

No se modificaron thresholds v1. Una medición humana limpia no demuestra seguridad universal, calidad perceptual, continuidad prosódica ni ausencia general de click/pop.

Detalle: `Validation/phase2d-human-acoustic-evidence.md`.

## Siguiente trabajo — Fase 2D.4

Diseñar una **Combined Eligibility / Promotion Policy Foundation** todavía no ejecutable:

1. combinar guardas semánticas, correction scope, fillers, join context y acoustics;
2. exigir paso acumulativo de todas las capas;
3. cualquier ambigüedad/riesgo => REVIEW/bloqueo;
4. validar `removedText` definitivo contra span/transcript/timestamps;
5. crear benchmark con positivos/negativos y fallos deliberados;
6. mantener `safe_for_cut=false`, `executable=false`, `auto_apply=false`;
7. no promover nada al Edit Plan hasta cerrar 2D.

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
