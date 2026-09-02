# Fase 1C — validación `large-v3-turbo` con español real

Fecha: 2026-09-02.
Estado final: **COMPLETADA**.

## Objetivo

Cerrar Fase 1C con una validación pesada y deliberada del modelo objetivo `large-v3-turbo` dentro del portable Windows, sobre voz humana real en español y con transcripción de referencia conocida.

No se pretende calibrar un benchmark ASR general; se busca evidencia reproducible de producto para comprobar precisión básica, word timestamps y coste local del modelo antes de entrar en semántica.

## Fixture

Se usan únicamente durante CI cuatro diálogos reales de SpanishPod alojados en Wikimedia Commons. No se versionan audios ni se suben como artifacts.

Fuentes:

1. `SpanishPod_newbie_lesson_A0006_dialogue.ogg`
   - `https://upload.wikimedia.org/wikipedia/commons/0/0a/SpanishPod_newbie_lesson_A0006_dialogue.ogg`
2. `SpanishPod_newbie_lesson_A0007_dialogue.ogg`
   - `https://upload.wikimedia.org/wikipedia/commons/4/4c/SpanishPod_newbie_lesson_A0007_dialogue.ogg`
3. `SpanishPod_newbie_lesson_A0013_dialogue.ogg`
   - `https://upload.wikimedia.org/wikipedia/commons/6/67/SpanishPod_newbie_lesson_A0013_dialogue.ogg`
4. `SpanishPod_newbie_lesson_A0116_dialogue.ogg`
   - `https://upload.wikimedia.org/wikipedia/commons/5/54/SpanishPod_newbie_lesson_A0116_dialogue.ogg`

Los ficheros indican licencia Creative Commons Attribution 3.0 Unported. El harness registra SHA-256 de cada descarga.

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

Fixture final validado:

```text
duration: 46.58025 s
sha256: A3548B0861F095F50D023A3CDC7DEBA99CF3523600AB6249C40240F61A5EA036
```

Hashes de fuentes:

```text
A0006 8868E068B1599C0010C3A2CF8B61D7EC3FDC2B8453EA0B97806EA2225DC19930
A0007 2736966B5B1469FD030FBA15D61A44872A558C1F186592E6DAE27E86AE40D0E9
A0013 DD516C03E89F99E0BCD1786E59BFF1916C432BC5FF17A8C86B798DCB621E0E12
A0116 2B175E67741C1D74D2334D80EF4BBA213EEB7363FFAF887703AFD7E713494230
```

## Modelo objetivo

```text
model: large-v3-turbo
device: cpu
compute_type: int8
language: es
portable strict: true
HF_HUB_OFFLINE: true durante inferencia
```

Para separar calidad ASR de disponibilidad del servicio de metadata, el modelo se staged directamente bajo `Models/whisper/large-v3-turbo`.

Fuente reproducible fijada:

```text
repo: rtlingo/mobiuslabsgmbh-faster-whisper-large-v3-turbo
revision: 6bd64462dd562f8062828f585c3709aa52df0083
model.bin bytes: 1617884929
model.bin sha256: e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da
```

El repositorio declara que contiene la conversión CTranslate2 de `openai/whisper-large-v3-turbo` para uso con faster-whisper. El árbol fijado contiene `config.json`, `preprocessor_config.json`, `tokenizer.json`, `vocabulary.json` y `model.bin`.

El harness descarga los cuatro JSON mediante `raw/<revision>` y `model.bin` mediante `resolve/<revision>`, valida tamaño + SHA-256 exactos del binario y sólo después construye el portable. La inferencia se ejecuta con `HF_HUB_OFFLINE=1`.

## Criterios fijados antes del resultado

### Precisión textual

```text
WER <= 0.15
```

El umbral sólo vale para este fixture limpio; no es automáticamente threshold de Release.

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

## Intentos previos de infraestructura

### Intento 1 — run `33652410474`

**FAILURE antes del modelo**.

- evaluator smoke PASS;
- portable build PASS;
- Wikimedia devolvió HTTP 429 al tercer audio usando `Special:Redirect/file`;
- modelo no descargado;
- ASR no ejecutado.

