# AGENTS.md — Video_Tunner

Contexto técnico permanente para agentes que trabajen en este repositorio. Referencia maestra externa vigente: `00.Contexto y Reglas de Trabajo_GitHub_Video_Tunner_v3`.

## 1. Producto e invariantes

Video_Tunner debe producir vídeo hablado limpio, natural, fiel, sincronizado, auditable y reversible en Windows 10/11 x64.

Requisitos estructurales:

1. portable real: ZIP → descomprimir → ejecutar;
2. vídeo con audio embebido o vídeo + audio externo;
3. master audio resuelto antes de análisis temporal;
4. auto-sync con confidence cuando exista referencia;
5. offset manual/override;
6. drift detectado/corregido sólo tras validación;
7. originales intactos;
8. edición derivada de datos auditables.

Arquitectura:

```text
source(s)
  ↓
ingest / sync
  ↓
MASTER AUDIO + video timeline
  ↓
analysis
  ↓
candidates
  ↓
decisions
  ↓
Edit Plan
  ↓
render
  ↓
audit
```

Candidato ≠ decisión ≠ edición. Baja confianza => KEEP/REVIEW, nunca adivinar.

## 2. Estado

Versión: `0.1.0-dev`.

Completado:

- Fase 0 bootstrap;
- Fase 0.5 technology harvest;
- CLI, FFmpeg/ffprobe, probe;
- Cleaner determinista de silencios;
- Edit Plan + render;
- WAV 16 kHz mono PCM16;
- transcript models + TXT/JSON/SRT;
- candidate schema review-only;
- source SHA-256;
- tests unitarios/E2E sintéticos;
- Fase 1A core portable Windows PASS.

Core portable evidence:

- Actions run `33600174568`, SUCCESS 2026-09-02;
- PyInstaller 6.22.2 onedir;
- bundled FFmpeg/ffprobe;
- PATH de prueba sin Python/FFmpeg;
- ruta con espacios;
- doctor/probe/clean/render PASS;
- ZIP temporal 122677058 bytes;
- 0 artifacts.

En curso: Fase 1A ML frozen.

## 3. Technology harvest

Video_Tunner NO es fork.

Referencias principales:

- `Railly/vcut` — EDL/audit/joins/retakes/repeats;
- `JosephLeon/Cadence-Lab` — clasificación contextual/cache;
- `timkulbaev/ai-video-editor` — pipeline talking-head;
- `SYSTRAN/faster-whisper` — STT + backend Silero VAD ONNX.

Ver `UPSTREAM_SOURCES.md`. Registrar licencia/commit antes de copiar código; preferir APIs públicas o reimplementación propia.

## 4. Portabilidad

Layout:

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

`tools.py`:

- frozen => portable strict;
- FFmpeg sólo desde `Tools/ffmpeg/bin`;
- modelos sólo desde `Models/`;
- no fallback a PATH ni model dirs externos en portable;
- desarrollo no frozen puede mantener env/PATH como compatibilidad.

Packaging base provisional: PyInstaller 6.22.2 `onedir`. Nuitka sólo si aparece un problema o ventaja medible.

Build script:

```powershell
.\.github\scripts\build_portable_windows.ps1 -Profile core
.\.github\scripts\build_portable_windows.ps1 -Profile analysis
```

No versionar binarios FFmpeg, builds, modelos ni ZIPs en main.

## 5. Stack ML portable

Critical pins del spike:

```text
faster-whisper 1.2.1
CTranslate2 4.8.1
ONNX Runtime 1.29.0
tokenizers 0.23.1
PyInstaller 6.22.2
```

PyAV y demás dependencias llegan vía faster-whisper.

VAD:

- usar `faster_whisper.audio.decode_audio`;
- `faster_whisper.vad.VadOptions`;
- `faster_whisper.vad.get_speech_timestamps`;
- asset esperado `faster_whisper/assets/silero_vad_v6.onnx`.

No reintroducir standalone `silero-vad`/Torch sin nueva evidencia.

## 6. Modelos Whisper

Modelo de producto previsto: `large-v3-turbo`.

El modelo NO forma parte del ejecutable congelado. Ruta:

```text
Models/whisper/<safe-model-name>/
```

Modelo mínimo completo:

- `config.json`;
- `model.bin`;
- `tokenizer.json`.

CLI:

```text
video-tunner model status MODEL
video-tunner model fetch MODEL [--replace]
```

`model fetch`:

1. descarga a `Temp/model-downloads/<modelo>.partial`;
2. cache bajo `Cache/huggingface`;
3. verifica mínimos;
4. sólo después mueve a `Models/whisper`;
5. limpia staging.

Portable strict:

- si modelo local completo existe, `WhisperModel` recibe el path y `local_files_only=True`;
- si no existe, `analyze` falla de forma explícita;
- nunca usar caché global silenciosamente como source of truth.

Primera adquisición puede usar red. Después debe poder inferir con `HF_HUB_OFFLINE=1`.

