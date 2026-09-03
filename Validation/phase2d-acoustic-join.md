# Phase 2D.3.2 — Acoustic Join Validation Foundation v1

## Objetivo

Añadir evidencia acústica real a los joins hipotéticos ya acotados por 2D.3.1, usando exactamente el **master audio acreditado** de la timeline.

Esta capa no decide si un contenido debe borrarse y no convierte ningún candidate en edit.

```text
candidate
→ correction/filler evidence
→ join context assessment
→ acoustic join assessment
→ future promotion policy
→ future approved Edit Plan
```

Invariante:

```text
acoustic context != semantic permission to cut
safe_for_cut = false
executable = false
auto_apply = false
automatic_edits = 0
```

## Arquitectura

Módulo: `Source/video_tunner/acoustic_join.py`.

Para evitar decodificar el mismo vídeo una vez por candidate:

1. el master audio se decodifica **una sola vez** mediante el FFmpeg resuelto por Video_Tunner;
2. salida temporal: PCM16 mono a 16 kHz;
3. el PCM temporal se abre mediante NumPy `memmap`;
4. cada join elegible lee sólo sus ventanas locales;
5. el PCM temporal se elimina al terminar.

No se almacena ni sube audio como artifact.

Sólo se mide un join cuyo assessment previo sea:

```text
join_context_only
```

Cualquier join ya bloqueado por semántica/timeline/segmentación/reparación recibe:

```text
blocked_by_context
```

y no necesita decode acústico.

## Ventanas y métricas v1

```text
sample_rate                   16000 Hz
edge_window                   80 ms por lado
edge_micro_window             12 ms por lado
```

Se registran:

```text
left_rms_dbfs
right_rms_dbfs
rms_delta_db
left_edge_rms_dbfs
right_edge_rms_dbfs
left_peak
right_peak
boundary_sample_jump
boundary_jump_ratio
```

## Thresholds conservadores v1

```text
SILENCE_DBFS                 = -42.0 dBFS
MAX_RMS_DELTA_DB             = 12.0 dB
MAX_BOUNDARY_SAMPLE_JUMP     = 0.35
MAX_BOUNDARY_JUMP_RATIO      = 1.25
```

No se movió ningún threshold para hacer pasar el benchmark.

## Estados v1

```text
blocked_by_context
insufficient_audio_context
low_energy_boundary_context
level_discontinuity_risk
waveform_discontinuity_risk
combined_discontinuity_risk
acoustic_context_only
```

Interpretación:

- `blocked_by_context`: una capa anterior ya detectó un riesgo; no se intenta sobreescribirla con acústica favorable;
- `insufficient_audio_context`: no hay ventanas bilaterales válidas;
- `low_energy_boundary_context`: ambos bordes son de energía muy baja;
- `level_discontinuity_risk`: diferencia RMS superior al threshold;
- `waveform_discontinuity_risk`: salto instantáneo conservador en el punto de unión;
- `combined_discontinuity_risk`: se activan ambas guardas;
- `acoustic_context_only`: no se activa una guarda v1, pero **no** significa safe-for-cut.

## Benchmark etiquetado

Fixture:

`tests/fixtures/acoustic_join_v1.json`

11 casos reproducibles:

- señal continua;
- baja energía;
- salto de nivel;
- salto duro de waveform;
- riesgo combinado;
- delta de nivel sub-threshold;
- salto pequeño sub-threshold;
- step de muy baja energía;
- ventana bilateral insuficiente;
- bloqueo por contexto léxico;
- bloqueo por repair context.

Harness:

`Source/video_tunner/acoustic_join_validation.py`

Gate:

```text
status_mismatches == 0
status_accuracy == 1.0
measurement_mismatches == 0
risk_recall == 1.0
safety_violations == 0
```

El benchmark usa el mismo `assess_join_edge_samples(...)` que producción para evitar una lógica paralela de validación.

## Evidencia con decode real

`tests/test_acoustic_join.py` incluye tests que generan WAV temporal y pasan por el decode real de FFmpeg:

1. master continuo → `acoustic_context_only`;
2. master con diferencia fuerte de nivel → riesgo de discontinuidad;
3. join demasiado próximo al borde del audio → `insufficient_audio_context`.

No se usa un fichero fake como falsa prueba de waveform en los tests de integración del pipeline: esos tests mockean sólo la capa acústica y verifican el wiring. El decode real está cubierto por los tests anteriores.

## CI

### Foundation

Run `33781430382`:

```text
131 tests PASS en 6.998 s
acoustic benchmark gate PASS
real FFmpeg/PCM join tests PASS
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

### Final — schema v7 + pipeline integration

Run `33781903986`:

```text
131 tests PASS en 7.401 s
acoustic benchmark gate PASS
real FFmpeg/PCM join tests PASS
schema v7 pipeline integration PASS
same accredited master wired into acoustic join layer
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

## `analysis.json` schema v7

Nueva separación:

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
acoustic_join_assessments[]
semantic_decisions[]
```

Flags:

```text
acoustic_join_assessments_are_not_edits = true
acoustic_join_assessments_executable = false
acoustic_join_assessments_safe_for_cut = false
join_acoustic_validation_enabled = true
join_acoustic_validation_is_not_cut_authorization = true
```

## Lo que esta foundation NO demuestra

Todavía no se acredita:

- calidad perceptual universal de un hard join;
- continuidad espectral/tímbrica;
- integridad fonética más allá de las protecciones temporales existentes;
- selección de zero crossing óptimo;
- crossfades/fades;
- continuidad prosódica;
- calidad sobre habla humana arbitraria;
- ausencia universal de click/pop después del render;
- promoción automática al Edit Plan.

Por tanto:

```text
acoustic_context_only != safe_for_cut
low_energy_boundary_context != safe_for_cut
```

## Siguiente evidencia recomendada

Antes de cerrar todo 2D y plantear promoción al Edit Plan:

1. ejecutar la capa acústica sobre joins derivados de **audio humano real** ya trazable;
2. observar falsos positivos/falsos negativos de los thresholds v1;
3. no ajustar thresholds sin evidencia medida;
4. después definir `removedText` definitivo + política combinada semántica/timeline/acústica;
5. dejar el tratamiento perceptual del join y la verificación post-render para la fase correspondiente.
