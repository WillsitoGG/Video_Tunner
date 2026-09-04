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
- Fase 1C — Transcripción/VAD + español real: ✅
- Fase 2A — Semantic Candidates: ✅
- Fase 2B — Semantic Decisions + Protection: ✅
- Fase 2C — Validación semántica real: ✅
- Fase 2D — Scope + fillers + join + eligibility: ✅ **cerrada como foundation/evidence**
- Fase 2E.1 — Promotion Policy Foundation: ✅
- Fase 2E.2 — Explicit Approval Contract: ✅
- Fase 2E.3 — Approved Edit Plan Proposal + Global Limits: ✅
- Fase 2E.4 — Execution Authorization / Semantic Render Gate: ✅
- Fase 2E — Promotion to Edit Plan: 🟡 **en curso**
- Fase 2E.5 — Semantic Render Verification / Close-out: 🟡 **siguiente**
- Release pública: ninguna

Video_Tunner es producto/repo propio, no un fork.

## Arquitectura actual

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
promotion_approval.json
  ↓
approved_edit_plan_proposal.json
  ↓
semantic_execution_authorization.json
  ↓
semantic_edit_plan.json
  ↓
semantic render gate
  ↓
FFmpeg render
  ↓
future post-render verification/audit
```

Invariantes:

```text
candidate != assessment != promotion != approval != proposal != authorization != semantic plan != rendered output
PROPOSED_CUT != executable CUT
foundation_guards_pass != safe cut
promotion_review_candidate != approval
valid_approved promotion approval != global execution authorization
proposal_ready_for_global_review != render authorization
proposed_edits[] != edits[]
global APPROVE != auto_apply
semantic_edit_plan requires semantic render gate
auto_apply = false
```

## Portable / ML validado

- Core portable `33600174568`: PASS.
- ML frozen `33621357438`: PASS.
- Sync hardening `33639009841`: PASS.
- Target Spanish `33656235038`: WER `1.64%`, RTF `0.4854`, word timestamps PASS, automatic edits 0.

Modelo objetivo: **`large-v3-turbo`**.

## Artifacts actuales

### Analysis

```text
analysis.json
schema_version = 9
```

Incluye `promotion_assessments[]` además de candidates/scopes/fillers/join/acoustic/semantic/eligibility.

### Approval individual

```text
promotion_approval.json
schema_version = 1
record_type = promotion_approval
```

### Proposal global acotada

```text
approved_edit_plan_proposal.json
schema_version = 1
record_type = approved_edit_plan_proposal
proposed_edits[]
```

Límites precomprometidos, iguales en ambos modos:

```text
max_semantic_edits    = 10
max_removed_seconds   = 30.0
max_removed_fraction  = 0.05
```

### Global execution authorization

```text
semantic_execution_authorization.json
schema_version = 1
record_type = semantic_execution_authorization
```

Liga la decisión global a SHA-256 exactos de analysis/proposal + fingerprint canónico de la proposal + actor/reason/timestamp.

Un APPROVE válido permite únicamente la cadena controlada:

```text
authorized = true
edit_plan_materialization_authorized = true
semantic_render_authorization = true
proposal_render_authorization = false
executable = false
auto_apply = false
```

### Semantic Edit Plan

```text
semantic_edit_plan.json
schema_version = 1
record_type = semantic_edit_plan
edits[]
```

Se materializa sólo si la autorización global sigue siendo `valid_authorized`. Conserva SHA-256 de analysis/proposal/authorization, fingerprint del plan y provenance de cada edit.

```text
globally_authorized = true
requires_semantic_render_gate = true
executable = true
auto_apply = false
```

## Semantic render gate

El comando genérico `render` **rechaza** tanto proposals como Semantic Edit Plans. La única vía semántica ejecutable es `execution render`, que justo antes de FFmpeg revalida:

1. analysis actual;
2. proposal actual;
3. global authorization actual;
4. SHA-256 de authorization ligado al plan;
5. plan fingerprint + edits exactos;
6. SHA-256 real del vídeo fuente frente a analysis/proposal/plan.

Si cualquier elemento es stale, manipulado o distinto, el render se bloquea.

CLI:

```text
video-tunner execution authorize ANALYSIS PROPOSAL --decision approve|reject --actor ACTOR --reason REASON --output semantic_execution_authorization.json
video-tunner execution validate ANALYSIS PROPOSAL AUTHORIZATION
video-tunner execution materialize ANALYSIS PROPOSAL AUTHORIZATION --output semantic_edit_plan.json
video-tunner execution plan-validate ANALYSIS PROPOSAL AUTHORIZATION PLAN
video-tunner execution render-check INPUT ANALYSIS PROPOSAL AUTHORIZATION PLAN
video-tunner execution render INPUT ANALYSIS PROPOSAL AUTHORIZATION PLAN OUTPUT
```

## Evidencia principal de Fase 2E

```text
33894995584  Human Positive Close-out — CLOSE_OUT_READY
33899201093  2E.1 schema v9 — 166/166 PASS + doctor
33899857378  2E.2 approval contract — 174/174 PASS + doctor
33900544072  2E.3 proposal foundation — 185/185 PASS + doctor
33908500929  2E.3 renderer isolation — 186/186 PASS + doctor
33909424933  2E.4 authorization/render-gate core — 201/201 PASS + doctor
33909625346  2E.4 real FFmpeg semantic render E2E — 202/202 PASS + doctor
```

### E2E real 2E.4

`33909625346` crea un MP4 real de 10 s con vídeo+audio y recorre:

```text
analysis
→ promotion approval
→ bounded proposal
→ global execution approval
→ semantic Edit Plan
→ semantic render gate
→ FFmpeg
```

El test final:

- materializa exactamente un edit de `0.4 s`;
- renderiza únicamente ese tramo autorizado;
- confirma que el SHA-256 del original no cambia;
- confirma duración de salida esperada con tolerancia `±0.15 s`;
- conserva 1 stream de vídeo + 1 de audio;
- mantiene `auto_apply=false`.

Esta evidencia valida la ruta técnica/gobernanza; **no** demuestra todavía calidad perceptual humana general de los joins renderizados.

Detalle: `Validation/phase2e-execution-authorization.md`.

## Siguiente trabajo — Fase 2E.5

**Semantic Render Verification / Close-out**:

1. post-render structural verification;
2. expected vs actual duration accounting;
3. comprobar streams y output provenance;
4. audit local alrededor de cada join renderizado;
5. evidencia perceptual/humana sobre joins semánticos reales;
6. informe completo analysis → approvals → proposal → authorization → plan → output;
7. decisión explícita de cierre de Fase 2E antes de pasar a capas audiovisuales posteriores.

## Principios

- portable por diseño;
- local-first;
- originales intactos;
- sync fiable antes de IA temporal;
- conservador por defecto;
- ante duda: KEEP/REVIEW;
- GitHub como source of truth;
- CI deliberada y sin artifacts pesados ordinarios;
- no GitHub Release sin autorización expresa de Guille.

Consulta `AGENTS.md`, `ROADMAP.md`, `RELEASE_STATUS.md`, `UPSTREAM_SOURCES.md` y `Validation/`.
