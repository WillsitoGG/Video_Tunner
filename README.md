# Video_Tunner

**Video_Tunner** es una aplicación portable para Windows 10/11 x64 orientada a la limpieza automática, inteligente, auditable y reversible de vídeo hablado.

El producto debe aceptar vídeo con audio embebido o vídeo + audio externo. Antes de cualquier transcripción o decisión temporal debe existir un **master audio** correctamente asociado a la línea temporal del vídeo. Los originales nunca se sobrescriben.

## Requisitos estructurales

### Portable real

Objetivo de distribución:

```text
ZIP → descomprimir → ejecutar
```

Sin instalador, permisos de administrador, Python preinstalado ni FFmpeg/ffprobe preinstalados. En modo portable las herramientas, modelos, configuración, temporales, cachés y logs deben resolverse desde el propio árbol de Video_Tunner.

### Dos modos de entrada

```text
A) vídeo + audio embebido → master audio
B) vídeo + audio externo → sync → master audio
```

El modo B deberá admitir auto-sync con confianza, offset manual/override y detección/corrección validada de drift. Si no existe referencia suficiente, Video_Tunner no debe adivinar la sincronización.

Ver `ROADMAP.md` para la secuencia técnica vigente.

## Estado actual

**Versión de desarrollo:** `0.1.0-dev`

- Fase 0 — Bootstrap: **implementada**.
- Fase 0.5 — Technology harvest: **cerrada**.
- Fase 1A — Portable Foundation: **implementación del spike preparada; validación Windows real pendiente**.
- Fase 1B — Ingesta dual + sincronización A/V: **pendiente**.
- Fase 1C — Transcripción + VAD: **parcialmente implementada**; pendiente de master audio y validación runtime real.
- Release pública: **ninguna**.

Video_Tunner sigue siendo un producto/repo propio. `vcut`, `Cadence-Lab`, `ai-video-editor` y dependencias upstream se estudian mediante technology harvest selectivo y trazable.

## Fase 1A — Portable Foundation

### Decisión de empaquetado

El spike usa **PyInstaller `onedir`**, actualmente fijado a `6.22.2` para la prueba.

Motivos:

- incluye el runtime Python sin exigir Python instalado al usuario;
- mantiene un árbol explícito y auditable en lugar de extraer todo a temporales como un `onefile`;
- permite situar `Tools/`, `Models/`, `Config/`, `Temp/`, `Cache/`, `Logs/` y `Output/` junto al ejecutable;
- simplifica diagnosticar DLLs y dependencias antes de una Release.

Nuitka queda como alternativa si PyInstaller demuestra problemas reales con CTranslate2/ONNX Runtime; no se introduce esa complejidad antes de necesitarla.

### Árbol portable objetivo del spike

```text
Video_Tunner/
├── Video_Tunner.exe
├── _internal/                runtime empaquetado por PyInstaller
├── Tools/
│   └── ffmpeg/
│       └── bin/
│           ├── ffmpeg.exe
│           └── ffprobe.exe
├── Models/
├── Config/
├── Temp/
├── Cache/
├── Logs/
├── Output/
└── portable-manifest.json
```

### Modo portable estricto

Cuando Video_Tunner está congelado por PyInstaller —o durante pruebas con `VIDEO_TUNNER_PORTABLE_STRICT=1`—:

- FFmpeg/ffprobe sólo se buscan en `Tools/ffmpeg/bin`;
- no existe fallback al `PATH`;
- `Models/` se resuelve dentro del runtime;
- `doctor` crea/verifica el layout local.

En desarrollo no congelado se mantiene, temporalmente, soporte para `VIDEO_TUNNER_FFMPEG_DIR` y `PATH`.

### FFmpeg del spike

El script `build_portable_windows.ps1` descarga para el spike un build Windows x64 de la rama estable FFmpeg 9.0 de `BtbN/FFmpeg-Builds`, copia únicamente `ffmpeg.exe` y `ffprobe.exe` y registra la versión real en `portable-manifest.json`.

**Importante:** el URL usado durante el spike es flotante dentro de la rama estable. Una Release final deberá fijar un asset/digest inmutable y cerrar la revisión de licencia/notices.

### VAD: decisión de portabilidad

Se elimina la dependencia directa `silero-vad` del extra `analysis`.

