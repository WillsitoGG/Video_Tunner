# Upstream Sources / Technology Harvest

Video_Tunner es producto propio y **no es un fork**.

Política:

1. registrar repositorio/licencia/commit de referencia;
2. distinguir idea, integración, adaptación y vendorización;
3. copiar sólo cuando sea necesario y mantener notices;
4. toda mejora upstream se revalida en Video_Tunner;
5. revisar nuevas releases/commits aunque no exista relación de fork.

## Railly/vcut

- Repo: `Railly/vcut`
- Licencia observada: MIT
- Referencia revisada: `2142cc54dc01a0d2272f1d99717b89cd1c7c9262` (2026-08-17)
- Rol: EDL/auditabilidad/joins/repeats/retakes/agent-first/audio-offset.

Patrones útiles:

- edits as data;
- source protection/hash;
- proposals vs approval;
- removedText/join checks;
- reproducible render;
- diagnostics sobre repeats/restarts en Whisper.

No adoptamos stack Node completo ni herramientas externas obligatorias.

## timkulbaev/ai-video-editor

- Repo: `timkulbaev/ai-video-editor`
- Licencia observada: MIT
- Referencia revisada: `cce2114019ca237a5e38468789ddac5eb764b9bd` (2026-02-24)
- Rol: referencia de pipeline Python talking-head.

Útil:

- extract audio → VAD → Whisper → decisions → assembly;
- modularidad.

No adoptamos eliminación automática de bursts cortos.

## JosephLeon/Cadence-Lab

- Repo: `JosephLeon/Cadence-Lab`
- Licencia observada: MIT
- Referencia revisada: `e4302c58723db54dc2ff82e3d957159f5812d79c` (2026-06-19)
- Rol: futura capa semántica.

Útil:

- clasificar función de pausas;
- KEEP/TRIM/CUT;
- context-aware retakes;
- deterministic candidates + bounded model decision;
- cache por content hash.

No adoptamos dependencia obligatoria Claude/Groq ni UI completa.

## SYSTRAN/faster-whisper

- Repo: `SYSTRAN/faster-whisper`
- Rol: dependencia directa de análisis y upstream de STT/VAD.
- Rango actual Video_Tunner: `>=1.2,<2`.

### STT

Se utiliza para Whisper mediante CTranslate2 y word timestamps.

### VAD — decisión Fase 1A

Video_Tunner deja de depender del paquete standalone `silero-vad`.

La implementación actual de faster-whisper contiene:

- `faster_whisper.vad` adaptado de Silero;
- `SileroVADModel` ejecutado con ONNX Runtime;
- asset `silero_vad_v6.onnx`;
- `faster_whisper.audio.decode_audio` para entrada 16 kHz;
- ONNX Runtime ya dentro de sus dependencias.

Esto permite compartir stack con STT y evita añadir Torch + torchaudio exclusivamente para VAD.

La integración se hace mediante API Python del paquete; no se copia el código de faster-whisper a Video_Tunner.

Riesgo portable pendiente: PyInstaller debe recopilar correctamente el asset ONNX y DLLs de onnxruntime/CTranslate2. Se validará en Fase 1A ML frozen sub-spike.

## snakers4/silero-vad

- Repo: `snakers4/silero-vad`
- Licencia observada: MIT
- Versión revisada durante Fase 1A: 6.2.1.
- Rol actual: upstream conceptual del modelo VAD, **no dependencia Python directa** de Video_Tunner.

Motivo: su paquete Python declara Torch + torchaudio como dependencias base. Para nuestro portable es redundante porque faster-whisper ya incorpora el modelo ONNX/engine necesario.

## PyInstaller

- Proyecto: PyInstaller
- Versión fijada para spike: `6.22.2`.
- Rol: empaquetado Windows `onedir` del runtime Python.

Es una decisión provisional de Fase 1A, no compromiso irreversible. Nuitka se evalúa sólo si aparece un problema/ventaja medible.

## BtbN/FFmpeg-Builds

- Repo: `BtbN/FFmpeg-Builds`
- Rol: proveedor del binario FFmpeg/ffprobe durante el portable spike.
- Spike: Windows x64 GPL rama estable 9.0.

El renderer actual necesita `libx264`, de ahí el perfil GPL del spike.

El URL usado por el script es flotante en el spike. Antes de Release:

- elegir asset inmutable;
- verificar SHA/digest;
- fijar versión;
- revisar notices/licencia/obligaciones de distribución.

## Seguimiento

Cuando un upstream evolucione:

1. comparar con referencia anterior;
2. identificar fix transferible;
3. adaptar/integrar de forma mínima;
4. añadir tests propios;
5. actualizar este fichero cuando el nuevo commit sea realmente relevante.
