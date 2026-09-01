# AGENTS.md — Video_Tunner

Contexto técnico permanente para cualquier agente que trabaje en este repositorio. La referencia maestra externa vigente es `00.Contexto y Reglas de Trabajo_GitHub_Video_Tunner_v3`.

## 1. Producto

Video_Tunner debe convertir vídeo hablado bruto en un resultado natural, fiel, sincronizado, auditable y reversible para Windows 10/11 x64.

Requisitos estructurales:

1. aplicación portable real: ZIP → descomprimir → ejecutar;
2. vídeo con audio embebido o vídeo + audio externo;
3. master audio resuelto antes de análisis temporal;
4. auto-sync con confianza cuando exista referencia;
5. offset manual/override;
6. detección y corrección validada de drift;
7. originales intactos;
8. edición derivada de datos auditables.

No convertir prematuramente el proyecto en un editor generalista.

## 2. Invariantes arquitectónicos

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

- Candidato ≠ decisión ≠ edición.
- El original y el audio externo nunca se sobrescriben.
- Un detector técnico no se convierte silenciosamente en decisor semántico.
- Baja confianza de sync o semántica => KEEP/REVIEW, no adivinar.
- El mismo master audio debe alimentar transcripción/VAD y render final.

## 3. Estado

Versión: `0.1.0-dev`.

Implementado/validado previamente en entorno de desarrollo:

- paquete Python y CLI;
- FFmpeg/ffprobe;
- probe;
- Cleaner determinista de silencios;
- Edit Plan schema v1;
- render H.264/AAC;
- extracción WAV 16 kHz mono PCM16;
- transcript models + TXT/JSON/SRT;
- candidate schema review-only;
- source SHA-256;
- tests unitarios/E2E sintéticos.

Fase 1A en curso:

- runtime layout portable;
- modo portable estricto sin fallback a PATH;
- PyInstaller `onedir` 6.22.2 para el spike;
- script Windows de build;
- FFmpeg/ffprobe bundled;
- workflow manual de validación aislada;
- eliminación de `silero-vad`/Torch del dependency graph de análisis;
- VAD Silero ONNX reutilizado desde `faster-whisper`.

Pendiente de validación real:

- workflow Windows portable;
- perfil ML frozen (`faster-whisper`/CTranslate2/ONNX Runtime);
- modelo `large-v3-turbo` real;
- inferencia VAD real;
- master audio/audio externo/sync.

## 4. Technology harvest

Video_Tunner NO es fork.

Upstreams principales:

- `Railly/vcut` — EDL, audit, joins, retakes/repeats, audio offset;
- `JosephLeon/Cadence-Lab` — clasificación contextual y cache por hash;
- `timkulbaev/ai-video-editor` — referencia pipeline talking-head;
- `SYSTRAN/faster-whisper` — STT y, desde Fase 1A, backend VAD Silero ONNX reutilizado.

Ver `UPSTREAM_SOURCES.md`.

Reglas:

- registrar licencia/commit antes de copiar código;
- preferir integración pública estable o reimplementación propia a copiar archivos enteros;
- cada port/adaptación requiere tests propios;
- revisar periódicamente upstreams sin ser fork.

## 5. Portabilidad

Portabilidad es requisito estructural desde Fase 1A.

### Layout

```text
Video_Tunner/
├── Video_Tunner.exe
├── _internal/
├── Tools/ffmpeg/bin/
├── Models/
├── Config/
├── Temp/
├── Cache/
├── Logs/
├── Output/
└── portable-manifest.json
```

### Resolución de runtime

`tools.py`:

- `is_frozen_runtime()` detecta PyInstaller;
- `portable_strict_mode()` es true si frozen o `VIDEO_TUNNER_PORTABLE_STRICT=1`;
- frozen/strict: FFmpeg sólo desde `<runtime>/Tools/ffmpeg/bin`;
- frozen/strict: modelos sólo desde `<runtime>/Models`;
- no fallback a PATH en portable;
- desarrollo no frozen puede usar env/PATH como compatibilidad temporal.

`doctor` debe exponer:

- portable mode;
- runtime root/layout;
- model root;
- FFmpeg/ffprobe version;
- disponibilidad de análisis.

### Empaquetado

Spike: PyInstaller `onedir` 6.22.2.

Razones:

- runtime Python autocontenido;
- árbol transparente;
- mejor diagnóstico de DLLs que onefile;
- encaja con Tools/Models/Config visibles.

Nuitka sólo se evaluará si existe evidencia de que PyInstaller no resuelve bien CTranslate2/ONNX o si aporta una ventaja concreta medible.

### FFmpeg

El spike descarga `BtbN/FFmpeg-Builds` Windows x64 GPL, rama estable 9.0, porque el renderer actual usa `libx264`.

El URL del spike es flotante y NO es criterio de Release. Antes de publicar:

- pin immutable asset/digest;
- revisar licencia/notices/source obligations;
- registrar versión exacta.

No versionar binarios FFmpeg dentro de `main`.

## 6. Dependencias ML / VAD

Extra actual:

```toml
analysis = ["faster-whisper>=1.2,<2"]
```

No reintroducir `silero-vad` sin una razón nueva y medida.

Motivo: la distribución standalone de silero-vad trae Torch/torchaudio, pero faster-whisper ya trae ONNX Runtime y el modelo Silero VAD ONNX.

`vad.py` reutiliza:

