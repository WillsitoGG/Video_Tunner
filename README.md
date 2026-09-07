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
- Fase 2E.5 — Semantic Render Verification / Human Close-out: ✅ **3/3 técnico + 3/3 humano**
- Fase 2E — Promotion to Edit Plan: ✅ **CLOSE_OUT_READY**
- Fase 3 — Calidad audiovisual / auditoría: ⏭️ siguiente
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
semantic_render_verification
  ↓
semantic_render_human_review
  ↓
phase2e_closeout_decision
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
technical post-render PASS != human perceptual PASS
stale/altered evidence = INVALID_EVIDENCE
auto_apply = false
```

## Portable / ML validado

- Core portable `33600174568`: PASS.
- ML frozen `33621357438`: PASS.
- Sync hardening `33639009841`: PASS.
- Target Spanish `33656235038`: WER `1.64%`, RTF `0.4854`, word timestamps PASS, automatic edits 0.

Modelo objetivo: **`large-v3-turbo`**.

La estrategia de transcripción de producto sigue siendo `single_pass` por defecto. `deterministic_overlap_12s_3s_repeat_consensus_v1` está expuesta como opt-in explícito y es la estrategia validada para el close-out 2E.5.

## Artifacts principales

```text
analysis.json                         schema v9
promotion_approval.json               schema v1
approved_edit_plan_proposal.json      schema v1
semantic_execution_authorization.json schema v1
semantic_edit_plan.json               schema v1
semantic_render_verification          schema v1
semantic_render_human_review          schema v1
phase2e_closeout_decision              schema v1
```

La proposal nunca es ejecutable. El Semantic Edit Plan sólo se materializa desde una autorización global vigente, y el renderer genérico rechaza proposals y Semantic Edit Plans fuera del semantic render gate.

## Semantic render gate

La vía semántica ejecutable es `execution render`, que justo antes de FFmpeg revalida:

1. analysis actual;
2. proposal actual;
3. global authorization actual;
4. SHA-256 de authorization ligado al plan;
5. plan fingerprint + edits exactos;
6. SHA-256 real del vídeo fuente frente a analysis/proposal/plan.

Si cualquier elemento es stale, manipulado o distinto, el render se bloquea.

## Evidencia principal de Fase 2E

```text
33899201093  2E.1 schema v9 — 166/166 PASS + doctor
33899857378  2E.2 approval contract — 174/174 PASS + doctor
33900544072  2E.3 proposal foundation — 185/185 PASS + doctor
33908500929  2E.3 renderer isolation — 186/186 PASS + doctor
33909424933  2E.4 authorization/render-gate core — 201/201 PASS + doctor
33909625346  2E.4 real FFmpeg semantic render E2E — 202/202 PASS + doctor
34119952855  2E.5 technical close-out — 278 tests + portable/provenance + 3/3 real AMI technical renders PASS
34121684853  2E.5 offline human-finalizer contract — PASS
```

Final 2E.5:

```text
cases = 3
sources = 2
technical PASS = 3/3
human perceptual PASS = 3/3
human FAIL = 0
invalid/stale reviews = 0
status = CLOSE_OUT_READY
auto_apply = false
```

Evidencia permanente: `Validation/phase2e-post-render-closeout.md` y `Validation/phase2e-human-closeout/`.

## Siguiente trabajo — Fase 3

Con Fase 2E cerrada, el siguiente bloque es **calidad audiovisual / auditoría**: tratamiento de joins, normalización/denoise controlados, auditoría avanzada de salida y calidad audiovisual end-to-end.

Después: Fase 4 UX mínima y Fase 5 Portable Release Hardening.

## Principios

- portable por diseño;
- local-first;
- originales intactos;
- sync fiable antes de IA temporal;
- conservador por defecto;
- ante duda: KEEP/REVIEW;
- GitHub como source of truth;
- CI deliberada y workflows pesados manual-only;
- `auto_apply=false`;
- no GitHub Release sin autorización expresa de Guille.

Consulta `AGENTS.md`, `ROADMAP.md`, `RELEASE_STATUS.md`, `UPSTREAM_SOURCES.md` y `Validation/`.
