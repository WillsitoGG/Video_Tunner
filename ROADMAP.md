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

Ver `Validation/sync-foundation-spike.md` y `Validation/sync-hardening.md`.

Thresholds de confidence/residual/drift/coverage siguen provisionales hasta corpus real.

## Fase 1C — Transcripción + VAD sobre master audio — COMPLETADA

`analyze` trabaja siempre sobre master audio acreditado. Whisper y Silero VAD reciben exactamente el mismo master; todos los timestamps permanecen en timeline de vídeo.

Run `33640872486` — SUCCESS:

- 41 tests PASS;
- build frozen analysis PASS;
- embedded/external master PASS;
- external +0.500 s → +0.49581 s;
- automatic edits `0`;
- artifacts `0`.

### `large-v3-turbo` + español real

Run definitivo `33656235038` — SUCCESS:

- fixture `46.58025 s`;
- 61 palabras de referencia / 62 de hipótesis;
- 1 error;
- WER `1.64%` frente a criterio `<=15%`;
- word timestamps PASS;
- CPU int8 `22.609 s`, RTF `0.4854`;
- peak working set `1818.7 MiB`;
- modelo `1546.5 MiB`;
- candidates `16`;
- automatic edits `0`;
- artifacts `0`.

**Fase 1C cerrada sin introducir auto-apply.**

## Fase 2 — Cleaner inteligente — EN CURSO

Objetivo: convertir transcript + VAD + candidates en propuestas semánticas auditables sin sacrificar significado.

### 2A — Semantic Candidates v1 — COMPLETADA

Implementado sobre word timestamps:

- `possible_repetition`;
- `possible_retake`;
- `explicit_correction`;
- evidencia exacta (`removed_text`, contexto, índices, timestamps, confidence);
- lectura posterior preservada fuera del span candidato en repeticiones/retomas;
- correcciones explícitas detectadas sin inventar todavía el límite del intento erróneo;
- modo Conservador más estricto que Agresivo;
- deduplicación de openers desplazados;
- `decision=undecided`;
- `suggested_decision=REVIEW`;
- `auto_apply=false`;
- `span_safe_for_auto_apply=false`.

Run `33659725847` — SUCCESS:

```text
Ran 48 tests in 6.469s
OK
```

Artifacts `0`. Ver `Validation/phase2-semantic-candidates.md`.

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

`analysis.json` actual usa schema v3 y separa `candidates[]` de `semantic_decisions[]`.

Guardas implementadas:

- span integrity: word indices/timestamps/`removed_text`;
- números, importes, porcentajes y unidades;
- negaciones;
- sujeto/persona;
- tiempo verbal/aspecto y marcadores temporales;
- causalidad/contraste;
- señal heurística de entidades/nombres relevantes;
- relación intento → corrección para `explicit_correction`.

Política:

- repetición exacta adyacente puede ser `PROPOSED_CUT`, nunca ejecutable;
- retake con material real/conflicto protegido → `REVIEW`;
- `explicit_correction` permanece `REVIEW` hasta inferir de forma segura el scope de la toma incorrecta;
- candidate inconsistente → `KEEP` fail-safe;
- `automatic_edits = 0`.

Run previo `33661062365`: 54/55 PASS; único fallo = test heredado esperaba schema v2.

Run final `33741195594` — SUCCESS:

```text
Ran 55 tests in 6.671s
OK
```

`doctor` PASS, E2E sync/FFmpeg PASS, artifacts `0`.

Ver `Validation/phase2-semantic-protection.md`.

### 2C — Validación semántica real — SIGUIENTE

Crear fixtures/corpus explícitos de habla real con:

- retomas;
- reinicios;
- repeticiones;
- errores/autocorrecciones;
- cifras/importes/porcentajes;
- negaciones;
- nombres/entidades;
- cambios de sujeto;
- cambios temporales;
- fillers.

Objetivos:

- medir falsos positivos/falsos negativos;
- validar qué guardas funcionan y cuáles faltan;
- probar especialmente correcciones tipo `200 → perdón → 250 mil euros`;
- confirmar que Conservador cae a KEEP/REVIEW ante conflicto;
- no introducir modelos semánticos sin un caso de uso medible y bounded por candidates/guardas deterministas.

### 2D — Scope de correcciones + fillers contextuales — FUTURA

- inferir de forma segura qué parte anterior es la toma incorrecta y qué parte posterior es la corrección válida;
- distinguir muletillas realmente eliminables de palabras/sonidos necesarios para naturalidad/significado;
- límites de frase y join safety;
- ampliar protección semántica sólo con evidencia real.

### 2E — Promotion to Edit Plan — FUTURA

Sólo después de 2C/2D:

- decidir qué clases pueden ser auto-aplicables;
- thresholds por modo;
- convertir únicamente decisiones inequívocamente seguras en Edit Plan;
- verificar joins/removedText;
- mantener límite global de eliminación y fail-safe;
- el resto permanece `REVIEW / KEEP`.

## Fase 3 — Calidad audiovisual / auditoría

Normalización, joins, denoise controlado, removedText definitivo, join audit, post-render verification, informe y rendimiento.

## Fase 4 — UX mínima

Seleccionar vídeo, audio externo opcional, confirmar sync, analizar, revisar, renderizar y abrir outputs. CLI se mantiene para tests/automation.

## Fase 5 — Portable Release Hardening

Build Windows limpia, ZIP final, versiones/digests inmutables, optimización de bundle, estrategia final de modelos, SHA-256, manifest, notices/licencias y zero-install/offline.

## Fase 6 — Extras

Subtítulos visuales, reframe, zooms, shorts, B-roll y otras funciones después del Cleaner fiable.

## Orden inmediato

1. crear corpus/fixtures de validación semántica real;
2. medir falsos positivos/falsos negativos de candidates + decisions;
3. tensionar cifras/unidades/negaciones/sujeto/tiempo/entidades;
4. resolver scope seguro de correcciones explícitas;
5. validar fillers contextuales;
6. mantener `executable=false` hasta disponer de evidencia suficiente;
7. no promover nada a Edit Plan antes de superar estas validaciones.
