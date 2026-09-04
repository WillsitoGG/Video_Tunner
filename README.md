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
- Fase 2E — Promotion to Edit Plan: 🟡 **en curso**
- Fase 2E.2 — Explicit Approval Contract: 🟡 **siguiente**
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
promotion assessments
  ↓
future explicitly approved Edit Plan
  ↓
render + audit
```

Invariantes:

```text
candidate != scope != assessment != semantic decision != edit
PROPOSED_CUT != executable CUT
foundation_guards_pass != safe cut
future_promotion_candidate != approved edit
promotion_review_candidate != approved edit
approved = false                 # Phase 2E.1
edit = null                      # Phase 2E.1
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

`analysis.json` actual usa **schema v9**:

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

Safety v9 añade:

```text
promotion_assessments_are_not_edits = true
promotion_review_requires_explicit_approval = true
promotion_assessments_approved = false
edit_plan_promotion_enabled = false
promotion_assessments_executable = false
promotion_assessments_safe_for_cut = false
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
33896244733  2E.1 isolated promotion policy PASS — 165/165
33899201093  2E.1 schema v9 integrated PASS — 166/166 + doctor
```

## Fase 2D — cerrada como foundation/evidence

2D validó guardas acumulativas y evidencia humana positiva sin activar cortes. Run final `33894995584`: 8 casos humanos AMI evaluados, 6 positivos alineados, 3 `foundation_guards_pass` en 2 fuentes independientes y 0 capacidad ejecutable. Detalle: `Validation/phase2d-human-positive-closeout.md`.

## Fase 2E.1 — Promotion Policy Foundation

2E.1 introduce una capa explícita entre eligibility y un futuro Edit Plan aprobado. **No crea edits.**

La única clase inicialmente respaldada por evidencia humana positiva suficiente para entrar en revisión de promoción es:

```text
possible_repetition
```

Conservative y aggressive usan por ahora exactamente la misma whitelist. El modo aggressive no amplía clases sin evidencia.

Estados de `promotion_assessments[]`:

```text
eligible_for_promotion_review
blocked_upstream_eligibility
blocked_removed_text_validation
blocked_unvalidated_candidate_kind
invalid_candidate_reference
```

Para llegar a `eligible_for_promotion_review` deben cumplirse simultáneamente:

1. candidato existente y kind consistente;
2. eligibility `foundation_guards_pass`;
3. `future_promotion_candidate=true`;
4. `removed_text_validation.valid=true`;
5. clase respaldada por evidencia humana positiva.

Incluso entonces:

```text
requires_explicit_approval = true
approval_state = required
approved = false
edit = null
safe_for_cut = false
executable = false
auto_apply = false
```

El mecanismo de aprobación explícita todavía **no existe** en 2E.1; pertenece a 2E.2.

### Validación

- `33896244733`: policy/report aislados, **165/165 PASS**.
- `33898758391`: integración 165/166; el fixture positivo usaba `hoy`, correctamente bloqueado como contexto temporal crítico.
- `33898967491`: integración 165/166; `vamos a lanzar` seguía activando contexto verbal crítico por `vamos`.
- Se modificaron sólo los fixtures sintéticos; no se cambió producto, thresholds ni guardas.
- `33899201093`: **166/166 PASS en 7.079 s + `doctor` PASS**.

La prueba positiva final usa contexto léxicamente neutro y confirma que una repetición interior puede llegar a `eligible_for_promotion_review` sin producir edit alguno.

Detalle: `Validation/phase2e-promotion-foundation.md`.

## Siguiente trabajo — Fase 2E.2

Objetivo: definir un **contrato de aprobación explícita** auditable entre `promotion_assessments[]` y una propuesta aprobada, todavía sin habilitar auto-apply indiscriminado.

1. definir quién/qué puede aprobar y cómo queda registrada la aprobación;
2. ligar la aprobación al candidate/promotion assessment exacto y a su target validado;
3. invalidar aprobación si cambia cualquier evidencia upstream;
4. mantener blockers 2D como veto acumulativo;
5. definir límites globales y fail-safe antes de ejecución;
6. separar aprobación, construcción de Edit Plan y ejecución/render;
7. validar primero con tests controlados y después con evidencia humana cuando cambie una decisión técnica.

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
