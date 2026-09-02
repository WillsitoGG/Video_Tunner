# AGENTS.md — Video_Tunner

Contexto técnico permanente para agentes. Referencia maestra externa vigente: `00.Contexto y Reglas de Trabajo_GitHub_Video_Tunner_v3`.

## 1. Invariantes

Video_Tunner debe producir vídeo hablado limpio, natural, fiel, sincronizado, auditable y reversible en Windows 10/11 x64.

Obligatorio:

1. portable real: ZIP → descomprimir → ejecutar;
2. vídeo con audio embebido o vídeo + audio externo;
3. master audio antes de análisis temporal;
4. auto-sync sólo con evidence/confidence suficiente;
5. offset manual/override;
6. drift corregido sólo tras validación;
7. originales intactos;
8. candidate ≠ decision ≠ edit;
9. ante duda: KEEP/REVIEW.

```text
sources → ingest/sync → MASTER AUDIO + timeline → analysis → candidates → decisions → Edit Plan → render → audit
```

## 2. Estado

Versión `0.1.0-dev`.

Completado:

- Fase 0 bootstrap;
- Fase 0.5 technology harvest;
- Cleaner de silencios + Edit Plan + render;
- transcript TXT/JSON/SRT word-level;
- Candidate Analysis review-only;
- Fase 1A Portable Foundation core + ML PASS Windows;
- Fase 1B dual ingest + master audio + sync/drift COMPLETADA y hardening Windows PASS;
- Fase 1C integración técnica de `analyze` sobre master audio PASS en portable Windows.

Pendiente inmediato de 1C: **validar `large-v3-turbo` sobre contenido real en español y medir calidad/rendimiento/tamaño**.

## 3. Evidencia portable

Core run `33600174568`: PASS.

ML run `33621357438`: PASS con faster-whisper 1.2.1, CTranslate2 4.8.1, ONNX Runtime 1.29.0, tokenizers 0.23.1, PyAV 18.1.0 y Silero V6 ONNX. Inferencia frozen/offline con modelo local PASS.

Master-audio analysis run `33640872486`: PASS con 41 tests, frozen portable, Whisper/VAD sobre master embebido y externo sincronizado y 0 artifacts.

PyInstaller `onedir` continúa como base provisional. No evaluar Nuitka sin problema/ventaja medible.

## 4. Stack de análisis

Pins:

```text
faster-whisper 1.2.1
CTranslate2 4.8.1
ONNX Runtime 1.29.0
tokenizers 0.23.1
NumPy 2.5.2
PyInstaller 6.22.2
```

VAD usa faster-whisper + `silero_vad_v6.onnx`; no standalone Torch sin nueva evidencia.

Modelo objetivo: `large-v3-turbo`. `tiny` sólo es fixture barato de runtime/CI.

## 5. Portable / modelos

```text
Video_Tunner/
├── Video_Tunner.exe
├── _internal/
├── Tools/ffmpeg/bin/
├── Models/whisper/
├── Config/
├── Temp/
├── Cache/
├── Logs/
├── Output/
└── portable-manifest.json
```

Frozen => portable strict. Sin fallback silencioso a PATH o cache global.

Modelo completo mínimo:

- config.json;
- model.bin;
- tokenizer.json.

CLI:

```text
video-tunner model status MODEL
video-tunner model fetch MODEL [--replace]
```

## 6. Fase 1B — ingesta/sync — COMPLETADA

### Contrato temporal

```text
video_time = offset_seconds + time_scale * external_time
```

- offset > 0: externo empieza después del vídeo;
- offset < 0: externo empieza antes;
- drift ppm = `(time_scale - 1) * 1e6`.

Esta convención no debe reinterpretarse en otros módulos.

### CLI

```text
video-tunner ingest VIDEO [--audio EXTERNAL] [--offset SEC] [--drift-ppm PPM] [--output-dir DIR]
```

### Auto-sync

`sync.py`:

1. FFmpeg → audio mono 8 kHz;
2. log-RMS envelope 50 Hz;
3. coarse ZNCC;
4. fine anchors multi-window;
5. fit `video = intercept + scale * external`;
6. outliers por MAD;
7. confidence por score, uniqueness, residual y anchor count.

Política actual:

```text
confidence >= 0.65
anchors >= 3
residual RMS <= 0.08 s
abs(drift) <= 2000 ppm
coverage >= 0.98
uncovered edge <= 5 s
```

Thresholds provisionales hasta corpus real.

Evidencia insuficiente => `review_required`, sin master. Sin audio de cámara => no auto-sync; requiere offset manual. Manual override puede aceptar coverage parcial, pero huecos son silencio y nunca mezcla implícita de camera audio.

### Master audio

Output:

```text
<stem>_master_audio.flac
<stem>_ingest.json
```

External master: drift con `atempo`, PTS regenerados, delay/trim según offset, pad/trim y duración final exacta de vídeo.

Embedded master: `aresample=async=1:first_pts=0` preserva el offset temporal de la pista y luego pad/trim alinea el master con toda la timeline del vídeo.

