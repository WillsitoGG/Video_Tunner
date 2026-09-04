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
- Fase 2D.3 — Join + acoustic + evidencia humana: ✅
- Fase 2D.4 — Combined Eligibility / Promotion Policy Foundation: ✅
- Fase 2D.5 — Human Combined Eligibility Evidence: ✅
- Fase 2D.6 — Human Positive Eligibility Expansion / Close-out Gate: ✅
- **Fase 2D — cerrada como foundation/evidence**
- Fase 2E — Promotion to Edit Plan: 🟡 **siguiente**
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
33892213960  AMI exact-repeat discovery PASS — 80 compatibles
33894995584  Human Positive Close-out PASS — CLOSE_OUT_READY
```

Todas mantienen automatic edits 0 donde aplica y artifacts pesados 0.

## Fase 2D — Combined Eligibility cerrada como foundation/evidence

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

### 2D.5 — evidencia humana combinada

Run `33791950505`: 142/142 tests PASS; 3 casos humanos, 1 `foundation_guards_pass`, 2 bloqueados y cero capacidad ejecutable. Detalle: `Validation/phase2d-human-combined-eligibility.md`.

### 2D.6 — positivos humanos y close-out

Para evitar seleccionar ejemplos después de ver Whisper, se creó un discovery reproducible sobre anotaciones manuales AMI de `repeat/reparandum/reparans`, con tokenización equivalente a producción y headsets individuales por hablante.

Discovery `33892213960`:

```text
80 exact repeats compatibles
8 casos seleccionados
4 headsets
```

El gate de suficiencia se fijó antes del run final:

```text
casos long evaluados                 >= 8
positivos humanos alineados          >= 3
foundation_guards_pass humanos       >= 2
fuentes/headsets con foundation pass >= 2
```

Run final `33894995584`:

```text
155 tests OK; 11 host-PATH skips
HUMAN_POSITIVE_EVIDENCE_GATE      PASS
HUMAN_POSITIVE_CLOSE_OUT_DECISION CLOSE_OUT_READY
casos evaluados                    8
positivos alineados                6
foundation_guards_pass             3
fuentes con foundation pass        2
hard failures                      0
safe_for_cut                       0
executable                         0
auto_apply                         0
automatic_edits                    0
artifacts                           0
```

Diagnóstico:

- 2 casos: Whisper no conserva la repetición humana completa;
- 3 casos: repetición detectada/alineada y `foundation_guards_pass`;
- 3 casos: repetición detectada/alineada pero `blocked_join_context`;
- 0 detector misses sobre una repetición completa preservada por ASR en **esta muestra**.

No se relajó ningún threshold o guarda. La conclusión no debe generalizarse fuera de la muestra.

Detalle: `Validation/phase2d-human-positive-closeout.md`.

## Siguiente trabajo — Fase 2E

**2E no significa activar cortes.** Su objetivo es diseñar y validar el contrato explícito de promoción al Edit Plan.

1. definir qué clases pueden siquiera optar a promoción;
2. conservar blockers de 2D como vetos acumulativos;
3. definir approval/thresholds por modo y límites globales;
4. mantener el resto en REVIEW/KEEP;
5. convertir eligibility → Edit Plan sólo mediante un contrato auditable;
6. validar primero sin habilitar ejecución automática;
7. usar evidencia humana antes de cualquier promoción productiva.

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
