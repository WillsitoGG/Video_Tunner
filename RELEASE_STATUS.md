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
- Fase 2C: **SIGUIENTE — validación semántica real / scope de correcciones**

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

Run `33640872486` — SUCCESS:

- 41 tests PASS;
- frozen analysis PASS;
- embedded/external master PASS;
- external +0.500 s → +0.49581 s;
- automatic edits 0;
- artifacts 0.

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

Modelo de validación:

```text
repo: rtlingo/mobiuslabsgmbh-faster-whisper-large-v3-turbo
revision: 6bd64462dd562f8062828f585c3709aa52df0083
model.bin sha256: e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da
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

Run final `33659725847` — SUCCESS:

```text
Ran 48 tests in 6.469s
OK
```

Doctor PASS, sync E2E PASS, artifacts 0.

## Fase 2B — Semantic Decisions + Protection v1

Contrato implementado:

```text
candidate != semantic decision != edit
PROPOSED_CUT != executable CUT
```

Decisiones posibles:

```text
KEEP
REVIEW
PROPOSED_TRIM
PROPOSED_CUT
```

Todas permanecen:

```text
executable = false
auto_apply = false
```

`analysis.json` actual usa **schema v3** y separa:

```text
candidates[]
semantic_decisions[]
```

Safety:

```text
semantic_protection_enabled = true
semantic_decisions_are_not_edits = true
semantic_decisions_executable = false
```

Guardas v1:

- integridad de span / word indices / timestamps / `removed_text`;
- cifras;
- importes, porcentajes y unidades;
- negaciones;
- persona/sujeto;
- tiempo/aspecto;
- causalidad/contraste;
- señal heurística de entidades.

Run `33661062365` — FAILURE diagnosticado:

```text
Ran 55 tests in 6.097s
54 PASS
1 FAIL
```

Único fallo: un test heredado esperaba schema v2 en vez del schema v3 deliberado. Todos los tests nuevos de 2B y los E2E de sync pasaron. Se corrigió únicamente el test, no código productivo.

Run final `33741195594` — **SUCCESS**:

```text
Ran 55 tests in 6.671s
OK
```

- Semantic Decisions/Protection PASS;
- schema v3 PASS;
- E2E FFmpeg/sync PASS;
- `video-tunner doctor` PASS;
- artifacts 0;
- `automatic_edits = 0`.

Ver `Validation/phase2-semantic-protection.md`.

## Pendiente antes de una Release

- Fase 2C: corpus/fixtures reales con retomas, errores y autocorrecciones;
- medir falsos positivos/falsos negativos;
- resolver scope seguro `intento incorrecto → corrección válida`;
- fillers contextuales;
- límites de frase y join safety;
- no promover semantic decisions al Edit Plan hasta disponer de evidencia suficiente;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- decidir estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión sustituida para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