Corrección: URLs directas `upload.wikimedia.org`, User-Agent y backoff.

### Intento 2 — run `33653108940`

**FAILURE antes de inferencia**.

- cuatro audios PASS;
- portable build PASS;
- fixture final `46.58025 s` PASS;
- `model fetch large-v3-turbo` recibió HTTP 429 en `/api/models/.../revision/main`;
- `model.bin` no descargado;
- ASR no ejecutado.

Corrección: desacoplar la validación ASR del endpoint de metadata.

### Intento 3 — run `33653826702`

**FAILURE antes del build y antes de inferencia**.

- fixture PASS;
- el SHA completo inferido para un mirror H2O era incorrecto;
- `config.json` devolvió 404;
- build no ejecutado;
- ASR no ejecutado.

Corrección: no inferir SHAs completos desde abreviados; seleccionar commit completo verificable.

### Intento 4 — run `33655947559`

**FAILURE antes del build y antes de inferencia**.

- fixture PASS;
- commit `rtlingo@6bd64462...` verificado externamente;
- el runner recibió 404 usando `resolve/<revision>` también para `config.json`;
- build no ejecutado;
- ASR no ejecutado.

Corrección: usar `raw/<revision>` para JSON y reservar `resolve/<revision>` para el binario Xet. También se eliminó cualquier ambigüedad de interpolación al construir las URLs.

Ninguno de estos cuatro intentos constituye un resultado negativo del modelo ASR: todos fallaron antes de inferencia.

## Intento 5 — evidencia definitiva

Run `33656235038` — **SUCCESS**, 2026-09-02.

### Adquisición del modelo

PASS:

```text
config.json                  2263 bytes
preprocessor_config.json      340 bytes
tokenizer.json            2710337 bytes
vocabulary.json           1068114 bytes
model.bin              1617884929 bytes
```

`model.bin`:

```text
SHA-256 E76620F83D5F5B69EFD3D87E3DC180C1BD21DF9FBEBACFD4335E5E1EFCC018DA
```

Modelo staged total:

```text
1621665983 bytes
1546.5 MiB
descarga directa: 11.032 s
```

### Portable frozen

PASS:

- PyInstaller analysis build;
- faster-whisper 1.2.1;
- CTranslate2 4.8.1;
- ONNX Runtime 1.29.0;
- tokenizers 0.23.1;
- NumPy 2.5.2;
- PyAV 18.1.0;
- Silero VAD V6 ONNX;
- FFmpeg/ffprobe bundled;
- inferencia posterior con `HF_HUB_OFFLINE=1`.

### Precisión española

```text
reference words: 61
hypothesis words: 62
word count ratio: 1.016393
word errors: 1
WER: 0.016393 = 1.64%
threshold: <= 15%
result: PASS
```

Hipótesis normalizada = referencia completa + una `y` extra al final.

### Word timestamps

Todos los checks PASS:

- finitos;
- no negativos;
- `start <= end`;
- starts monótonos;
- dentro de timeline;
- duración mediana de palabra `0.36 s`.

### Rendimiento CPU

```text
fixture duration: 46.58025 s
analyze: 22.609 s
real-time factor: 0.4854
peak working set: 1818.7 MiB
```

En este runner Windows, el análisis fue aproximadamente **2.06× más rápido que tiempo real**.

### Safety / arquitectura

```text
candidates: 16
automatic edits: 0
video duration: 46.58025 s
master duration: 46.58025 s
artifacts: 0
```

Candidate ≠ decision ≠ edit se mantiene intacto.

## Conclusión

Las cinco condiciones de cierre de Fase 1C se cumplen:

1. frozen portable carga `large-v3-turbo` localmente — PASS;
2. inferencia con `HF_HUB_OFFLINE=1` — PASS;
3. WER y sanity temporal — PASS;
4. RAM/tiempo/tamaño registrados — PASS;
5. candidates separados de decisions/edits — PASS.

**Fase 1C queda COMPLETADA.**

El siguiente trabajo es Fase 2: retomas, repeticiones, correcciones/errores, fillers contextuales y protección semántica, manteniendo Conservador por defecto y sin auto-apply prematuro.