- `faster_whisper.audio.decode_audio`;
- `faster_whisper.vad.VadOptions`;
- `faster_whisper.vad.get_speech_timestamps`.

Los timestamps devueltos por faster-whisper VAD son muestras; Video_Tunner los convierte a segundos con sample rate 16 kHz.

Pendiente: comprobar que PyInstaller incluye correctamente `faster_whisper/assets/silero_vad_v6.onnx` y las DLLs de ONNX Runtime/CTranslate2 en el perfil ML.

## 7. Ingesta dual / master audio — siguiente fase

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

1. audio camera + external a mono analysis representation;
2. coarse correlation;
3. fine correlation;
4. confidence;
5. multi-window anchors;
6. drift estimate;
7. validated correction.

Metadata mínima futura:

- method;
- offset;
- confidence;
- anchors;
- residual error;
- drift ppm/ms-h;
- correction;
- manual override.

Sin referencia suficiente => manual offset/review.

## 8. Transcripción / candidates

Motor previsto: faster-whisper, modelo default `large-v3-turbo`, word timestamps.

`analyze` sigue siendo no destructivo.

Artefactos actuales:

- transcript JSON;
- transcript TXT;
- SRT;
- analysis JSON.

Candidates actuales:

- pause;
- possible_filler;
- `decision="undecided"`;
- `auto_apply=false`.

No convertir ASR probability en confianza semántica.

Parte del pipeline actual todavía asume audio embebido; debe adaptarse a master audio en Fase 1B/1C.

## 9. Edit Plan / render

Edit Plan schema v1 contiene ediciones efectivas. No meter candidates sin fase explícita de decisión.

Renderer actual:

- complemento de `remove` edits;
- merge overlaps;
- trim/atrim + concat;
- H.264 `libx264` + AAC;
- no overwrite source;
- aborta si se elimina todo.

Mejoras futuras:

- source hash en Edit Plan;
- removedText;
- join audit;
- edge fades;
- loudness normalization;
- output verification.

## 10. Validación

No afirmar funcionalidad por compilación.

### Portable spike

Workflow: `.github/workflows/portable-spike.yml`, manual-only.

Debe probar:

- source tests;
- Windows x64 build;
- isolated path with spaces;
- no Python/FFmpeg on test PATH;
- bundled doctor;
- bundled FFmpeg fixture generation;
- bundled probe;
- bundled clean/render;
- bundled ffprobe validation;
- ZIP size + SHA in logs;
- no artifact upload.

Hasta PASS: Fase 1A no validada.

### ML portable pendiente

Debe probar después:

- faster-whisper import frozen;
- CTranslate2 DLL loading;
- ONNX Runtime DLL loading;
- Silero ONNX asset discovery;
- Models local;
- no global HuggingFace cache as source of truth;
- offline inference after model availability.

### Sync futura

Tests obligatorios:

- embedded;
- external positive/negative offset;
- low confidence;
- manual override;
- no camera reference;
- external shorter/longer;
- noisy correlation;
- synthetic drift;
- post-cut sync.

Distinguir unit / automated E2E / model integration / CI / manual user test.

## 11. GitHub / cuota

GitHub es source of truth.

- workflows pesados manual-only salvo justificación;
- no polling frecuente;
- no commits artificiales para disparar CI;
- concurrency + cancel obsolete;
- no models/videos/ZIPs como artifacts ordinarios;
- guardar evidence ligera;
- no reducir pruebas necesarias para ahorrar cuota.

El portable-spike calcula ZIP SHA/size pero NO lo sube como artifact.

## 12. Repo cleanliness

Mantener `main` sin:

- build/dist;
- modelos;
- outputs;
- vídeos grandes;
- temporales/cache/logs;
- workflows one-shot;
- scripts descartados.

`Archive/` sólo versiones finales publicadas y sustituidas.

## 13. Docs

Cambios de arquitectura, dependencia, build, packaging, validación o uso => actualizar README + AGENTS en el mismo cambio cuando corresponda.

`ROADMAP.md` = planificación vigente.
`UPSTREAM_SOURCES.md` = provenance.
`Validation/` = evidencia ligera.

## 14. Releases

No publicar Release sin autorización expresa del usuario.

Final portable:

- ZIP Windows x64;
- runtime + tools;
- models strategy cerrada;
- pinned versions/digests;
- SHA-256;
- manifest;
- notices/licenses;
- zero-install validation.

## 15. Orden inmediato

1. ejecutar/corregir portable core spike;
2. frozen ML dependency spike;
3. cerrar Fase 1A;
4. Fase 1B ingest + sync + drift;
5. adaptar analyze a master audio;
6. validar real Whisper/VAD;
7. Fase 2 semantic cleaner.

## 16. Changelog técnico

### 0.1.0-dev — bootstrap

CLI, FFmpeg/ffprobe, probe, silence Cleaner, Edit Plan, render, tests, manual CI.

### 0.1.0-dev — transcription/VAD candidate layer

faster-whisper plumbing, transcript artifacts, initial Silero VAD, candidates, source hash, upstream harvest.

### 0.1.0-dev — portable foundation spike

- PyInstaller onedir strategy;
- strict portable tool/model resolution;
- runtime layout;
- bundled FFmpeg build script;
- isolated Windows validation workflow;
- VAD migrated from standalone silero-vad/Torch to faster-whisper Silero ONNX;
- packaging dependency profile;
- portable unit tests.
