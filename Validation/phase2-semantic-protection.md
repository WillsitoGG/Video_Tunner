# Fase 2B — Semantic Decisions + Protection

Fecha de cierre: 2026-09-03.

## Objetivo

Introducir una capa explícita entre `candidate` y `edit` que evalúe guardas semánticas deterministas antes de permitir siquiera una propuesta de corte.

```text
candidate → semantic decision → future approved edit
```

En este milestone **ninguna semantic decision es ejecutable**.

## Contrato

Decisiones posibles:

```text
KEEP
REVIEW
PROPOSED_TRIM
PROPOSED_CUT
```

Invariantes actuales:

```text
executable = false
auto_apply = false
```

`PROPOSED_CUT` significa únicamente que una heurística pasó las guardas deterministas disponibles. No modifica Edit Plan ni render.

## Schema

`analysis.json` pasa a schema v3 y mantiene bloques separados:

```text
candidates[]
semantic_decisions[]
```

Cada decision referencia `candidate_id` y registra:

- decision y confidence;
- guard status (`pass`, `review`, `blocked`);
- proposed span;
- `removed_text`;
- validación de word indices/timestamps;
- rasgos semánticos protegidos;
- rationale;
- `executable=false`;
- `auto_apply=false`.

El report declara además:

```text
semantic_protection_enabled = true
semantic_decisions_are_not_edits = true
semantic_decisions_executable = false
```

## Guardas v1

### Span integrity

Antes de razonar sobre significado:

- word indices deben existir y estar dentro del transcript;
- `removed_text` normalizado debe coincidir con las palabras del span;
- start/end deben coincidir con los word timestamps dentro de tolerancia.

Mismatch => **KEEP fail-safe**.

### Cifras

Detectar:

- dígitos/decimales;
- porcentajes;
- palabras numéricas comunes ES/EN.

Ejemplo crítico:

```text
la facturación fue de 200 perdón de 250 mil euros
```

`200` y `250` se registran como valores distintos a ambos lados del marcador y la decisión queda `REVIEW`.

### Unidades / importes

Detectar de forma conservadora símbolos y unidades comunes:

- `%`, `€`, `$`, `£`;
- euro/dólar;
- kg/g/l/ml;
- m/km;
- segundos/minutos/horas;
- equivalentes básicos EN.

No inferir conversiones/equivalencias.

### Negaciones

Protección de `no`, `nunca`, `jamás`, `sin`, `not`, `never`, etc.

Cambio de negación alrededor de una autocorrección => `REVIEW`.

### Persona / sujeto

Pronombres personales básicos ES/EN se registran como rasgo protegido. Esta heurística no sustituye a un parser lingüístico.

### Tiempo / aspecto

Se registran auxiliares y marcadores temporales básicos (por ejemplo `fue`, `era`, `será`, `ayer`, `mañana`, `was`, `will`). Es una guardia conservadora, no análisis morfosintáctico completo.

### Causalidad / contraste

Marcadores conservadores como `pero`, `aunque`, `porque`, `sino`, `excepto`, `salvo`, `entonces` y equivalentes básicos EN se consideran señales sensibles.

### Entidades

Se registra una señal heurística de tokens capitalizados. No se afirma NER fiable todavía; cualquier uso de esta señal debe seguir siendo review-only.

## Política por candidate kind

### `possible_repetition`

Si ambas ocurrencias son exactamente equivalentes tras normalización y la segunda queda fuera del proposed span:

```text
PROPOSED_CUT
executable=false
```

Incluso si la frase contiene cifras/negaciones, la propuesta no es ejecutable; la equivalencia exacta conserva una copia de esos rasgos.

### `possible_retake`

Si existe material intermedio no trivial o conflicto protegido:

```text
REVIEW
```

Sólo material compuesto por tokens de vacilación/corrección muy restringidos podría llegar a `PROPOSED_CUT`, todavía no ejecutable.

### `explicit_correction`

Siempre `REVIEW` en v1. Detectar `perdón` no demuestra automáticamente dónde empieza la toma incorrecta.

Se registra una `correction_relation` con ventanas de intento/corrección y cambios protegidos.

## Tests de riesgo

La suite específica cubre:

1. repetición exacta → `PROPOSED_CUT`, no ejecutable;
2. `200 → perdón → 250 mil euros` → REVIEW + cifra/unidad crítica;
3. `10% → perdón → 15%` → protección de número y `%`;
4. cambio de negación → REVIEW;
5. retoma con contenido no trivial → REVIEW;
6. candidate span corrupto → KEEP fail-safe;
7. todas las semantic decisions permanecen no ejecutables;
8. pipeline integra decisions separadas de candidates y mantiene `automatic_edits=0`;
9. pipeline base acredita schema v3 e invariantes semánticas incluso cuando el fixture no genera semantic decisions.

## Validación Windows ligera

### Run `33661062365` — FAILURE diagnosticado

```text
Ran 55 tests in 6.097s
54 PASS
1 FAIL
```

Único fallo:

```text
test_analysis_pipeline.AnalysisPipelineTests.
test_pipeline_uses_the_same_verified_master_for_whisper_and_vad
```

El test heredado esperaba:

```python
report["schema_version"] == 2
```

pero Fase 2B eleva deliberadamente el `analysis.json` actual a schema v3. Todos los tests nuevos de Semantic Decisions/Protection y todos los E2E de sync pasaron en ese run.

No se modificó código productivo para resolverlo. Se actualizó únicamente la expectativa heredada y se reforzó ese mismo test con las invariantes:

```text
schema_version == 3
semantic_protection_enabled == true
semantic_decisions_are_not_edits == true
semantic_decisions_executable == false
semantic_decisions == []
```

### Run final `33741195594` — SUCCESS

```text
Ran 55 tests in 6.671s
OK
```

También:

- `video-tunner doctor` PASS;
- E2E FFmpeg/sync PASS;
- semantic candidates PASS;
- semantic decisions/protection PASS;
- artifacts: `0`;
- workflow restaurado a `workflow_dispatch` tras el trigger one-shot;
- marker temporal eliminado.

La CI ligera instaló únicamente el paquete editable + `numpy==2.5.2` y FFmpeg del runner/Chocolatey; no reinstaló Whisper/CTranslate2/ONNX ni pretende sustituir las validaciones ML/portable previas.

## Resultado de Fase 2B

**Fase 2B completada.**

Queda demostrado el contrato:

```text
candidate != semantic decision != edit
PROPOSED_CUT != executable CUT
```

`automatic_edits` permanece en `0`.

## Pendiente antes de promover edits

- corpus/fixtures de habla real con errores, retomas y autocorrecciones deliberadas;
- análisis de falsos positivos/falsos negativos;
- inferir de forma segura el scope de la toma incorrecta en correcciones explícitas;
- fillers contextuales;
- ampliar guardas lingüísticas sólo con evidencia;
- join safety y límites de frase;
- decisión explícita de qué clases podrían ser auto-aplicables por modo;
- ningún Edit Plan automático hasta superar esas validaciones.
