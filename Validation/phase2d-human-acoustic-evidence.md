# Fase 2D.3.3 — Human-audio Acoustic Join Evidence

Fecha: 2026-09-03.

Estado: **COMPLETADA COMO MICROFASE DE EVIDENCIA HUMANA v1**.

## Objetivo

Validar la capa acústica de joins sobre audio humano real sin volver a ejecutar `large-v3-turbo` ni promover ningún corte.

Se reutilizan endpoints de palabra congelados del run audio-backed real `33755013415` y se aplican las capas actuales de correction scope, join context y acoustic join sobre el WAV original AMI.

```text
AMI real audio
+ frozen large-v3-turbo word endpoints
→ correction scope
→ join assessment
→ acoustic join assessment
```

## Fuente y trazabilidad

Corpus: **AMI Meeting Corpus**, meeting `ES2012d`, `Mix-Headset.wav`.

```text
license  CC BY 4.0
bytes    30388952
sha256   39FCDE566E2D1BC7EC40A31DEC19251CC253AAC54BE94713E68EEA3008AF4F8D
ASR run  33755013415
model    large-v3-turbo
```

El audio se descarga únicamente a `RUNNER_TEMP`. No se versiona ni se publica como artifact.

El validador comprueba tamaño y SHA-256 antes de usar la señal.

## Casos

Tres controles derivados de habla humana real:

1. `ami-human-pause-control-0311`
   - join contextual ordinario;
   - debe producir una medición acústica real;
   - no debe autorizar corte.
2. `ami-human-retake-protected-0311`
   - retake humano;
   - `repair_or_protected_context_risk`;
   - acústica debe permanecer `blocked_by_context`.
3. `ami-human-correction-ambiguous-0250`
   - correction humana `I mean`;
   - scope `ambiguous`;
   - join `invalid_or_unbounded_target`;
   - acústica debe permanecer `blocked_by_context`.

## Run 33782959293

**SUCCESS**.

Regresión completa:

```text
134/134 tests PASS en 6.803 s
FFmpeg/sync E2E PASS
human fixture contract PASS
```

Gate humano:

```text
cases                 3
failures              0
measured_cases        1
blocked_cases         2
automatic_edits       0
executable            0
auto_apply            0
HUMAN_ACOUSTIC_GATE   PASS
artifacts              0
```

Checks:

```text
all_cases_evaluated        true
at_least_one_real_measurement true
context_blocks_preserved   true
no_contract_failures       true
non_executable             true
```

## Medición humana real

Caso `ami-human-pause-control-0311`:

```text
status                    acoustic_context_only
sample_rate               16000 Hz
left/right window          1280 samples = 80 ms
left RMS                  -35.9051 dBFS
right RMS                 -30.9682 dBFS
RMS delta                   4.9369 dB
left edge RMS             -38.3848 dBFS
right edge RMS            -37.2891 dBFS
left peak                   0.050354
right peak                  0.088837
boundary sample jump        0.030243
boundary jump ratio         0.340433
safe_for_cut                false
executable                  false
auto_apply                  false
```

Con thresholds v1, la señal no activa riesgo de nivel ni waveform. Esto sólo significa **ausencia de las discontinuidades v1 medidas**; no demuestra calidad perceptual ni permiso semántico para cortar.

## Bloqueos humanos preservados

### Retake

```text
join_status      repair_or_protected_context_risk
acoustic_status  blocked_by_context
measurement      false
```

La capa acústica no intenta rescatar un join ya bloqueado por contexto de reparación.

### Correction ambigua

```text
scope_status     ambiguous
join_status      invalid_or_unbounded_target
acoustic_status  blocked_by_context
measurement      false
```

Un scope ambiguo sigue siendo un bloqueo anterior a acústica.

## Qué demuestra

- los endpoints reales congelados de `large-v3-turbo` pueden reconstruirse de forma trazable sobre el WAV humano original;
- la capa puede medir una ventana humana real con los thresholds v1 sin cambiar esos thresholds;
- los bloqueos semánticos/contextuales sobreviven a la existencia de una capa acústica posterior;
- `acoustic_context_only` no se convierte en `safe_for_cut`;
- no se habilita Edit Plan, ejecución ni auto-apply.

## Qué NO demuestra

- seguridad general de los thresholds sobre habla arbitraria;
- ausencia universal de click/pop;
- continuidad espectral o prosódica;
- calidad perceptual tras hard concat;
- suficiencia de una única medición humana positiva;
- que cualquier clase sea apta todavía para auto-apply.

## Decisión

No modificar thresholds v1 a partir de este run.

La siguiente microfase debe diseñar y validar una **política combinada de elegibilidad/promoción** que trate semántica, scope, fillers, join context y acoustics como guardas acumulativas, todavía sin ejecutar cortes. El `removedText` definitivo también debe formar parte de esa validación.