Motivo: la distribución Python oficial de `silero-vad` añade Torch + torchaudio, mientras que `faster-whisper` ya incluye:

- ONNX Runtime como dependencia;
- su implementación de Silero VAD;
- el asset `silero_vad_v6.onnx`.

Video_Tunner reutiliza ese backend ONNX de `faster-whisper`, evitando duplicar un stack PyTorch pesado sólo para VAD.

## Pipeline objetivo

```text
vídeo + audio embebido
          O
vídeo + audio externo
          ↓
       ingest/sync
          ↓
      MASTER AUDIO
          ↓
transcripción + VAD + análisis
          ↓
 candidatos auditables
          ↓
 KEEP / TRIM / CUT / REVIEW
          ↓
 protección semántica
          ↓
       Edit Plan
          ↓
 render + auditoría
```

Candidato ≠ decisión ≠ edición.

## Funcionalidad ya existente

Validada en el entorno de desarrollo previo:

- CLI `video-tunner`;
- FFmpeg/ffprobe + `probe`;
- Cleaner determinista de silencios;
- `edit_plan.json`;
- render H.264/AAC sin sobrescribir el original;
- extracción WAV mono 16 kHz PCM16;
- modelos/serialización de transcripción word-level;
- TXT/JSON/SRT;
- Candidate Analysis review-only;
- SHA-256 del source;
- tests unitarios y E2E sintéticos.

Implementado pero aún pendiente de inferencia real:

- `faster-whisper` + `large-v3-turbo`;
- timestamps word-level reales;
- VAD Silero ONNX mediante `faster-whisper`;
- `video-tunner analyze` completo con backends reales.

## Desarrollo local

```powershell
python -m pip install -e .
```

Análisis:

```powershell
python -m pip install -e ".[analysis]"
```

Packaging del spike:

```powershell
python -m pip install -e ".[packaging]"
.\.github\scripts\build_portable_windows.ps1
```

### Comandos

```powershell
video-tunner doctor
video-tunner probe "video.mp4"
video-tunner plan "video.mp4" --mode conservative --output edit_plan.json
video-tunner clean "video.mp4" --mode conservative --output-dir Output
video-tunner analyze "video.mp4" --language es --output-dir Output
video-tunner render "video.mp4" edit_plan.json "video_clean.mp4"
```

`analyze` todavía consume el audio embebido del vídeo; se adaptará al concepto de `master audio` en Fase 1B/1C.

## Validación del portable spike

Workflow manual: `.github/workflows/portable-spike.yml`.

Debe comprobar en Windows:

1. tests source;
2. build `onedir`;
3. FFmpeg + ffprobe propios;
4. copia a una ruta aislada con espacios;
5. eliminación de Python y FFmpeg del `PATH` de la prueba;
6. `Video_Tunner.exe doctor`;
7. creación de fixture con el FFmpeg empaquetado;
8. `probe` desde el ejecutable;
9. `clean` y render real;
10. validación con el `ffprobe` empaquetado;
11. tamaño + SHA-256 de un ZIP temporal;
12. **no subir el ZIP como artifact de Actions**.

Hasta que ese workflow pase no se afirmará que la base portable está validada.

## Próximos pasos

1. Ejecutar y corregir el Portable Foundation spike en Windows.
2. Evaluar empaquetado del perfil ML (`faster-whisper` + CTranslate2 + ONNX Runtime) dentro del mismo `onedir`.
3. Cerrar Fase 1A con evidencia real.
4. Implementar Fase 1B: vídeo + audio externo, master audio, auto-sync, offset manual y drift.
5. Adaptar `analyze` al master audio y validar Whisper/VAD reales.
6. Sólo después construir retomas/repeticiones y la capa semántica.

## Principios

- portable por diseño;
- procesamiento local por defecto;
- originales intactos;
- línea temporal A/V fiable antes de IA;
- candidato ≠ decisión ≠ edición;
- modo Conservador por defecto;
- ante duda semántica o de sync, conservar/revisar;
- GitHub como fuente de verdad;
- CI deliberada y sin artifacts pesados ordinarios.

Consulta `AGENTS.md`, `ROADMAP.md`, `UPSTREAM_SOURCES.md` y `Validation/` para el contexto técnico y la evidencia.
