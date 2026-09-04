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
- Fase 2E — Promotion to Edit Plan: 🟡 **en curso**
- Fase 2E.3 — Approved Edit Plan Proposal + Global Limits: 🟡 **siguiente**
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
explicit approval artifact (separate, auditable, stale-safe)
  ↓
future approved Edit Plan proposal
  ↓
future execution / render + audit
```

Invariantes:

```text
candidate != assessment != promotion assessment != approval != edit
PROPOSED_CUT != executable CUT
foundation_guards_pass != safe cut
future_promotion_candidate != approved edit
promotion_review_candidate != approval
valid_approved approval != Edit Plan authorization
edit_plan_authorization = false          # Phase 2E.2
edit = null                              # Phase 2E.2
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

## Analysis + approval artifacts

`analysis.json` sigue usando **schema v9**:

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
acoustic_join_assessments[]
semantic_decisions[]
eligibility_assessments[]
promotion_assessments[]
```

2E.2 añade un artefacto separado:

```text
promotion_approval.json
schema_version = 1
record_type = promotion_approval
```

No se muta `analysis.json` al aprobar o rechazar.

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
33894995584  Human Positive Close-out PASS — CLOSE_OUT_READY
33899201093  2E.1 integrated schema v9 PASS — 166/166 + doctor
33899857378  2E.2 approval contract PASS — 174/174 + doctor
```

## Fase 2E.1 — Promotion Policy Foundation

Sólo `possible_repetition`, respaldada por la evidencia humana positiva de 2D.6, puede llegar a `eligible_for_promotion_review`. Sigue sin ser un edit ni una aprobación. Detalle: `Validation/phase2e-promotion-foundation.md`.

## Fase 2E.2 — Explicit Approval Contract

La aprobación es una **decisión humana explícita y auditable** sobre una promotion assessment concreta. Se materializa fuera de `analysis.json` para conservar el análisis original y permitir verificación de vigencia.

Comandos:

```text
video-tunner approval create ANALYSIS \
  --promotion-assessment ID \
  --decision approve|reject \
  --actor ACTOR \
  --reason REASON \
  --output promotion_approval.json

video-tunner approval validate ANALYSIS promotion_approval.json
```

### Integridad y provenance

El artefacto liga la decisión a:

- SHA-256 del `analysis.json` exacto;
- candidate ID/kind;
- eligibility assessment ID/status;
- promotion assessment ID/status;
- mode;
- target exacto;
- fingerprint SHA-256 de una representación JSON canónica de esa evidencia;
- actor, motivo y fecha de decisión.

Si el análisis cambia, el target cambia o la evidencia upstream deja de ser compatible, la aprobación deja de ser vigente.

Estados principales de validación:

```text
valid_approved
valid_rejected
stale_analysis
stale_evidence
stale_or_invalid_reference
invalid_record
```

Un `APPROVE` válido significa únicamente que el revisor aprobó esa promotion assessment contra esa evidencia concreta:

```text
approved = true
edit_plan_authorization = false
edit = null
safe_for_cut = false
executable = false
auto_apply = false
```

2E.2 rechaza además records manipulados que intenten declarar `edit_plan_authorization=true`, añadir un `edit` o activar capacidad ejecutable.

### Validación

Run `33899857378`:

```text
174/174 tests PASS en 7.150 s
doctor PASS
APPROVE válido pero no ejecutable PASS
REJECT auditable PASS
stale por SHA de analysis PASS
stale por evidencia upstream PASS
upstream blocker veto PASS
tampering / falsa autorización de edit bloqueado PASS
actor + reason obligatorios PASS
save/load fingerprint PASS
```

Workflow final: manual-only. No se subieron artifacts pesados.

Detalle: `Validation/phase2e-explicit-approval-contract.md`.

## Siguiente trabajo — Fase 2E.3

Construir una **propuesta** de Edit Plan exclusivamente desde approvals `valid_approved`, con límites globales predefinidos antes de habilitar cualquier ejecución:

1. revalidar approval contra el análisis exacto;
2. aceptar inicialmente sólo `possible_repetition`;
3. generar propuesta, no auto-render;
4. rechazar overlaps/conflictos;
5. limitar número de semantic edits;
6. limitar segundos y porcentaje total retirado;
7. validar bounds contra la timeline fuente;
8. mantener stale/invalid/rejected como veto;
9. separar propuesta, aprobación del plan y ejecución/render.

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
