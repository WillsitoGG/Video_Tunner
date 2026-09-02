# Fase 1C — plan de validación `large-v3-turbo` con español real

Fecha de diseño: 2026-09-02.

## Objetivo

Cerrar Fase 1C con una validación pesada y deliberada del modelo objetivo `large-v3-turbo` dentro del portable Windows, sobre voz humana real en español y con transcripción de referencia conocida.

No se pretende calibrar todavía un benchmark ASR general; se busca una evidencia reproducible de producto que permita comprobar precisión básica, word timestamps y coste local del modelo antes de entrar en semántica.

## Fixture

Se usan únicamente durante CI cuatro diálogos reales de SpanishPod alojados en Wikimedia Commons. No se versionan audios ni se suben como artifacts.

Fuentes:

1. `SpanishPod_newbie_lesson_A0006_dialogue.ogg`
   - Commons: `https://commons.wikimedia.org/wiki/File:SpanishPod_newbie_lesson_A0006_dialogue.ogg`
   - original: `https://upload.wikimedia.org/wikipedia/commons/0/0a/SpanishPod_newbie_lesson_A0006_dialogue.ogg`
2. `SpanishPod_newbie_lesson_A0007_dialogue.ogg`
   - Commons: `https://commons.wikimedia.org/wiki/File:SpanishPod_newbie_lesson_A0007_dialogue.ogg`
   - original: `https://upload.wikimedia.org/wikipedia/commons/4/4c/SpanishPod_newbie_lesson_A0007_dialogue.ogg`
3. `SpanishPod_newbie_lesson_A0013_dialogue.ogg`
   - Commons: `https://commons.wikimedia.org/wiki/File:SpanishPod_newbie_lesson_A0013_dialogue.ogg`
   - original: `https://upload.wikimedia.org/wikipedia/commons/6/67/SpanishPod_newbie_lesson_A0013_dialogue.ogg`
4. `SpanishPod_newbie_lesson_A0116_dialogue.ogg`
   - Commons: `https://commons.wikimedia.org/wiki/File:SpanishPod_newbie_lesson_A0116_dialogue.ogg`
   - original: `https://upload.wikimedia.org/wikipedia/commons/5/54/SpanishPod_newbie_lesson_A0116_dialogue.ogg`

Los ficheros indican licencia Creative Commons Attribution 3.0 Unported. La validación registra SHA-256 de cada descarga.

## Transcripción de referencia

```text
¡Hola, guapa! ¿Cómo te va? Bien, bien. ¿Y tú? ¿Qué tal? Todo bien, gracias. Me alegra.
¿De dónde eres? Soy de Perú. ¿Y tú? Yo soy de Colombia. ¡Qué bien!
Voy a lavar la ropa. ¿Hay detergente? Sí hay, abajo en la cocina. ¿Dónde? ¿En qué parte? No sé. ¡Búscalo!
¿Quieres una menta? ¿Por qué? ¿Me huele la boca? Sí, ¡toma!
```

Normalización de minúsculas, diacríticos y puntuación: **61 palabras**.

## Construcción

- cada diálogo → mono 16 kHz PCM;
- orden A0006 → A0007 → A0013 → A0116;
- pausa determinista de 0.6 s entre diálogos;
- WAV final incrustado en vídeo negro;
- pipeline completo `ingest → master audio → analyze`;
- contenido hablado no modificado.

## Modelo objetivo

```text
model: large-v3-turbo
device: cpu
compute_type: int8
language: es
portable strict: true
HF_HUB_OFFLINE: true durante inferencia
```

Para la validación de inferencia, el modelo se puede staged directamente bajo `Models/whisper/large-v3-turbo`; la fiabilidad del servicio de descarga no debe confundirse con la calidad ASR.

Tras un rate-limit de la API de metadata de Hugging Face, el harness fija como fuente de CI el snapshot:

```text
repo: h2oai/faster-whisper-large-v3-turbo
revision: d9e74de5094e9b435ce024f77e90c8cbb8d1afe1
```

Hugging Face identifica ese snapshot como duplicado de `mobiuslabsgmbh/faster-whisper-large-v3-turbo`. Se descargan directamente `config.json`, `preprocessor_config.json`, `tokenizer.json`, `vocabulary.json` y `model.bin`; se registran tamaños y SHA-256. La inferencia posterior se ejecuta offline.

## Métricas y criterios fijados antes del resultado

### Precisión textual

WER normalizado a nivel de palabra:

```text
WER <= 0.15
```

Este umbral sólo vale para este fixture limpio; no es automáticamente threshold de Release.

### Word timestamps

- al menos 80% de las 61 palabras de referencia;
- timestamps finitos y no negativos;
- `start <= end`;
- starts monótonos;
- ningún end más de 0.5 s fuera de timeline;
- duración mediana de palabra > 0 y < 1.5 s.

No hay ground truth palabra-a-palabra fiable, por lo que no se calcula error absoluto de timestamp.

### Rendimiento informativo

Registrar:

- duración del fixture;
- segundos de `analyze`;
- real-time factor;
- peak working set;
- tamaño local del modelo;
- tiempo de adquisición del modelo;
- palabras y candidates;
- automatic edits = `0`.

## Política CI

- cada run pesado debe aportar evidencia nueva;
- workflow manual-only fuera del instante de disparo;
- sin artifacts;
- sin guardar modelo, vídeos ni audio;
- ante fallo, diagnosticar primero y no mover thresholds.

## Intento 1 — fallo externo de Wikimedia

Run `33652410474` — **FAILURE antes del modelo**:

- evaluador smoke: PASS;
- portable analysis build: PASS;
- A0006/A0007 descargados;
- A0013 recibió HTTP `429 Too many requests` mediante `Special:Redirect/file`;
- modelo no descargado;
- ASR no ejecutado.

Corrección: URLs directas `upload.wikimedia.org`, User-Agent, backoff y descargas antes del build.

## Intento 2 — fixture resuelto; fallo externo de Hugging Face metadata

Run `33653108940` — **FAILURE antes de inferencia**:

- evaluador smoke: PASS;
- preflight de los cuatro audios: PASS;
- hashes:
  - A0006 `8868E068B1599C0010C3A2CF8B61D7EC3FDC2B8453EA0B97806EA2225DC19930`;
  - A0007 `2736966B5B1469FD030FBA15D61A44872A558C1F186592E6DAE27E86AE40D0E9`;
  - A0013 `DD516C03E89F99E0BCD1786E59BFF1916C432BC5FF17A8C86B798DCB621E0E12`;
  - A0116 `2B175E67741C1D74D2334D80EF4BBA213EEB7363FFAF887703AFD7E713494230`;
- portable build: PASS;
- fixture final: `46.58025 s`, SHA-256 `A3548B0861F095F50D023A3CDC7DEBA99CF3523600AB6249C40240F61A5EA036`;
- `model fetch large-v3-turbo` recibió HTTP `429` en `huggingface.co/api/models/.../revision/main`;
- no se descargó `model.bin`;
- ASR no ejecutado.

Este run tampoco es un resultado negativo de `large-v3-turbo`.

Corrección: adquisición directa de snapshot fijado, sin endpoint `/api/models`, antes del build; inferencia posterior completamente offline.

## Condición de cierre de 1C

Fase 1C podrá marcarse COMPLETADA si:

1. el frozen portable carga `large-v3-turbo` localmente;
2. la inferencia funciona con `HF_HUB_OFFLINE=1`;
3. WER y sanity temporal pasan los criterios fijados;
4. RAM/tiempo/tamaño quedan registrados;
5. candidates siguen separados de decisiones y edits.
