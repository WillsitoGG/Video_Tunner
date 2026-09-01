# Release Status

## Estado actual

- Proyecto: Video_Tunner
- Versión de desarrollo: `0.1.0-dev`
- Release publicada: **no**
- ZIP portable final validado: **no**
- Windows 10/11 x64 validado manualmente: **no**
- Fase 0: bootstrap implementado
- Fase 0.5: technology harvest definido
- Fase 1A: portable core spike implementado; ejecución Windows real pendiente
- Fase 1B: ingesta dual + sincronización A/V pendiente
- Fase 1C: transcript/candidates parcialmente implementados; master audio + runtime real pendientes

## Portable Foundation

Decisión provisional para spike:

- PyInstaller 6.22.2 `onedir`;
- FFmpeg/ffprobe bundled;
- modo portable estricto sin PATH fallback;
- Silero VAD vía ONNX de faster-whisper, evitando standalone silero-vad/Torch.

No considerar Fase 1A validada hasta que `portable-spike.yml` pase en Windows. El primer PASS core tampoco valida todavía el perfil ML frozen; CTranslate2/ONNX Runtime/model assets requieren un sub-spike posterior.

No existe todavía ningún paquete final que deba figurar en `SHA256SUMS.txt` ni ninguna versión sustituida para `Archive/`.

No publicar una GitHub Release sin autorización expresa del usuario.
