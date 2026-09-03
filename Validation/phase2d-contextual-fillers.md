# Fase 2D.2 — Fillers contextuales

Fecha: 2026-09-03.

Estado: **COMPLETADA COMO FOUNDATION v1; NO HABILITA CORTES**.

## Objetivo

Separar la detección superficial de una vacilación vocal de la evaluación contextual necesaria antes de considerar cualquier eliminación:

```text
possible_filler candidate
!= contextual filler assessment
!= semantic decision
!= edit
```

Un token como `eh`, `um` o `uh` no es por sí solo prueba de que pueda borrarse sin afectar naturalidad, reparación del habla o estructura prosódica.

## Implementación

Módulos:

```text
Source/video_tunner/filler_context.py
Source/video_tunner/filler_context_validation.py
Source/video_tunner/filler_context_report.py
```

Fixture:

```text
tests/fixtures/filler_context_v1.json
```

Tests:

```text
tests/test_filler_context.py
tests/test_filler_context_validation.py
```

Estados v1:

```text
isolated_hesitation
hesitation_cluster
protected_repair_context
boundary_hesitation
uncertain_asr
invalid
```

Todos los assessments mantienen:

```text
safe_for_cut = false
executable = false
auto_apply = false
```

## Reglas conservadoras v1

### `protected_repair_context`

Si el filler solapa o está inmediatamente junto a un `possible_retake` o `explicit_correction`, queda protegido como parte del evento de reparación. No se evalúa como token aislado.

### `hesitation_cluster`

Dos o más fillers adyacentes se consideran un cluster y no deben cortarse token a token de forma independiente.

### `boundary_hesitation`

Un filler en el inicio/final del transcript o junto a una pausa amplia se conserva para revisión porque puede formar parte del ritmo, frontera de frase o turno.

Threshold temporal v1:

```text
BOUNDARY_GAP_SECONDS = 0.60
```

### `uncertain_asr`

Un filler con evidencia ASR insuficiente no se evalúa como eliminable.

Threshold v1:

```text
LOW_ASR_PROBABILITY = 0.60
```

### `isolated_hesitation`

Un filler aislado, con contexto léxico a ambos lados y probabilidad ASR suficiente, se etiqueta sólo como señal contextual. **Sigue sin ser safe-for-cut** hasta disponer de sentence/join safety.

## Benchmark v1

El corpus contiene 15 casos y cubre:

- fillers aislados ES/EN;
- clusters ES/EN;
- fillers dentro de retakes/correcciones;
- filler humano real del retake AMI ya trazado en 2C;
- ASR de baja confianza;
- boundaries al inicio/final;
- pausas amplias antes/después;
- controles sin filler;
- control humano SpanishPod sin filler.

El gate exige:

```text
record_count_mismatches == 0
status_mismatches == 0
status_accuracy == 1.0
repair_link_mismatches == 0
repair_protection_recall == 1.0
safety_violations == 0
```

## Evidencia CI

### Run 33771489008 — benchmark/context foundation

```text
101/101 tests PASS en 7.030 s
filler context benchmark PASS
human AMI retake filler protected
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

### Run 33771792867 — final schema v5 integration

```text
101/101 tests PASS en 5.031 s
analysis schema v5 integration PASS
filler_assessments[] PASS
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

## `analysis.json` schema v5

La nueva capa queda explícitamente separada:

```text
candidates[]
correction_scopes[]
filler_assessments[]
semantic_decisions[]
```

Safety flags añadidos:

```text
filler_assessments_are_not_edits = true
filler_assessments_executable = false
filler_assessments_safe_for_cut = false
```

## Evidencia humana y limitación ASR

El fixture humano AMI manual:

```text
have a look at the uh th- have a look at the prototypes
```

produce un `possible_filler` para `uh` que queda correctamente enlazado al `possible_retake` como `protected_repair_context`.

Sin embargo, el run audio-backed real de 2C.3 (`33755013415`) mostró que `large-v3-turbo` puede omitir esa vacilación y transcribir aproximadamente:

```text
have a look at the have a look at the prototypes
```

Por tanto:

```text
filler_context v1 clasifica fillers que sobreviven al ASR
!= detector de fillers omitidos por Whisper
```

No se debe inventar un filler ausente del transcript. La seguridad frente a esa pérdida se mantiene en las otras capas: el retake colapsado por ASR continúa `REVIEW` gracias a la protección temporal de repetición.

## Qué demuestra

- existe una capa contextual independiente para `possible_filler`;
- fillers dentro de reparaciones quedan protegidos;
- clusters y boundaries no se tratan como tokens aislados;
- baja confianza ASR hace fail-safe;
- el benchmark v1 es exacto para sus 15 casos;
- `analysis.json` registra la evidencia sin crear edits;
- ninguna clase de filler es todavía ejecutable.

## Qué NO demuestra

- que `isolated_hesitation` sea seguro de eliminar;
- seguridad acústica del join resultante;
- naturalidad prosódica después del corte;
- detección de fillers que Whisper omite;
- robustez universal fuera del corpus v1;
- autorización para promoción al Edit Plan.

## Siguiente

Fase 2D.3:

1. sentence/turn boundaries;
2. join safety temporal y acústica;
3. removedText exacto;
4. guardas contra joins antinaturales o semánticamente peligrosos;
5. mantener `safe_for_cut=false`, `executable=false` y `auto_apply=false` hasta superar el gate correspondiente.
