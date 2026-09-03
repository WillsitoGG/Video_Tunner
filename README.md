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
- Fase 2A — Semantic Candidates v1: ✅
- Fase 2B — Semantic Decisions + Protection v1: ✅
- Fase 2C — Validación semántica real / scope de correcciones: 🟡 siguiente
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
- Fase 1C introdujo `analysis.json` schema v2 para provenance; el schema actual es v3 desde Fase 2B;
- candidates nunca son edits.

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

## Fase 2A — Semantic Candidates v1 — COMPLETADA

`analyze` añade una primera capa semántica **determinista y review-only** sobre los word timestamps.

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

Cada candidato semántico registra `removed_text`, contexto, word indices/timestamps, evidence y confidence, y permanece:

```text
suggested_decision = REVIEW
decision = undecided
auto_apply = false
span_safe_for_auto_apply = false
```

Referencia conceptual revisada: `Railly/vcut@2142cc54dc01a0d2272f1d99717b89cd1c7c9262`; la implementación Python es propia.

Run `33659725847` — **SUCCESS**:

```text
Ran 48 tests in 6.469s
OK
```

Artifacts `0`. Ver `Validation/phase2-semantic-candidates.md`.

## Fase 2B — Semantic Decisions + Protection v1 — COMPLETADA

Se introduce una capa explícita y separada:

```text
candidate
   ↓
semantic decision + protection
   ↓
KEEP / REVIEW / PROPOSED_TRIM / PROPOSED_CUT
```

Contrato obligatorio:

```text
candidate != semantic decision != edit
PROPOSED_CUT != executable CUT
executable = false
auto_apply = false
```

`analysis.json` actual usa **schema v3** y separa:

```text
candidates[]
semantic_decisions[]
```

El report declara además:

```text
semantic_protection_enabled = true
semantic_decisions_are_not_edits = true
semantic_decisions_executable = false
```

Guardas v1 implementadas:

- integridad del span: word indices, timestamps y `removed_text` deben coincidir;
- cifras;
- importes, porcentajes y unidades;
- negaciones;
- persona/sujeto;
- tiempo/aspecto y marcadores temporales;
- causalidad/contraste;
- señal heurística de entidades/nombres propios.

Comportamiento:

- repetición adyacente exacta puede producir `PROPOSED_CUT`, siempre no ejecutable;
- retoma con material real o cambios protegidos → `REVIEW`;
- `explicit_correction` → siempre `REVIEW` en v1 porque detectar `perdón` no demuestra el límite exacto de la toma incorrecta;
- candidate corrupto/inconsistente → `KEEP` fail-safe;
- `automatic_edits` permanece `0`.

Casos explícitos cubiertos:

```text
200 → perdón → 250 mil euros   => REVIEW
10% → perdón → 15%             => REVIEW
no funciona → perdón → funciona => REVIEW
```

### Validación final — run `33741195594`

**SUCCESS**:

```text
Ran 55 tests in 6.671s
OK
```

- semantic decisions/protection PASS;
- pipeline schema v3 PASS;
- E2E sync/FFmpeg PASS;
- `video-tunner doctor` PASS;
- artifacts `0`.

El run previo `33661062365` hizo 54/55 PASS y falló únicamente porque un test heredado seguía esperando schema v2. Se actualizó ese test a la realidad v3 sin tocar código productivo.

Ver `Validation/phase2-semantic-protection.md`.

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
semantic decisions + protection
  ↓
future approved Edit Plan
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

## Siguiente trabajo — Fase 2C

1. crear fixtures/corpus explícitos de habla real con retomas, reinicios, repeticiones, errores y autocorrecciones;
2. medir falsos positivos y falsos negativos;
3. validar especialmente cifras, porcentajes, negaciones, nombres, sujeto y tiempo;
4. inferir de forma segura el scope `intento incorrecto → corrección válida`;
5. distinguir fillers eliminables de elementos necesarios para naturalidad/significado;
6. reforzar protección sólo con evidencia real;
7. mantener todas las semantic decisions no ejecutables hasta demostrar qué clases pueden promoverse con seguridad.

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