### Evidencia

Foundation `33634775313` PASS tras fix de timeline.

Hardening `33639009841` PASS:

- 37 tests;
- negative offset;
- media-level drift;
- low/flat signal => REVIEW;
- manual override sin camera audio;
- partial coverage;
- 0 artifacts.

Ver `Validation/sync-foundation-spike.md` y `Validation/sync-hardening.md`.

## 7. Fase 1C — transcripción/VAD sobre master audio — INTEGRACIÓN TÉCNICA PASS

### Contrato actual de `analyze`

`analyze` siempre trabaja sobre un master audio acreditado.

Puede:

1. resolver master embebido mediante `ingest`;
2. resolver audio externo mediante auto-sync;
3. usar override manual de offset/drift;
4. reutilizar un master pre-resuelto sólo si se proporciona su `ingest.json`.

Reglas obligatorias:

- Whisper y Silero VAD consumen exactamente el mismo master;
- timestamps de transcript/VAD/candidates permanecen en timeline de vídeo;
- un master pre-resuelto exige provenance de ingest;
- SHA-256 del vídeo debe coincidir con el registrado en `ingest.json`;
- si ingest devuelve `review_required`, no se inicia Whisper ni VAD;
- `analysis.json` schema v2 registra master + ingest provenance;
- candidates siguen `undecided` y `auto_apply=false`.

### Evidencia Windows portable

Run `33640872486` — SUCCESS a la primera:

- 41 tests PASS;
- build frozen analysis PASS;
- NumPy + stack ML + Silero ONNX operativos sin Python/FFmpeg externos en PATH;
- inferencia con `HF_HUB_OFFLINE=1`;
- embedded retrasado: 89 palabras, 11 pause candidates, vídeo/master 45.6/45.6 s;
- external auto-sync: 88 palabras, 9 pause candidates;
- offset real +0.500 s → estimado +0.49581 s;
- confidence 1.0;
- drift estimado 192.308 ppm;
- vídeo/master external 44.58275/44.58275 s;
- 0 automatic edits;
- 0 artifacts.

Ver `Validation/master-audio-analysis-spike.md`.

### Pendiente para cerrar 1C

- `large-v3-turbo` con contenido hablado real en español;
- calidad cualitativa y word timestamps;
- tiempo de inferencia CPU;
- RAM pico;
- tamaño del modelo local;
- revisar configuración Whisper/VAD con ese fixture.

## 8. Edit Plan / render

Edit Plan contiene ediciones efectivas, no candidates sin decision layer.

Renderer: merge overlaps, trim/atrim+concat, H.264/AAC, no overwrite, abort si elimina todo.

Pendiente futuro: source hash, removedText, join audit, edge fades, loudness y post-render verification.

## 9. Technology harvest

Video_Tunner NO es fork.

Principales referencias: Railly/vcut, Cadence-Lab, ai-video-editor, SYSTRAN/faster-whisper. Ver `UPSTREAM_SOURCES.md`.

Antes de copiar: licencia + commit + razón. Preferir API pública o reimplementación propia.

## 10. GitHub / cuota

GitHub = source of truth.

- heavy CI deliberada;
- workflows pesados manual-only normalmente;
- no polling frecuente;
- cancelar obsolete;
- no modelos/vídeos/ZIPs como artifacts ordinarios;
- evidence ligera en `Validation/`;
- no Release sin autorización expresa.

El conector no expone `workflow_dispatch`. Procedimiento excepcional one-shot:

1. push temporal limitado a marker path;
2. crear marker una vez;
3. confirmar un run;
4. restaurar manual-only inmediatamente;
5. borrar marker;
6. verificar que no aparece run extra.

No usar como trigger normal.

## 11. Repo / docs

No versionar builds, binarios, modelos, vídeos, caches, outputs ni ZIPs.

Cambios de arquitectura/dependencias/build/validación => README + AGENTS sincronizados.

- `ROADMAP.md`: planificación;
- `UPSTREAM_SOURCES.md`: provenance;
- `Validation/`: evidencia;
- `Archive/`: releases publicadas sustituidas.

## 12. Orden inmediato

1. validar `large-v3-turbo` en español real;
2. medir calidad, timestamps, velocidad, RAM y tamaño;
3. cerrar Fase 1C;
4. Fase 2 semantic cleaner.

## 13. Changelog técnico

### bootstrap
CLI, tools, silence Cleaner, Edit Plan, render.

### analysis layer
Word timestamps, transcript artifacts, Silero VAD, candidates.

### portable core/ML
PyInstaller onedir, local tools/models, offline frozen inference Windows PASS.

### sync foundation + hardening
Dual ingest, multi-anchor offset/drift estimator, confidence/coverage policy, manual override, failure-safe review y master FLAC alineado.

### master-audio analysis
`analyze` resuelve o verifica master audio, preserva provenance, bloquea analysis si sync exige revisión y usa el mismo master para Whisper + VAD; portable Windows PASS.
