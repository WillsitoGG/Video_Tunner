# ROADMAP — Video_Tunner

Este roadmap refleja las dos condiciones estructurales del producto que deben cumplirse desde el diseño, no al final:

1. **Video_Tunner debe ser una aplicación portable para Windows 10/11 x64.**
2. Debe aceptar **vídeo con audio embebido** o **vídeo + audio externo**, incluyendo sincronización automática cuando sea técnicamente posible y fallback manual cuando no lo sea.

El roadmap se organiza para reducir riesgo técnico temprano: portabilidad e ingest/sync se validan antes de añadir más inteligencia semántica.

## Principios de planificación

- Portabilidad es un invariante arquitectónico, no una fase cosmética de empaquetado.
- El audio de trabajo debe estar definido y sincronizado antes de transcribir, detectar silencios o generar decisiones.
- El original y el audio externo nunca se modifican.
- Toda transformación temporal debe quedar representada de forma auditable.
- Si la sincronización automática no alcanza confianza suficiente, Video_Tunner no debe adivinar: debe pedir/aceptar un offset manual o marcar el caso para revisión.
- La IA semántica sólo se construye sobre una línea temporal A/V ya validada.

---

## Fase 0 — Bootstrap — COMPLETADA

- estructura inicial;
- README / AGENTS / release status;
- FFmpeg/ffprobe;
- probe;
- Cleaner de silencios determinista;
- Edit Plan inicial;
- render;
- tests sintéticos;
- CI manual de bajo consumo.

## Fase 0.5 — Technology Harvest — COMPLETADA

- Video_Tunner permanece como producto propio;
- no fork;
- `vcut`, `Cadence-Lab` y `ai-video-editor` como upstreams de referencia;
- provenance en `UPSTREAM_SOURCES.md`.

## Fase 1A — Portable Foundation — SIGUIENTE BLOQUE CRÍTICO

Objetivo: demostrar pronto que la arquitectura puede terminar como aplicación realmente portable.

### Requisitos

- Windows 10/11 x64;
- ZIP → descomprimir → ejecutar;
- sin instalador;
- sin permisos de administrador;
- sin Python preinstalado;
- sin FFmpeg/ffprobe preinstalados;
- sin depender de PATH;
- rutas relativas al runtime;
- funcionar desde carpetas con espacios;
- `Models/`, `Temp/`, `Cache/`, `Config/` y `Logs/` bajo control de la aplicación;
- no depender silenciosamente de AppData, cachés globales o registro de Windows;
- limpieza de temporales y procesos.

### Spike técnico obligatorio

Antes de seguir ampliando el stack ML:

1. elegir/probar estrategia de empaquetado del runtime Python;
2. empaquetar FFmpeg + ffprobe;
3. ejecutar `doctor`, `probe` y un render mínimo desde una carpeta aislada;
4. comprobar que la máquina de prueba no necesita Python/FFmpeg externos;
5. evaluar el impacto real de `faster-whisper`, CTranslate2 y Silero en tamaño/packaging;
6. decidir si Silero se empaqueta vía Torch o una alternativa ONNX más ligera, basándonos en evidencia de tamaño, compatibilidad y rendimiento.

### Modelos

La aplicación debe seguir siendo portable aunque el modelo se obtenga inicialmente por descarga:

- cualquier modelo descargado debe ir a `Models/` dentro del runtime portable;
- no usar cachés globales como fuente de verdad;
- después de adquirir el modelo, el funcionamiento debe poder ser local/offline;
- antes de Release se decidirá con datos si el modelo por defecto se incluye en el ZIP o se ofrece adquisición local en primer arranque.

La distribución del modelo no puede romper el principio de portabilidad.

---

## Fase 1B — Ingesta dual y sincronización A/V — NUEVA PRIORIDAD

Objetivo: crear una línea temporal maestra correcta antes de cualquier análisis inteligente.

### Modos de entrada obligatorios

**Modo A — vídeo con audio embebido**

```text
video.mp4
  ├─ video track
  └─ audio track → master audio
```

**Modo B — vídeo + audio externo**

```text
video.mp4 + audio.wav
        ↓
      sync
        ↓
video timeline + synchronized master audio
```

El audio externo sincronizado pasa a ser el **master audio** para transcripción, VAD, decisiones y render final. El audio de cámara, si existe, se utiliza como referencia de sincronización salvo que se indique lo contrario.

### Sincronización automática

Cuando el vídeo contiene audio de referencia y se aporta audio externo:

1. extraer representaciones mono de análisis de ambas pistas;
2. estimar offset temporal mediante correlación de señal, primero de forma gruesa y después fina;
3. producir `offset_ms` y una medida de confianza;
4. validar la alineación en más de una ventana del archivo;
5. detectar posible drift de reloj en grabaciones largas;
6. si existe drift significativo, estimar una corrección temporal lineal y validarla antes de aplicarla;
7. conservar los parámetros de sync como datos auditables.

