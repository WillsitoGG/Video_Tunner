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
- Fase 2: **siguiente milestone — semantic cleaner review-only**

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

Implementado:

- embedded/external ingest;
- master FLAC 48 kHz;
- auto-sync multi-anchor;
- offset positivo/negativo;
- confidence;
- drift ppm/time scale;
- residual RMS;
- coverage;
- manual `--offset` + `--drift-ppm`;
- `review_required` sin master ante evidencia insuficiente;
- metadata + SHA-256 auditable;
- master final con duración exacta de la timeline del vídeo.

Foundation `33634775313` — SUCCESS tras corregir PTS/padding.

Hardening `33639009841` — SUCCESS:

- 37 tests PASS;
- offset negativo E2E PASS;
- drift a nivel de media +1000 ppm PASS;
- low/flat signal => `review_required`, sin master;
- manual override sin audio de cámara PASS;
- coverage externa parcial + warning PASS;
- artifacts: 0.

Ver `Validation/sync-foundation-spike.md` y `Validation/sync-hardening.md`.

## Fase 1C — master audio analysis

Integración implementada:

- `analyze` resuelve master embebido o externo vía ingest;
- acepta override manual;
- puede reutilizar un master pre-resuelto sólo junto con `ingest.json`;
- verifica SHA-256 del vídeo fuente;
- Whisper y Silero VAD usan exactamente el mismo master;
- timestamps permanecen sobre timeline de vídeo;
- `review_required` detiene el pipeline antes de Whisper/VAD;
- `analysis.json` schema v2 registra provenance;
- candidates siguen sin auto-apply;
- embedded master preserva offset interno de pista y se extiende exactamente a la timeline del vídeo.

Run `33640872486` — **SUCCESS**, 2026-09-02:

- 41 tests PASS;
- build frozen analysis PASS;
- stack ML + NumPy + Silero ONNX operativos sin Python/FFmpeg externos en PATH;
- inferencia posterior con `HF_HUB_OFFLINE=1`;
- embedded retrasado: 89 palabras, 11 pause candidates, vídeo/master `45.6 / 45.6 s`;
- external auto-sync: 88 palabras, 9 pause candidates;
- offset real `+0.500 s` → estimado `+0.49581 s`;
- confidence `1.0`;
- drift estimado `192.308 ppm`;
- vídeo/master external `44.58275 / 44.58275 s`;
- automatic edits: `0`;
- artifacts: `0`.

Ver `Validation/master-audio-analysis-spike.md`.

## Fase 1C — modelo objetivo + español real

Run definitivo `33656235038` — **SUCCESS**, 2026-09-02.

Configuración:

```text
large-v3-turbo
CPU
int8
language=es
portable strict
HF_HUB_OFFLINE=1 durante inferencia
```

Resultados:

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

Criterio predefinido WER `<= 15%`: PASS.
Todos los checks de word timestamps: PASS.
El único error textual fue una `y` extra al final.

Modelo de validación fijado por commit y SHA-256:

```text
repo: rtlingo/mobiuslabsgmbh-faster-whisper-large-v3-turbo
revision: 6bd64462dd562f8062828f585c3709aa52df0083
model.bin sha256: e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da
```

Los runs `33652410474`, `33653108940`, `33653826702` y `33655947559` fallaron antes de inferencia por infraestructura/adquisición. Ver diagnóstico completo en `Validation/spanish-large-v3-turbo-plan.md`.

**Conclusión: Fase 1C COMPLETADA.**

## Pendiente antes de una Release

- Fase 2 semantic cleaner: retomas, repeticiones, correcciones, fillers contextuales, decision layer y protección semántica;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- decidir estrategia final de distribución/adquisición del modelo objetivo basándose en tamaño, RAM y experiencia de usuario.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión sustituida para `Archive/`.

**No publicar una GitHub Release sin autorización expresa del usuario.**
