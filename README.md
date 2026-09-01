# Video_Tunner

**Video_Tunner** es una aplicación portable para Windows 10/11 x64 orientada a la limpieza automática, inteligente, auditable y reversible de vídeo hablado.

El objetivo es convertir material bruto en una versión limpia sin alterar el significado: primero se resuelve la fuente audiovisual y su sincronización, después se analiza, se generan **candidatos y decisiones estructuradas**, y sólo entonces se renderiza un **Edit Plan** aprobado. Los originales nunca se sobrescriben.

## Requisitos estructurales no negociables

### 1. Aplicación portable

El producto final debe poder utilizarse como:

```text
ZIP → descomprimir → ejecutar
```

Sin instalador, sin permisos de administrador y sin requerir Python, FFmpeg u otros runtimes preinstalados.

La arquitectura debe trabajar desde rutas relativas al runtime y mantener bajo control de la aplicación sus dependencias, modelos, configuración, temporales, cachés y logs. La portabilidad no se considera una tarea cosmética al final del proyecto: debe demostrarse progresivamente desde las primeras fases.

### 2. Dos modos de entrada de audio

Video_Tunner debe soportar obligatoriamente:

**A. Vídeo con audio embebido**

```text
video.mp4 → video + audio embebido
```

**B. Vídeo + audio externo**

```text
video.mp4 + audio.wav
        ↓
   sincronización
        ↓
video + master audio sincronizado
```

Cuando se proporciona audio externo, éste será el **master audio** para transcripción, VAD, decisiones y render final. El audio de cámara, si existe, podrá utilizarse como referencia para estimar automáticamente el offset.

La sincronización debe contemplar:

- offset positivo o negativo;
- estimación automática por correlación de señal cuando exista referencia suficiente;
- medida de confianza;
- fallback/override manual;
- detección de drift progresivo en grabaciones largas;
- corrección de drift sólo después de validarla;
- registro auditable de los parámetros de sincronización.

Si no existe audio de referencia o la confianza es insuficiente, Video_Tunner **no debe adivinar** una sincronización.

Ver `ROADMAP.md` para la planificación revisada.

## Estado actual

**Versión de desarrollo:** `0.1.0-dev`

- Fase 0 — Bootstrap: **implementada**.
- Fase 0.5 — Technology harvest: **decisión arquitectónica cerrada**.
- Fase 1A — Portable Foundation: **pendiente / siguiente bloque crítico**.
- Fase 1B — Ingesta dual + sincronización A/V: **pendiente / siguiente bloque funcional**.
- Fase 1C — Transcripción + VAD: **parcialmente implementada**, pendiente de adaptación a `master audio` y validación runtime real.
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

Estas funciones requieren las dependencias opcionales de análisis y, en el caso de Whisper, descargar el modelo la primera vez. **No se afirma todavía que el pipeline completo Whisper + Silero esté validado en Windows o en un paquete portable.**

### Requisitos ya fijados pero todavía no implementados

- ZIP portable autocontenido para Windows x64.
- Resolución de runtime sin Python/FFmpeg externos.
- Ingesta de vídeo + audio externo.
- Sincronización automática de audio externo contra audio de cámara.
- Offset manual como fallback/override.
- Detección y corrección validada de drift.
- Abstracción de `master audio` común a análisis y render.
- Decisión semántica `KEEP / TRIM / CUT / REVIEW`.
- Detección fiable de errores, retomas y repeticiones.
- Protección semántica completa.
- Conversión explícita de candidatos semánticos en Edit Plan aprobado.
- Normalización de volumen y tratamiento de ruido.
- Informe HTML de edición.
- GUI mínima de aplicación.

## Arquitectura objetivo revisada

```text
                ENTRADA
                  │
        ┌─────────┴─────────┐
        │                   │
 vídeo + audio          vídeo + audio
   embebido               externo
        │                   │
        │             auto/manual sync
        │                   │
        └─────────┬─────────┘
                  ↓
             MASTER AUDIO
                  ↓
     transcripción + VAD + análisis
                  ↓
          candidatos auditables
                  ↓
        KEEP / TRIM / CUT / REVIEW
                  ↓
          protección semántica
                  ↓
              Edit Plan
                  ↓
         render video + master audio
                  ↓
              auditoría
```

El `master audio` es una decisión de ingest/sync y debe quedar resuelto **antes** de que Whisper, VAD o la lógica semántica tomen decisiones temporales.

## Dos flujos de código actuales

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

Este flujo sigue disponible con `video-tunner clean` mientras se construye la arquitectura revisada.

### Análisis inteligente actual — sin cortes automáticos

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

Antes de cerrar esta fase, este pipeline se adaptará para consumir un `master audio` embebido o externo ya sincronizado.

Separar **detección** de **decisión** es obligatorio: un candidato no es una edición.

## Desarrollo local actual

Mientras se construye el empaquetado portable, los requisitos de desarrollo siguen siendo:

- Python 3.11 o superior.
- FFmpeg + ffprobe accesibles mediante uno de estos mecanismos, por orden:
  1. variable `VIDEO_TUNNER_FFMPEG_DIR`;
  2. `Tools/ffmpeg/bin` dentro de Video_Tunner;
  3. `PATH`.

Esto es un requisito **de desarrollo actual**, no del producto final.

Instalación base:

```powershell
python -m pip install -e .
```

Para usar `analyze`:

```powershell
python -m pip install -e ".[analysis]"
```

Esto añade `faster-whisper` y `silero-vad`. El modelo Whisper se guarda por defecto en `Models/whisper/`, excluido de Git. Puede cambiarse con `VIDEO_TUNNER_MODEL_DIR`.

