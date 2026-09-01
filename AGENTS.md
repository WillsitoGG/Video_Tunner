# AGENTS.md — Video_Tunner

Contexto técnico permanente para cualquier agente o conversación que trabaje sobre este repositorio.

## 1. Objetivo

Video_Tunner debe convertir vídeo hablado bruto en un vídeo limpio, natural, fiel, auditable y reversible para Windows 10/11 x64.

Prioridades funcionales, por orden:

1. silencios y pausas excesivas;
2. errores y retomas;
3. repeticiones;
4. muletillas evidentes;
5. protección semántica;
6. normalización de audio y reducción de ruido;
7. transcripción/SRT/informe;
8. portabilidad Windows;
9. sólo después, funciones editoriales adicionales.

No convertir el proyecto prematuramente en un editor gráfico generalista.

## 2. Regla arquitectónica principal

El vídeo **no se modifica directamente mediante decisiones opacas**.

Flujo obligatorio:

```text
source → análisis → candidatos → decisiones → Edit Plan → render → output → auditoría
```

Invariantes:

- El original nunca se sobrescribe.
- **Candidato ≠ decisión ≠ edición.**
- Cada corte significativo debe quedar representado en el Edit Plan.
- El plan debe ser suficientemente preciso para explicar y reproducir la edición.
- Ante duda en una decisión semántica, conservar el fragmento o marcarlo para revisión.
- Un detector técnico no debe convertirse silenciosamente en decisor semántico.

## 3. Estado técnico actual

Versión: `0.1.0-dev`.

Implementado y validado en entorno de desarrollo:

- paquete Python `video_tunner`;
- CLI;
- resolución de FFmpeg/ffprobe;
- probe audiovisual;
- `silencedetect`;
- Edit Plan schema v1 para silencios;
- render determinista de segmentos conservados;
- modos conservative/aggressive para silencios;
- extracción de audio de análisis WAV mono 16 kHz PCM16;
- modelos de datos para transcripción word-level;
- escritores TXT/JSON/SRT;
- modelo de candidatos review-only;
- SHA-256 del source en el analysis report;
- tests unitarios y end-to-end sintéticos.

Implementado en código pero pendiente de validación runtime con dependencias/modelos reales:

- `faster-whisper` + `large-v3-turbo`;
- word-level timestamps reales;
- `silero-vad` real;
- comando `video-tunner analyze` completo con esos backends.

No afirmar que esta integración está validada en Windows o en el portable hasta ejecutarla realmente.

Pendiente inmediato:

- validación real Whisper + Silero sobre vídeo hablado;
- tuneo de thresholds únicamente sobre corpus representativo;
- candidatos de retoma/repetición;
- clasificador semántico `KEEP / TRIM / CUT`;
- protección de cifras/negaciones/semántica;
- promoción explícita de decisiones aprobadas a Edit Plan;
- informe de edición.

## 4. Estrategia upstream — NO FORK

Video_Tunner permanece como producto y repositorio propios.

Se adopta **technology harvest selectivo**. Upstreams principales:

- `Railly/vcut` — EDL, auditabilidad, joins, retomas/repeticiones, agent-first;
- `timkulbaev/ai-video-editor` — referencia Python VAD + faster-whisper;
- `JosephLeon/Cadence-Lab` — referencia para clasificación semántica de pausas/retomas.

La provenance vigente está en `UPSTREAM_SOURCES.md`.

Reglas:

1. no copiar archivos completos por comodidad;
2. registrar commit/licencia upstream antes de adaptar código;
3. distinguir idea, adaptación y vendorización;
4. cualquier port debe tener tests propios;
5. una mejora upstream nunca se considera automáticamente válida en Video_Tunner;
6. revisar periódicamente nuevos commits/releases relevantes aunque no exista relación de fork.

En la iteración `phase1-transcription-vad` las implementaciones son propias; no se ha vendorizado código de esos tres repositorios.

## 5. Estructura

```text
Archive/                 Sólo versiones finales sustituidas
Source/video_tunner/     Source vigente
Validation/              Provenance/hashes/evidencia ligera
.github/workflows/       Workflows permanentes mínimos
.github/scripts/         Sólo scripts permanentes cuando sean necesarios
tests/                   Tests pequeños; preferir fixtures sintéticos
README.md
AGENTS.md
UPSTREAM_SOURCES.md
RELEASE_STATUS.md
SHA256SUMS.txt
pyproject.toml
```

