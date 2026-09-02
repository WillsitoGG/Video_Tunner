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

ML frozen run `33621357438` PASS:

- faster-whisper 1.2.1;
- CTranslate2 4.8.1;
- ONNX Runtime 1.29.0;
- tokenizers 0.23.1;
- PyAV 18.1.0;
- Silero V6 ONNX;
- inferencia offline con modelo local;
- PyInstaller `onedir` aceptado como base provisional.

## Fase 1B — Ingesta dual + sincronización A/V — EN CURSO

### 1B.1 Contrato de ingesta — IMPLEMENTADO

```text
A) video + embedded audio → master audio
B) video + external audio → sync → external synchronized master audio
```

`ingest.json` registra fuentes, SHA-256, timeline, método, sync, coverage, master y warnings.

### 1B.2 Auto-sync offset — IMPLEMENTADO / FOUNDATION PASS

Backend propio:

- referencia mono 8 kHz;
- envolvente log-RMS 50 Hz;
- ZNCC coarse;
- 7 anchors fine multi-window;
- offset positivo/negativo;
- confidence;
- outlier rejection por MAD.

Convención:

```text
video_time = offset_seconds + time_scale * external_time
```

### 1B.3 Manual fallback — IMPLEMENTADO

- `--audio` opcional;
- `--offset` manual;
- `--drift-ppm` manual;
- sin referencia suficiente => REVIEW/no master;
- sin audio de cámara => no auto-sync, requiere override.

### 1B.4 Drift — IMPLEMENTADO EN ESTIMADOR / HARDENING E2E PENDIENTE

- ajuste lineal multi-anchor;
- `time_scale`;
- drift ppm;
- residual RMS;
- corrección temporal mediante `atempo`;
- preservación de pitch inherente al filtro tempo.

Tests sintéticos recuperan drift conocido, pero falta E2E Windows con drift aplicado a media real.

### 1B.5 Master timeline — FOUNDATION PASS

El master externo se materializa como FLAC 48 kHz.

Tras descubrir en runs #1/#2 un problema real de duración por timestamps FFmpeg, la cadena fue endurecida con:

- `asetpts=N/SR/TB`;
- `apad=whole_dur`;
- `atrim=duration`;
- límite `-t`.

Run final `33634775313` — SUCCESS:

- 33 tests PASS;
- offset `+1.500 s` recuperado exactamente;
- confidence `1.000`;
- 7 anchors;
- drift `0 ppm`;
- vídeo/master `90.000 / 90.000 s`;
- 0 artifacts.

Ver `Validation/sync-foundation-spike.md`.

### 1B.6 Hardening restante

Antes de cerrar Fase 1B:

- E2E offset negativo;
- E2E drift conocido;
- baja señal/ambigüedad => REVIEW;
- manual override E2E;
- external shorter/longer y coverage;
- niveles/ruido/mics diferentes;
- confirmar política de embedded audio con timeline no trivial;
- post-sync residual validation;
- rutas con espacios ya demostradas en el caso foundation.

### Cierre 1B

No marcar COMPLETADA hasta que el hardening anterior demuestre que sync no sólo funciona en el caso positivo nominal, sino que falla de forma segura en casos ambiguos.

## Fase 1C — Transcripción + VAD sobre master audio

Parte del código ya existe. Falta:

- adaptar `analyze` a master audio;
- mantener video timeline como referencia de timestamps;
- `large-v3-turbo` como modelo objetivo;
- word timestamps + TXT/JSON/SRT;
- Silero VAD ONNX;
- validación real en español;
- medir calidad/velocidad/model size.

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

1. Hardening restante de Fase 1B.
2. Cerrar sync/master audio con evidencia segura.
3. Adaptar `analyze` al master audio.
4. Validar `large-v3-turbo` + VAD sobre vídeo hablado real en español.
5. Entrar en Fase 2 semántica.
