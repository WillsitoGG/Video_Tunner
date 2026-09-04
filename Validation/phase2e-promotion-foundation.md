# Phase 2E.1 — Promotion Policy Foundation

## Objetivo

Introducir una capa explícita y fail-safe entre `eligibility_assessments[]` y un futuro Edit Plan aprobado, sin activar cortes ni crear edits en esta fase.

## Alcance

Schema nuevo: **v9**.

```text
eligibility_assessments[]
        ↓
promotion_assessments[]
        ↓
future explicit approval
        ↓
future approved Edit Plan
```

2E.1 termina en `promotion_assessments[]`. No implementa todavía approval, Edit Plan promotion ni ejecución.

## Policy v1

### Clase respaldada por evidencia humana

```text
possible_repetition
```

La whitelist se deriva del close-out humano 2D.6. Pausas, fillers, retakes y corrections no se promocionan sólo porque alguna instancia pueda atravesar eligibility foundation.

`conservative` y `aggressive` mantienen la misma whitelist en 2E.1.

### Estados

```text
eligible_for_promotion_review
blocked_upstream_eligibility
blocked_removed_text_validation
blocked_unvalidated_candidate_kind
invalid_candidate_reference
```

### Contrato positivo

Un registro sólo puede ser `eligible_for_promotion_review` si:

1. existe el candidate referenciado;
2. `candidate_kind` coincide;
3. la eligibility es `foundation_guards_pass`;
4. `future_promotion_candidate=true`;
5. `removed_text_validation.valid=true`;
6. el kind está respaldado por evidencia humana positiva.

Resultado positivo:

```text
promotion_review_candidate = true
requires_explicit_approval = true
approval_state = required
approved = false
edit = null
safe_for_cut = false
executable = false
auto_apply = false
```

Los blockers de 2D nunca pueden ser rescatados por la capa de promoción.

## Safety schema v9

```text
promotion_assessments_are_not_edits = true
promotion_review_requires_explicit_approval = true
promotion_assessments_approved = false
edit_plan_promotion_enabled = false
promotion_assessments_executable = false
promotion_assessments_safe_for_cut = false
```

## Implementación

Archivos principales:

- `Source/video_tunner/promotion.py`
- `Source/video_tunner/promotion_report.py`
- integración en `Source/video_tunner/analysis_pipeline.py`
- `tests/test_promotion.py`
- `tests/test_promotion_report.py`
- cobertura de integración en `tests/test_analysis_pipeline.py`
- cobertura end-to-end sintética de capas en `tests/test_semantic_pipeline_integration.py`

## Validación

### 1. Policy/report aislados

Run `33896244733`:

```text
165/165 tests PASS en 7.752 s
FFmpeg/ffprobe PASS
doctor PASS
```

Esto validó la policy aislada, estados fail-safe, summary y safety flags antes de integrarla en `analyze`.

### 2. Integración — diagnóstico de fixtures

Run `33898758391`:

```text
165/166 PASS
1 failure: positive integration fixture
```

El fixture usaba:

```text
hoy vamos a lanzar vamos a lanzar ...
```

`hoy` pertenece al contexto temporal crítico del join, por lo que eligibility produjo correctamente `blocked_join_context`.

Run `33898967491`:

```text
165/166 PASS
1 failure: positive integration fixture
```

Tras retirar `hoy`, la repetición `vamos a lanzar` seguía activando correctamente contexto verbal/temporal crítico por `vamos`.

**Decisión:** no tocar ninguna guarda. Se sustituyó únicamente el fixture positivo por una repetición y contexto léxicamente neutros:

```text
equipo proyecto central listo proyecto central listo seguimos bien
```

Estos fallos intermedios se consideran evidencia útil de que la protección join seguía activa durante 2E.1.

### 3. Final integrado

Run `33899201093`, commit evaluado `2e8b3ca902f893fbe69d80bcd1717f3c26761d4a`:

```text
166/166 tests PASS en 7.079 s
FFmpeg 9.0.1 PASS
ffprobe 9.0.1 PASS
doctor PASS
```

Cobertura específica confirmada:

- upstream join blocker → `blocked_upstream_eligibility` en promotion;
- correction bloqueada upstream → permanece bloqueada;
- repetición interior con contexto neutro → `foundation_guards_pass` → `eligible_for_promotion_review`;
- el positivo conserva `approved=false`, `edit=null`, `safe_for_cut=false`, `executable=false`, `auto_apply=false`;
- `automatic_edits=0`.

## Higiene de CI

- `manual-ci.yml` se habilitó sólo mediante triggers one-shot de rama;
- después de cada ejecución se restauró a `workflow_dispatch`;
- estado final de rama: manual-only;
- no se subieron artifacts pesados.

## Conclusión

**Phase 2E.1 Promotion Policy Foundation: PASS.**

Schema v9 distingue por primera vez de forma explícita:

```text
future_promotion_candidate
!= promotion_review_candidate
!= approved edit
```

La única clase habilitada para **revisión** es `possible_repetition`, por respaldo humano 2D.6. Nada queda aprobado ni ejecutable.

## Siguiente

Fase 2E.2 — Explicit Approval Contract:

- objeto/schema de aprobación explícita;
- vínculo fuerte a candidate/promotion assessment/target;
- fingerprint/provenance para detectar stale approvals;
- blockers upstream como veto;
- separación approval → Edit Plan proposal → ejecución.
