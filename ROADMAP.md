# ROADMAP — Video_Tunner

Roadmap vigente tras fijar dos requisitos estructurales:

1. aplicación portable Windows 10/11 x64;
2. vídeo con audio embebido o vídeo + audio externo sincronizable.

La prioridad es reducir riesgo técnico temprano: **portable + ingest/sync antes de ampliar IA semántica**.

## Principios

- Portabilidad es invariante de arquitectura.
- Master audio y relación temporal con vídeo deben resolverse antes de transcripción/VAD/semántica.
- Originales intactos.
- Sync/ediciones auditables.
- Baja confianza => REVIEW/manual, no adivinar.
- CI pesada sólo cuando aporta evidencia nueva.

---

## Fase 0 — Bootstrap — COMPLETADA

- repo/documentación;
- Python CLI;
- FFmpeg/ffprobe;
- probe;
- silence Cleaner;
- Edit Plan;
- render;
- tests sintéticos;
- CI manual.

## Fase 0.5 — Technology Harvest — COMPLETADA

- repo propio, no fork;
- vcut/Cadence-Lab/ai-video-editor como referencias;
- provenance trazable.

---

## Fase 1A — Portable Foundation — EN CURSO

### 1A.1 Core portable spike — IMPLEMENTADO / RUN WINDOWS PENDIENTE

Decisiones:

- PyInstaller 6.22.2 `onedir` para el primer spike;
- `Video_Tunner.exe` + `_internal/`;
- FFmpeg/ffprobe locales en `Tools/ffmpeg/bin`;
- `Models/Config/Temp/Cache/Logs/Output` locales;
- frozen/strict runtime sin fallback a PATH;
- workflow manual `portable-spike.yml`;
- validación en ruta con espacios y PATH sin Python/FFmpeg;
- ZIP temporal sólo para hash/tamaño, no artifact.

FFmpeg del spike usa build Windows x64 GPL de la rama estable 9.0 de BtbN porque el renderer actual usa `libx264`. El URL flotante es aceptable sólo para el spike; Release debe fijar asset/digest.

### 1A.2 Simplificación VAD — IMPLEMENTADA

Se elimina la dependencia directa `silero-vad`.

Nuevo backend:

```text
faster-whisper
  ├─ CTranslate2 → Whisper
  └─ ONNX Runtime + silero_vad_v6.onnx → VAD
```

Esto evita empaquetar Torch + torchaudio sólo para VAD.

### 1A.3 Acceptance core

El run Windows debe demostrar:

- build `onedir`;
- bundled FFmpeg/ffprobe;
- no Python/FFmpeg externos;
- doctor/probe/clean reales;
- render validado con ffprobe bundled;
- rutas con espacios;
- package size/SHA.

### 1A.4 ML frozen sub-spike — SIGUIENTE DENTRO DE 1A

Después de core PASS:

- instalar `.[analysis]` durante build;
- congelar faster-whisper;
- validar CTranslate2 DLLs;
- validar ONNX Runtime DLLs;
- comprobar inclusión/localización de `silero_vad_v6.onnx`;
- comprobar modelo desde `<runtime>/Models`;
- ejecutar VAD real mínimo;
- ejecutar Whisper real con un modelo de prueba razonable;
- medir tamaño portable core vs ML;
- decidir si PyInstaller sigue siendo base o Nuitka aporta ventaja real.

No descargar `large-v3-turbo` en CI ordinaria si un modelo menor puede demostrar exclusivamente packaging/runtime. La calidad STT se validará aparte con el modelo objetivo.

### Cierre Fase 1A

No cerrar hasta demostrar:

- core portable PASS Windows;
- ML runtime portable viable;
- estrategia de modelos local/offline definida;
- dependencias/licencias principales identificadas;
- tamaño y riesgos conocidos.

---

## Fase 1B — Ingesta dual + sincronización A/V

### Entradas

A) vídeo con audio embebido → master audio.

B) vídeo + audio externo → sync → master audio externo.

### Auto-sync

- extracción de referencias mono;
- correlación gruesa + fina;
- offset positivo/negativo;
- confidence;
- validación multi-window;
- anchors auditables;
- manual override.

### Drift

- estimar diferencia temporal progresiva;
- registrar ppm/ms-h;
- error residual;
- corregir sólo si mejora validada;
- preservar pitch y calidad.

### Fallbacks

- sin camera reference => manual offset/review;
- low confidence => no auto-apply;
- external audio shorter/longer => política explícita;
- nunca alternar silenciosamente camera/external audio.

### Tests

- embedded;
- external ±offset;
- noisy signal;
- ambiguous signal;
- no reference;
- manual override;
- external coverage mismatch;
- synthetic drift;
- post-cut sync.

---

## Fase 1C — Transcripción + VAD reales

Sobre master audio ya resuelto:

- faster-whisper `large-v3-turbo` como modelo objetivo;
- word timestamps;
- TXT/JSON/SRT;
- Silero VAD ONNX via faster-whisper;
- candidates;
- cache local por hash cuando compense;
- validación real en español y vídeo hablado.

Parte del código ya existe; debe migrar de `video input audio` a abstracción de master audio.

---

## Fase 2 — Cleaner inteligente

- retakes;
- repetitions;
- corrections/errors;
- contextual fillers;
- KEEP/TRIM/CUT/REVIEW;
- semantic protection;
- cifras/negaciones/nombres;
- conservative/aggressive;
- candidates → decisions → Edit Plan.

No empezar antes de que 1A y 1B estén suficientemente demostradas.

---

## Fase 3 — Calidad audiovisual / auditoría

- loudness normalization;
- join smoothing;
- denoise sólo con control/default seguro;
- removedText;
- join audit;
- post-render verification;
- informe HTML;
- rendimiento.

---

## Fase 4 — UX mínima

- elegir vídeo;
- audio externo opcional;
- mostrar/confirmar sync;
- conservative/aggressive;
- analizar;
- revisar;
- renderizar;
- abrir output/informe.

CLI permanece para automation/tests.

---

## Fase 5 — Portable Release Hardening

No inicia portabilidad; endurece lo probado desde 1A:

- clean Windows build;
- final ZIP;
- immutable dependency versions/digests;
- runtime/tools/models strategy;
- zero-install;
- offline after model acquisition;
- SHA256 + manifest;
- notices/licenses;
- clean environment validation.

---

## Fase 6 — Extras

Después del Cleaner fiable:

- burned captions;
- reframe;
- zooms;
- clips/shorts;
- B-roll;
- otras features editoriales.

## Orden inmediato

1. Ejecutar/corregir **1A.1 portable core Windows**.
2. Ejecutar/corregir **1A.4 ML frozen sub-spike**.
3. Cerrar Fase 1A.
4. Implementar **Fase 1B sync/master audio**.
5. Adaptar `analyze` y validar Fase 1C real.
6. Entrar en Fase 2 semántica.
