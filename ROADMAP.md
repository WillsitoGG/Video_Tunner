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

Foundation run `33634775313` — SUCCESS tras corregir un bug real de timestamps/padding.

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

## Fase 1C — Transcripción + VAD sobre master audio — EN CURSO / INTEGRACIÓN TÉCNICA PASS

### Integración completada

`analyze` ya trabaja sobre master audio y no presupone audio embebido directo.

Puede:

- resolver master embebido mediante `ingest`;
- resolver audio externo mediante auto-sync;
- aceptar override manual;
- reutilizar un master pre-resuelto sólo junto con su `ingest.json`;
- verificar SHA-256 de procedencia antes de reutilizarlo.

Whisper y Silero VAD reciben exactamente el mismo master. Todos los timestamps permanecen en timeline de vídeo.

El master embebido también preserva offsets internos de la pista y se pad/trim hasta la duración exacta del vídeo.

### Evidencia portable

Run `33640872486` — **SUCCESS a la primera**:

- 41 tests PASS;
- build frozen analysis PASS;
- NumPy + stack ML + Silero ONNX operativos sin Python/FFmpeg externos en PATH;
- inferencia posterior con `HF_HUB_OFFLINE=1`;
- embedded retrasado: 89 palabras, 11 pause candidates, vídeo/master `45.6 / 45.6 s`;
- external auto-sync: 88 palabras, 9 pause candidates;
- offset real `+0.500 s` → estimado `+0.49581 s`;
- confidence `1.0`;
- drift estimado `192.308 ppm`;
- vídeo/master external `44.58275 / 44.58275 s`;
- automatic edits `0`;
- artifacts `0`.

Ver `Validation/master-audio-analysis-spike.md`.

### Pendiente para cerrar Fase 1C

1. validar `large-v3-turbo` con contenido hablado real en español;
2. medir precisión cualitativa de transcripción y word timestamps;
3. medir velocidad CPU, RAM y tamaño real del modelo;
4. revisar parámetros Whisper/VAD sobre ese contenido;
5. confirmar que el coste portable del modelo objetivo es aceptable;
6. cerrar Fase 1C sin introducir auto-apply.

## Fase 2 — Cleaner inteligente

Retomas, repeticiones, correcciones, muletillas contextuales, KEEP/TRIM/CUT/REVIEW, protección semántica y modos Conservador/Agresivo.

## Fase 3 — Calidad audiovisual / auditoría

Normalización, joins, denoise controlado, removedText, join audit, post-render verification, informe y rendimiento.

## Fase 4 — UX mínima

Seleccionar vídeo, audio externo opcional, confirmar sync, analizar, revisar, renderizar y abrir outputs. CLI se mantiene para tests/automation.

## Fase 5 — Portable Release Hardening

Build Windows limpia, ZIP final, versiones/digests inmutables, optimización de bundle, estrategia final de modelos, SHA-256, manifest, notices/licencias y zero-install/offline.

## Fase 6 — Extras

Subtítulos visuales, reframe, zooms, shorts, B-roll y otras funciones después del Cleaner fiable.

## Orden inmediato

1. Validar `large-v3-turbo` con español real.
2. Medir calidad, word timestamps, velocidad, RAM y tamaño.
3. Cerrar Fase 1C.
4. Entrar en Fase 2 semántica.
