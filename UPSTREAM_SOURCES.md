# Upstream Sources / Technology Harvest

Video_Tunner es un producto propio y **no es un fork** de ninguno de los proyectos siguientes.

Este documento registra proyectos open source estudiados como referencia para evitar reinventar trabajo ya resuelto y para poder revisar sus mejoras futuras de forma trazable.

## Política

Para cada upstream:

1. registrar repositorio, licencia y commit revisado;
2. distinguir entre idea/referencia, código adaptado y código vendorizado;
3. si se incorpora código, conservar las atribuciones/licencias exigibles;
4. portar sólo lo necesario para Video_Tunner;
5. no asumir que una mejora upstream es segura: debe volver a validarse en nuestro contexto.

En la iteración `phase1-transcription-vad` **no se ha copiado ni vendorizado código fuente** de los tres proyectos auditados. Las nuevas implementaciones son propias y están informadas por los patrones observados.

## Railly/vcut

- Repo: `Railly/vcut`
- Licencia observada: MIT
- Commit de referencia revisado: `2142cc54dc01a0d2272f1d99717b89cd1c7c9262` (2026-08-17)
- Rol para Video_Tunner: upstream principal de referencia.

Ideas/patrones que queremos conservar:

- EDL/Edit Plan como fuente de verdad de la edición;
- original hasheado y protegido;
- propuestas separadas de aprobación/render;
- `removedText` y auditoría de joins;
- render reproducible y validado contra el plan;
- experiencia agent-first;
- detección/diagnóstico específico de repeticiones y retomas;
- aprendizaje empírico sobre timestamps de Whisper, especialmente en español.

No adoptamos automáticamente:

- stack Node/TypeScript;
- dependencia externa obligatoria de herramientas en PATH;
- arquitectura completa del CLI;
- cualquier heurística sin validación propia.

## timkulbaev/ai-video-editor

- Repo: `timkulbaev/ai-video-editor`
- Licencia observada: MIT
- Commit de referencia revisado: `cce2114019ca237a5e38468789ddac5eb764b9bd` (2026-02-24)
- Rol para Video_Tunner: referencia de pipeline Python talking-head.

Ideas/patrones revisados:

- separación `extract audio → VAD → Whisper → decisions → assembly`;
- uso de Silero VAD;
- uso de faster-whisper con timestamps por palabra;
- configuración modular del pipeline.

No adoptamos su heurística de eliminar automáticamente bursts cortos: en Video_Tunner los candidatos no semánticos permanecen sin aplicar hasta disponer de protección suficiente.

## JosephLeon/Cadence-Lab

- Repo: `JosephLeon/Cadence-Lab`
- Licencia observada: MIT
- Commit de referencia revisado: `e4302c58723db54dc2ff82e3d957159f5812d79c` (2026-06-19)
- Rol para Video_Tunner: referencia para la futura capa semántica.

Ideas/patrones que interesan:

- clasificar pausas por función, no sólo por amplitud;
- distinguir `KEEP / TRIM / CUT`;
- tratar respiraciones de forma diferente a silencios vacíos;
- precomputar candidatos deterministas y pedir al modelo que clasifique un conjunto acotado;
- detectar retomas mediante contexto completo;
- cachear análisis por hash para no repetir trabajo caro.

No adoptamos como requisito:

- dependencia obligatoria de Claude/Groq;
- su stack/UI completos;
- decisiones semánticas automáticas sin modo conservador y trazabilidad propia.

## Dependencias directas de análisis

La implementación actual añade como dependencias opcionales:

- `faster-whisper` — transcripción local y timestamps por palabra;
- `silero-vad` — voice activity detection local.

Antes del empaquetado/release portable se realizará una revisión específica de licencias, binarios, modelos y notices de todas las dependencias transitivas incluidas en el ZIP.

## Seguimiento futuro

No necesitamos ser fork para aprovechar nuevas mejoras. Cuando alguno de estos upstreams evolucione:

1. comparar releases/commits relevantes con el commit de referencia anterior;
2. identificar fixes transferibles;
3. adaptar o reimplementar el cambio en Video_Tunner;
4. añadir tests propios;
5. actualizar este documento con el nuevo commit de referencia cuando corresponda.
