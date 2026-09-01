# AGENTS.md — Video_Tunner

Contexto técnico permanente para cualquier agente o conversación que trabaje sobre este repositorio.

## 1. Objetivo

Video_Tunner debe convertir vídeo hablado bruto en un vídeo limpio, natural, fiel, auditable y reversible para Windows 10/11 x64.

Dos requisitos son **estructurales y no negociables**:

1. **La aplicación final debe ser portable**: ZIP → descomprimir → ejecutar, sin instalador, sin permisos de administrador y sin requerir Python/FFmpeg preinstalados.
2. Debe soportar tanto **vídeo con audio embebido** como **vídeo + audio externo**, incluyendo sincronización A/V automática cuando exista referencia suficiente y fallback/override manual cuando no la haya.

Prioridades funcionales revisadas:

1. portabilidad arquitectónica;
2. ingesta dual y línea temporal A/V correcta;
3. transcripción/VAD y candidatos;
4. silencios y pausas excesivas;
5. errores y retomas;
6. repeticiones;
7. muletillas evidentes;
8. protección semántica;
9. calidad de audio;
10. informe/UX;
11. sólo después, funciones editoriales adicionales.

No convertir el proyecto prematuramente en un editor gráfico generalista.

## 2. Invariantes arquitectónicos

Flujo objetivo obligatorio:

```text
input media
   ↓
ingest / probe
   ↓
master audio + sync metadata
   ↓
analysis
   ↓
candidates
   ↓
decisions
   ↓
Edit Plan
   ↓
render
   ↓
output + audit
```

Invariantes:

- El vídeo original nunca se sobrescribe.
- El audio externo original nunca se modifica.
- **Candidato ≠ decisión ≠ edición.**
- La línea temporal A/V debe quedar resuelta antes de transcribir o tomar decisiones temporales.
- Cada corte significativo debe quedar representado en el Edit Plan.
- Toda transformación de sincronización debe quedar registrada.
- Ante duda semántica, conservar o revisar.
- Ante duda de sincronización, no adivinar.
- Un detector técnico no debe convertirse silenciosamente en decisor semántico.

## 3. Portabilidad — requisito de producto

Portabilidad no es una Fase 4 opcional: es un constraint desde el diseño.

Criterio objetivo de producto:

```text
Video_Tunner.zip
      ↓
descomprimir
      ↓
ejecutar
```

Sin:

- instalación;
- permisos de administrador;
- Python preinstalado;
- FFmpeg/ffprobe preinstalados;
- PATH del usuario como dependencia;
- servicios o registro de Windows;
- dependencia silenciosa de AppData o cachés globales.

El árbol portable debe controlar, cuando proceda:

```text
Video_Tunner/
├─ runtime / executable
├─ Tools/
│  └─ ffmpeg/
├─ Models/
├─ Config/
├─ Temp/
├─ Cache/
├─ Logs/
└─ Output/
```

Reglas:

- rutas relativas al runtime;
- funcionar desde carpetas con espacios;
- no incrustar rutas absolutas del entorno de build;
- limpiar temporales y procesos;
- los modelos deben resolverse desde `Models/` local;
- una descarga inicial de modelo es compatible con portabilidad sólo si el modelo queda dentro del árbol portable y después puede utilizarse localmente/offline;
- antes de Release se decidirá con evidencia si el modelo por defecto se incluye en el ZIP o se obtiene localmente en primer arranque.

No afirmar “portable” hasta validarlo en un entorno Windows limpio.

## 4. Ingesta y master audio

Video_Tunner debe tener una abstracción explícita de **master audio**.

### Modo A — audio embebido

```text
video.mp4
  ├─ video track
  └─ embedded audio → master audio
```

### Modo B — audio externo

```text
video.mp4 + external.wav
          ↓
        sync
          ↓
external audio sincronizado → master audio
```

Cuando existe audio externo seleccionado:

- se usa para transcripción;
- se usa para VAD;
- se usa para decisiones semánticas;
- se usa en el render final;
- el audio de cámara, si existe, se considera referencia de sincronización salvo override.

No analizar una pista y renderizar otra sin registrar explícitamente esa decisión.

## 5. Sincronización A/V

### Sincronización automática

Cuando existe audio de referencia en el vídeo y audio externo:

1. extraer representaciones de análisis de ambas pistas;
2. estimar offset por correlación de señal;
3. realizar búsqueda gruesa + ajuste fino;
4. calcular una medida de confianza;
5. validar en varias ventanas temporales;
6. detectar drift progresivo en grabaciones largas;
7. si existe drift significativo, estimar una corrección temporal lineal;
8. validar la corrección antes de usarla en render/análisis.

