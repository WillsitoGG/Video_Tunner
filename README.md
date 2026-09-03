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
- Fase 2C — Validación semántica real v1: ✅
- Fase 2D.1 — Correction scope foundation v1: ✅
- Fase 2D.2 — Fillers contextuales foundation v1: ✅
- Fase 2D.3.1 — Sentence/join context foundation v1: ✅
- Fase 2D.3.2 — Acoustic join validation foundation v1: ✅
- Fase 2D.3.3 — Human-audio acoustic evidence v1: ✅
- Fase 2D.4 — Combined Eligibility / Promotion Policy Foundation: ✅
- Fase 2D.5 — Human Combined Eligibility Evidence: ✅
- Fase 2D.6 — Human Positive Eligibility Expansion / Close-out Gate: 🟡 **siguiente**
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
candidates
  ↓
correction scopes + filler assessments
  ↓
join assessments
  ↓
acoustic join assessments
  ↓
semantic decisions + protection
  ↓
combined eligibility assessments
  ↓
future approved Edit Plan
  ↓
render + audit
```

Invariantes:

```text
candidate != scope != assessment != semantic decision != edit
PROPOSED_CUT != executable CUT
foundation_guards_pass != safe cut
future_promotion_candidate != approved edit
safe_for_cut = false
executable = false
auto_apply = false
automatic_edits = 0
```

## Portable / ML validado

- Core portable `33600174568`: PASS.
- ML frozen `33621357438`: PASS.
- Sync hardening `33639009841`: PASS.
- Target Spanish `33656235038`: WER `1.64%`, RTF `0.4854`, word timestamps PASS, automatic edits 0.

Modelo objetivo: **`large-v3-turbo`**.

## Análisis

`analysis.json` actual usa **schema v8**:

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
acoustic_join_assessments[]
semantic_decisions[]
eligibility_assessments[]
```

Safety v8:

```text
eligibility_assessments_are_not_edits = true
eligibility_assessments_executable = false
eligibility_assessments_safe_for_cut = false
future_promotion_candidates_are_not_approved_edits = true
combined_eligibility_enabled = true
combined_eligibility_is_not_edit_plan_promotion = true
```

## Evidencia principal de Fase 2

```text
33750836791  Human correction corpus PASS
33755013415  Audio-backed semantic gate PASS
33758185755  88/88 — correction scope/schema v4
33771792867  101/101 — contextual fillers/schema v5
33773287106  117/117 — join context/schema v6
33781903986  131/131 — acoustic join/schema v7
33782959293  134/134 — human acoustic gate PASS
33790792753  138/138 — combined eligibility/schema v8 PASS
33791950505  142/142 — human combined eligibility PASS
```

Todas mantienen automatic edits 0 y artifacts 0.

## Fase 2D.4 — Combined Eligibility Foundation v1

La policy combina guardas de forma acumulativa. Una señal posterior favorable nunca rescata una anterior.

Estados v1:

```text
foundation_guards_pass
blocked_acoustic_context
blocked_filler_context
blocked_semantic_decision
blocked_join_context
blocked_correction_scope
invalid_removed_text
missing_required_evidence
```

`foundation_guards_pass` sólo significa que las guardas implementadas han pasado:

```text
future_promotion_candidate = true
safe_for_cut = false
executable = false
auto_apply = false
```

La capa vuelve a validar `removedText`/target contra índices, transcript y timestamps. Corrections con scope `bounded` pueden usar el target definitivo `attempt + marker`.

Run `33790792753`: 138/138 PASS; schema v8 + eligibility gate + removedText contract PASS; artifacts 0.

Detalle: `Validation/phase2d-combined-eligibility.md`.

## Fase 2D.5 — Human Combined Eligibility Evidence

La policy v8 se ha aplicado a endpoints reales congelados de `large-v3-turbo` y al WAV AMI original, sin volver a ejecutar el modelo.

Baseline `33791636767`:

```text
141/141 regresiones PASS
human gate FAIL sólo por diagnóstico
```

La correction humana `I mean` tenía scope `ambiguous` y, correctamente, ningún target de join. La policy la etiquetó primero como `invalid_removed_text`; la seguridad permaneció intacta, pero la causa principal más informativa era `blocked_correction_scope`.

Se cambió únicamente la precedencia diagnóstica para corrections no acotadas. No se añadió ninguna ruta positiva ni se relajó ningún gate.

Final `33791950505`:

```text
142/142 tests PASS en 7.087 s
cases                   3
failures                0
foundation_guards_pass  1
blocked                  2
safe_for_cut             0
executable               0
auto_apply               0
automatic_edits          0
HUMAN_ELIGIBILITY_GATE   PASS
artifacts                0
```

Resultados humanos:

- pausa control → `foundation_guards_pass`, pero sigue `safe_for_cut=false`;
- retake real → `blocked_semantic_decision`;
- correction real con scope ambiguo → `blocked_correction_scope`, conservando `removed_text_reason=missing_target_span`.

La pausa es **control de plumbing/policy**, no una etiqueta que justifique borrarla automáticamente.

Detalle: `Validation/phase2d-human-combined-eligibility.md`.

## Siguiente trabajo — Fase 2D.6

Antes de 2E necesitamos positivos humanos etiquetados como **realmente descartables**, no sólo controles técnicos.

1. buscar/seleccionar varios positivos humanos trazables: pausas limpias, fillers aislados y repeticiones/retakes claramente descartables;
2. acompañarlos de negativos cercanos;
3. comprobar si atraviesan la policy actual sin relajarla;
4. validar `removedText`, timings y join real;
5. no fabricar positivos modificando thresholds;
6. mantener `safe_for_cut=false`, `executable=false`, `auto_apply=false`, `automatic_edits=0` durante toda 2D.6;
7. usar ese gate para decidir si 2D puede cerrarse o necesita más hardening.

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
