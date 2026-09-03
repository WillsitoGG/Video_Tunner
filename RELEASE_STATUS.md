# Release Status

## Estado actual

- Proyecto: Video_Tunner
- Versión de desarrollo: `0.1.0-dev`
- Release publicada: **no**
- ZIP portable final validado: **no**
- Windows 10/11 x64 validado manualmente por Guille: **no**
- Fase 0: COMPLETADA
- Fase 0.5: COMPLETADA
- Fase 1A: **COMPLETADA — Portable Foundation Windows core + ML PASS**
- Fase 1B: **COMPLETADA — dual ingest + sync/drift + hardening Windows PASS**
- Fase 1C: **COMPLETADA — master audio → Whisper/VAD + `large-v3-turbo` español real PASS**
- Fase 2A: **COMPLETADA — Semantic Candidates v1**
- Fase 2B: **COMPLETADA — Semantic Decisions + Protection v1**
- Fase 2C: **EN CURSO — benchmark foundation v1 COMPLETADA; positivos humanos espontáneos pendientes**

## Evidencia portable / ML

### Core — `33600174568`

SUCCESS.

- PyInstaller 6.22.2 `onedir`;
- bundled FFmpeg/ffprobe;
- PATH sin Python/FFmpeg externos;
- `doctor`, `probe`, `clean`, render y ffprobe PASS;
- ZIP temporal `122677058` bytes;
- SHA-256 `5F3CFE09F017DE0421B906CE529822F830C8FFDE0731161AAFA42120464F4E97`;
- artifacts 0.

### ML — `33621357438`

SUCCESS.

- faster-whisper 1.2.1;
- CTranslate2 4.8.1;
- ONNX Runtime 1.29.0;
- tokenizers 0.23.1;
- NumPy 2.5.2;
- PyAV 18.1.0;
- Silero VAD V6 ONNX frozen;
- frozen/offline Whisper + VAD PASS;
- artifacts 0.

## Fase 1B — sync

Foundation `33634775313` — SUCCESS.

Hardening `33639009841` — SUCCESS: 37 tests, offset negativo, drift +1000 ppm, low-signal review, manual override y partial coverage. Artifacts 0.

## Fase 1C — master audio + modelo objetivo

Run `33640872486` — SUCCESS: 41 tests PASS, frozen analysis PASS, embedded/external master PASS, automatic edits 0, artifacts 0.

Run target Spanish `33656235038` — SUCCESS:

```text
fixture duration           46.58025 s
reference words           61
hypothesis words          62
word errors               1
WER                       1.64%
median word duration      0.36 s
analyze                   22.609 s
real-time factor          0.4854
peak working set          1818.7 MiB
model staged              1546.5 MiB
candidates                16
automatic edits           0
artifacts                 0
```

## Fase 2A — Semantic Candidates v1

Clases:

```text
possible_repetition
possible_retake
explicit_correction
```

Todo candidate sigue review-only:

```text
decision = undecided
suggested_decision = REVIEW
auto_apply = false
span_safe_for_auto_apply = false
```

Run final `33659725847` — SUCCESS: 48 tests, doctor PASS, sync E2E PASS, artifacts 0.

## Fase 2B — Semantic Decisions + Protection v1

Contrato:

```text
candidate != semantic decision != edit
PROPOSED_CUT != executable CUT
```

Todas las decisiones permanecen:

```text
executable = false
auto_apply = false
```

`analysis.json` usa schema v3 y separa `candidates[]` de `semantic_decisions[]`.

Run final `33741195594` — **SUCCESS**:

```text
Ran 55 tests in 6.671s
OK
```

- Semantic Decisions/Protection PASS;
- E2E FFmpeg/sync PASS;
- `video-tunner doctor` PASS;
- artifacts 0;
- `automatic_edits = 0`.

## Fase 2C — Semantic Validation Foundation v1

Se ha creado un benchmark etiquetado para separar calidad de detección y seguridad de decisiones.

Corpus v1 final:

```text
21 casos
11 constructed_positive
6 constructed_negative
4 human_speech_reference
11 eventos esperados
```

Los 4 controles humanos derivan de diálogos SpanishPod ya validados con audio + `large-v3-turbo` en `33656235038`; no son positivos humanos de retoma/autocorrección.

### Baseline

Run `33742519997` — SUCCESS:

```text
Ran 60 tests in 6.603s
FP                       2
FN                       0
precision           84.62%
recall             100.00%
F1                  91.67%
unsafe proposals         0
executable decisions     0
auto_apply decisions     0
```

Los FP observados fueron reutilización legítima cercana del opener y `quiero decir` literal. Ambos eran review-only.

### Tuneo

Sólo se endureció el detector Conservador:

- continuidad normal sin reparación => no retake;
- evidencia de vacilación/reparación sigue permitiendo retake;
- `quiero decir` / `I mean` se consideran ambiguos en contextos literales y siguen disponibles tras un intento previo.

### Final

Run `33743029443` — **SUCCESS**:

```text
Ran 64 tests in 6.588s
cases                    21
expected events          11
actual candidates        11
FP                        0
FN                        0
precision           100.00%
recall              100.00%
F1                  100.00%
decision mismatches       0
unsafe proposals          0
missing safe proposals    0
executable decisions      0
auto_apply decisions      0
artifacts                  0
```

`video-tunner doctor` y E2E FFmpeg/sync PASS.

**Limitación:** este 100% sólo acredita el corpus v1. Fase 2C no se cierra completamente hasta añadir positivos humanos reales con retomas/reinicios/autocorrecciones y medirlos con el mismo harness.

Ver `Validation/phase2c-semantic-validation.md`.

## Pendiente antes de una Release

- completar Fase 2C con positivos humanos reales;
- resolver scope seguro `intento incorrecto → corrección válida`;
- fillers contextuales;
- límites de frase y join safety;
- no promover semantic decisions al Edit Plan hasta evidencia suficiente;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- decidir estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión sustituida para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
