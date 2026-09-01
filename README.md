# Video_Tunner

**Video_Tunner** es un limpiador automático, auditable y reversible de vídeo hablado para Windows 10/11 x64.

El objetivo es convertir un vídeo bruto en una versión limpia sin alterar el significado: primero se analiza el archivo, después se genera un **Edit Plan** estructurado y sólo entonces se renderiza el resultado. El original nunca se sobrescribe.

## Estado actual

**Versión de desarrollo:** `0.1.0-dev`

- Fase 0 — Bootstrap: **implementada**.
- Fase 1 — Cleaner técnico: **parcialmente implementada**.
- Release pública: **ninguna**.

### Ya funciona

- CLI `video-tunner`.
- Detección de `FFmpeg` y `ffprobe`.
- Inspección real de vídeo mediante `ffprobe`.
- Detección de silencios mediante `FFmpeg silencedetect`.
- Modos `conservative` y `aggressive` para silencios.
- Generación de `edit_plan.json` auditable.
- Render desde el Edit Plan sin sobrescribir el original.
- Manejo de rutas con espacios.
- Tests unitarios y test end-to-end sintético sin almacenar vídeos de prueba en Git.

### Aún no está implementado

- Transcripción y timestamps por palabra.
- Detección de errores, retomas y repeticiones.
- Eliminación inteligente de muletillas.
- Protección semántica basada en transcripción.
- Normalización de volumen y reducción de ruido.
- SRT y transcripción TXT.
- Informe HTML de edición.
- Empaquetado portable con FFmpeg/Python incluidos.
- GUI.

No se debe interpretar `0.1.0-dev` como una versión final o portable.

## Flujo

```text
Vídeo original
    ↓
ffprobe
    ↓
análisis de silencios
    ↓
Edit Plan JSON
    ↓
FFmpeg
    ↓
vídeo limpio
```

El diseño futuro añadirá transcripción y análisis semántico entre el análisis técnico y el Edit Plan, manteniendo el mismo principio: **decidir primero, registrar la decisión y renderizar después**.

## Desarrollo local

Requisitos actuales de desarrollo:

- Python 3.11 o superior.
- FFmpeg + ffprobe accesibles mediante uno de estos mecanismos, por orden:
  1. variable `VIDEO_TUNNER_FFMPEG_DIR`;
  2. `Tools/ffmpeg/bin` dentro de Video_Tunner;
  3. `PATH`.

El objetivo de la Fase 4 es eliminar estos requisitos externos para el usuario final mediante un ZIP portable.

Instalación editable:

```powershell
python -m pip install -e .
```

Comprobar entorno:

```powershell
video-tunner doctor
```

Inspeccionar un vídeo:

```powershell
video-tunner probe "C:\ruta\video.mp4"
```

Generar sólo el Edit Plan:

```powershell
video-tunner plan "video.mp4" --mode conservative --output edit_plan.json
```

Renderizar un plan existente:

```powershell
video-tunner render "video.mp4" edit_plan.json "video_clean.mp4"
```

Primer flujo automático completo:

```powershell
video-tunner clean "video.mp4" --mode conservative --output-dir Output
```

Salida actual del comando `clean`:

```text
Output/
├── video_clean.mp4
└── video_edit_plan.json
```

## Modos actuales

| Modo | Silencio mínimo | Pausa conservada | Intención |
|---|---:|---:|---|
| `conservative` | 0,65 s | 0,20 s | Priorizar naturalidad |
| `aggressive` | 0,35 s | 0,10 s | Ritmo más compacto |

Estos parámetros son provisionales y deberán validarse con vídeo hablado real.

## Validación

La primera implementación se ha comprobado con:

- tests unitarios del parser de silencios;
- tests del cálculo de segmentos conservados;
- prueba end-to-end sintética `tono → silencio → tono`;
- generación real de MP4 final;
- comprobación de audio + vídeo en el resultado;
- rutas con espacios.

La validación anterior se realizó en el entorno de desarrollo. **La CI Windows manual y la portabilidad Windows final todavía no se han ejecutado/validado.**

La CI del repositorio es deliberadamente `workflow_dispatch`: no se ejecuta automáticamente en cada commit para evitar consumo innecesario de cuota de GitHub Actions.

## Estructura

```text
Archive/                 Histórico final sustituido
Source/video_tunner/     Código fuente vigente
Validation/              Evidencias técnicas ligeras
.github/workflows/       CI permanente mínima
README.md                Producto y uso
AGENTS.md                Contexto técnico permanente
RELEASE_STATUS.md        Estado real de releases
SHA256SUMS.txt            Hashes de paquetes publicados
```

## Principios

- El original nunca se modifica.
- Toda edición debe ser auditable y reversible.
- El modo por defecto es conservador.
- Ante ambigüedad semántica futura, se conserva contenido.
- Procesamiento local siempre que sea razonable.
- No se suben vídeos del usuario a servicios externos de forma silenciosa.
- GitHub es la fuente de verdad técnica.
- Las Actions pesadas sólo se ejecutan cuando aportan evidencia nueva.

Consulta `AGENTS.md` para arquitectura, reglas técnicas y criterios de contribución.