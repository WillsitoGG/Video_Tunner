# Video_Tunner

**Video_Tunner** es un limpiador automático, auditable y reversible de vídeo hablado para Windows 10/11 x64.

El objetivo es convertir un vídeo bruto en una versión limpia sin alterar el significado: primero se analiza el archivo, después se generan **candidatos y decisiones estructuradas**, y sólo entonces se renderiza un **Edit Plan** aprobado. El original nunca se sobrescribe.

## Estado actual

**Versión de desarrollo:** `0.1.0-dev`

- Fase 0 — Bootstrap: **implementada**.
- Fase 0.5 — Technology harvest: **decisión arquitectónica cerrada**.
- Fase 1 — Cleaner técnico: **en desarrollo**.
- Release pública: **ninguna**.

Video_Tunner continúa como producto y repositorio propios. No es un fork. `vcut`, `Cadence-Lab` y `ai-video-editor` se mantienen como upstreams de referencia; ver `UPSTREAM_SOURCES.md`.

### Validado en el entorno de desarrollo

- CLI `video-tunner`.
- Detección de `FFmpeg` y `ffprobe`.
- Inspección real de vídeo mediante `ffprobe`.
- Detección de silencios mediante `FFmpeg silencedetect`.
- Modos `conservative` y `aggressive` para el Cleaner determinista actual.
- Generación de `edit_plan.json` auditable.
- Render desde el Edit Plan sin sobrescribir el original.
- Extracción de WAV de análisis mono / 16 kHz / PCM 16-bit.
- Escritura de transcripción JSON/TXT y SRT a partir de timestamps.
- Modelo de candidatos auditable que **no aplica cortes automáticamente**.
- Hash SHA-256 del source en el informe de análisis.
- Tests unitarios y end-to-end sintéticos sin almacenar vídeos de prueba en Git.

### Implementado en código, pendiente de validación runtime con modelos reales

- Transcripción local con `faster-whisper` y timestamps palabra a palabra.
- Modelo por defecto `large-v3-turbo`.
- Detección de actividad de voz con `silero-vad`.
- Generación conjunta de candidatos de pausa y posibles muletillas vocales.

Estas funciones requieren las dependencias opcionales de análisis y, en el caso de Whisper, descargar el modelo la primera vez. **No se afirma todavía que el pipeline completo Whisper + Silero esté validado en Windows o en el paquete portable final.**

### Aún no está implementado

- Decisión semántica `KEEP / TRIM / CUT`.
- Detección fiable de errores, retomas y repeticiones.
- Protección semántica completa.
- Conversión automática de candidatos semánticos en Edit Plan aprobado.
- Normalización de volumen y reducción de ruido.
- Informe HTML de edición.
- Empaquetado portable con FFmpeg/Python/modelos incluidos.
- GUI.

## Dos flujos actuales

### Cleaner determinista existente

```text
Vídeo original
    ↓
ffprobe
    ↓
FFmpeg silencedetect
    ↓
Edit Plan JSON
    ↓
FFmpeg
    ↓
vídeo limpio
```

Este flujo sigue disponible con `video-tunner clean` mientras se construye y valida el Cleaner inteligente.

### Nuevo análisis inteligente — sin cortes automáticos

```text
Vídeo original
    ↓
WAV mono 16 kHz
    ├── faster-whisper → palabras + timestamps → TXT / JSON / SRT
    └── Silero VAD → segmentos de habla
                  ↓
          candidatos auditables
                  ↓
          *_analysis.json
                  ↓
       NINGÚN corte automático
```

Separar **detección** de **decisión** es obligatorio: un candidato no es una edición.

## Desarrollo local

Requisitos base:

- Python 3.11 o superior.
- FFmpeg + ffprobe accesibles mediante uno de estos mecanismos, por orden:
  1. variable `VIDEO_TUNNER_FFMPEG_DIR`;
  2. `Tools/ffmpeg/bin` dentro de Video_Tunner;
  3. `PATH`.

Instalación base:

```powershell
python -m pip install -e .
```

Para usar `analyze`:

```powershell
python -m pip install -e ".[analysis]"
```

Esto añade `faster-whisper` y `silero-vad`. El modelo Whisper se guarda por defecto en `Models/whisper/`, excluido de Git. Puede cambiarse con `VIDEO_TUNNER_MODEL_DIR`.

La primera ejecución puede necesitar conexión para **descargar el modelo**, pero Video_Tunner no necesita subir el vídeo ni el audio del usuario a una API: transcripción y VAD se ejecutan localmente.

## Comandos

