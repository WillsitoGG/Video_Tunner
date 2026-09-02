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

### Contrato

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
- correlación coarse ZNCC;
- anchors multi-window;
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

### Foundation Windows

Run `33634775313` — SUCCESS tras detectar y corregir un bug real de timestamps/padding.

- 33 tests PASS;
- offset `+1.500 s` recuperado exactamente;
- confidence `1.000`;
- 7 anchors;
- vídeo/master `90/90 s`;
- 0 artifacts.

### Hardening Windows

Run `33639009841` — **SUCCESS**.

- 37 tests PASS;
- negative offset E2E PASS;
- media-level drift E2E con `+1000 ppm` objetivo PASS dentro de tolerancia;
- señal plana/insuficiente => REVIEW, sin master;
- manual override sin audio de cámara PASS;
- coverage parcial + warning PASS;
- master timeline regression PASS;
- fixture nominal +1.5 s continúa PASS;
- 0 artifacts.

Ver `Validation/sync-foundation-spike.md` y `Validation/sync-hardening.md`.

### Nota de producto

Thresholds actuales de confidence/residual/drift/coverage son provisionales. Deben recalibrarse con corpus real antes de Release, pero ya no bloquean la arquitectura.

## Fase 1C — Transcripción + VAD sobre master audio — SIGUIENTE

Código existente:

- faster-whisper word-level;
- TXT/JSON/SRT;
- Silero VAD ONNX;
- Candidate Analysis review-only.

Trabajo pendiente:

1. hacer que `analyze` consuma master audio en lugar de extraer siempre audio embebido;
2. preservar la timeline del vídeo como referencia de timestamps;
3. integrar `ingest` + `analyze` sin duplicar trabajo/artefactos;
4. validar tanto audio embebido como externo sincronizado;
5. validar `large-v3-turbo` con vídeo hablado real en español;
6. medir calidad/velocidad/model size;
7. mantener candidates sin auto-apply.

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

1. Migrar `analyze` a master audio.
2. Validar pipeline ingest → master → Whisper/VAD/candidates.
3. Validar `large-v3-turbo` en español real.
4. Cerrar Fase 1C.
5. Entrar en Fase 2 semántica.
