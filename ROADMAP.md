# ROADMAP — Video_Tunner

## Principios

- Windows 10/11 x64 portable: ZIP → descomprimir → ejecutar.
- Vídeo con audio embebido o vídeo + audio externo.
- Resolver master audio y sincronización antes de transcripción/VAD/semántica.
- Originales intactos y decisiones auditables.
- Ante baja confianza: revisión/manual, no adivinar.
- CI pesada sólo cuando aporta evidencia nueva.

## Fase 0 — Bootstrap — COMPLETADA

CLI, FFmpeg/ffprobe, probe, Cleaner de silencios, Edit Plan, render, tests y CI manual.

## Fase 0.5 — Technology Harvest — COMPLETADA

Repo propio, no fork. vcut/Cadence-Lab/ai-video-editor como referencias selectivas y trazables.

## Fase 1A — Portable Foundation — COMPLETADA

### Core portable — PASS

Run `33600174568`:

- PyInstaller 6.22.2 `onedir`;
- `Video_Tunner.exe` + runtime Python;
- FFmpeg/ffprobe locales;
- layout `Models/Config/Temp/Cache/Logs/Output`;
- PATH de prueba sin Python/FFmpeg externos;
- `doctor`, `probe`, `clean`, render y ffprobe PASS;
- ZIP temporal core `122677058` bytes;
- 0 artifacts.

### Stack ML portable — PASS

Run `33621357438`:

- faster-whisper 1.2.1;
- CTranslate2 4.8.1;
- ONNX Runtime 1.29.0;
- tokenizers 0.23.1;
- PyAV 18.1.0;
- Silero V6 ONNX bundled;
- imports/DLLs frozen PASS;
- modelo `tiny` adquirido dentro de `Models/whisper/tiny`;
- `HF_HUB_OFFLINE=1` + `Video_Tunner.exe analyze` PASS;
- 22 palabras y 3 candidatos pause;
- 0 edits automáticos;
- ZIP runtime ML sin modelo `212334854` bytes (~202.5 MiB);
- 0 artifacts.

### Decisiones 1A

- PyInstaller `onedir` continúa como base provisional.
- Modelos fuera del EXE bajo `Models/whisper/<modelo>`.
- `model status` / `model fetch` y staging/cache locales.
- Silero VAD vía faster-whisper/ONNX; no standalone Torch.
- `large-v3-turbo` sigue siendo el modelo objetivo de producto; `tiny` sólo validó runtime.
- La reducción del bundle ONNX queda para optimización posterior; no justifica otra Action ahora.

## Fase 1B — Ingesta dual + sincronización A/V — SIGUIENTE

### 1B.1 Contrato de ingesta

Modo A:

```text
video + audio embebido → master audio
```

Modo B:

```text
video + audio externo → sincronización → audio externo sincronizado = master audio
```

Registrar vídeo, duración, pistas embebidas, audio externo opcional, propiedades de audio, master seleccionado, estado de sync y mapping temporal.

### 1B.2 Auto-sync por offset

Cuando exista audio de referencia en cámara:

1. extraer referencias mono;
2. correlación gruesa;
3. correlación fina;
4. estimar offset positivo/negativo;
5. calcular confidence;
6. validar en varias ventanas.

Debe tolerar niveles y ruido diferentes y audio externo empezando antes o después del vídeo.

### 1B.3 Fallback/manual

- CLI con audio externo opcional;
- offset manual/override;
- sin referencia suficiente no aplicar auto-sync;
- metadata distingue estimación automática y override manual.

### 1B.4 Drift

- anchors en varias ventanas;
- offset como función del tiempo;
- drift estimado en ppm/ms por hora;
- medir error residual;
- aplicar corrección temporal sólo si mejora la alineación;
- preservar pitch/calidad.

### 1B.5 Metadata

Registrar método, offset, confidence, anchors, residuos, drift, corrección, override y avisos de cobertura.

### 1B.6 Tests

- embedded audio;
- external ±offset conocido;
- señal con niveles/ruido diferentes;
- señal ambigua;
- vídeo sin referencia de audio;
- offset manual;
- audio externo más corto/largo;
- drift sintético;
- consistencia temporal post-sync;
- rutas con espacios.

### Cierre 1B

Master audio explícito, ingest embebido/externo, offset automático con confidence, fallback manual, drift validado y metadata auditable.

## Fase 1C — Transcripción + VAD sobre master audio

- adaptar `analyze` a master audio;
- `large-v3-turbo` como modelo objetivo;
- word timestamps + TXT/JSON/SRT;
- Silero VAD ONNX;
- candidates;
- validación real en español;
- medir calidad/velocidad/tamaño del modelo objetivo.

## Fase 2 — Cleaner inteligente

Retomas, repeticiones, correcciones, muletillas contextuales, KEEP/TRIM/CUT/REVIEW, protección semántica, confidence y modos Conservador/Agresivo.

## Fase 3 — Calidad audiovisual / auditoría

Normalización, joins, reducción de ruido controlada, removedText, audit, post-render verification, informe y rendimiento.

## Fase 4 — UX mínima

Seleccionar vídeo, audio externo opcional, confirmar sync, modo, analizar, revisar, renderizar y abrir outputs. Mantener CLI para tests/automatización.

## Fase 5 — Portable Release Hardening

Build Windows limpia, ZIP final, versiones/digests inmutables, optimización de bundle, estrategia final de modelos, SHA-256, manifest, notices/licencias y prueba zero-install/offline.

## Fase 6 — Extras

Subtítulos visuales, reframe, zooms, shorts, B-roll y otras funciones sólo después de un Cleaner fiable.

## Orden inmediato

1. Implementar Fase 1B: ingesta dual + master audio.
2. Auto-sync offset + confidence + override manual.
3. Drift multi-window + corrección validada.
4. Adaptar `analyze` al master audio.
5. Validar `large-v3-turbo` + VAD sobre vídeo hablado real en español.
6. Entrar en Fase 2 semántica.