Comprobar entorno:

```powershell
video-tunner doctor
```

Inspeccionar un vídeo:

```powershell
video-tunner probe "C:\ruta\video.mp4"
```

Generar sólo el Edit Plan de silencios actual:

```powershell
video-tunner plan "video.mp4" --mode conservative --output edit_plan.json
```

Ejecutar el nuevo análisis local:

```powershell
video-tunner analyze "video.mp4" --mode conservative --language es --output-dir Output
```

Opcionalmente:

```powershell
video-tunner analyze "video.mp4" --model large-v3-turbo --device cuda
```

El valor por defecto de `--device` es `cpu` para mantener un baseline reproducible. CUDA es opt-in hasta que la aceleración GPU esté validada en el empaquetado Windows.

Salida del comando `analyze`:

```text
Output/
├── video_analysis.json
├── video_transcript.json
├── video_transcript.txt
└── video.srt
```

`video_analysis.json` contiene:

- SHA-256 del source;
- motor/modelo de transcripción;
- idioma detectado;
- segmentos de habla de Silero;
- candidatos de pausa;
- candidatos de muletilla vocal obvia;
- evidencia temporal/contextual;
- estado `undecided`;
- `auto_apply=false`.

Ningún candidato generado por `analyze` entra todavía en `edits[]`.

Renderizar un Edit Plan existente:

```powershell
video-tunner render "video.mp4" edit_plan.json "video_clean.mp4"
```

Cleaner de silencios actual:

```powershell
video-tunner clean "video.mp4" --mode conservative --output-dir Output
```

## Modos

### Cleaner FFmpeg actual

| Modo | Silencio mínimo | Pausa conservada | Intención |
|---|---:|---:|---|
| `conservative` | 0,65 s | 0,20 s | Priorizar naturalidad |
| `aggressive` | 0,35 s | 0,10 s | Ritmo más compacto |

### Candidatos de análisis

Los umbrales de VAD/word-gap se usan sólo para **proponer revisión**, no para cortar. Son provisionales y se tunearán con vídeo hablado real.

## Validación

En la iteración actual se han comprobado en entorno de desarrollo:

- tests unitarios de timestamps/transcripción/SRT;
- complemento y fusión de segmentos VAD;
- creación y enriquecimiento de candidatos;
- garantía `candidate != edit`;
- SHA-256 del source;
- orquestación del pipeline mediante backends simulados;
- extracción real de WAV 16 kHz mono PCM con FFmpeg;
- regresión end-to-end del Cleaner de silencios existente;
- compilación Python del source.

**No se ha ejecutado todavía una transcripción real `large-v3-turbo` ni una inferencia real Silero VAD en esta iteración**, porque esas dependencias/modelos no están disponibles en el entorno de trabajo actual. Tampoco equivale a validación Windows o portable.

La CI del repositorio sigue siendo deliberadamente `workflow_dispatch`: no se ejecuta automáticamente en cada commit para evitar consumo innecesario de cuota de GitHub Actions.

## Upstreams y licencia

Video_Tunner no se convierte en fork. Se adopta un modelo de **technology harvest selectivo**:

- estudiar fixes y patrones útiles;
- portar o reimplementar únicamente lo relevante;
- registrar commit y licencia upstream;
- revisar periódicamente evoluciones interesantes.

Ver `UPSTREAM_SOURCES.md` para provenance técnico. En esta iteración no se ha vendorizado código fuente de esos tres proyectos; las implementaciones nuevas son propias, informadas por la auditoría.

## Estructura

```text
Archive/                 Histórico final sustituido
Source/video_tunner/     Código fuente vigente
Validation/              Evidencias técnicas ligeras
.github/workflows/       CI permanente mínima
README.md                Producto y uso
AGENTS.md                Contexto técnico permanente
UPSTREAM_SOURCES.md       Referencias/provenance de technology harvest
RELEASE_STATUS.md        Estado real de releases
SHA256SUMS.txt            Hashes de paquetes publicados
```

## Principios

- El original nunca se modifica.
- Candidato ≠ decisión ≠ edición.
- Toda edición debe ser auditable y reversible.
- El modo por defecto es conservador.
- Ante ambigüedad semántica, se conserva contenido.
- Procesamiento local siempre que sea razonable.
- No se suben vídeos del usuario a servicios externos de forma silenciosa.
- GitHub es la fuente de verdad técnica.
- Las Actions pesadas sólo se ejecutan cuando aportan evidencia nueva.

Consulta `AGENTS.md` para arquitectura, reglas técnicas y criterios de contribución.
