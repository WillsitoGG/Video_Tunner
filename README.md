# Video_Tunner

**Video_Tunner** es una aplicación portable para Windows 10/11 x64 orientada a la limpieza automática, inteligente, auditable y reversible de vídeo hablado.

Debe aceptar vídeo con audio embebido o vídeo + audio externo. Antes de cualquier transcripción o decisión temporal debe existir un **master audio** correctamente asociado a la línea temporal del vídeo. Los originales nunca se sobrescriben.

## Requisitos estructurales

```text
ZIP → descomprimir → ejecutar
```

Sin instalador, permisos de administrador, Python preinstalado ni FFmpeg/ffprobe preinstalados. Herramientas, modelos, configuración, temporales, caches y logs se resuelven desde el árbol portable.

```text
A) vídeo + audio embebido → master audio
B) vídeo + audio externo → sync → master audio
```

Sin referencia suficiente, Video_Tunner no inventa la sincronización.

## Estado actual

**Versión:** `0.1.0-dev`

- Fase 0 — Bootstrap: ✅
- Fase 0.5 — Technology harvest: ✅
- Fase 1A — Portable Foundation: ✅
- Fase 1B — Ingesta dual + sync/drift: ✅
- Fase 1C — Transcripción/VAD sobre master audio + `large-v3-turbo` español real: ✅
- Fase 2 — Cleaner semántico: 🟡 **Semantic Candidates v1 completado; decision/protection layer pendiente**
- Release pública: ninguna

Video_Tunner sigue siendo producto/repo propio, no un fork.

## Portable Foundation

### Core — run `33600174568`

- PyInstaller 6.22.2 `onedir`;
- runtime Python + FFmpeg/ffprobe propios;
- PATH sin Python/FFmpeg externos;
- `doctor`, `probe`, `clean`, render y ffprobe PASS;
- ZIP temporal: `122677058` bytes;
- 0 artifacts.

### ML — run `33621357438`

- faster-whisper 1.2.1;
- CTranslate2 4.8.1;
- ONNX Runtime 1.29.0;
- tokenizers 0.23.1;
- NumPy 2.5.2;
- PyAV 18.1.0;
- Silero VAD V6 ONNX frozen;
- modelo local bajo `Models/whisper/<modelo>`;
- frozen/offline Whisper + VAD PASS;
- 0 artifacts.

Modelo objetivo de producto: **`large-v3-turbo`**. `tiny` sólo se utiliza como fixture barato de runtime/CI.

## Fase 1B — ingesta y sincronización

```powershell
video-tunner ingest "video.mp4" --output-dir Output
video-tunner ingest "video.mp4" --audio "grabador.wav" --output-dir Output
video-tunner ingest "video.mp4" --audio "grabador.wav" --offset 1.25 --output-dir Output
video-tunner ingest "video.mp4" --audio "grabador.wav" --offset -2.0 --drift-ppm 120 --output-dir Output
```

Convención temporal:

```text
video_time = offset_seconds + time_scale * external_time
```

Auto-sync: envolvente log-RMS → ZNCC coarse → anchors fine → ajuste offset/drift → confidence/residual/coverage. Si la evidencia no supera los thresholds, `ingest` devuelve `review_required` y no genera master.

Outputs:

```text
<video>_master_audio.flac
<video>_ingest.json
```

Hardening Windows run `33639009841`: 37 tests PASS, offset negativo, drift real, low-signal failure-safe, override manual y coverage parcial. Ver `Validation/sync-foundation-spike.md` y `Validation/sync-hardening.md`.

## Fase 1C — análisis sobre master audio — COMPLETADA

`analyze` ya no asume que debe leer el audio embebido del MP4.

Puede:

```powershell
# Audio embebido: ingest + master + analyze
video-tunner analyze "video.mp4" --model large-v3-turbo --language es --output-dir Output

# Audio externo: auto-sync + master + analyze
video-tunner analyze "video.mp4" --audio "micro.wav" --model large-v3-turbo --language es --output-dir Output

# Audio externo con override manual
video-tunner analyze "video.mp4" --audio "micro.wav" --offset 1.25 --model large-v3-turbo --language es --output-dir Output

# Reutilizar un master ya resuelto y acreditado
video-tunner analyze "video.mp4" --master-audio "video_master_audio.flac" --ingest-report "video_ingest.json" --model large-v3-turbo --language es --output-dir Output
```

Reglas:

- Whisper y Silero VAD reciben **exactamente el mismo master**;
- el master cubre la timeline completa del vídeo;
- todos los timestamps de transcript/VAD/candidates están en tiempo de vídeo;
- un master pre-resuelto exige su `ingest.json`;
- se verifica SHA-256 del vídeo fuente antes de reutilizarlo;
- si ingest devuelve `review_required`, Whisper/VAD no arrancan;
- `analysis.json` schema v2 registra provenance de master e ingest;
- candidates siguen `undecided` y `auto_apply=false`.

