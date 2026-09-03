# Phase 2D.1 — Correction Scope Validation

Fecha: 2026-09-03.

Estado: **FOUNDATION v1 COMPLETADA**.

## Objetivo

Separar tres conceptos que no pueden conflarse:

```text
explicit_correction candidate
!= correction scope evidence
!= semantic decision
!= edit
```

Detectar `perdón`, `I mean`, `quiero decir`, etc. no demuestra automáticamente dónde empieza el intento incorrecto anterior.

## Nueva capa

`Source/video_tunner/correction_scope.py` produce registros `correction_scopes[]` sólo para `explicit_correction`.

Estados:

```text
bounded
ambiguous
invalid
```

`bounded` significa únicamente que existe una frontera izquierda local y determinista suficiente para describir un **attempt span candidato**. No implica que ese span sea seguro de cortar.

Invariantes:

```text
safe_for_cut = false
executable = false
auto_apply = false
automatic_edits = 0
```

## Estrategias v1

### repeated_corrected_prefix_anchor

Busca un prefijo corto de la formulación corregida que ya aparezca inmediatamente antes del marcador y que deje material adicional dentro del intento previo.

Ejemplo:

```text
la facturación fue de 200 perdón de 250 mil euros
```

Scope:

```text
attempt_span = "de 200"
marker_span  = "perdón"
status       = bounded
safe_for_cut = false
```

### local_numeric_replacement

Si existe una sustitución numérica local a ambos lados del marcador y no hay un anchor repetido más informativo, se acota únicamente el valor previo.

Ejemplo:

```text
el margen era 10% perdón 15% este año
```

Scope:

```text
attempt_span = "10%"
status       = bounded
safe_for_cut = false
```

### no_deterministic_left_boundary

Una corrección puede estar correctamente detectada y, aun así, no existir evidencia suficiente para identificar su frontera izquierda.

Ejemplo AMI/ASR:

```text
i just wonder i mean how will people put these down i wonder
```

Resultado:

```text
explicit_correction = detected
correction scope     = ambiguous
attempt_span         = null
```

Esto es comportamiento esperado y fail-safe.

## Benchmark de scope v1

Fixture:

```text
tests/fixtures/correction_scope_v1.json
```

12 casos etiquetados:

```text
6 expected bounded
3 expected ambiguous
3 expected no correction candidate
```

Incluye construidos y referencias humanas AMI/CORMA ya trazadas en Phase 2C.

Métricas separadas de marker detection:

- candidate misses / false positives;
- scope count mismatches;
- bounded exact / bounded wrong;
- ambiguous correct;
- status / strategy mismatches;
- attempt text mismatches;
- unsafe bounded;
- safety violations;
- bounded exactness;
- scope status accuracy.

Gate v1:

```text
candidate contract clean
bounded_exactness == 1.0
status/strategy/attempt mismatches == 0
unsafe_bounded == 0
safety_violations == 0
```

Un scope `bounded` incorrecto en un caso que debería ser `ambiguous` se considera fallo de seguridad, no simple ruido.

## Evidencia CI

### Foundation aislada — run 33757158460

```text
83 tests PASS en 6.767 s
7 correction-scope tests PASS
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

### Benchmark — run 33757481376

```text
87 tests PASS en 6.595 s
scope benchmark gate PASS
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

### Primer intento de integración schema v4 — run 33757887930

```text
88 tests
87 PASS / 1 FAIL
```

El único fallo fue una aserción histórica de `tests/test_analysis_pipeline.py` que seguía esperando `schema_version == 3` después de añadir deliberadamente `correction_scopes[]` como nueva capa de schema v4.

No falló ninguna heurística de scope, benchmark ni safety guard.

### Integración final — run 33758185755

```text
88/88 tests PASS en 6.711 s
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

## analysis.json schema v4

El pipeline ahora expone:

```text
candidates[]
correction_scopes[]
semantic_decisions[]
```

Cada scope está vinculado a su `candidate_id`.

Safety flags añadidos:

```text
correction_scopes_are_not_edits = true
correction_scopes_executable = false
correction_scopes_safe_for_cut = false
```

`summary.correction_scopes` registra counts por status/strategy y confirma `safe_for_cut=0`, `executable=0`, `auto_apply=0`.

## Qué demuestra

- marker detection y correction scope son capas separadas;
- algunos scopes locales pueden acotarse de forma determinista;
- correcciones reales pueden permanecer `ambiguous` aunque el marker esté bien detectado;
- el benchmark mide errores de boundary de forma explícita;
- ningún bounded scope se convierte en cut;
- schema v4 mantiene candidatos, scopes y decisiones separados.

## Qué NO demuestra

- que un `bounded` scope sea seguro para editar;
- que el corpus v1 cubra habla arbitraria;
- join safety;
- sentence/turn boundary safety;
- prosodia correcta tras un hipotético corte;
- que correction scopes puedan auto-aplicarse.

## Siguiente

Phase 2D.2 — fillers contextuales:

1. distinguir vacilación vocal eliminable de elemento discursivo útil;
2. no usar una lista de tokens como prueba suficiente;
3. medir FP/FN y seguridad con contexto;
4. mantener cualquier decisión no ejecutable;
5. después abordar sentence boundaries + join safety.