## 7. Doctor

`doctor` debe comprobar funcionalidad real, no sólo presencia de módulos:

- faster_whisper;
- ctranslate2;
- onnxruntime;
- tokenizers;
- av;
- Silero ONNX asset;
- FFmpeg/ffprobe;
- runtime/model roots.

Los imports capturan excepciones de DLL loading y deben reportar `error`.

## 8. Transcripción / candidates

`analyze` sigue siendo no destructivo.

Artefactos:

- transcript JSON;
- transcript TXT;
- SRT;
- analysis JSON.

Candidates actuales:

- pause;
- possible_filler;
- `decision="undecided"`;
- `auto_apply=false`.

No usar probabilidad ASR como confianza semántica.

El pipeline actual todavía toma audio embebido del vídeo. Debe migrar a master audio en Fase 1B/1C.

## 9. Fase 1A ML validation

Workflow: `.github/workflows/portable-ml-spike.yml`, manual-only de forma permanente.

Modelo `tiny` sólo para runtime/packaging. No implica decisión de producto.

Acceptance:

- tests source con analysis deps;
- build analysis onedir;
- frozen imports y native DLLs;
- Silero ONNX asset;
- ruta aislada + PATH sin Python/FFmpeg;
- `model fetch tiny` dentro de Models;
- fixture hablado temporal upstream;
- `HF_HUB_OFFLINE=1` tras adquisición;
- frozen `analyze` con Whisper + VAD reales;
- word_count >= 5;
- analysis/candidates generados sin edits automáticos;
- ZIP size/SHA en logs;
- no artifact upload.

Registrar evidencia en `Validation/portable-analysis-spike.md`.

## 10. Ingesta dual / sync — siguiente fase

Modo A:

```text
video + embedded audio → master audio
```

Modo B:

```text
video + external audio
  ↓
correlation / manual offset / drift correction
  ↓
synchronized master audio
```

Auto-sync futuro:

1. referencias mono;
2. coarse correlation;
3. fine correlation;
4. confidence;
5. multi-window anchors;
6. drift estimate;
7. validated correction.

Metadata: method, offset, confidence, anchors, residual error, drift, correction, override.

Sin referencia/confidence suficiente => manual/review.

## 11. Edit Plan / render

Edit Plan schema v1 sólo contiene ediciones efectivas. No meter candidates como edits sin fase de decisión.

Renderer actual:

- complemento de remove edits;
- merge overlaps;
- trim/atrim + concat;
- H.264 libx264 + AAC;
- no overwrite;
- aborta si elimina todo.

Futuro: source hash, removedText, join audit, edge fades, loudness, post-render verification.

## 12. GitHub / Actions

GitHub es source of truth.

- CI pesada sólo deliberada;
- workflows pesados manual-only normalmente;
- no polling frecuente;
- concurrency + cancel obsolete;
- no models/videos/ZIPs como artifacts ordinarios;
- conservar sólo evidencia ligera;
- no publicar Release sin autorización expresa.

El conector actual no expone `workflow_dispatch`. Si es necesario disparar una única validación autónomamente, puede usarse excepcionalmente el procedimiento ya probado:

1. añadir temporalmente `push` limitado a un marker path único;
2. crear marker una vez;
3. confirmar exactamente un run;
4. restaurar manual-only mientras el run sigue ligado a su SHA;
5. borrar marker;
6. comprobar que no aparece un segundo run.

No usar esta técnica como trigger normal ni para crear commits de CI repetitivos.

## 13. Repo cleanliness / docs

Mantener main sin:

- build/dist;
- modelos;
- outputs;
- vídeos grandes;
- temporales/cache/logs;
- markers one-shot;
- workflows one-shot abandonados.

Cambios de arquitectura/dependencias/build/validación => actualizar README + AGENTS cuando proceda.

`ROADMAP.md` = planificación.
`UPSTREAM_SOURCES.md` = provenance.
`Validation/` = evidencia.
`Archive/` = sólo versiones finales publicadas y sustituidas.

## 14. Orden inmediato

1. validar/corregir ML portable spike;
2. cerrar Fase 1A;
3. Fase 1B ingest + external audio + sync + drift;
4. adaptar analyze a master audio;
5. validar `large-v3-turbo`/VAD real en español;
6. Fase 2 semantic cleaner.

## 15. Changelog técnico

### 0.1.0-dev — bootstrap

CLI, FFmpeg/ffprobe, probe, silence Cleaner, Edit Plan, render, tests, manual CI.

### 0.1.0-dev — transcription/VAD candidate layer

faster-whisper plumbing, transcript artifacts, Silero VAD, candidates, source hash, upstream harvest.

### 0.1.0-dev — portable core

PyInstaller onedir, strict local tools/models, runtime layout, bundled FFmpeg, Windows isolated PASS.

### 0.1.0-dev — portable ML spike

Pinned ML stack, frozen diagnostics, local model lifecycle, offline inference acceptance workflow.
