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
- Fase 1C: transcript/candidates parcialmente implementados; pendiente adaptación a master audio + modelo objetivo

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
- PyAV 18.1.0;
- Silero VAD V6 ONNX frozen;
- modelo `tiny` local bajo `Models/whisper/tiny`;
- `HF_HUB_OFFLINE=1` + frozen `analyze` PASS;
- 22 palabras, 3 pause candidates, 0 automatic edits;
- bundle ML temporal sin modelo `212334854` bytes (~202.5 MiB);
- SHA-256 `F1208C6E830A60CB06C1AB7781C0D7D60161341AC5C9DEA3D12EFB3F2BE3AF05`;
- artifacts: 0.

## Fase 1B — sync foundation + hardening

Implementado:

- modo embedded y external;
- `ingest` CLI;
- master FLAC 48 kHz;
- auto-sync multi-anchor;
- offset positivo/negativo;
- confidence;
- drift ppm/time scale;
- residual RMS;
- coverage;
- manual `--offset` + `--drift-ppm`;
- `review_required` sin master cuando la evidencia es insuficiente;
- metadata + SHA-256 auditable;
- master final con duración exacta de la timeline del vídeo.

### Foundation Windows

- run `33633846344` — FAILURE: aserción inicial incorrecta;
- run `33634121264` — FAILURE útil: descubrió master `88.756 s` frente a vídeo `90.000 s`;
- run `33634775313` — SUCCESS tras corregir PTS/padding.

### Hardening Windows

Run `33639009841` — **SUCCESS**.

- 37 tests PASS;
- offset negativo E2E PASS;
- drift a nivel de media con `+1000 ppm` objetivo PASS dentro de tolerancia;
- low/flat signal => `review_required`, sin master;
- manual override sin audio de cámara PASS;
- coverage externa parcial + warning PASS;
- timeline regression PASS;
- fixture nominal: `+1.500 s`, confidence `1.000`, 7 anchors, drift `0 ppm`, vídeo/master `90/90 s`;
- artifacts: 0.

Ver `Validation/sync-foundation-spike.md` y `Validation/sync-hardening.md`.

Los thresholds de auto-sync siguen siendo provisionales y deberán calibrarse con grabaciones reales antes de Release.

## Pendiente antes de una Release

- Fase 1C: adaptar `analyze` al master audio;
- validar pipeline completo embedded/external con Whisper + VAD;
- validar `large-v3-turbo` con vídeo hablado real en español;
- semantic cleaner;
- calidad audiovisual/audit;
- UX;
- Release Hardening + licencias/notices + Windows limpio real.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión sustituida para `Archive/`.

**No publicar una GitHub Release sin autorización expresa del usuario.**
