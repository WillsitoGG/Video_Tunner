# Release Status

## Estado actual

- Proyecto: Video_Tunner
- Versión de desarrollo: `0.1.0-dev`
- Release publicada: **no**
- ZIP portable final validado: **no**
- Windows 10/11 x64 validado manualmente por Guille: **no**
- Fase 0: bootstrap implementado
- Fase 0.5: technology harvest definido
- Fase 1A: **Portable Foundation PASS en Windows (core + stack ML CPU)**
- Fase 1B: **COMPLETADA — dual ingest + sync/drift + hardening Windows PASS**
- Fase 1C: **COMPLETADA — master audio → Whisper/VAD + `large-v3-turbo` sobre español real PASS**
- Fase 2: **EN CURSO — Semantic Candidates v1 COMPLETADO; decision/protection layer pendiente**

## Portable Foundation — core

Run `33600174568` — SUCCESS, 2026-09-02.

- PyInstaller 6.22.2 `onedir`;
- bundled FFmpeg/ffprobe;
- PATH sin Python/FFmpeg externos;
- `doctor`, `probe`, `clean`, render y ffprobe PASS;
- ZIP temporal `122677058` bytes;
- SHA-256 `5F3CFE09F017DE0421B906CE529822F830C8FFDE0731161AAFA42120464F4E97`;
- artifacts: 0.

## Portable Foundation — ML

Run `33621357438` — SUCCESS, 2026-09-02.

- faster-whisper 1.2.1;
- CTranslate2 4.8.1;
- ONNX Runtime 1.29.0;
- tokenizers 0.23.1;
- NumPy 2.5.2;
- PyAV 18.1.0;
- Silero VAD V6 ONNX frozen;
- modelo local bajo `Models/whisper/<modelo>`;
- frozen/offline Whisper + VAD PASS;
- bundle ML temporal sin modelo `212334854` bytes (~202.5 MiB);
- artifacts: 0.

## Fase 1B — sync foundation + hardening

Implementado embedded/external ingest, master FLAC 48 kHz, auto-sync multi-anchor, offset positivo/negativo, confidence, drift, residual, coverage, manual override, `review_required`, SHA-256 auditable y master con duración exacta de timeline.

Foundation `33634775313` — SUCCESS tras corregir PTS/padding.

Hardening `33639009841` — SUCCESS: 37 tests, negative offset, drift +1000 ppm, low-signal review, manual override y partial coverage. Artifacts 0.

## Fase 1C — master audio analysis

Run `33640872486` — SUCCESS:

- 41 tests PASS;
- build frozen analysis PASS;
- stack ML + Silero ONNX operativo;
- embedded/external master PASS;
- external +0.500 s → +0.49581 s;
- automatic edits 0;
- artifacts 0.

## Fase 1C — modelo objetivo + español real

Run definitivo `33656235038` — SUCCESS.

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
model staged              1621665983 bytes / 1546.5 MiB
candidates                16
automatic edits           0
video/master duration     46.58025 / 46.58025 s
artifacts                 0
```

Criterio WER `<=15%`: PASS. Todos los checks temporales PASS. Inferencia `HF_HUB_OFFLINE=1` PASS.

Modelo de validación fijado:

```text
repo: rtlingo/mobiuslabsgmbh-faster-whisper-large-v3-turbo
revision: 6bd64462dd562f8062828f585c3709aa52df0083
model.bin sha256: e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da
```

**Conclusión: Fase 1C COMPLETADA.**

## Fase 2A — Semantic Candidates v1

Implementado e integrado en `analysis.json`:

```text
possible_repetition
possible_retake
explicit_correction
```

Todo candidato permanece:

```text
decision = undecided
suggested_decision = REVIEW
auto_apply = false
span_safe_for_auto_apply = false
```

Evidence incluye `removed_text`, contexto, índices/timestamps, confidence y evidencia específica. En retomas/repeticiones la lectura posterior se mantiene fuera del span candidato. En correcciones explícitas el detector marca sólo el marcador y no adivina todavía qué intento anterior debe eliminarse.

### Validación

Run `33659514611` — FAILURE de configuración preexistente de Manual CI: tres E2E de sync necesitaron NumPy, que el workflow core no instalaba. Los 7 tests nuevos semánticos pasaron.

Corrección: Manual CI ligero instala paquete base + `numpy==2.5.2`, sin stack ML pesado.

Run `33659725847` — **SUCCESS**:

```text
Ran 48 tests in 6.469s
OK
```

- semantic unit tests PASS;
- semantic pipeline integration PASS;
- sync E2E PASS;
- doctor PASS;
- artifacts 0.

Ver `Validation/phase2-semantic-candidates.md`.

## Pendiente antes de una Release

- Fase 2B semantic decisions/protection: números, negaciones, sujeto/persona, tiempo verbal, entidades y relación intento→corrección;
- validar habla real con errores/retomas deliberados;
- no promover candidates al Edit Plan hasta completar estas guardas;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- decidir estrategia final de distribución/adquisición del modelo según tamaño, RAM y UX.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión sustituida para `Archive/`.

**No publicar una GitHub Release sin autorización expresa del usuario.**
