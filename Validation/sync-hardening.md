# Fase 1B — Sync Hardening

Fecha: 2026-09-02

## Objetivo

Cerrar Fase 1B demostrando que la ingesta/sincronización no sólo funciona en el caso nominal positivo, sino también con offset negativo, drift real, ausencia de referencia útil y override manual.

## Ejecución

Workflow: `Sync Foundation Spike`

Run: `33639009841`

Resultado: **SUCCESS**

Artifacts almacenados: **0**

El workflow fue armado temporalmente con un trigger limitado a `Validation/sync-hardening.trigger`. Tras confirmar exactamente un run, volvió a `workflow_dispatch` y el marker fue eliminado. No quedó trigger automático permanente.

## Suite

**37 tests PASS** en Windows.

Hardening E2E añadido:

1. offset negativo real:
   - grabador externo empieza antes del vídeo;
   - auto-sync debe recuperar offset negativo;
   - confidence >= 0.65;
   - >=3 anchors;
   - master final debe coincidir con la duración de la timeline del vídeo.

2. drift a nivel de media:
   - fixture continuo con `offset = +0.6 s`;
   - `time_scale = 1.001`;
   - drift objetivo `+1000 ppm`;
   - auto-sync debe quedar dentro de tolerancia de ±450 ppm;
   - residual RMS <= 0.08 s;
   - master final debe coincidir con la timeline del vídeo.

3. señal plana/insuficiente:
   - cámara y externo sin información acústica útil;
   - resultado obligatorio: `review_required`;
   - no se materializa master audio;
   - se registran `review_reasons`.

4. override manual sin audio de cámara:
   - vídeo sin pista de audio;
   - audio externo de cobertura parcial;
   - `--offset` manual produce `ready_manual`;
   - coverage aproximada 0.80;
   - warning explícito de cobertura parcial;
   - huecos = silencio, nunca mezcla implícita con cámara;
   - master conserva duración exacta del vídeo.

5. regresión positiva de timeline:
   - se mantiene el test que protege el fix `asetpts + apad=whole_dur + atrim=duration + -t`.

## Fixture nominal adicional del workflow

La comprobación CLI existente volvió a pasar:

- offset esperado/estimado: `+1.500 s / +1.500 s`;
- confidence: `1.000`;
- anchors: `7`;
- drift: `0 ppm`;
- vídeo/master: `90.000 s / 90.000 s`.

## Conclusión

La Fase 1B queda **COMPLETADA** a nivel de foundation/hardening sintético Windows:

- dual ingest;
- master audio explícito;
- auto-sync positivo/negativo;
- confidence y anchors;
- drift multi-window;
- corrección temporal;
- fallback manual;
- failure-safe ante evidencia insuficiente;
- coverage auditable;
- timeline final consistente.

Los thresholds (`confidence`, residual, drift máximo y coverage) siguen siendo provisionales hasta disponer de un corpus real de grabaciones/cámaras/micrófonos. La validación acústica con material real continuará en fases posteriores, pero ya no bloquea la arquitectura ni la transición de `analyze` al master audio.