### Drift

Dos grabadores independientes pueden empezar sincronizados y separarse progresivamente por diferencias de reloj.

Video_Tunner debe poder registrar como mínimo:

- offset inicial;
- anchors utilizados;
- error residual;
- drift estimado (`ppm` o equivalente temporal);
- corrección aplicada, si procede.

La técnica final de corrección —resampling/time-stretch u otra— se seleccionará por prueba real, preservando tono y sincronía.

### Fallbacks obligatorios

- Si el vídeo no contiene audio de referencia, no se puede garantizar auto-sync sólo por correlación de audio. Debe admitirse `--audio-offset`/ajuste manual equivalente.
- Si la confianza de auto-sync es baja, no aplicar una alineación silenciosa.
- Permitir override manual aunque exista una estimación automática.
- Gestionar offsets positivos y negativos.
- Si el audio externo no cubre toda la duración útil, avisar o abortar según el caso; nunca mezclar silenciosamente audio de cámara y externo.

### Metadata de sincronización

El análisis futuro debe poder registrar una estructura equivalente a:

```json
{
  "audio_source": "external",
  "sync": {
    "method": "waveform_correlation",
    "offset_ms": -842,
    "drift_ppm": 12.4,
    "confidence": 0.97,
    "manual_override": false
  }
}
```

Los nombres exactos del schema se fijarán al implementar, pero el contenido debe ser auditable.

### Tests mínimos

- embedded audio;
- external audio con offset positivo;
- external audio con offset negativo;
- audio externo más largo/corto que vídeo;
- rutas con espacios;
- ausencia de referencia de cámara;
- señal insuficiente/ambigua → no adivinar;
- sync con ruido razonable;
- drift sintético conocido;
- render final manteniendo A/V sync después de cortes.

---

## Fase 1C — Transcripción + VAD reales

Sólo sobre el **master audio ya sincronizado**:

- `faster-whisper`;
- timestamps palabra a palabra;
- TXT / JSON / SRT;
- Silero VAD o alternativa validada para el portable;
- candidate analysis;
- cache local por hash cuando aporte valor;
- validación real sobre vídeo hablado.

Parte de esta fase ya está implementada en código, pero debe adaptarse a la abstracción de `master audio` antes de considerarse cerrada.

---

## Fase 2 — Cleaner inteligente

- retomas;
- repeticiones;
- errores/correcciones;
- muletillas contextuales;
- clasificación `KEEP / TRIM / CUT / REVIEW`;
- protección semántica;
- cifras, negaciones, nombres y cambios de significado;
- modos Conservador / Agresivo;
- candidatos → decisiones → Edit Plan.

No empezar esta fase hasta que ingest/sync y la base portable estén suficientemente demostradas.

---

## Fase 3 — Calidad audiovisual

- normalización de loudness;
- suavizado de joins/cortes;
- reducción de ruido sólo con defaults seguros o control explícito;
- preservación de master audio externo;
- informe de edición;
- verificación post-render;
- auditoría de joins;
- rendimiento.

---

## Fase 4 — UX mínima de aplicación

Sólo cuando el core sea fiable.

Objetivo: hacer sencillo el caso de uso sin convertir Video_Tunner en Premiere.

Como mínimo la futura UI debe permitir:

- elegir vídeo;
- opcionalmente elegir audio externo;
- mostrar/confirmar sincronización;
- elegir modo Conservador/Agresivo;
- lanzar análisis;
- revisar candidatos/decisiones cuando corresponda;
- renderizar;
- abrir output/informe.

La CLI seguirá siendo útil para automatización y tests.

---

## Fase 5 — Portable Release Hardening

No es el momento en que empieza la portabilidad: es el cierre de una arquitectura que ya debe ser portable desde Fase 1A.

- build Windows x64 limpia;
- ZIP final;
- runtime y herramientas incluidas;
- resolución local de modelos;
- ejecución sin Python/FFmpeg instalados;
- entorno sin cachés previas;
- SHA-256;
- manifiesto de versiones;
- notices/licencias;
- tests de instalación cero;
- limpieza de temporales;
- no depender de red una vez adquiridos los modelos necesarios.

---

## Fase 6 — Funciones adicionales

Sólo después de que el Cleaner sea fiable:

- subtítulos incrustados;
- reencuadre;
- zooms;
- clips/shorts;
- B-roll;
- otras funciones editoriales.

---

## Orden inmediato revisado

El siguiente desarrollo no será todavía la capa semántica.

Orden:

1. **Portable Foundation spike**.
2. **Ingesta dual + sincronización A/V**.
3. Adaptar `analyze` al concepto de `master audio`.
4. Validar Whisper + VAD reales sobre un vídeo hablado.
5. Sólo entonces: retomas/repeticiones y clasificación semántica.

Este orden minimiza el riesgo de construir inteligencia sobre una base que luego no pueda empaquetarse o cuya línea temporal A/V sea incorrecta.
