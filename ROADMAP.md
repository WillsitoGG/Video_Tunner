# ROADMAP — Video_Tunner

## Principios

- Windows 10/11 x64 portable: ZIP → descomprimir → ejecutar.
- Vídeo con audio embebido o vídeo + audio externo.
- Resolver master audio y sincronización antes de transcripción/VAD/semántica.
- Originales intactos y decisiones auditables.
- Ante baja confianza: REVIEW/manual, no adivinar.
- CI pesada sólo cuando aporta evidencia nueva.

## Fase 0 — Bootstrap — COMPLETADA

CLI, FFmpeg/ffprobe, probe, Cleaner de silencios, Edit Plan, render y tests.

## Fase 0.5 — Technology Harvest — COMPLETADA

Repo propio, no fork. Upstreams sólo como referencias/integraciones trazables.

## Fase 1A — Portable Foundation — COMPLETADA

Core Windows run `33600174568` PASS.

ML frozen run `33621357438` PASS con faster-whisper/CTranslate2/ONNX Runtime/Silero VAD ONNX e inferencia offline desde modelo local.

PyInstaller `onedir` queda como base provisional.

## Fase 1B — Ingesta dual + sincronización A/V — COMPLETADA

Contrato:

```text
A) video + embedded audio → master audio
B) video + external audio → sync → external synchronized master audio
```

Convención única:

```text
video_time = offset_seconds + time_scale * external_time
```

Implementado:

- `ingest` CLI;
- master audio FLAC 48 kHz;
- SHA-256 y metadata de fuentes;
- ZNCC coarse + anchors multi-window;
- offset positivo/negativo;
- confidence;
- ajuste lineal de drift;
- residual RMS;
- rejection de outliers por MAD;
- coverage;
- override `--offset` y `--drift-ppm`;
- `review_required` sin master ante evidencia insuficiente;
- sin mezcla implícita de audio de cámara;
- timeline final del master igual a la del vídeo.

Foundation run `33634775313` — SUCCESS tras corregir PTS/padding.

Hardening run `33639009841` — SUCCESS con 37 tests, negative offset, drift +1000 ppm, low-signal failure-safe, manual override y coverage parcial.

## Fase 1C — Transcripción + VAD sobre master audio — COMPLETADA

`analyze` trabaja siempre sobre master audio acreditado. Whisper y Silero VAD reciben exactamente el mismo master; todos los timestamps permanecen en timeline de vídeo.

Run `33640872486` — SUCCESS: 41 tests, build frozen analysis, embedded/external master, automatic edits `0`, artifacts `0`.

Target Spanish `33656235038` — SUCCESS: WER `1.64%`, word timestamps PASS, RTF `0.4854`, automatic edits `0`, artifacts `0`.

## Fase 2 — Cleaner inteligente — EN CURSO

Objetivo: convertir transcript + VAD + candidates en propuestas semánticas auditables sin sacrificar significado.

### 2A — Semantic Candidates v1 — COMPLETADA

Implementado:

- `possible_repetition`;
- `possible_retake`;
- `explicit_correction`;
- evidencia exacta (`removed_text`, contexto, índices, timestamps, confidence);
- lectura posterior preservada fuera del span candidato;
- modo Conservador más estricto;
- `decision=undecided`;
- `suggested_decision=REVIEW`;
- `auto_apply=false`;
- `span_safe_for_auto_apply=false`.

Run `33659725847` — SUCCESS: 48 tests, artifacts `0`.

### 2B — Semantic Decisions + Protection v1 — COMPLETADA

Arquitectura:

```text
candidate → semantic decision/protection → future approved edit
```

Salida:

```text
KEEP
REVIEW
PROPOSED_TRIM
PROPOSED_CUT
```

Contrato:

```text
candidate != semantic decision != edit
PROPOSED_CUT != executable CUT
executable = false
auto_apply = false
```

`analysis.json` usa schema v3 y separa `candidates[]` de `semantic_decisions[]`.

Guardas implementadas:

- span integrity;
- números/importes/porcentajes/unidades;
- negaciones;
- sujeto/persona;
- tiempo verbal/aspecto;
- causalidad/contraste;
- señal heurística de entidades;
- relación intento → corrección.

