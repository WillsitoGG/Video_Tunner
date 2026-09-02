# ROADMAP — Video_Tunner

## Principios

- Windows 10/11 x64 portable: ZIP → descomprimir → ejecutar.
- Vídeo con audio embebido o vídeo + audio externo.
- Resolver master audio y sincronización antes de transcripción/VAD/semántica.
- Originales intactos y decisiones auditables.
- Ante baja confianza: REVIEW/manual, no adivinar.
- CI pesada sólo cuando aporta evidencia nueva.

## Fase 0 — Bootstrap — COMPLETADA

CLI, FFmpeg/ffprobe, probe, Cleaner de silencios, Edit Plan, render y tests.

## Fase 0.5 — Technology Harvest — COMPLETADA

Repo propio, no fork. Upstreams sólo como referencias/integraciones trazables.

## Fase 1A — Portable Foundation — COMPLETADA

Core Windows run `33600174568` PASS.

ML frozen run `33621357438` PASS con faster-whisper/CTranslate2/ONNX Runtime/Silero VAD ONNX e inferencia offline desde modelo local.

PyInstaller `onedir` queda como base provisional.

## Fase 1B — Ingesta dual + sincronización A/V — COMPLETADA

Contrato:

```text
A) video + embedded audio → master audio
B) video + external audio → sync → external synchronized master audio
```

Convención única:

```text
video_time = offset_seconds + time_scale * external_time
```

Implementado:

- `ingest` CLI;
- master audio FLAC 48 kHz;
- SHA-256 y metadata de fuentes;
- ZNCC coarse + anchors multi-window;
- offset positivo/negativo;
- confidence;
- ajuste lineal de drift;
- residual RMS;
- rejection de outliers por MAD;
- coverage;
- override `--offset` y `--drift-ppm`;
- `review_required` sin master ante evidencia insuficiente;
- sin mezcla implícita de audio de cámara;
- timeline final del master igual a la del vídeo.

Foundation run `33634775313` — SUCCESS tras corregir PTS/padding.

Hardening run `33639009841` — SUCCESS:

- 37 tests PASS;
- negative offset E2E PASS;
- media-level drift +1000 ppm PASS;
- señal plana/insuficiente => REVIEW/no master;
- manual override sin audio de cámara PASS;
- coverage parcial + warning PASS;
- 0 artifacts.

Ver `Validation/sync-foundation-spike.md` y `Validation/sync-hardening.md`.

Thresholds de confidence/residual/drift/coverage siguen provisionales hasta corpus real.

## Fase 1C — Transcripción + VAD sobre master audio — COMPLETADA

### Integración de master audio

`analyze` trabaja siempre sobre master audio acreditado y no presupone audio embebido directo.

Puede:

- resolver master embebido mediante `ingest`;
- resolver audio externo mediante auto-sync;
- aceptar override manual;
- reutilizar un master pre-resuelto sólo junto con su `ingest.json`;
- verificar SHA-256 de procedencia antes de reutilizarlo.

Whisper y Silero VAD reciben exactamente el mismo master. Todos los timestamps permanecen en timeline de vídeo.

El master embebido preserva offsets internos de pista y se pad/trim hasta la duración exacta del vídeo.

Run `33640872486` — **SUCCESS**:

- 41 tests PASS;
- build frozen analysis PASS;
- stack ML + Silero ONNX operativo sin Python/FFmpeg externos en PATH;
- inferencia offline desde modelo local;
- embedded retrasado: 89 palabras, 11 pause candidates, vídeo/master `45.6 / 45.6 s`;
- external auto-sync: 88 palabras, 9 pause candidates;
- offset real `+0.500 s` → estimado `+0.49581 s`;
- confidence `1.0`;
- drift estimado `192.308 ppm`;
- vídeo/master external `44.58275 / 44.58275 s`;
- automatic edits `0`;
- artifacts `0`.

Ver `Validation/master-audio-analysis-spike.md`.

### `large-v3-turbo` + español real

Run definitivo `33656235038` — **SUCCESS**:

- fixture real español: `46.58025 s`;
- 61 palabras de referencia / 62 de hipótesis;
- 1 error a nivel palabra;
- **WER `1.64%`**, frente a criterio predefinido `<= 15%`;
- todos los sanity checks de word timestamps PASS;
- mediana de duración de palabra `0.36 s`;
- `analyze` CPU int8: `22.609 s`;
- **RTF `0.4854`**;
- peak working set: **1818.7 MiB**;
- modelo staged: **1546.5 MiB** (`1621665983` bytes);
- candidates: `16`;
- automatic edits: `0`;
- vídeo/master: `46.58025 / 46.58025 s`;
- artifacts: `0`.

La inferencia se ejecutó con `HF_HUB_OFFLINE=1` desde el modelo local. El snapshot de validación quedó fijado por commit y SHA-256 del `model.bin`.

Los runs `33652410474`, `33653108940`, `33653826702` y `33655947559` fallaron antes de inferencia por adquisición/infraestructura; no son resultados negativos del modelo. Su diagnóstico y correcciones están en `Validation/spanish-large-v3-turbo-plan.md`.

### Cierre

Se cumplen las condiciones definidas para Fase 1C:

1. frozen portable carga `large-v3-turbo` localmente;
2. inferencia offline PASS;
3. calidad textual y sanity temporal PASS;
4. tiempo/RAM/tamaño registrados;
5. candidates continúan separados de decisions/edits.

**Fase 1C cerrada sin introducir auto-apply.**

## Fase 2 — Cleaner inteligente — SIGUIENTE MILESTONE

Objetivo: convertir transcript + VAD + candidates en propuestas semánticas auditables sin sacrificar significado.

Alcance:

- retomas y reinicios de frase;
- repeticiones;
- correcciones/errores hablados;
- muletillas contextuales;
- decision layer `KEEP / TRIM / CUT / REVIEW`;
- protección de negaciones, cifras, sujetos, tiempos verbales y correcciones;
- modos Conservador/Agresivo;
- Conservador por defecto;
- ante incertidumbre, REVIEW;
- no auto-apply hasta disponer de evidencia suficiente.

## Fase 3 — Calidad audiovisual / auditoría

Normalización, joins, denoise controlado, removedText, join audit, post-render verification, informe y rendimiento.

## Fase 4 — UX mínima

Seleccionar vídeo, audio externo opcional, confirmar sync, analizar, revisar, renderizar y abrir outputs. CLI se mantiene para tests/automation.

## Fase 5 — Portable Release Hardening

Build Windows limpia, ZIP final, versiones/digests inmutables, optimización de bundle, estrategia final de modelos, SHA-256, manifest, notices/licencias y zero-install/offline.

## Fase 6 — Extras

Subtítulos visuales, reframe, zooms, shorts, B-roll y otras funciones después del Cleaner fiable.

## Orden inmediato

1. diseñar detector semántico de retomas/repeticiones/correcciones;
2. definir contratos de candidate → decision y protección semántica;
3. implementar primero en modo review-only;
4. validar con fixtures hablados específicos antes de permitir auto-apply;
5. mantener CI pesada sólo para hitos con evidencia nueva.
