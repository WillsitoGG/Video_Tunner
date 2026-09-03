# Fase 2D.4 — Combined Eligibility / Promotion Policy Foundation

Fecha: 2026-09-03.

Estado: **COMPLETADA COMO FOUNDATION NO EJECUTABLE v1**.

## Objetivo

Combinar de forma acumulativa las capas ya validadas sin convertirlas todavía en edits:

```text
candidate
→ semantic decision / correction scope / filler context
→ join context
→ acoustic join assessment
→ combined eligibility assessment
→ future promotion only
```

La regla central es fail-safe:

> una señal posterior favorable nunca puede rescatar una guarda anterior bloqueada.

Incluso cuando todas las guardas v1 pasan, el resultado es sólo:

```text
foundation_guards_pass
future_promotion_candidate = true
safe_for_cut = false
executable = false
auto_apply = false
```

## Schema v8

`analysis.json` añade:

```text
eligibility_assessments[]
```

El esquema queda:

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
acoustic_join_assessments[]
semantic_decisions[]
eligibility_assessments[]
```

## Política acumulativa v1

Orden de precedencia:

1. `removedText`/target inválido → `invalid_removed_text`;
2. correction sin scope `bounded` → `blocked_correction_scope`;
3. filler distinto de `isolated_hesitation` → `blocked_filler_context`;
4. semantic kind sin semantic decision → `missing_required_evidence`;
5. semantic decision distinta de `PROPOSED_CUT/PROPOSED_TRIM` con `guard_status=pass` → `blocked_semantic_decision`;
6. join distinto de `join_context_only` → `blocked_join_context`;
7. acoustic assessment ausente → `missing_required_evidence`;
8. acústica distinta de `acoustic_context_only/low_energy_boundary_context` o sin medición → `blocked_acoustic_context`;
9. todas las guardas anteriores pasan → `foundation_guards_pass`.

No existe una rama que produzca `safe_for_cut=true`.

## Validación de removedText

La policy vuelve a verificar el target final, no confía ciegamente en capas previas.

### Spans de texto

Exige:

- índices de palabra válidos;
- texto normalizado igual al transcript;
- timestamps inicial/final dentro de tolerancia de `0.03 s`.

### Pausas

Para `candidate_temporal_gap` exige:

- candidate de tipo `pause`;
- target textual vacío;
- start/end iguales al candidate dentro de tolerancia.

### Correcciones

El target definitivo puede venir de:

```text
bounded_correction_attempt_plus_marker
```

Por tanto, una correction no queda limitada al marker-only original si el scope posterior ha acotado de forma determinista `attempt + marker`.

## Benchmark v1

Fixture: `tests/fixtures/eligibility_v1.json`.

12 casos etiquetados:

```text
foundation_guards_pass        4
blocked_acoustic_context      1
blocked_filler_context        1
blocked_semantic_decision     2
blocked_join_context          1
blocked_correction_scope      1
invalid_removed_text          1
missing_required_evidence     1
```

Rutas positivas foundation:

1. pausa con join/acústica limpios;
2. pausa con ambos bordes de energía baja;
3. filler `isolated_hesitation` con resto de guardas limpias;
4. repetición con semantic `PROPOSED_CUT/pass`, join limpio y acústica medida limpia.

Rutas negativas incluyen fallos deliberados en cada capa, incluido target textual corrupto y acoustic evidence ausente.

## Gate

```text
cases >= 10
all required statuses exercised
status mismatches == 0
removedText contract failures == 0
safety violations == 0
future promotion candidates >= 3
safe_for_cut == 0
executable == 0
auto_apply == 0
```

## Run 33790792753

**SUCCESS**.

```text
138/138 tests PASS en 7.035 s
combined eligibility gate PASS
schema v8 pipeline integration PASS
removedText validation PASS
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

No fue necesario mover thresholds, relajar gates ni modificar las capas semántica/acústica previas.

## Safety flags v8

```text
eligibility_assessments_are_not_edits = true
eligibility_assessments_executable = false
eligibility_assessments_safe_for_cut = false
future_promotion_candidates_are_not_approved_edits = true
combined_eligibility_enabled = true
combined_eligibility_is_not_edit_plan_promotion = true
```

Además permanecen:

```text
safe_for_cut = false
executable = false
auto_apply = false
automatic_edits = 0
```

## Qué demuestra

- existe una política determinista de guardas acumulativas;
- una guarda posterior favorable no rescata una anterior;
- `removedText`/target se vuelve a comprobar en el último nivel antes de una futura promoción;
- el pipeline puede emitir schema v8 con una assessment de elegibilidad asociada a cada join analizado;
- hay rutas que pasan las guardas foundation sin convertirse en edits.

## Qué NO demuestra

- que `foundation_guards_pass` sea seguro para cortar automáticamente;
- precisión/recall de la policy sobre vídeo humano arbitrario;
- calidad perceptual del render;
- que pausas, fillers o repeticiones positivas deban auto-aplicarse;
- que correction alguna sea elegible para auto-apply;
- que el Edit Plan deba aceptar todavía estos records.

## Siguiente microfase

Antes de 2E debe validarse la policy combinada sobre evidencia humana real ya trazable y/o nuevos controles humanos donde aporte señal nueva.

Objetivo recomendado: **2D.5 — Human Combined Eligibility Evidence**.

Debe comprobar que:

- casos humanos protegidos siguen bloqueados;
- un control humano acústicamente limpio no obtiene permiso de cut;
- `removedText` se mantiene íntegro con endpoints reales;
- cualquier `foundation_guards_pass` humano sigue siendo sólo candidato de futura promoción;
- `automatic_edits=0`.