### Drift

Dos dispositivos pueden tener relojes ligeramente distintos. Un offset inicial correcto no garantiza sync al final de una grabación larga.

La metadata debe poder registrar como mínimo:

- método;
- offset inicial;
- anchors o ventanas utilizadas;
- confianza;
- error residual;
- drift estimado, por ejemplo en ppm o ms/h;
- corrección aplicada;
- override manual.

La técnica exacta de corrección —resampling/time-stretch u otra— debe decidirse con pruebas reales, preservando tono y sincronía.

### Fallbacks

- Si el vídeo no tiene audio de referencia, la correlación automática no puede garantizar sync: permitir offset manual.
- Si la confianza es baja, no aplicar una estimación silenciosamente.
- Permitir override manual siempre.
- Gestionar offsets positivos y negativos.
- Gestionar audio externo que comienza antes/después del vídeo.
- Si el audio externo no cubre la duración útil, avisar/abortar según política explícita; nunca alternar silenciosamente entre audio externo y cámara.

## 6. Estado técnico actual

Versión: `0.1.0-dev`.

Implementado y validado en entorno de desarrollo:

- paquete Python `video_tunner`;
- CLI;
- resolución de FFmpeg/ffprobe;
- probe audiovisual;
- `silencedetect`;
- Edit Plan schema v1 para silencios;
- render determinista de segmentos conservados;
- modos conservative/aggressive;
- extracción WAV mono 16 kHz PCM16;
- modelos de datos para transcripción word-level;
- escritores TXT/JSON/SRT;
- Candidate Analysis review-only;
- SHA-256 del source;
- tests unitarios y E2E sintéticos.

Implementado en código pero pendiente de validación runtime real:

- `faster-whisper` + `large-v3-turbo`;
- timestamps palabra a palabra reales;
- `silero-vad` real;
- `video-tunner analyze` completo con esos backends.

Todavía no implementado:

- portable Windows real;
- runtime empaquetado;
- audio externo;
- auto-sync;
- offset manual;
- drift detection/correction;
- master-audio abstraction;
- capa semántica.

No afirmar que ninguna de esas piezas está validada hasta ejecutarla realmente.

## 7. Estrategia upstream — NO FORK

Video_Tunner permanece como producto y repositorio propios.

Technology harvest selectivo:

- `Railly/vcut` — EDL, auditabilidad, joins, retomas/repeticiones, audio externo/offset y agent-first;
- `timkulbaev/ai-video-editor` — referencia Python VAD + faster-whisper;
- `JosephLeon/Cadence-Lab` — clasificación semántica de pausas/retomas.

La provenance vigente está en `UPSTREAM_SOURCES.md`.

Reglas:

1. no copiar archivos completos por comodidad;
2. registrar commit/licencia upstream antes de adaptar código;
3. distinguir idea, adaptación y vendorización;
4. cualquier port debe tener tests propios;
5. una mejora upstream nunca se considera automáticamente válida;
6. revisar periódicamente nuevos commits/releases relevantes.

## 8. Estructura

```text
Archive/                 Sólo versiones finales sustituidas
Source/video_tunner/     Source vigente
Validation/              Provenance/hashes/evidencia ligera
.github/workflows/       Workflows permanentes mínimos
.github/scripts/         Sólo scripts permanentes
tests/                   Tests pequeños/sintéticos
README.md
AGENTS.md
ROADMAP.md
UPSTREAM_SOURCES.md
RELEASE_STATUS.md
SHA256SUMS.txt
pyproject.toml
```

No dejar en `main` builds, dist, outputs, vídeos grandes, cachés, modelos descargados, logs, scripts temporales ni experimentos descartados.

## 9. Dependencias y packaging

Core de desarrollo actual:

- Python >= 3.11;
- FFmpeg;
- ffprobe.

Dependencias opcionales de análisis actuales:

- `faster-whisper>=1.2,<2`;
- `silero-vad>=6.2,<7`.

El paquete oficial `silero-vad` 6.2.1 declara Torch y torchaudio como dependencias base y ONNX Runtime como opción adicional. Eso introduce un riesgo de tamaño/packaging para el portable.

Antes de ampliar el stack ML se debe ejecutar un **portable foundation spike** que compare, como mínimo:

- tamaño;
- compatibilidad Windows;
- facilidad de empaquetado;
- rendimiento CPU;
- dependencia de DLLs/runtimes;
- estrategia Torch vs ONNX para VAD.

