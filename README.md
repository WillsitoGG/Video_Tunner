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
- Fase 2D — Scope + fillers + join + combined eligibility: ✅ **cerrada como foundation/evidence**
- Fase 2E.1 — Promotion Policy Foundation: ✅
- Fase 2E.2 — Explicit Approval Contract: ✅
- Fase 2E.3 — Approved Edit Plan Proposal + Global Limits: ✅
- Fase 2E — Promotion to Edit Plan: 🟡 **en curso**
- Fase 2E.4 — Execution Authorization / Semantic Render Gate: 🟡 **siguiente**
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
candidates → scopes/fillers → join → acoustic join → semantic decisions
  ↓
eligibility assessments
  ↓
promotion assessments
  ↓
explicit approval artifacts
  ↓
approved_edit_plan_proposal
  ↓
future global execution authorization
  ↓
future executable Edit Plan → render → audit
```

Invariantes:

```text
candidate != assessment != promotion assessment != approval != proposal != executable edit
PROPOSED_CUT != executable CUT
foundation_guards_pass != safe cut
promotion_review_candidate != approval
valid_approved approval != Edit Plan authorization
proposal_ready_for_global_review != render authorization
proposed_edits[] != edits[]
render_authorization = false          # Phase 2E.3
globally_approved = false             # Phase 2E.3
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

## Analysis + approval + proposal artifacts

`analysis.json` sigue usando **schema v9**.

2E.2 añade un artefacto separado:

```text
promotion_approval.json
schema_version = 1
record_type = promotion_approval
```

2E.3 añade otro artefacto separado:

```text
approved_edit_plan_proposal.json
schema_version = 1
record_type = approved_edit_plan_proposal
```

Una proposal lista usa `proposed_edits[]`, deliberadamente **no** `edits[]`. El renderer rechaza explícitamente cualquier artefacto que contenga `proposed_edits`.

## Evidencia principal de Fase 2

```text
33790792753  Combined eligibility/schema v8 PASS — 138/138
33791950505  Human combined eligibility PASS — 142/142
33894995584  Human Positive Close-out PASS — CLOSE_OUT_READY
33899201093  2E.1 integrated schema v9 PASS — 166/166 + doctor
33899857378  2E.2 approval contract PASS — 174/174 + doctor
33900544072  2E.3 proposal foundation PASS — 185/185 + doctor
33908500929  2E.3 final renderer isolation PASS — 186/186 + doctor
```

## Fase 2E.1 — Promotion Policy Foundation

Sólo `possible_repetition`, respaldada por evidencia humana positiva de 2D.6, puede llegar a `eligible_for_promotion_review`. Sigue sin ser edit ni aprobación. Detalle: `Validation/phase2e-promotion-foundation.md`.

## Fase 2E.2 — Explicit Approval Contract

La aprobación es una decisión humana explícita y auditable sobre una promotion assessment concreta. Se liga al SHA-256 del analysis exacto y a un fingerprint canónico de la evidencia. Un `valid_approved` sigue teniendo `edit_plan_authorization=false`, `edit=null`, `executable=false` y `auto_apply=false`.

CLI:

```text
video-tunner approval create ANALYSIS --promotion-assessment ID --decision approve|reject --actor ACTOR --reason REASON --output promotion_approval.json
video-tunner approval validate ANALYSIS promotion_approval.json
```

Detalle: `Validation/phase2e-explicit-approval-contract.md`.

## Fase 2E.3 — Approved Edit Plan Proposal + Global Limits

2E.3 transforma exclusivamente approvals que siguen validando como `valid_approved` en una **propuesta globalmente acotada y no ejecutable**.

CLI:

```text
video-tunner proposal build ANALYSIS \
  --approval promotion_approval_1.json \
  --approval promotion_approval_2.json \
  --output approved_edit_plan_proposal.json
```

### Envelope de seguridad precomprometido

Los límites se fijaron antes de observar resultados y son iguales en `conservative` y `aggressive`:

```text
max_semantic_edits    = 10
max_removed_seconds   = 30.0
max_removed_fraction  = 0.05
```

Sólo `possible_repetition` está soportada inicialmente.

La proposal completa queda bloqueada si aparece cualquiera de estos casos:

- approval stale, rejected o invalid;
- approval/target duplicado;
- candidate kind no soportado;
- target ausente o fuera de la timeline fuente;
- targets aprobados solapados;
- más de 10 semantic edits;
- más de 30 segundos retirados;
- más del 5% de duración retirado;
- ausencia de approvals válidos.

Una proposal válida queda:

```text
status = proposal_ready_for_global_review
requires_global_review = true
globally_approved = false
render_authorization = false
executable = false
auto_apply = false
```

Cada elemento de `proposed_edits[]` también mantiene `globally_approved=false`, `render_authorized=false`, `executable=false` y `auto_apply=false`.

### Aislamiento del renderer

2E.3 no confía sólo en la diferencia estructural `proposed_edits[] != edits[]`: `render_from_plan` rechaza explícitamente cualquier proposal para evitar que pueda pasar accidentalmente por el renderer como Edit Plan.

### Validación

Run inicial `33900544072`:

```text
185/185 tests PASS en 5.144 s
doctor PASS
límites independientes PASS
overlap/duplicate/stale/rejected/timeline blockers PASS
valid proposal remains review-only PASS
```

Hardening final `33908500929`:

```text
186/186 tests PASS en 7.887 s
doctor PASS
renderer rejects non-executable proposal PASS
```

Workflow final: `workflow_dispatch` manual-only. No se habilitó render semántico ni auto-apply.

Detalle: `Validation/phase2e-approved-plan-proposal.md`.

## Siguiente trabajo — Fase 2E.4

Definir el **contrato de autorización global de ejecución** sin mezclarlo con las approvals individuales:

1. validar que la proposal sigue vigente frente al `analysis.json` exacto;
2. ligar la autorización a SHA/fingerprint exactos de proposal + analysis;
3. exigir revisión global explícita y actor/motivo auditables;
4. invalidar automáticamente autorización stale o manipulada;
5. materializar un Edit Plan ejecutable sólo desde una autorización global válida;
6. mantener el renderer cerrado a proposals no autorizadas;
7. definir semantic render gate y post-render verification antes de auto-apply general.

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
