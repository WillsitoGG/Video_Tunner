# Fase 2D.5 — Human Combined Eligibility Evidence

Fecha: 2026-09-03.

Estado: **COMPLETADA COMO EVIDENCIA HUMANA v1, SIN PROMOCIÓN A EDIT PLAN**.

## Objetivo

Aplicar la policy acumulativa de schema v8 a evidencia humana real y trazable antes de considerar cualquier promoción.

Se reutilizan:

- el WAV AMI original `ES2012d.Mix-Headset.wav`;
- los endpoints reales de palabra de `large-v3-turbo` fijados en el run `33755013415`;
- las decisiones semánticas humanas ya observadas en ese run;
- las capas actuales de correction scope, join context, acoustic join y combined eligibility.

No se vuelve a descargar ni ejecutar el modelo de ~1,6 GB.

```text
real AMI waveform
+ frozen real large-v3-turbo endpoints
+ frozen semantic decisions
→ scope / join / acoustics
→ combined eligibility
```

## Fuente y trazabilidad

```text
corpus   AMI Meeting Corpus
meeting  ES2012d
audio    ES2012d.Mix-Headset.wav
license  CC BY 4.0
bytes    30388952
sha256   39FCDE566E2D1BC7EC40A31DEC19251CC253AAC54BE94713E68EEA3008AF4F8D
ASR run  33755013415
model    large-v3-turbo
```

El WAV sólo existe de forma efímera en `RUNNER_TEMP`; no se versiona ni se sube como artifact.

## Casos humanos

### 1. Control de pausa humana

`ami-human-pause-control-0311`

```text
join_status                 join_context_only
acoustic_status             acoustic_context_only
measurement_available       true
semantic_decision           none
expected eligibility        foundation_guards_pass
```

Este caso es **un control de plumbing/policy**, no una etiqueta humana que afirme que la pausa deba eliminarse automáticamente.

Incluso cuando pasa todas las guardas foundation:

```text
future_promotion_candidate  true
safe_for_cut                 false
executable                   false
auto_apply                   false
```

### 2. Retake humano protegido

`ami-human-retake-protected-0311`

Decisión semántica congelada del run real:

```text
REVIEW / guard_status=review
```

La cadena sigue:

```text
repair_or_protected_context_risk
→ acoustic blocked_by_context
→ blocked_semantic_decision
```

No puede ser rescatado por una capa posterior.

### 3. Correction humana ambigua

`ami-human-correction-ambiguous-0250`

```text
semantic_decision       REVIEW
correction_scope        ambiguous
join_status             invalid_or_unbounded_target
acoustic_status         blocked_by_context
```

Un scope ambiguo no produce target de join por diseño.

## Baseline — run 33791636767

La regresión general pasó:

```text
141/141 tests PASS en 6.908 s
```

La validación humana produjo:

```text
cases                   3
foundation_guards_pass  1
blocked                  2
safe_for_cut             0
executable               0
auto_apply               0
automatic_edits          0
```

Pero el gate humano falló por **un único desacuerdo diagnóstico**:

```text
expected: blocked_correction_scope
actual:   invalid_removed_text
reason:   missing_target_span
```

La correction seguía completamente bloqueada; no existió fallo de seguridad.

### Causa

La policy v1 evaluaba inicialmente la integridad del target antes que el estado del correction scope.

Para una correction `ambiguous`, la ausencia de target es precisamente el comportamiento esperado de la capa de join. Por tanto, etiquetarla primero como target corrupto era menos informativo que reportar la causa upstream real: scope no acotado.

## Ajuste guiado por evidencia humana

Se cambió exclusivamente la **precedencia diagnóstica**:

Antes:

```text
invalid removed target
→ correction scope blocker
```

Después:

```text
explicit_correction + scope != bounded
→ blocked_correction_scope
→ sólo después validar removed target cuando procede
```

La información secundaria de `removed_text_validation` se conserva:

```text
valid   false
reason  missing_target_span
```

Por tanto, no se oculta la ausencia del target; simplemente el estado principal refleja correctamente la causa upstream.

Este cambio:

- no añade ninguna ruta positiva;
- no modifica thresholds;
- no cambia semantic decisions;
- no cambia join/acoustic pass criteria;
- no cambia `safe_for_cut`;
- no habilita ejecución ni auto-apply.

Se añadió una regresión específica:

`test_ambiguous_correction_without_target_is_diagnosed_as_scope_blocker`.

## Final — run 33791950505

**SUCCESS**.

Regresión:

```text
142/142 tests PASS en 7.087 s
```

Human combined eligibility:

```text
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

Checks:

```text
all_cases_evaluated=true
human_foundation_control_exists=true
human_blockers_preserved=true
no_contract_failures=true
non_executable=true
```

### Resultado final por caso

#### Pausa control

```text
join                   join_context_only
acoustic               acoustic_context_only
removedText valid      true
eligibility            foundation_guards_pass
future promotion       true
safe_for_cut           false
```

#### Retake humano

```text
semantic               REVIEW
join                   repair_or_protected_context_risk
acoustic               blocked_by_context
removedText valid      true
eligibility            blocked_semantic_decision
future promotion       false
```

#### Correction humana ambigua

```text
semantic               REVIEW
scope                   ambiguous
join                    invalid_or_unbounded_target
acoustic                blocked_by_context
removedText valid       false
removedText reason      missing_target_span
eligibility             blocked_correction_scope
future promotion        false
```

## Qué demuestra

- la policy schema v8 funciona sobre evidencia humana real/trazable;
- los blockers semánticos y de scope sobreviven a las capas posteriores;
- una correction sin target por scope ambiguo se diagnostica correctamente sin perder la evidencia secundaria;
- existe al menos una ruta humana de control que atraviesa todas las guardas foundation;
- `foundation_guards_pass` sigue sin convertirse en permiso de corte;
- toda la cadena permanece no ejecutable.

## Qué NO demuestra

- que el control de pausa deba borrarse en producto;
- que exista todavía una clase humana etiquetada como **realmente descartable** y suficientemente validada para auto-apply;
- precisión/recall general de eligibility sobre habla arbitraria;
- calidad perceptual de un render tras el corte;
- que 2D pueda cerrarse ya para promoción automática.

## Decisión

**No pasar todavía a 2E.**

La evidencia humana actual contiene un control positivo de plumbing/policy, pero no un conjunto suficiente de positivos humanos etiquetados como realmente eliminables.

Siguiente microfase recomendada:

**2D.6 — Human Positive Eligibility Expansion / Close-out Gate**.

Objetivo:

1. obtener varios positivos humanos legítimos y trazables de material realmente descartable;
2. priorizar pausas limpias, fillers aislados y repeticiones/tomas descartables donde la etiqueta humana sea clara;
3. medir si atraviesan la policy actual sin relajarla;
4. incluir negativos cercanos para controlar falsos positivos;
5. validar `removedText` y joins reales;
6. si la policy no deja pasar suficientes positivos, registrar el resultado y ajustar sólo con evidencia;
7. mantener `safe_for_cut=false`, `executable=false`, `auto_apply=false`, `automatic_edits=0` durante todo 2D.6.