No elegir la variante por intuición: medir.

Orden de resolución actual durante desarrollo para FFmpeg/ffprobe:

1. `VIDEO_TUNNER_FFMPEG_DIR`;
2. `<runtime-root>/Tools/ffmpeg/bin`;
3. `PATH`.

El producto portable final no debe depender del punto 3.

Modelos:

1. `VIDEO_TUNNER_MODEL_DIR` si existe;
2. `<runtime-root>/Models`.

La fuente de verdad final debe ser local al portable.

## 10. Pipeline de análisis actual

`video-tunner analyze` permanece no destructivo.

Actual:

```text
video source
  ↓
FFmpeg → WAV mono 16k PCM16
  ├─ faster-whisper
  └─ Silero VAD
          ↓
     candidates
          ↓
TXT + JSON + SRT + analysis.json
```

Objetivo tras Fase 1B:

```text
video + optional external audio
          ↓
      ingest/sync
          ↓
       master audio
          ↓
FFmpeg analysis representation
  ├─ faster-whisper
  └─ VAD
          ↓
     candidates
```

La transcripción/VAD no debe calcularse sobre una pista distinta del master audio salvo operación explícita de diagnóstico.

## 11. Transcripción

Motor actual previsto: `faster-whisper`.

Default actual:

- `large-v3-turbo`;
- device CPU;
- compute type `int8` en CPU;
- `word_timestamps=True`;
- `vad_filter=False` porque la VAD se audita separadamente.

`--device cuda` es opt-in hasta validar packaging/driver behavior en Windows.

Una probabilidad ASR no es confianza semántica.

## 12. VAD

Silero VAD se usa como detector, nunca como decisor de corte.

No adoptar reglas tipo “todo tramo corto de habla es un error”.

Durante el portable spike debe comprobarse si mantener el paquete Torch completo compensa frente a una implementación ONNX más ligera.

## 13. Candidate Analysis

`*_analysis.json` es distinto del Edit Plan.

Cada candidato debe conservar:

- id;
- kind;
- start/end/duration;
- reason;
- confidence sólo si está calibrada para esa decisión;
- `decision="undecided"`;
- `auto_apply=false`;
- evidencia.

La próxima evolución del schema debe añadir procedencia del master audio y sync metadata cuando aplique.

## 14. Edit Plan

El Edit Plan representa ediciones efectivas, no candidatos.

Debe evolucionar para poder registrar también:

- hash del vídeo source;
- hash del audio externo cuando exista;
- source de master audio;
- parámetros de sync;
- transform temporal/drift correction;
- removed text por corte semántico;
- audit de joins.

No cambiar silenciosamente el significado de schema v1; usar migración/versionado explícito.

## 15. Capa semántica futura

No empezar hasta que portabilidad base e ingest/sync estén suficientemente demostrados.

```text
candidate + transcript context
          ↓
semantic classifier
          ↓
KEEP / TRIM / CUT / REVIEW
          ↓
semantic guard
          ↓
approved Edit Plan
```

Conservative: duda = KEEP/REVIEW.

Aggressive: puede proponer más, nunca saltarse semantic guard.

## 16. Render

El render actual trabaja con una sola entrada audiovisual y aplica `trim/atrim + concat`.

Debe evolucionar para:

- mantener la pista de vídeo original;
- usar master audio embebido o externo;
- aplicar el mismo mapping temporal de Edit Plan a vídeo y master audio;
- incluir offset/drift correction cuando proceda;
- mantener A/V sync tras múltiples cortes;
- validar duración y streams de salida;
- no sobrescribir ningún source.

## 17. Validación mínima revisada

### Portable

- Windows 10/11 x64;
- ejecución desde carpeta aislada;
- sin Python del sistema;
- sin FFmpeg/ffprobe del sistema;
- PATH irrelevante;
- rutas con espacios;
- modelos locales;
- no depender de cachés previas;
- limpieza de procesos/temp.

### Ingest/sync

- embedded audio;
- external audio;
- offsets positivos y negativos;
- auto-sync correcto sobre señal conocida;
- baja confianza → no aplicar;
- manual override;
- ausencia de camera reference;
- audio más corto/largo;
- ruido razonable;
- drift sintético conocido;
- corrección validada;
- render final en sync.

### Transcripción/VAD

- inferencia real;
- timestamps ordenados;
- TXT/JSON/SRT;
- análisis sobre master audio correcto.

### Semántica

- retomas;
- repeticiones;
- correcciones;
- cifras/negaciones;
- no pérdida de contenido válido.

