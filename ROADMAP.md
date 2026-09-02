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

Incluye todos los E2E de sync y 7 tests nuevos de semantic candidates/integración. Artifacts `0`.

Run previo `33659514611`: falló por una inconsistencia preexistente de Manual CI (NumPy no instalado para E2E de sync), mientras todos los tests semánticos pasaban. El workflow ligero queda corregido con NumPy 2.5.2, sin instalar el stack ML completo.

Ver `Validation/phase2-semantic-candidates.md`.

### 2B — Semantic Decisions + Protection — SIGUIENTE

Antes de cualquier edit ejecutable, crear una capa explícita candidate → decision.

Salida inicial:

```text
KEEP
REVIEW
proposed TRIM
proposed CUT
```

pero:

```text
executable = false
auto_apply = false
```

Protecciones mínimas:

- números, importes, porcentajes y unidades;
- negaciones;
- sujeto/persona;
- tiempo verbal/aspecto;
- entidades/nombres relevantes cuando sean detectables;
- relación intento → versión corregida;
- conectores que cambien causalidad/contraste;
- límites de word timing;
- `removed_text` debe corresponder exactamente al span propuesto;
- segunda lectura de retoma/repetición no debe quedar dentro del span eliminado.

Validación requerida antes de avanzar:

- fixtures sintéticos con números y negaciones;
- habla real con errores/retomas deliberados;
- false-positive cases: énfasis, repetición intencional y frases legítimamente reutilizadas;
- Conservador debe caer a KEEP/REVIEW ante cualquier conflicto.

### 2C — Promotion to Edit Plan — FUTURA

Sólo después de 2B:

- decidir qué clases pueden ser auto-aplicables;
- thresholds por modo;
- convertir decisiones aprobadas en Edit Plan;
- verificar joins/removedText;
- mantener límite global de eliminación y fail-safe.

## Fase 3 — Calidad audiovisual / auditoría

Normalización, joins, denoise controlado, removedText, join audit, post-render verification, informe y rendimiento.

## Fase 4 — UX mínima

Seleccionar vídeo, audio externo opcional, confirmar sync, analizar, revisar, renderizar y abrir outputs. CLI se mantiene para tests/automation.

## Fase 5 — Portable Release Hardening

Build Windows limpia, ZIP final, versiones/digests inmutables, optimización de bundle, estrategia final de modelos, SHA-256, manifest, notices/licencias y zero-install/offline.

## Fase 6 — Extras

Subtítulos visuales, reframe, zooms, shorts, B-roll y otras funciones después del Cleaner fiable.

## Orden inmediato

1. implementar semantic decision/protection layer review-only;
2. proteger números/negaciones/sujeto/tiempo verbal/entidades;
3. modelar corrección intento → versión corregida;
4. crear fixtures específicos de riesgo semántico;
5. validar con habla real que contenga errores/retomas deliberados;
6. no promover nada a Edit Plan hasta superar estas guardas.
