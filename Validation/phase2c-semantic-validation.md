# Fase 2C — Semantic Validation Foundation

Fecha: 2026-09-03.

Estado: **BENCHMARK FOUNDATION COMPLETADA; FASE 2C SIGUE EN CURSO**.

## Objetivo

Crear una validación semántica explícita que mida por separado:

- detección de candidates: TP / FP / FN, precision, recall y F1;
- seguridad de semantic decisions;
- propuestas `PROPOSED_CUT` incorrectas;
- decisiones que se volvieran ejecutables o auto-aplicables por accidente.

Esta fase no promueve nada al Edit Plan.

```text
candidate != semantic decision != edit
executable = false
auto_apply = false
```

## Harness

Nuevo módulo:

```text
Source/video_tunner/semantic_validation.py
```

Fixture etiquetado:

```text
tests/fixtures/semantic_corpus_v1.json
```

Tests:

```text
tests/test_semantic_validation.py
```

El evaluador genera word timings deterministas para aislar el comportamiento de la capa semántica respecto de la calidad ASR. Estos timings sintéticos **no son ground truth temporal**.

## Corpus v1

Composición actual:

```text
22 casos
11 constructed_positive
6 constructed_negative
4 human_speech_reference
1 human_speech_positive
12 eventos semánticos esperados
```

Positivos construidos:

- repetición exacta;
- repetición exacta con negación;
- repetición exacta con cifra/unidad;
- corrección de cifra;
- corrección de porcentaje;
- corrección de negación;
- corrección de persona/sujeto;
- corrección temporal;
- corrección de entidad;
- retake con vacilación;
- retake con contenido intermedio no trivial.

Negativos construidos:

- énfasis oral corto;
- marcador discursivo legítimo;
- filler aislado;
- reutilización legítima de opener;
- `quiero decir` literal al inicio;
- `lo que quiero decir` literal.

### Controles de habla humana real

Se reutilizan como controles negativos cuatro diálogos reales de SpanishPod que ya habían sido validados con audio + `large-v3-turbo` en el run `33656235038`:

```text
SpanishPod_newbie_lesson_A0006_dialogue.ogg
SpanishPod_newbie_lesson_A0007_dialogue.ogg
SpanishPod_newbie_lesson_A0013_dialogue.ogg
SpanishPod_newbie_lesson_A0116_dialogue.ogg
```

No se repite la CI ML pesada porque esa evidencia sigue vigente y el objetivo aquí es medir ruido semántico sobre el contenido humano ya acreditado.

### Primer positivo humano real — AMI

Se incorpora un retake de habla espontánea procedente de **AMI Meeting Corpus**, con transcript manual y licencia pública CC BY 4.0:

```text
meeting: ES2012d
source type: human_speech_positive
expected kind: possible_retake
expected decision: REVIEW
```

La fuente exacta queda registrada en `source_reference` dentro del fixture. El caso contiene un opener repetido tras una vacilación/interrupción real y el detector Conservador debe encontrarlo sin convertirlo en corte ejecutable.

Este caso valida contenido humano real, pero en el harness se siguen generando timings deterministas: esta prueba no sustituye una futura validación audio → Whisper → semántica específica del mismo fragmento.

## Baseline antes del tuneo

Run `33742519997` — **SUCCESS**.

```text
Ran 60 tests in 6.603s
OK
```

Benchmark inicial:

```text
cases                 16
expected events       11
false positives        2
false negatives        0
precision         84.62%
recall           100.00%
F1                91.67%
unsafe proposals       0
decision mismatches    0
executable decisions   0
auto-apply decisions   0
```

Los dos falsos positivos medidos fueron:

1. reutilización cercana y legítima del opener `vamos a lanzar` tras una continuación normal;
2. `quiero decir` usado literalmente al comienzo de una frase.

Ambos seguían siendo `REVIEW`, por lo que el baseline ya tenía **0 violaciones de seguridad**, pero generaba ruido innecesario.

## Tuneo basado en evidencia

Se modificó únicamente el detector determinista de candidates en modo Conservador:

### Retakes

- reconocer marcadores de continuación normales (`y`, `pero`, `porque`, `luego`, `ahora`, etc.; equivalentes EN);
- si reaparece un opener tras una continuación normal y no existe evidencia de reparación/vacilación, no generar retake;
- conservar retakes cuando sí existe evidencia como `eh`, `um`, `perdón`, etc.;
- registrar `repair_evidence`.

### `quiero decir` / `I mean`

Se mantienen como marcadores ambiguos, no fuertes:

- al inicio de la transcripción no se consideran autocorrección;
- `lo que quiero decir` / `what I mean` se trata como construcción literal;
- después de un intento previo siguen pudiendo generar `explicit_correction`, siempre `REVIEW`.

No se introdujo ninguna dependencia ML nueva.

## Validaciones

### Corpus ajustado sin positivo humano

Run `33743029443` — **SUCCESS**.

```text
Ran 64 tests in 6.588s
OK
```

Corpus de ese run:

```text
cases                       21
source: constructed positive 11
source: constructed negative  6
source: human speech reference 4
expected events             11
actual candidates            11
false positives               0
false negatives               0
precision               100.00%
recall                  100.00%
F1                      100.00%
decision mismatches           0
unsafe proposals              0
missing safe proposals        0
executable decisions          0
auto-apply decisions          0
```

### Primer positivo humano AMI

Run `33743638690` — **SUCCESS**.

```text
Ran 65 tests in 6.789s
OK
```

También:

- el caso `human-ami-es2012d-retake` se detecta como `possible_retake`;
- la semantic decision resultante es `REVIEW`;
- `guard_status=review`;
- `video-tunner doctor` PASS;
- E2E FFmpeg/sync PASS;
- artifacts `0`.

Benchmark actual:

```text
cases                       22
source: constructed positive 11
source: constructed negative  6
source: human speech reference 4
source: human speech positive  1
expected events             12
actual candidates            12
false positives               0
false negatives               0
precision               100.00%
recall                  100.00%
F1                      100.00%
decision mismatches           0
unsafe proposals              0
missing safe proposals        0
executable decisions          0
auto-apply decisions          0
```

El gate v1 queda fijado en:

```text
precision >= 0.95
recall >= 0.95
unsafe proposals == 0
decision mismatches == 0
missing safe proposals == 0
executable decisions == 0
auto_apply decisions == 0
```

## Qué demuestra y qué NO demuestra

Demuestra:

- existe una métrica reproducible para candidates + semantic decisions;
- el tuneo fue guiado por falsos positivos observados, no por intuición;
- el corpus v1 actual queda 0 FP / 0 FN;
- cuatro controles humanos reales no introducen ruido semántico;
- un primer retake humano espontáneo real se detecta correctamente y permanece `REVIEW`;
- ninguna propuesta insegura aparece en este corpus;
- nada se vuelve ejecutable ni auto-aplicable.

NO demuestra todavía:

- seguridad general sobre cualquier habla real;
- precisión robusta sobre una muestra amplia de retomas/autocorrecciones humanas espontáneas;
- precisión específica sobre positivos humanos en español;
- comportamiento del mismo positivo AMI pasando de audio real por Whisper en este run;
- scope seguro de `intento incorrecto → corrección válida`;
- seguridad de joins tras una futura promoción al Edit Plan;
- que `PROPOSED_CUT` pueda ejecutarse automáticamente.

## Siguiente trabajo dentro de 2C

1. ampliar positivos humanos reales con retomas, reinicios y autocorrecciones;
2. incorporar como siguiente fixture la autocorrección humana AMI ya localizada con marcador `I mean`;
3. buscar positivos equivalentes en español cuando exista fuente/licencia adecuada;
4. evaluar transcript real producido por Whisper cuando aporte evidencia nueva;
5. ampliar el corpus sin mover thresholds para acomodar fallos;
6. usar los fallos observados para endurecer guardas;
7. después abordar scope de correcciones, fillers contextuales y join safety;
8. mantener `executable=false` hasta completar esta evidencia.
