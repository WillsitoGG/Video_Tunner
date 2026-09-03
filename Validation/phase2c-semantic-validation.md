# Fase 2C — Semantic Validation

Fecha: 2026-09-03.

Estado: **BENCHMARK FOUNDATION COMPLETADA; FASE 2C SIGUE EN CURSO**.

## Objetivo

Validar por separado calidad de detección y seguridad:

- candidate TP / FP / FN;
- precision / recall / F1;
- decision mismatches;
- `PROPOSED_CUT` incorrectos;
- missing safe proposals;
- decisiones ejecutables o auto-aplicables por accidente.

Esta fase no promueve nada al Edit Plan.

```text
candidate != semantic decision != edit
PROPOSED_CUT != executable CUT
executable = false
auto_apply = false
automatic_edits = 0
```

## Harness

```text
Source/video_tunner/semantic_validation.py
tests/fixtures/semantic_corpus_v1.json
tests/fixtures/semantic_human_corrections_v1.json
tests/test_semantic_validation.py
tests/test_semantic_human_corrections.py
```

El harness genera word timings deterministas para aislar la capa semántica de ASR. Esos timings **no son ground truth temporal** ni sustituyen una validación audio → Whisper → semántica.

## 2C.1 — Foundation v1

### Baseline inicial

Run `33742519997` — SUCCESS:

```text
60 tests PASS
16 casos
11 eventos esperados
FP 2
FN 0
precision 84.62%
recall 100%
F1 91.67%
unsafe proposals 0
executable 0
auto_apply 0
```

FP observados:

1. reutilización legítima cercana de opener;
2. `quiero decir` literal.

Ambos eran `REVIEW`: ruido, no fallo de seguridad.

### Tuneo inicial

En modo Conservador:

- reutilización de opener tras continuación normal y sin reparación => no retake;
- se registra `repair_evidence`;
- `quiero decir` / `I mean` se consideran ambiguos en frames literales.

Run `33743029443` — SUCCESS:

```text
64 tests PASS en 6.588 s
21 casos / 11 eventos
FP 0 / FN 0
precision = recall = F1 = 100% en este corpus
unsafe proposals 0
executable 0
auto_apply 0
artifacts 0
```

### Primer positivo humano

Se añadió un retake espontáneo de AMI Meeting Corpus ES2012d.

Run `33743638690` — SUCCESS:

```text
65 tests PASS en 6.789 s
22 casos / 12 eventos
FP 0 / FN 0
unsafe proposals 0
executable 0
auto_apply 0
artifacts 0
```

Resultado:

```text
possible_retake → REVIEW
guard_status = review
```

## 2C.2 — Correcciones humanas y ambigüedad de marcadores

Se añadió un bloque humano bilingüe con dos positivos y dos negativos deliberadamente pareados:

### Positivos humanos

1. **AMI ES2012d — inglés**
   - intento interrumpido;
   - `I mean`;
   - reformulación;
   - esperado: `explicit_correction → REVIEW`.

2. **CORMA — español**
   - fragmento abandonado `dee-`;
   - `Perdón`;
   - reformulación;
   - esperado: `explicit_correction → REVIEW`.

### Negativos humanos

1. **AMI ES2012d**: `I mean` usado como marcador discursivo sin reparación.
2. **CORMA**: `perdón eh` usado como disculpa/inciso, sin autocorrección del contenido posterior.

Provenance/licencias: `Validation/phase2c-semantic-validation-sources.md`.

### Baseline humano bilingüe

Run `33750475437` — SUCCESS:

```text
69 tests PASS en 6.718 s
26 casos
14 eventos esperados
14 TP
2 FP
0 FN
precision 87.50%
recall 100%
F1 93.33%
unsafe proposals 0
decision mismatches 0
executable 0
auto_apply 0
```

El gate `precision >= 0.95 / recall >= 0.95` falló **únicamente por precision**.

Los dos FP fueron exactamente los controles humanos ambiguos:

- `I mean` discursivo;
- `perdón eh` como disculpa/inciso.

No hubo ninguna violación de seguridad.

### Tuneo guiado por el baseline

Sólo se endureció candidate generation en modo Conservador:

#### `I mean` / `quiero decir`

Requiere evidencia local adicional:

- frontera explícita de reparación antes del marcador — guion/token truncado tipo `h-`, `dee-`, etc.; **o**
- sustitución numérica detectable a ambos lados (`veinte → quiero decir → treinta`).

Sin esa evidencia, un uso discursivo de `I mean / quiero decir` no se marca como autocorrección.

#### `perdón` / `perdona` / `sorry`

En Conservador:

- se exige contexto léxico a izquierda y derecha;
- patrón de disculpa seguido de vacilación (`perdón eh ...`) sin intento interrumpido => no correction candidate;
- tras fragmento explícitamente truncado sí permanece `explicit_correction → REVIEW`.

Modo Agresivo mantiene detección más amplia. No se añadió ML ni se modificó semantic decision execution.

### Validación final de 2C.2

Run `33750836791` — **SUCCESS**:

```text
74 tests PASS en 6.729 s
26 casos
14 eventos esperados
14 candidates
FP 0
FN 0
precision 100%
recall 100%
F1 100%
decision mismatches 0
unsafe proposals 0
missing safe proposals 0
executable decisions 0
auto_apply decisions 0
artifacts 0
```

También:

- `video-tunner doctor` PASS;
- E2E FFmpeg/sync PASS;
- workflow restaurado a `workflow_dispatch`;
- marker one-shot eliminado.

## Composición actual de evidencia

Sobre el conjunto combinado de 26 casos:

```text
11 constructed_positive
 6 constructed_negative
 4 human_speech_reference        # controles SpanishPod
 3 human_speech_positive         # AMI retake + AMI correction + CORMA correction
 2 human_speech_negative         # AMI discourse + CORMA apology
14 eventos esperados
```

El **100% sólo vale para este corpus etiquetado**. No generalizar a habla arbitraria.

## Gate v1

```text
precision >= 0.95
recall >= 0.95
unsafe proposals == 0
decision mismatches == 0
missing safe proposals == 0
executable decisions == 0
auto_apply decisions == 0
```

No mover thresholds para acomodar fallos futuros: ampliar corpus y corregir causas.

## Qué demuestra

- el benchmark separa ruido de candidate y fallos de seguridad;
- los tuneos se derivan de FP medidos;
- ya existe evidencia humana positiva y negativa en inglés **y español**;
- `I mean` y `perdón` no se tratan ya como prueba suficiente de autocorrección;
- las correcciones humanas positivas siguen siendo `REVIEW`;
- ninguna semantic decision se vuelve ejecutable.

## Qué NO demuestra

- seguridad general sobre cualquier habla real;
- precisión robusta sobre una muestra grande y diversa;
- que Whisper conserve siempre guiones/truncamientos del transcript manual;
- scope seguro de `intento incorrecto → corrección válida`;
- seguridad de joins;
- que `PROPOSED_CUT` pueda auto-aplicarse.

## Siguiente trabajo dentro de Fase 2C

1. ampliar positivos/negativos humanos, especialmente español y variaciones donde ASR pierda puntuación/truncamientos;
2. seleccionar pocos clips humanos con licencia adecuada para una validación real audio → `large-v3-turbo` → semántica cuando aporte evidencia nueva;
3. medir qué señales sobreviven realmente a Whisper;
4. después resolver scope seguro de correcciones;
5. validar fillers contextuales;
6. añadir límites de frase y join safety;
7. mantener `executable=false` hasta completar la evidencia.
