# ROADMAP — Video_Tunner

## Principios

- Windows 10/11 x64 portable: ZIP → descomprimir → ejecutar.
- Vídeo con audio embebido o vídeo + audio externo.
- Master audio y sincronización antes de transcripción/VAD/semántica.
- Originales intactos y decisiones auditables/reversibles.
- Ante baja confianza: REVIEW/manual, no adivinar.
- CI pesada sólo cuando aporta evidencia nueva.

## Fases completadas

### Fase 0 — Bootstrap
CLI, FFmpeg/ffprobe, probe, Cleaner de silencios, Edit Plan, render y tests.

### Fase 0.5 — Technology Harvest
Repo propio, no fork. Upstreams sólo como referencias/integraciones trazables.

### Fase 1A — Portable Foundation
- core `33600174568` PASS;
- ML frozen `33621357438` PASS.

### Fase 1B — Ingesta dual + sincronización A/V
- master FLAC;
- offset positivo/negativo;
- drift;
- confidence/residual/coverage;
- manual override y `review_required`.

Hardening `33639009841` PASS.

### Fase 1C — Transcripción + VAD sobre master
Whisper y Silero VAD reciben exactamente el mismo master.

Target Spanish `33656235038`: WER `1.64%`, word timestamps PASS, RTF `0.4854`, automatic edits 0.

### Fase 2A — Semantic Candidates v1
`possible_repetition`, `possible_retake`, `explicit_correction`, todo review-only.

Run `33659725847`: 48 tests PASS.

### Fase 2B — Semantic Decisions + Protection v1

```text
candidate → semantic decision/protection → future approved edit
```

```text
KEEP / REVIEW / PROPOSED_TRIM / PROPOSED_CUT
executable = false
auto_apply = false
```

Run `33741195594`: 55 tests PASS, artifacts 0.

## Fase 2 — Cleaner inteligente — EN CURSO

### 2C — Validación semántica real — COMPLETADA COMO BLOQUE DE EVIDENCIA v1

#### 2C.1 — Benchmark/Validation Foundation v1 — COMPLETADA

Harness TP/FP/FN + precision/recall/F1 + safety.

`33743029443`: 21 casos / 11 eventos, 0 FP/FN, unsafe 0.

#### 2C.2 — Positivos/negativos humanos bilingües — COMPLETADA

AMI EN + CORMA ES + controles SpanishPod.

Final `33750836791`:

```text
74 tests PASS en 6.729 s
26 casos / 14 eventos
FP 0 / FN 0
precision = recall = F1 = 100% en el corpus etiquetado actual
unsafe proposals 0
executable 0
auto_apply 0
artifacts 0
```

#### 2C.3 — Audio real → Whisper → semántica — COMPLETADA

Audio real AMI ES2012d procesado con portable frozen y modelo fijado `large-v3-turbo`.

Ligera `33754755238`:

```text
76/76 tests PASS en 5.561 s
FFmpeg/sync E2E PASS
doctor PASS
artifacts 0
```

Final pesada `33755013415`:

```text
3 casos reales
0 failures
53.810 s análisis total
SEMANTIC_AUDIO_GATE=PASS
automatic_edits 0
executable 0
auto_apply 0
artifacts 0
```

Evidencia nueva:

- Whisper puede borrar una vacilación y fabricar una repetición textual perfecta;
- repetición con timing anómalamente comprimido => `REVIEW`;
- Whisper puede eliminar guiones/truncamientos de una autocorrección;
- `question_reframe_cue` recupera el caso real `I mean how...` de forma conservadora;
- `I mean` discursivo sigue sin ser `explicit_correction`.

**El 100% de 2C.2 sólo vale para ese corpus; 2C.3 demuestra comportamiento de tres casos audio-backed, no seguridad universal.**

### 2D — Scope de correcciones + fillers contextuales + join safety — EN CURSO

#### 2D.1 — Correction scope — SIGUIENTE

Objetivo: inferir y medir el span `intento incorrecto → marcador/corrección` sin confundir marker detection con boundary de borrado.

Orden:

1. definir representación explícita de `attempt_span` / `correction_marker_span` / `corrected_span` como evidencia, sin edit executable;
2. construir corpus etiquetado de scopes positivos/negativos;
3. medir exactitud de boundary/span separada de candidate detection;
4. proteger números, unidades, negaciones, sujeto/persona, tiempo/aspecto, entidades y causalidad;
5. si boundary es ambiguo => `REVIEW`, sin propuesta de corte automática;
6. validar primero con tests deterministas y después con pocos audios reales si aporta evidencia nueva.

#### 2D.2 — Fillers contextuales — FUTURA

- distinguir muletilla eliminable de marcador discursivo necesario;
- Conservador debe priorizar naturalidad e integridad semántica;
- no usar listas de palabras como prueba suficiente.

#### 2D.3 — Sentence boundaries + join safety — FUTURA

- límites de frase/turno;
- joins que no alteren negación, sujeto o prosodia;
- removedText exacto;
- guardas acústicas/temporales antes de cualquier promoción.

### 2E — Promotion to Edit Plan — FUTURA

Sólo después de 2D:

- decidir clases auto-aplicables;
- thresholds por modo;
- verificar joins y removedText;
- límite global de eliminación y fail-safe;
- resto en `REVIEW / KEEP`.

## Fase 3 — Calidad audiovisual / auditoría
Normalización, joins, denoise controlado, join audit, post-render verification e informe.

## Fase 4 — UX mínima
Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, renderizar y abrir outputs.

## Fase 5 — Portable Release Hardening
Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras
Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. cerrar/mergear evidencia 2C.3;
2. arrancar 2D.1 correction scope;
3. medir scope exactness sin habilitar edits;
4. fillers contextuales;
5. sentence/join safety;
6. mantener `executable=false` y `auto_apply=false`;
7. no promover al Edit Plan hasta superar 2D.
