# AGENTS.md — Video_Tunner

Contexto técnico permanente para agentes. Referencia maestra externa vigente: `00.Contexto y Reglas de Trabajo_GitHub_Video_Tunner_v3`.

## 1. Invariantes de producto

Video_Tunner debe producir vídeo hablado limpio, natural, fiel, sincronizado, auditable y reversible en Windows 10/11 x64.

Obligatorio:

1. portable real: ZIP → descomprimir → ejecutar;
2. vídeo con audio embebido o vídeo + audio externo;
3. resolver master audio antes de cualquier análisis temporal;
4. auto-sync con confidence cuando haya referencia;
5. offset manual/override;
6. drift detectado/corregido sólo tras validación;
7. originales intactos;
8. candidate ≠ decision ≠ edit;
9. ante duda, KEEP/REVIEW.

Pipeline:

```text
sources → ingest/sync → MASTER AUDIO + timeline → analysis → candidates → decisions → Edit Plan → render → audit
```

## 2. Estado

Versión: `0.1.0-dev`.

Completado:

- Fase 0 bootstrap;
- Fase 0.5 technology harvest;
- CLI, FFmpeg/ffprobe, probe;
- Cleaner de silencios, Edit Plan y render;
- WAV 16 kHz mono PCM16;
- transcript TXT/JSON/SRT + word timestamps;
- Candidate Analysis review-only;
- source SHA-256;
- **Fase 1A Portable Foundation core + ML PASS Windows**.

Siguiente: **Fase 1B ingesta dual + master audio + sync/drift**.

## 3. Evidencia portable

### Core — PASS

Actions run `33600174568`:

- PyInstaller 6.22.2 onedir;
- bundled FFmpeg/ffprobe;
- PATH sin Python/FFmpeg externos;
- ruta con espacios;
- doctor/probe/clean/render PASS;
- ZIP temporal `122677058` bytes;
- 0 artifacts.

### ML frozen — PASS

Actions run `33621357438`:

- faster-whisper 1.2.1;
- CTranslate2 4.8.1;
- ONNX Runtime 1.29.0;
- tokenizers 0.23.1;
- PyAV 18.1.0;
- Silero VAD V6 ONNX bundled;
- imports y native DLLs PASS;
- `model fetch tiny` → `Models/whisper/tiny`;
- `HF_HUB_OFFLINE=1` + frozen `analyze` PASS;
- 22 words;
- 3 pause candidates;
- 0 automatic edits;
- ZIP runtime ML sin modelo `212334854` bytes (~202.5 MiB);
- 0 artifacts.

PyInstaller onedir queda como base provisional. No evaluar Nuitka sin problema/ventaja medible.

Existe una optimización futura: `--collect-all onnxruntime` recoge módulos opcionales. No gastar CI ahora sólo para adelgazar el bundle.

## 4. Technology harvest

Video_Tunner NO es fork.

Referencias:

- Railly/vcut — EDL/audit/joins/retakes/repeats;
- Cadence-Lab — clasificación contextual;
- ai-video-editor — talking-head pipeline;
- SYSTRAN/faster-whisper — STT + Silero VAD ONNX.

Ver `UPSTREAM_SOURCES.md`. Antes de copiar código: licencia + commit + razón. Preferir API pública o reimplementación propia.

## 5. Portable layout

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
- FFmpeg sólo desde Tools en frozen;
- modelos sólo desde Models en frozen;
- sin fallback PATH/caches externas en portable;
- desarrollo no frozen puede usar env/PATH.

No versionar binarios, builds, modelos, vídeos, outputs ni ZIPs en main.

## 6. Stack ML

Critical pins demostrados:

```text
faster-whisper 1.2.1
CTranslate2 4.8.1
ONNX Runtime 1.29.0
tokenizers 0.23.1
PyInstaller 6.22.2
```

PyAV resuelto actualmente como 18.1.0.

VAD usa faster-whisper + `silero_vad_v6.onnx`. No reintroducir standalone Silero/Torch sin nueva evidencia.

## 7. Modelos Whisper

Modelo objetivo previsto: `large-v3-turbo`.

Ruta:

```text
Models/whisper/<safe-name>/
```

Disponibilidad mínima:

- config.json;
- model.bin;
- tokenizer.json.

CLI:

```text
video-tunner model status MODEL
video-tunner model fetch MODEL [--replace]
```

Descarga:

1. staging `Temp/model-downloads`;
2. cache `Cache/huggingface`;
3. verificar ficheros;
4. mover a Models;
5. limpiar staging.

Portable strict:

