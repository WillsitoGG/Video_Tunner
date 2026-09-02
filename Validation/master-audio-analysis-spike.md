# Fase 1C — Master Audio Analysis Spike

Fecha: 2026-09-02

## Objetivo

Demostrar que `analyze` deja de depender de la pista embebida como supuesto estructural y ejecuta Whisper + Silero VAD sobre el **mismo master audio** previamente resuelto por `ingest`, manteniendo todos los timestamps sobre la timeline del vídeo.

## Ejecución

Workflow: `Master Audio Analysis Spike`

Run: `33640872486`

Resultado: **SUCCESS a la primera**

Artifacts almacenados: **0**

El trigger temporal quedó limitado a `Validation/master-analysis.trigger`, se confirmó exactamente un run y el workflow volvió inmediatamente a `workflow_dispatch`; el marker fue eliminado.

## Source tests

**41 tests PASS** en Windows.

Incluyen:

- Whisper y VAD reciben exactamente el mismo master;
- `review_required` en ingest bloquea Whisper/VAD;
- un master pre-resuelto exige `ingest.json`;
- el SHA-256 del vídeo debe coincidir con el acreditado por `ingest.json`;
- regresión de audio embebido con PTS inicial retrasado;
- regresiones y hardening completos de Fase 1B.

## Portable frozen

PyInstaller `analysis` build: PASS.

En portable strict:

- Python externo no disponible en PATH;
- FFmpeg externo no disponible en PATH;
- FFmpeg/ffprobe locales operativos;
- NumPy 2.5.2 frozen: available;
- faster-whisper 1.2.1: available;
- CTranslate2 4.8.1: available;
- ONNX Runtime 1.29.0: available;
- tokenizers 0.23.1: available;
- PyAV 18.1.0: available;
- Silero VAD V6 ONNX: available.

FFmpeg archive del run:

`453d5494608010b937324b147de2b12c4b5e211eb0f7f69e29e0b34de09ba8e4`

## Fixture

Fuente upstream fijada:

`SYSTRAN/faster-whisper v1.2.1 / tests/data/jfk.flac`

SHA-256:

`63A4B1E4C1DC655AC70961FFBF518ACD249DF237E5A0152FAAE9A4A836949715`

Para evitar periodicidad artificial en correlación, se construyó una secuencia hablada de 4 tramos con tempos `0.92 / 1.00 / 1.08 / 0.96`.

Duración resultante: `44.58275 s`.

El modelo `tiny` se adquirió dentro de `Models/whisper/tiny`. Tras la adquisición se activó `HF_HUB_OFFLINE=1`; las dos inferencias siguientes fueron offline.

## Caso A — embedded audio con inicio retrasado

Vídeo:

- audio hablado embebido con `+0.4 s` de inicio;
- timeline de vídeo: `45.6 s`.

Resultado:

- `status=analyzed`;
- master generado por ingest;
- analysis schema v2;
- provenance `input_mode=embedded_audio`;
- `master_audio_is_timeline_source=true`;
- Whisper word count: **89**;
- candidates: **11 pause**;
- automatic edits: **0**;
- duración vídeo: `45.6 s`;
- duración master: `45.6 s`.

Esto valida también el hardening de master embebido:

`aresample=async=1:first_pts=0` + pad/trim + PTS regenerados mantienen el audio en su posición temporal y extienden el master a toda la timeline del vídeo.

## Caso B — audio externo auto-sincronizado

Vídeo con camera reference y audio externo derivado de la misma secuencia con offset real `+0.5 s`.

Resultado:

- `status=analyzed`;
- ingest `ready_auto`;
- `input_mode=external_audio`;
- `sync_method=auto_correlation`;
- offset estimado: **`+0.49581 s`**;
- error absoluto de offset: ~`4.19 ms`;
- confidence: **`1.0`**;
- drift estimado: **`192.308 ppm`**;
- Whisper word count: **88**;
- candidates: **9 pause**;
- automatic edits: **0**;
- duración vídeo: `44.58275 s`;
- duración master: `44.58275 s`.

El pequeño drift estimado no representa un drift introducido deliberadamente en este fixture; está dentro de los thresholds actuales y es compatible con diferencias de codificación/resampling entre camera AAC y external PCM. Los thresholds siguen pendientes de calibración con corpus real.

## Provenance / safety

`analysis.json` schema v2 registra:

- master audio file/duration/SHA-256;
- ingest report asociado;
- ingest status/input mode/sync method;
- timeline convention;
- source video SHA-256;
- `automatic_edits=0`.

Un `--master-audio` pre-resuelto sólo es aceptado junto con su `--ingest-report` y si el SHA-256 del vídeo coincide.

Si ingest devuelve `review_required`, el pipeline devuelve revisión en stage `ingest` y no invoca Whisper ni VAD.

## Conclusión

La **integración técnica master audio → Whisper/VAD/candidates está VALIDADA en Windows portable**, tanto para audio embebido como externo auto-sincronizado.

Fase 1C no se considera totalmente cerrada porque falta:

1. validar el modelo objetivo `large-v3-turbo`;
2. usar contenido hablado real en español;
3. medir calidad, velocidad y tamaño de modelo;
4. revisar/calibrar parámetros de transcripción/VAD antes de entrar en semantic cleaner.
