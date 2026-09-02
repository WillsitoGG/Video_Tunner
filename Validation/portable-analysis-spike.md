# Portable Analysis Spike — Fase 1A

## Estado

**IMPLEMENTADO / PENDIENTE DE EJECUCIÓN WINDOWS REAL**

Este sub-spike amplía el core portable ya validado para demostrar que el stack local de análisis puede funcionar congelado dentro del mismo `onedir` de Windows.

## Alcance

Perfil `analysis`:

- `faster-whisper==1.2.1`;
- `ctranslate2==4.8.1`;
- `onnxruntime==1.29.0`;
- `tokenizers==0.23.1`;
- PyAV como dependencia resuelta de faster-whisper;
- Silero VAD V6 ONNX incluido por faster-whisper;
- runtime Python congelado por PyInstaller 6.22.2;
- FFmpeg/ffprobe locales ya validados en el core.

## Estrategia de modelos

Los modelos Whisper NO se incrustan dentro de `Video_Tunner.exe` ni de `_internal/`.

Ruta portable:

```text
Models/whisper/<modelo>/
```

Un modelo se considera disponible únicamente si contiene al menos:

- `config.json`;
- `model.bin`;
- `tokenizer.json`.

Comandos:

```text
video-tunner model status <modelo>
video-tunner model fetch <modelo>
```

La descarga usa staging bajo `Temp/model-downloads` y cache bajo `Cache/huggingface`. Sólo después de verificar los ficheros mínimos se mueve el modelo a su destino definitivo.

En modo portable estricto, `analyze` no puede usar un nombre de modelo para resolver silenciosamente una caché externa: debe encontrar el modelo completo en `Models/whisper`.

## Workflow de validación

`.github/workflows/portable-ml-spike.yml`

Manual-only en estado permanente; no sube artifacts.

El modelo `tiny` se usa exclusivamente para demostrar empaquetado/runtime/inferencia con un coste razonable. No sustituye al modelo objetivo de producto `large-v3-turbo` ni valida su calidad.

El fixture hablado se descarga en runtime desde `SYSTRAN/faster-whisper` v1.2.1 (`tests/data/jfk.flac`) y no se versiona.

## Acceptance criteria

- [ ] Windows x64 job PASS.
- [ ] source tests con dependencias `analysis` PASS.
- [ ] build PyInstaller `onedir` perfil analysis PASS.
- [ ] `faster_whisper` import frozen PASS.
- [ ] CTranslate2 DLL loading PASS.
- [ ] ONNX Runtime DLL loading PASS.
- [ ] tokenizers/PyAV frozen PASS.
- [ ] `silero_vad_v6.onnx` localizable dentro del frozen bundle.
- [ ] Python y FFmpeg externos ausentes del PATH de prueba.
- [ ] modelo `tiny` descargado dentro de `Models/whisper/tiny`.
- [ ] modelo marcado disponible sólo tras verificar sus ficheros mínimos.
- [ ] `HF_HUB_OFFLINE=1` durante inferencia posterior a la adquisición.
- [ ] `analyze` frozen + offline produce transcript JSON.
- [ ] transcript contiene palabras reales (`word_count >= 5`).
- [ ] VAD real produce analysis JSON sin aplicar edits automáticos.
- [ ] tamaño + SHA-256 del ZIP temporal emitidos a logs.
- [ ] 0 artifacts pesados almacenados.

## Qué NO valida este sub-spike

- calidad STT de `large-v3-turbo`;
- rendimiento final sobre vídeos largos;
- CUDA/GPU;
- audio externo/sync/drift;
- protección semántica;
- UX final;
- paquete Release definitivo.

Si este sub-spike pasa, PyInstaller `onedir` queda demostrado como base viable para continuar Fase 1A y se puede pasar a Fase 1B. La optimización de tamaño y el modelo final se endurecerán antes de Release.