La primera ejecución puede necesitar conexión para descargar un modelo durante desarrollo. Para el producto portable, cualquier modelo adquirido debe quedar dentro del árbol portable `Models/` y no depender de cachés globales. Antes de Release se decidirá, con datos de tamaño/licencia, si el modelo por defecto se incluye en el ZIP o se descarga localmente en primer arranque.

## Comandos actuales

Comprobar entorno:

```powershell
video-tunner doctor
```

Inspeccionar un vídeo:

```powershell
video-tunner probe "C:\ruta\video.mp4"
```

Generar el Edit Plan de silencios actual:

```powershell
video-tunner plan "video.mp4" --mode conservative --output edit_plan.json
```

Ejecutar el análisis local actual:

```powershell
video-tunner analyze "video.mp4" --mode conservative --language es --output-dir Output
```

Opcionalmente:

```powershell
video-tunner analyze "video.mp4" --model large-v3-turbo --device cuda
```

El valor por defecto de `--device` es `cpu` para mantener un baseline reproducible. CUDA es opt-in hasta que la aceleración GPU esté validada en el empaquetado Windows.

Salida actual del comando `analyze`:

```text
Output/
├── video_analysis.json
├── video_transcript.json
├── video_transcript.txt
└── video.srt
```

`video_analysis.json` contiene actualmente:

- SHA-256 del source;
- motor/modelo de transcripción;
- idioma detectado;
- segmentos de habla de Silero;
- candidatos de pausa;
- candidatos de muletilla vocal obvia;
- evidencia temporal/contextual;
- estado `undecided`;
- `auto_apply=false`.

La futura revisión del schema añadirá la procedencia del master audio y metadata de sincronización cuando exista audio externo.

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

## Portabilidad — criterio de aceptación

No se afirmará que Video_Tunner es portable hasta demostrar como mínimo:

- ejecución desde ZIP descomprimido en Windows 10/11 x64;
- máquina sin Python instalado o sin utilizarlo;
- máquina sin FFmpeg/ffprobe en PATH;
- runtime y herramientas resueltos desde el árbol de Video_Tunner;
- rutas con espacios;
- modelos resueltos desde `Models/` local;
- temporales/cachés controlados;
- ausencia de rutas del entorno de build;
- cierre limpio de procesos;
- funcionamiento local después de disponer de los modelos requeridos.

## Sincronización A/V — criterio de aceptación

La futura ingesta de audio externo no se considerará completa sólo porque permita indicar un offset.

Debe validar progresivamente:

- audio embebido;
- audio externo con offset positivo/negativo;
- auto-sync con referencia suficiente;
- baja confianza → no aplicar silenciosamente;
- override manual;
- audio externo que empieza antes/después del vídeo;
- detección de drift en grabaciones largas;
- corrección de drift verificada;
- cortes posteriores sin perder A/V sync.

## Validación actual

En la iteración transcription/VAD se comprobaron en entorno de desarrollo:

- tests unitarios de timestamps/transcripción/SRT;
- complemento y fusión de segmentos VAD;
- creación y enriquecimiento de candidatos;
- garantía `candidate != edit`;
- SHA-256 del source;
- orquestación del pipeline mediante backends simulados;
- extracción real de WAV 16 kHz mono PCM con FFmpeg;
- regresión end-to-end del Cleaner de silencios existente;
- compilación Python del source.

**No se ha ejecutado todavía una transcripción real `large-v3-turbo` ni una inferencia real Silero VAD en esa iteración. Tampoco se ha validado todavía la portabilidad ni la sincronización con audio externo.**

La CI del repositorio sigue siendo deliberadamente `workflow_dispatch`: no se ejecuta automáticamente en cada commit para evitar consumo innecesario de cuota de GitHub Actions.

## Upstreams y licencia

Video_Tunner no se convierte en fork. Se adopta un modelo de **technology harvest selectivo**:

- estudiar fixes y patrones útiles;
- portar o reimplementar únicamente lo relevante;
- registrar commit y licencia upstream;
- revisar periódicamente evoluciones interesantes.

`vcut` es también referencia para el soporte de audio externo/offset, pero Video_Tunner deberá implementar además su propia sincronización automática y manejo de drift con criterios de confianza.

Ver `UPSTREAM_SOURCES.md` para provenance técnico.

## Estructura

```text
Archive/                 Histórico final sustituido
Source/video_tunner/     Código fuente vigente
Validation/              Evidencias técnicas ligeras
.github/workflows/       CI permanente mínima
README.md                Producto y uso
AGENTS.md                Contexto técnico permanente
ROADMAP.md               Plan técnico vigente
UPSTREAM_SOURCES.md       Referencias/provenance de technology harvest
RELEASE_STATUS.md        Estado real de releases
SHA256SUMS.txt            Hashes de paquetes publicados
```

## Orden inmediato revisado

1. **Portable Foundation spike**.
2. **Ingesta dual + sincronización A/V**.
3. Adaptar `analyze` al concepto de `master audio`.
4. Validar Whisper + VAD reales sobre vídeo hablado.
5. Después: retomas, repeticiones y clasificación semántica.

## Principios

- Video_Tunner debe ser portable por diseño.
- El original y el audio externo nunca se modifican.
- Una línea temporal A/V fiable precede a cualquier decisión semántica.
- Candidato ≠ decisión ≠ edición.
- Toda edición debe ser auditable y reversible.
- El modo por defecto es conservador.
- Ante ambigüedad semántica o de sincronización, se conserva/revisa en lugar de adivinar.
- Procesamiento local siempre que sea razonable.
- No se suben vídeos del usuario a servicios externos de forma silenciosa.
- GitHub es la fuente de verdad técnica.
- Las Actions pesadas sólo se ejecutan cuando aportan evidencia nueva.

Consulta `AGENTS.md` para arquitectura y reglas permanentes y `ROADMAP.md` para la secuencia técnica vigente.