- modelo completo => path local + `local_files_only=True`;
- modelo ausente/incompleto => error explícito;
- nunca cache global silenciosa como source of truth.

Primera adquisición puede usar red; después inferencia offline debe funcionar. Esto ya está demostrado con `tiny`.

`tiny` NO es decisión de producto; sólo fixture de runtime. Calidad de `large-v3-turbo` se valida en Fase 1C.

## 8. `doctor`

Debe comprobar imports reales, no sólo specs:

- faster_whisper;
- ctranslate2;
- onnxruntime;
- tokenizers;
- av;
- Silero ONNX asset;
- FFmpeg/ffprobe;
- runtime/model roots.

Errores de DLL deben aparecer como `error`.

## 9. Transcripción / candidates

`analyze` no es destructivo.

Artefactos:

- transcript JSON;
- transcript TXT;
- SRT;
- analysis JSON.

Candidates actuales:

- pause;
- possible_filler;
- `decision=undecided`;
- `auto_apply=false`.

No usar probabilidad ASR como confianza semántica.

Actualmente `analyze` aún toma audio embebido del vídeo. Debe migrar a **master audio** en Fase 1B/1C.

## 10. Fase 1B — siguiente implementación

### Input contract

Modo A:

```text
video + embedded audio → master audio
```

Modo B:

```text
video + external audio → sync → external synchronized audio = master audio
```

Si hay audio de cámara y el usuario aporta externo, cámara sirve como referencia de sync; el externo sincronizado es master.

### Auto-sync

1. extraer referencias mono de análisis;
2. coarse correlation;
3. fine correlation;
4. offset positivo/negativo;
5. confidence;
6. multi-window validation;
7. si inconsistente/low confidence => manual/review.

### Manual fallback

- external audio opcional;
- offset manual/override;
- sin camera reference no prometer auto-sync;
- metadata distingue auto vs manual.

### Drift

- anchors en varias ventanas;
- estimar offset(t);
- drift ppm/ms-h;
- residual error antes/después;
- correction sólo si mejora;
- preservar pitch/calidad.

### Sync metadata

Registrar source/master, method, offset, confidence, anchors, residuals, drift, correction, override y coverage warnings.

### Tests mínimos

- embedded;
- external ±offset conocido;
- niveles/ruido diferentes;
- señal ambigua;
- no camera reference;
- manual override;
- external shorter/longer;
- synthetic drift;
- paths con espacios;
- timeline consistency.

## 11. Edit Plan / render

Edit Plan v1 sólo contiene ediciones efectivas. Candidates no entran sin decision layer.

Renderer actual:

- merge overlap remove edits;
- trim/atrim + concat;
- H.264/AAC;
- no overwrite;
- aborta si elimina todo.

Futuro: source hash, removedText, join audit, edge fades, loudness y post-render verification.

## 12. GitHub / Actions

GitHub = source of truth.

- heavy CI deliberada;
- workflows pesados manual-only normalmente;
- no polling frecuente;
- cancel obsolete;
- no modelos/vídeos/ZIPs como artifacts ordinarios;
- conservar evidencia ligera;
- no Release sin autorización expresa.

El conector actual no expone `workflow_dispatch`. Procedimiento excepcional ya probado para una única ejecución autónoma:

1. añadir temporalmente `push` limitado a marker path;
2. crear marker una vez;
3. confirmar exactamente un run;
4. restaurar manual-only mientras el run sigue ligado a su SHA;
5. borrar marker;
6. confirmar que no aparece un segundo run.

No usar como trigger normal.

## 13. Documentación / limpieza

Cambios de arquitectura/dependencias/build/validación => README + AGENTS sincronizados.

- `ROADMAP.md` = planificación;
- `UPSTREAM_SOURCES.md` = provenance;
- `Validation/` = evidencia;
- `Archive/` = sólo releases publicadas sustituidas.

## 14. Orden inmediato

1. Fase 1B ingest/master audio;
2. offset correlation + confidence + manual override;
3. drift multi-window;
4. adaptar analyze a master audio;
5. validar large-v3-turbo/VAD en español;
6. Fase 2 semantic cleaner.

## 15. Changelog técnico

### 0.1.0-dev — bootstrap
CLI, tools, probe, silence Cleaner, Edit Plan, render, tests.

### 0.1.0-dev — analysis layer
Transcript artifacts, word timestamps, Silero VAD, candidates, source hash.

### 0.1.0-dev — portable core
PyInstaller onedir, strict local tools/models, bundled FFmpeg, Windows isolated PASS.

### 0.1.0-dev — portable ML
Pinned ML stack, frozen imports/native DLLs, local model lifecycle, offline Whisper+VAD inference PASS.