No dejar en `main` builds, dist, outputs, vídeos grandes, cachés, modelos descargados, logs, scripts temporales ni experimentos descartados.

## 6. Dependencias y resolución de herramientas

Core base:

- Python >= 3.11.
- FFmpeg.
- ffprobe.

Dependencias opcionales de análisis:

- `faster-whisper>=1.2,<2`;
- `silero-vad>=6.2,<7`.

Se instalan con:

```powershell
python -m pip install -e ".[analysis]"
```

No convertirlas en imports eager del core: `probe`, `plan`, `render` y `clean` deben seguir funcionando sin el stack ML.

Orden de resolución actual para FFmpeg/ffprobe:

1. `VIDEO_TUNNER_FFMPEG_DIR`;
2. `<runtime-root>/Tools/ffmpeg/bin`;
3. `PATH`.

Modelos:

1. `VIDEO_TUNNER_MODEL_DIR` si existe;
2. `<runtime-root>/Models`.

Whisper usa `<model-root>/whisper` como `download_root`. `Models/` está excluido de Git.

El uso de PATH y la descarga inicial de modelos son válidos durante desarrollo. La build portable final debe demostrar que funciona con sus dependencias empaquetadas y sin depender accidentalmente del runner, caché del usuario o red.

Antes de añadir una dependencia:

1. justificar el problema concreto que resuelve;
2. comprobar si el stack actual ya lo resuelve;
3. fijar/versionar su uso de forma reproducible;
4. validar integración real;
5. revisar licencia y packaging antes de incluirla en Release.

## 7. Pipeline de análisis

`video-tunner analyze` debe permanecer **no destructivo** hasta incorporar la capa de decisión semántica.

Flujo actual:

```text
source
  ↓
ffprobe
  ↓
FFmpeg → WAV mono 16k PCM16
  ├─ faster-whisper → TranscriptResult (segmentos + palabras)
  └─ Silero VAD → SpeechInterval[]
                    ↓
              candidates.py
                    ↓
    TXT + JSON + SRT + analysis.json
```

Artefactos:

- `<stem>_transcript.json`;
- `<stem>_transcript.txt`;
- `<stem>.srt`;
- `<stem>_analysis.json`.

El WAV temporal se crea dentro del output root y se elimina al terminar.

## 8. Transcripción

Motor previsto: `faster-whisper`.

Default actual:

- modelo: `large-v3-turbo`;
- device: `cpu`;
- compute type: `int8` cuando está en CPU;
- `word_timestamps=True`;
- `vad_filter=False`, porque la VAD de Video_Tunner se procesa separadamente y queda auditada.

`--device cuda` es opt-in. No afirmar aceleración GPU portable hasta validarla en Windows.

El JSON de transcripción debe conservar timestamps por palabra y probabilidad ASR cuando exista. Una probabilidad de Whisper **no es confianza semántica del candidato**.

El SRT se genera actualmente a nivel de segmento para legibilidad; el JSON conserva granularidad word-level para futuros cortes.

## 9. Silero VAD

Silero VAD se usa como detector de actividad de voz, no como decisor de corte.

`vad.py` debe devolver intervalos de habla puros. `non_speech_gaps()` calcula su complemento de manera determinista, fusionando speech solapado y recortando a la duración del media.

No adoptar heurísticas tipo “todo burst corto es un error”. Un tramo corto de habla puede ser contenido válido.

## 10. Candidate Analysis schema v1

`*_analysis.json` es distinto del Edit Plan.

Contiene como mínimo:

- `schema_version`;
- timestamp de creación;
- source file + duration + SHA-256;
- modo;
- motores/modelos;
- resumen de transcript;
- speech segments;
- `candidates[]`;
- summary;
- bloque safety.

Cada candidato actual debe incluir:

- `id` estable dentro del informe;
- `kind`;
- `start/end/duration`;
- reason;
- `confidence` sólo si existe una medida calibrada para esa decisión; en caso contrario `null`;
- `decision="undecided"`;
- `auto_apply=false`;
- evidencia relevante.

Tipos actuales:

- `pause`;
- `possible_filler`.

Los candidatos de pausa pueden combinar evidencia de:

- Silero VAD;
- gap entre timestamps de palabras.