### Integración portable — run `33640872486`

- 41 source tests PASS;
- build frozen analysis PASS;
- embedded y external master PASS;
- offset real `+0.500 s` → estimado `+0.49581 s`;
- inferencia offline;
- automatic edits: `0`;
- artifacts: `0`.

### Modelo objetivo + español real — run `33656235038`

- fixture hablado real: `46.58025 s`, 61 palabras de referencia;
- hipótesis: 62 palabras;
- errores: `1`;
- **WER `1.64%`** frente al criterio predefinido `<= 15%`;
- word timestamps: PASS;
- análisis: `22.609 s`;
- **RTF `0.4854`**;
- RAM pico: **1818.7 MiB**;
- modelo staged: **1546.5 MiB**;
- candidates: `16`;
- automatic edits: `0`;
- vídeo/master: `46.58025 / 46.58025 s`;
- artifacts: `0`.

Con esta evidencia se cerró Fase 1C. Ver `Validation/master-audio-analysis-spike.md` y `Validation/spanish-large-v3-turbo-plan.md`.

## Fase 2 — Semantic Candidates v1

`analyze` añade ahora una primera capa semántica **determinista y review-only** sobre los word timestamps.

Clases iniciales:

```text
possible_repetition
possible_retake
explicit_correction
```

Ejemplos:

```text
vamos a lanzar | vamos a lanzar el producto
^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^
candidato        lectura posterior conservada
```

```text
la facturación fue de 200 perdón de 250 mil euros
                          ^^^^^^^
                          marcador detectado
```

En una corrección explícita, Video_Tunner **no adivina todavía** que todo lo anterior al marcador deba borrarse. El candidato del marcador conserva contexto antes/después para que la futura capa semántica pueda distinguir, por ejemplo, `200` de `250` sin alterar significado.

Cada candidato semántico registra:

- `removed_text` exacto del span candidato;
- contexto anterior/posterior;
- word indices/timestamps;
- evidencia de clase;
- confidence;
- `suggested_decision=REVIEW`;
- `decision=undecided`;
- `auto_apply=false`;
- `span_safe_for_auto_apply=false`.

Referencia conceptual revisada: `Railly/vcut@2142cc54dc01a0d2272f1d99717b89cd1c7c9262`; la implementación Python es propia.

### Validación — run `33659725847`

**SUCCESS**:

```text
Ran 48 tests in 6.469s
OK
```

Incluye todos los E2E de sync y los 7 tests nuevos de Semantic Candidates v1. `video-tunner doctor` PASS y artifacts `0`.

El run anterior `33659514611` falló porque el workflow core no instalaba NumPy aunque ejecutaba E2E de auto-sync; todos los tests semánticos habían pasado. Manual CI queda corregida para instalar sólo `numpy==2.5.2` adicionalmente, sin añadir Whisper/CTranslate2/ONNX al workflow ligero.

Ver `Validation/phase2-semantic-candidates.md`.

## Pipeline

```text
sources
  ↓
ingest / sync
  ↓
MASTER AUDIO + video timeline
  ↓
Whisper word-level + Silero VAD
  ↓
acoustic + semantic candidates auditables
  ↓
KEEP / TRIM / CUT / REVIEW
  ↓
protección semántica
  ↓
Edit Plan
  ↓
render + audit
```

**Candidato ≠ decisión ≠ edición.**

## Modelos Whisper

```text
Models/whisper/<modelo>/
```

```powershell
Video_Tunner.exe model status large-v3-turbo
Video_Tunner.exe model fetch large-v3-turbo
```

En portable strict no existe fallback silencioso a caches globales.

## Siguiente trabajo — Fase 2 semantic protection

1. crear `candidate → decision` sin convertir todavía decisiones en edits ejecutables;
2. proteger cifras, importes, porcentajes y unidades;
3. proteger negaciones y cambios de sujeto/persona;
4. proteger tiempo verbal/aspecto y entidades relevantes;
5. modelar corrección `intento → versión corregida`;
6. verificar que `removed_text` coincide exactamente con el span propuesto;
7. validar con habla que contenga errores/retomas deliberados;
8. mantener `auto_apply=false` hasta disponer de evidencia suficiente.

## Principios

- portable por diseño;
- local-first;
- originales intactos;
- sync fiable antes de IA temporal;
- Conservador por defecto;
- ante duda: KEEP/REVIEW;
- GitHub como source of truth;
- CI deliberada y sin artifacts pesados ordinarios.

Consulta `AGENTS.md`, `ROADMAP.md`, `UPSTREAM_SOURCES.md` y `Validation/`.
