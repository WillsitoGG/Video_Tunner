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

### 1A.1 Core portable — PASS

GitHub Actions run #1 (`33600174568`) validó en Windows:

- PyInstaller 6.22.2 `onedir`;
- `Video_Tunner.exe` + `_internal/`;
- FFmpeg/ffprobe locales en `Tools/ffmpeg/bin`;
- `Models/Config/Temp/Cache/Logs/Output` locales;
- ejecución desde ruta con espacios;
- PATH de prueba sin Python ni FFmpeg externos;
- `doctor`, `probe`, `clean`, render y ffprobe PASS;
- ZIP temporal core `122677058` bytes;
- no artifacts almacenados.

### 1A.2 Simplificación VAD — CERRADA

Backend elegido:

```text
faster-whisper
  ├─ CTranslate2 → Whisper
  └─ ONNX Runtime + silero_vad_v6.onnx → VAD
```

No empaquetar standalone `silero-vad` + Torch/torchaudio salvo nueva evidencia que lo justifique.

### 1A.3 Modelo local/offline — IMPLEMENTADO / PENDIENTE DE RUN

Estrategia:

```text
Models/whisper/<modelo>/
```

- el modelo queda fuera del EXE y de `_internal`;
- se puede cambiar de modelo sin recompilar;
- `model fetch` descarga mediante staging local `Temp/model-downloads`;
- cache de adquisición bajo `Cache/huggingface`;
- sólo se publica como disponible tras verificar `config.json`, `model.bin`, `tokenizer.json`;
- portable strict no resuelve silenciosamente modelos desde caches globales;
- tras adquisición debe poder inferir offline.

Modelo de producto previsto: `large-v3-turbo`.
Modelo de spike: `tiny`, exclusivamente para demostrar packaging/runtime con coste razonable.

### 1A.4 ML frozen sub-spike — SIGUIENTE VALIDACIÓN

Versiones críticas fijadas para reducir variabilidad:

- faster-whisper 1.2.1;
- CTranslate2 4.8.1;
- ONNX Runtime 1.29.0;
- tokenizers 0.23.1;
- PyInstaller 6.22.2.

Workflow manual: `.github/workflows/portable-ml-spike.yml`.

Debe demostrar en una única ejecución deliberada:

- source tests con stack analysis;
- frozen imports reales, no sólo `find_spec`;
- DLL loading CTranslate2 y ONNX Runtime;
- PyAV/tokenizers;
- asset Silero V6 ONNX empaquetado;
- PATH aislado sin Python/FFmpeg externos;
- `model fetch tiny` dentro de `Models/`;
- fixture hablado upstream pequeño;
- `HF_HUB_OFFLINE=1` después de adquirir modelo;
- `analyze` frozen/offline con Whisper real + VAD real;
- transcript con palabras;
- analysis/candidates sin edits automáticos;
- tamaño + SHA-256 del ZIP temporal;
- cero artifacts pesados.

### Cierre Fase 1A

Cerrar cuando:

- core portable PASS Windows;
- ML runtime frozen PASS Windows;
- estrategia Models local/offline demostrada;
- dependencias principales/versiones conocidas;
- tamaño y riesgos documentados.

Si PyInstaller pasa el ML sub-spike, se mantiene como base provisional. Nuitka sólo se evalúa ante un problema o ventaja medible.

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

1. Ejecutar/corregir **1A.4 ML frozen sub-spike**.
2. Cerrar Fase 1A si pasa.
3. Implementar **Fase 1B sync/master audio**.
4. Adaptar `analyze` y validar Fase 1C con `large-v3-turbo` sobre vídeo hablado real.
5. Entrar en Fase 2 semántica.