Los fillers léxicos actuales se limitan a vocalizaciones inequívocas (`eh`, `um`, `uh`, etc.) y siguen siendo review-only. No añadir palabras ambiguas tipo `este`, `like`, `actually`, etc. como eliminación automática.

## 11. Edit Plan schema v1

El Edit Plan actual sigue reservado para **ediciones efectivas**.

Contiene:

- `schema_version`;
- `created_utc`;
- metadatos mínimos de source sin ruta absoluta;
- `mode`;
- parámetros de análisis;
- `edits[]` con action/kind/start/end/duration/reason/confidence;
- resumen de tiempo eliminado y duración estimada.

No meter `analysis.candidates[]` dentro de `edits[]` sin una fase explícita de decisión/aprobación.

Al evolucionar el schema, mantener compatibilidad o migración explícita; no cambiar silenciosamente el significado de campos existentes.

## 12. Modos

Modo por defecto: `conservative`.

Cleaner FFmpeg actual:

- conservative: `noise_db=-40`, `min_silence=0.65`, `keep_pause=0.20`.
- aggressive: `noise_db=-38`, `min_silence=0.35`, `keep_pause=0.10`.

Candidate discovery actual:

- conservative: VAD gap >= 0.65 s; word gap >= 0.45 s;
- aggressive: VAD gap >= 0.35 s; word gap >= 0.25 s.

Estos números son **provisionales**. En Candidate Analysis sólo determinan qué revisar, no qué borrar. Cualquier tuneo debe validarse con muestras representativas.

## 13. Futura capa semántica

Inspiración conceptual principal: Cadence-Lab + patrones de vcut, reimplementados para las restricciones de Video_Tunner.

Objetivo futuro:

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

Categorías candidatas futuras pueden incluir:

- breath;
- hesitation;
- filler;
- emphasis;
- transition;
- retake;
- repetition;
- correction.

Reglas:

- las categorías no deben implicar automáticamente acción;
- cifras, negaciones, nombres y correcciones requieren protección especial;
- Conservative: duda = KEEP/REVIEW;
- Aggressive puede proponer más, nunca saltarse la protección semántica.

## 14. Render

El render actual:

- calcula el complemento temporal de los cortes `remove`;
- fusiona cortes superpuestos;
- usa `trim/atrim + concat`;
- codifica H.264 (`libx264`) + AAC;
- cancela si el plan eliminaría todo el vídeo;
- impide que destination sea el mismo archivo que source.

Actualmente se asume al menos una pista de vídeo y una de audio para el Cleaner hablado. Ampliar esta regla sólo con tests específicos.

Mejoras futuras inspiradas por upstreams, todavía no implementadas:

- hash de source también en Edit Plan;
- verificación de render contra plan;
- `removedText` por semantic cut;
- join audit;
- edge fades / loudness normalisation.

## 15. Validación

No dar por válida una función sólo porque compile.

Cobertura actual de la iteración transcription/VAD:

- serialización word-level;
- TXT/JSON/SRT;
- timestamps SRT;
- complemento/fusión de speech intervals;
- generación de candidatos y contexto;
- candidatos nunca auto-aplicados;
- SHA-256 source;
- pipeline orquestado con backends mock;
- WAV real 16 kHz mono PCM16 mediante FFmpeg;
- regresión E2E del Cleaner de silencios previo;
- `compileall`.

Pendiente por falta de dependencias/modelos en el entorno actual:

- inferencia real faster-whisper;
- descarga/carga real `large-v3-turbo`;
- inferencia real `silero-vad`;
- pipeline `analyze` completo con vídeo hablado real.

Distinguir siempre:

- test unitario;
- test automático end-to-end;
- integración real con modelo;
- CI;
- validación manual realizada realmente por Guille.

No atribuir pruebas manuales que no se hayan realizado.

## 16. GitHub / CI / cuota

GitHub es la fuente de verdad técnica.

La cuota de GitHub Actions es un recurso finito:

- no lanzar CI si no aporta evidencia técnica nueva;
- agrupar cambios coherentes;
- evitar polling frecuente;
- reutilizar resultados aún válidos;
- no crear commits artificiales para disparar builds;
- cancelar runs obsoletos mediante `concurrency`;
- repetir sólo el job fallido cuando sea suficiente;
- reservar validaciones pesadas para hitos, cambios de alcance completo o candidatos de entrega;
- no descargar modelos multi-GB en CI ordinaria sin necesidad concreta;
- no almacenar ZIPs, vídeos, modelos o payloads grandes como artifacts ordinarios;
- mantener retención mínima cuando un artifact pesado sea imprescindible;
- ahorrar eliminando redundancia, **nunca debilitando una prueba necesaria**.