Distinguir siempre test unitario, E2E automático, integración real con modelo, CI y prueba manual real.

## 18. GitHub / CI / cuota

GitHub es la fuente de verdad técnica.

La cuota de GitHub Actions es finita:

- no lanzar CI si no aporta evidencia nueva;
- agrupar cambios;
- evitar polling frecuente;
- reutilizar resultados válidos;
- no crear commits artificiales para disparar builds;
- cancelar runs obsoletos;
- repetir sólo el job necesario;
- reservar pruebas pesadas para hitos útiles;
- no descargar modelos multi-GB en CI ordinaria sin necesidad;
- no almacenar ZIPs/modelos/vídeos grandes como artifacts ordinarios;
- ahorrar eliminando redundancia, nunca debilitando una prueba necesaria.

El workflow sigue `workflow_dispatch` salvo necesidad explícita.

## 19. Documentación

Regla obligatoria:

**Cualquier cambio relevante de funcionamiento, arquitectura, dependencias, build, packaging, validación o uso debe actualizar README.md y AGENTS.md cuando les afecte.**

- README = producto/uso/estado.
- AGENTS = contexto técnico permanente.
- ROADMAP = orden técnico vigente.
- UPSTREAM_SOURCES = provenance/harvest.
- RELEASE_STATUS = qué está realmente validado/publicado.

No crear `00.Prompt Inicial` dentro del repo.

## 20. Seguridad y privacidad

- procesamiento local por defecto;
- no enviar media a APIs externas silenciosamente;
- modelos pueden descargarse, media no;
- no versionar originales/outputs;
- no almacenar secretos;
- limpiar temporales;
- no sobrescribir sources;
- sync metadata puede versionarse sólo si no incluye rutas o datos sensibles innecesarios.

## 21. Releases y Archive

No publicar ninguna Release sin autorización expresa de Guille.

Release final:

- ZIP portable Windows x64;
- runtime/herramientas necesarias incluidas o adquiribles dentro del árbol portable;
- SHA-256;
- manifiesto de versiones;
- notices/licencias de FFmpeg, faster-whisper, CTranslate2, VAD y transitivas;
- no usar GitHub Actions como archivo permanente.

`Archive/` contiene sólo versiones finales realmente publicadas y posteriormente sustituidas.

## 22. Roadmap técnico revisado

Ver `ROADMAP.md` como fuente de verdad del orden.

Resumen:

### Fase 0 — Bootstrap — COMPLETADA

### Fase 0.5 — Technology harvest — COMPLETADA

### Fase 1A — Portable Foundation — SIGUIENTE BLOQUE CRÍTICO

- packaging spike;
- Python runtime;
- FFmpeg/ffprobe bundled;
- rutas locales;
- estrategia ML portable;
- Torch vs ONNX VAD.

### Fase 1B — Ingesta dual + sincronización A/V

- embedded/external audio;
- master audio;
- offset automático/manual;
- confidence;
- drift detection/correction;
- sync metadata.

### Fase 1C — Transcripción + VAD reales

- adaptar `analyze` a master audio;
- validar Whisper/VAD reales;
- corpus hablado.

### Fase 2 — Cleaner inteligente

- retomas;
- repeticiones;
- muletillas contextuales;
- semantic classifier/guard;
- candidatos → Edit Plan.

### Fase 3 — Calidad audiovisual

### Fase 4 — UX mínima de aplicación

### Fase 5 — Portable Release Hardening

### Fase 6 — Extras

## 23. Changelog de tuneos

### 0.1.0-dev — bootstrap inicial

- source-first;
- CLI;
- FFmpeg/ffprobe;
- Cleaner silencios;
- Edit Plan schema v1;
- render;
- tests sintéticos;
- CI manual.

### 0.1.0-dev — transcription/VAD candidate layer

- repo propio + upstream harvest;
- WAV análisis;
- faster-whisper lazy;
- `large-v3-turbo` default;
- word-level model;
- TXT/JSON/SRT;
- Silero VAD lazy;
- Candidate Analysis v1;
- source SHA-256;
- `candidate != edit`.

### 0.1.0-dev — requirements reset: portable + external audio

- portabilidad pasa a ser invariante desde arquitectura;
- nueva Fase 1A de portable foundation;
- nuevo soporte objetivo video + audio externo;
- master-audio abstraction como requisito;
- auto-sync con confidence + manual fallback;
- drift detection/correction para grabaciones largas;
- semántica aplazada hasta demostrar portable + sync.

Mantener este changelog actualizado con cambios técnicos relevantes.