Run final `33741195594` — SUCCESS: 55 tests, doctor PASS, artifacts `0`, automatic edits `0`.

### 2C — Validación semántica real — EN CURSO

#### 2C.1 — Benchmark/Validation Foundation v1 — COMPLETADA

Se ha creado un harness reproducible para medir:

- TP / FP / FN;
- precision / recall / F1;
- decision mismatches;
- unsafe proposals;
- missing safe proposals;
- executable decisions;
- auto-apply decisions.

Corpus v1 final:

```text
21 casos
11 constructed_positive
6 constructed_negative
4 human_speech_reference
11 eventos esperados
```

Los 4 controles humanos reutilizan diálogos SpanishPod ya validados con audio + `large-v3-turbo` en `33656235038`; son controles negativos humanos, no positivos de retoma/autocorrección.

Baseline `33742519997` — SUCCESS:

```text
60 tests
FP 2
FN 0
precision 84.62%
recall 100%
F1 91.67%
unsafe proposals 0
```

Los dos FP medidos eran:

- reutilización legítima cercana de opener;
- `quiero decir` literal.

Tuneo Conservador guiado por evidencia:

- rechazar retakes aparentes separados por continuación normal si no hay señal de reparación/vacilación;
- registrar `repair_evidence`;
- tratar `quiero decir` / `I mean` como marcadores ambiguos y no fuertes en contextos literales.

Final `33743029443` — SUCCESS:

```text
64 tests en 6.588 s
FP 0
FN 0
precision 100%
recall 100%
F1 100%
unsafe proposals 0
executable decisions 0
auto_apply decisions 0
artifacts 0
```

**Este 100% sólo vale para corpus v1.** No generalizar a habla arbitraria.

Ver `Validation/phase2c-semantic-validation.md`.

#### 2C.2 — Positivos humanos espontáneos — SIGUIENTE

- incorporar habla humana real con retomas, reinicios y autocorrecciones;
- usar corpus públicos/licenciados o fixtures propios controlados;
- evaluar transcripción real Whisper cuando aporte evidencia nueva;
- mantener thresholds predefinidos y no relajarlos para ocultar fallos;
- usar falsos positivos/negativos observados para guiar tuneos.

### 2D — Scope de correcciones + fillers contextuales — FUTURA

- inferir de forma segura qué parte anterior es la toma incorrecta y cuál es la corrección válida;
- distinguir fillers eliminables de elementos necesarios para naturalidad/significado;
- límites de frase y join safety;
- ampliar protección sólo con evidencia real.

### 2E — Promotion to Edit Plan — FUTURA

Sólo después de 2C/2D:

- decidir qué clases pueden ser auto-aplicables;
- thresholds por modo;
- convertir únicamente decisiones inequívocamente seguras en Edit Plan;
- verificar joins/removedText;
- mantener límite global de eliminación y fail-safe;
- resto en `REVIEW / KEEP`.

## Fase 3 — Calidad audiovisual / auditoría

Normalización, joins, denoise controlado, removedText definitivo, join audit, post-render verification, informe y rendimiento.

## Fase 4 — UX mínima

Seleccionar vídeo, audio externo opcional, confirmar sync, analizar, revisar, renderizar y abrir outputs. CLI se mantiene para tests/automation.

## Fase 5 — Portable Release Hardening

Build Windows limpia, ZIP final, versiones/digests inmutables, optimización de bundle, estrategia final de modelos, SHA-256, manifest, notices/licencias y zero-install/offline.

## Fase 6 — Extras

Subtítulos visuales, reframe, zooms, shorts, B-roll y otras funciones después del Cleaner fiable.

## Orden inmediato

1. conseguir positivos humanos reales con retomas/reinicios/autocorrecciones;
2. incorporarlos al mismo benchmark de 2C;
3. medir FP/FN y unsafe proposals sin mover thresholds;
4. corregir sólo problemas observados;
5. después resolver scope de correcciones y fillers contextuales;
6. mantener `executable=false`;
7. no promover a Edit Plan hasta superar estas validaciones.