El workflow inicial es exclusivamente `workflow_dispatch` y no debe adquirir triggers automáticos sin una necesidad técnica justificada.

## 17. README y este fichero

Regla obligatoria:

**Cualquier cambio relevante que modifique funcionamiento, arquitectura, dependencias, build, packaging, validación o forma de uso debe actualizar README.md y AGENTS.md en el mismo cambio cuando les afecte.**

README = descripción viva de producto/uso/estado.
AGENTS = contexto técnico permanente.
UPSTREAM_SOURCES = provenance viva del technology harvest.

No crear un `00.Prompt Inicial` dentro del repositorio.

## 18. Seguridad y privacidad

- Procesamiento local por defecto.
- No enviar vídeos a APIs externas silenciosamente.
- La descarga de un modelo no equivale a subir media; debe seguir documentada.
- No versionar originales ni outputs del usuario.
- No almacenar secretos o tokens.
- Evitar contenido sensible en logs.
- Limpiar temporales/procesos cuando corresponda.
- No permitir que un output sobreescriba el source.

## 19. Releases y Archive

No publicar ninguna Release sin autorización expresa de Guille.

Release final:

- un ZIP portable por plataforma salvo necesidad funcional real;
- hashes/provenance/logs permanecen en el repo, no como assets innecesarios;
- GitHub Actions no es almacenamiento histórico;
- revisar licencias/notices de FFmpeg, faster-whisper, CTranslate2, Silero y dependencias transitivas antes de empaquetar.

`Archive/` contiene únicamente versiones finales realmente publicadas y posteriormente sustituidas. Nunca builds fallidas, pruebas o reconstrucciones no verificadas.

## 20. Roadmap técnico

### Fase 0 — Bootstrap

Implementada.

### Fase 0.5 — Technology harvest

Decisión cerrada:

- conservar Video_Tunner propio;
- no fork;
- harvest selectivo y trazable.

### Fase 1 — Cleaner técnico

Implementado:

- probe;
- silencio determinista;
- Edit Plan + render;
- extracción de audio;
- artefactos transcript;
- candidate schema.

Pendiente para cerrar fase:

- validación runtime real faster-whisper + Silero;
- robustez/model caching y errores de modelo;
- corpus de validación hablado.

### Fase 2 — Cleaner inteligente

- retomas;
- repeticiones;
- muletillas contextuales;
- clasificación semántica;
- niveles de confianza calibrados cuando sea posible;
- semantic protection;
- promoción candidatos → decisiones → Edit Plan.

### Fase 3 — Calidad audiovisual

Normalización, reducción de ruido, suavizado de cortes e informe.

### Fase 4 — Portable Windows

Empaquetado completo, rutas portables, entorno limpio, ZIP, SHA-256 y manifiesto.

### Fase 5 — Adicionales

Sólo si el Cleaner ya es fiable: subtítulos incrustados, reencuadre, zooms, clips/shorts, B-roll y otras funciones.

## 21. Changelog de tuneos

### 0.1.0-dev — bootstrap inicial

- Creación de arquitectura source-first.
- CLI inicial.
- Integración FFmpeg/ffprobe.
- Primer Cleaner de silencios auditable.
- Edit Plan schema v1.
- Render desde plan.
- Tests sintéticos sin fixtures audiovisuales persistentes.
- CI manual de bajo consumo.

### 0.1.0-dev — transcription/VAD candidate layer

- Decisión formal de conservar repo propio y usar upstreams como referencia.
- `UPSTREAM_SOURCES.md` con provenance.
- extracción WAV de análisis;
- integración lazy de faster-whisper;
- modelo `large-v3-turbo` por defecto;
- word-level transcript model;
- outputs TXT/JSON/SRT;
- integración lazy de Silero VAD;
- Candidate Analysis schema v1;
- source SHA-256;
- `candidate != edit` como invariante;
- tests de orquestación sin descargar modelos;
- documentación explícita de lo todavía no validado.

Mantener este changelog actualizado con cambios técnicos relevantes.
