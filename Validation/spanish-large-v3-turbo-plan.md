# Fase 1C — plan de validación `large-v3-turbo` con español real

Fecha de diseño: 2026-09-02.

## Objetivo

Cerrar Fase 1C con una única validación pesada y deliberada del modelo objetivo `large-v3-turbo` dentro del portable Windows, sobre voz humana real en español y con transcripción de referencia conocida.

No se pretende calibrar todavía un benchmark ASR general; se busca una evidencia reproducible de producto que permita comprobar precisión básica, word timestamps y coste local del modelo antes de entrar en semántica.

## Fixture

Se usarán únicamente durante CI cuatro diálogos reales de SpanishPod alojados en Wikimedia Commons. No se versionan los audios ni se suben como artifacts.

Fuentes de audio:

1. `SpanishPod_newbie_lesson_A0006_dialogue.ogg`
   - Commons: `https://commons.wikimedia.org/wiki/Special:Redirect/file/SpanishPod_newbie_lesson_A0006_dialogue.ogg`
   - referencia Wikibooks: `Spanish by Choice/SpanishPod newbie lesson A0006`
2. `SpanishPod_newbie_lesson_A0007_dialogue.ogg`
   - Commons: `https://commons.wikimedia.org/wiki/Special:Redirect/file/SpanishPod_newbie_lesson_A0007_dialogue.ogg`
   - referencia Wikibooks: `Spanish by Choice/SpanishPod newbie lesson A0007`
3. `SpanishPod_newbie_lesson_A0013_dialogue.ogg`
   - Commons: `https://commons.wikimedia.org/wiki/Special:Redirect/file/SpanishPod_newbie_lesson_A0013_dialogue.ogg`
   - referencia Wikibooks: `Spanish by Choice/SpanishPod newbie lesson A0013`
4. `SpanishPod_newbie_lesson_A0116_dialogue.ogg`
   - Commons: `https://commons.wikimedia.org/wiki/Special:Redirect/file/SpanishPod_newbie_lesson_A0116_dialogue.ogg`
   - referencia Wikibooks: `Spanish by Choice/SpanishPod newbie lesson A0116`

Los ficheros de SpanishPod publicados en Commons indican licencia Creative Commons Attribution 3.0 Unported. La validación registra SHA-256 de cada descarga.

## Transcripción de referencia

```text
¡Hola, guapa! ¿Cómo te va? Bien, bien. ¿Y tú? ¿Qué tal? Todo bien, gracias. Me alegra.
¿De dónde eres? Soy de Perú. ¿Y tú? Yo soy de Colombia. ¡Qué bien!
Voy a lavar la ropa. ¿Hay detergente? Sí hay, abajo en la cocina. ¿Dónde? ¿En qué parte? No sé. ¡Búscalo!
¿Quieres una menta? ¿Por qué? ¿Me huele la boca? Sí, ¡toma!
```

Tras normalizar minúsculas, diacríticos y puntuación: **61 palabras de referencia**.

## Construcción del fixture

- cada diálogo se convierte a mono 16 kHz PCM;
- se concatenan en orden A0006 → A0007 → A0013 → A0116;
- se insertan pausas breves deterministas entre diálogos;
- el WAV resultante se incrusta en un vídeo negro para pasar por `ingest → master audio → analyze` completo;
- no se modifica el contenido hablado.

## Configuración objetivo

```text
model: large-v3-turbo
device: cpu
compute_type: int8
language: es
portable strict: true
HF_HUB_OFFLINE: true durante inferencia
```

`large-v3-turbo` es resuelto por faster-whisper 1.2.1 al modelo CTranslate2 asociado por su catálogo oficial.

## Métricas

### 1. Precisión textual

WER sobre texto normalizado mediante distancia de Levenshtein a nivel de palabra.

Criterio de spike:

```text
WER <= 0.15
```

Este umbral es deliberadamente conservador y sólo vale para este fixture limpio; no se convierte automáticamente en threshold de Release.

### 2. Word timestamps

Debe cumplirse:

- transcript con al menos 80% de las 61 palabras de referencia;
- todos los word timestamps finitos y no negativos;
- `start <= end`;
- orden temporal monótono;
- ningún word timestamp termina más de 0.5 s fuera de la timeline del vídeo;
- duración mediana de palabra > 0 y < 1.5 s.

No se calcula error de timestamps contra ground truth porque estas fuentes no publican alineación palabra-a-palabra fiable.

### 3. Rendimiento

Registrar, sin imponer todavía threshold de Release:

- duración del fixture;
- segundos totales de `analyze`;
- real-time factor = tiempo de análisis / duración de audio;
- peak working set del proceso;
- tamaño total local de `Models/whisper/large-v3-turbo`;
- número de palabras y candidates;
- automatic edits, que debe seguir siendo `0`.

## Política de CI

- un único run deliberado;
- workflow manual-only fuera del instante de disparo;
- sin artifacts;
- sin guardar modelo, vídeos ni audio;
- si falla, leer primero logs y corregir causa antes de cualquier rerun.

## Condición de cierre de 1C

Fase 1C podrá marcarse COMPLETADA si:

1. el portable frozen carga `large-v3-turbo` localmente;
2. la inferencia funciona offline después de la adquisición del modelo;
3. WER y sanity temporal pasan el criterio anterior;
4. RAM/tiempo/tamaño quedan registrados para decidir la estrategia portable posterior;
5. candidates siguen separados de decisiones y edits.
