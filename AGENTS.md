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
- Fase 1B sync foundation implementada y validada en caso nominal positivo.

Fase 1B sigue **EN CURSO** hasta hardening de negativos, drift E2E, ambigüedad, manual y coverage.

## 3. Evidencia portable

Core run `33600174568`: PASS.

ML run `33621357438`: PASS con faster-whisper 1.2.1, CTranslate2 4.8.1, ONNX Runtime 1.29.0, tokenizers 0.23.1, PyAV 18.1.0 y Silero V6 ONNX. Inferencia frozen/offline con modelo local PASS.

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

Modelo objetivo: `large-v3-turbo`. `tiny` sólo fue fixture de runtime.

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

## 6. Fase 1B — ingesta/sync

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

### Auto-sync actual

`sync.py`:

1. FFmpeg → audio mono 8 kHz;
2. log-RMS envelope 50 Hz;
3. coarse ZNCC ~10 Hz;
4. fine anchors en 7 ventanas;
5. fit `video = intercept + scale * external`;
6. outliers por MAD;
7. confidence por score, uniqueness, residual y anchor count.

`SyncEstimate` registra:

- offset;
- time_scale;
- drift_ppm;
- confidence;
- residual_rms;
- coarse offset/score;
- anchors con score/margin/residual.

### Política de aceptación

Actual:

```text
confidence >= 0.65
anchors >= 3
residual RMS <= 0.08 s
abs(drift) <= 2000 ppm
coverage >= 0.98
uncovered edge <= 5 s
```

Son thresholds provisionales que requieren datos reales antes de Release.

Evidence insuficiente => `review_required`, sin master.

Sin audio de cámara => no auto-sync; requiere offset manual.

Manual override puede aceptar coverage parcial, pero huecos son silencio; **no mezclar camera audio implícitamente**.

### Master audio

Output:

```text
<stem>_master_audio.flac
<stem>_ingest.json
```

External master:

- drift con `atempo=1/time_scale`;
- PTS regenerados con `asetpts=N/SR/TB`;
- positivo => `adelay`;
- negativo => `atrim`;
- `apad=whole_dur=video_duration`;
- `atrim=duration=video_duration`;
- `-t video_duration`;
- FLAC 48 kHz.

No volver a usar `apad` indefinido + `atrim` timestamp-only: produjo masters cortos aunque el sync fuese correcto.

### Evidencia sync

Runs:

- `33633846344` failure de aserción inicial;
- `33634121264` failure útil: vídeo 90 s, master 88.756 s;
- `33634775313` SUCCESS tras fix.

Run final:

- 33 tests PASS;
- +1.500 s recuperado exactamente;
- confidence 1.000;
- 7 anchors;
- drift 0 ppm;
- video/master 90/90 s;
- 0 artifacts.

Ver `Validation/sync-foundation-spike.md`.

### Hardening restante 1B

Obligatorio antes de cerrar:

- negative offset E2E;
- drift E2E;
- low/ambiguous signal => REVIEW;
- manual override E2E;
- external shorter/longer;
- acoustic mismatch/noise;
- embedded timeline no trivial;
- post-sync residual validation.

## 7. Transcripción / candidates

`analyze` todavía toma audio embebido del vídeo. No migrar semántica antes de adaptar a master audio tras hardening de 1B.

Artefactos actuales:

- transcript JSON/TXT;
- SRT;
- analysis JSON.

Candidates actuales: pause + possible_filler, siempre `undecided`, `auto_apply=false`.

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

1. hardening Fase 1B;
2. cerrar master/sync con casos negativos y failure-safe;
3. adaptar `analyze` al master audio;
4. validar `large-v3-turbo`/VAD en español;
5. Fase 2 semantic cleaner.

## 13. Changelog técnico

### bootstrap
CLI, tools, silence Cleaner, Edit Plan, render.

### analysis layer
Word timestamps, transcript artifacts, Silero VAD, candidates.

### portable core/ML
PyInstaller onedir, local tools/models, offline frozen inference Windows PASS.

### sync foundation
Dual ingest, multi-anchor offset/drift estimator, confidence/coverage policy, manual override, master FLAC e ingest audit; Windows nominal +1.5 s PASS after master-timeline regression fix.
