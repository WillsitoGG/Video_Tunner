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
- Fase 2D.3.3 — Audio humano real para join acoustics: 🟡 **siguiente**
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

## Análisis

```powershell
video-tunner analyze "video.mp4" --model large-v3-turbo --language es --output-dir Output
video-tunner analyze "video.mp4" --audio "micro.wav" --model large-v3-turbo --language es --output-dir Output
video-tunner analyze "video.mp4" --master-audio "video_master_audio.flac" --ingest-report "video_ingest.json" --model large-v3-turbo --language es --output-dir Output
```

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

## Fase 2A — Semantic Candidates v1

Clases: `possible_repetition`, `possible_retake`, `explicit_correction`. Todo candidate sigue review-only.

Run `33659725847`: 48 tests PASS, artifacts 0.

## Fase 2B — Semantic Decisions + Protection v1

Decisiones: `KEEP / REVIEW / PROPOSED_TRIM / PROPOSED_CUT`. Todas son no ejecutables.

Run `33741195594`: 55 tests PASS, doctor PASS, artifacts 0.

## Fase 2C — Semantic Validation

- 2C.1 `33743029443`: benchmark foundation PASS.
- 2C.2 `33750836791`: 74 tests PASS; corpus humano bilingüe etiquetado.
- 2C.3 `33755013415`: 3 casos de audio humano real → `large-v3-turbo` → semantic gate PASS; artifacts 0.

No generalizar métricas de corpus a habla arbitraria.

## Fase 2D.1 — Correction Scope Foundation v1

`bounded` describe un boundary local determinista; **no** significa cut seguro.

Final `33758185755`: 88/88 PASS; schema v4; E2E FFmpeg/sync + doctor PASS; artifacts 0.

Evidencia: `Validation/phase2d-correction-scope.md`.

## Fase 2D.2 — Fillers Contextuales Foundation v1

Separa `possible_filler` de su evaluación contextual. Incluso `isolated_hesitation` permanece `safe_for_cut=false`.

Final `33771792867`: 101/101 PASS; schema v5; artifacts 0.

Evidencia: `Validation/phase2d-contextual-fillers.md`.

## Fase 2D.3.1 — Sentence/Join Context Foundation v1

`join_assessments[]` valida target, contexto bilateral, boundaries, reparaciones y tokens críticos antes de cualquier consideración acústica.

Final `33773287106`: 117/117 PASS; schema v6; artifacts 0.

Evidencia: `Validation/phase2d-join-safety.md`.

## Fase 2D.3.2 — Acoustic Join Validation Foundation v1

La capa acústica usa el **mismo master audio acreditado** que Whisper/VAD.

Implementación:

```text
master audio
→ un único decode FFmpeg a PCM16 mono / 16 kHz temporal
→ NumPy memmap
→ ventanas locales de 80 ms por lado
→ métricas acústicas auditables
```

Sólo se mide `join_context_only`; un join ya bloqueado por contexto permanece `blocked_by_context`.

Estados:

```text
blocked_by_context
insufficient_audio_context
low_energy_boundary_context
level_discontinuity_risk
waveform_discontinuity_risk
combined_discontinuity_risk
acoustic_context_only
```

Thresholds v1:

```text
silence                  -42.0 dBFS
max RMS delta             12.0 dB
max boundary sample jump   0.35
max boundary jump ratio    1.25
```

Benchmark: 11 casos reproducibles. Además hay tests que pasan por decode real FFmpeg/PCM.

Runs:

```text
33781430382  131/131 PASS en 6.998 s — acoustic foundation
33781903986  131/131 PASS en 7.401 s — schema v7 + pipeline integration
```

Ambos: benchmark gate PASS; FFmpeg/sync + doctor PASS; artifacts 0.

La foundation **no** demuestra todavía calidad perceptual universal, continuidad espectral/prosódica, zero-cross optimization, crossfades ni ausencia universal de click/pop.

Evidencia: `Validation/phase2d-acoustic-join.md`.

## Siguiente trabajo — Fase 2D.3.3

Antes de cerrar 2D y plantear promoción:

1. ejecutar `acoustic_join_assessments` sobre joins derivados de audio humano real trazable;
2. medir cómo se comportan los thresholds v1 fuera de señales construidas;
3. ajustar sólo si aparece evidencia real de FP/FN;
4. mantener `safe_for_cut=false`, `executable=false`, `auto_apply=false`;
5. después definir la política combinada de promoción y `removedText` definitivo.

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
