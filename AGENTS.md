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
source → análisis → decisiones → Edit Plan → render → output
```

- El original nunca se sobrescribe.
- Cada corte significativo debe quedar representado en el Edit Plan.
- El plan debe ser suficientemente preciso para explicar y reproducir la edición.
- Ante duda futura en una decisión semántica, conservar el fragmento o marcarlo para revisión.

## 3. Estado técnico actual

Versión: `0.1.0-dev`.

Implementado:

- paquete Python `video_tunner`;
- CLI;
- resolución de FFmpeg/ffprobe;
- probe audiovisual;
- `silencedetect`;
- Edit Plan schema v1 para silencios;
- render determinista de segmentos conservados;
- modos conservative/aggressive para silencios;
- tests unitarios y end-to-end sintéticos.

Pendiente inmediato:

- motor de transcripción con timestamps precisos;
- transcript TXT/SRT;
- detección semántica de retomas/repeticiones/errores;
- protección semántica;
- informe de edición.

## 4. Estructura

```text
Archive/                 Sólo versiones finales sustituidas
Source/video_tunner/     Source vigente
Validation/              Provenance/hashes/evidencia ligera
.github/workflows/       Workflows permanentes mínimos
.github/scripts/         Sólo scripts permanentes cuando sean necesarios
tests/                   Tests pequeños; preferir fixtures sintéticos
README.md
AGENTS.md
RELEASE_STATUS.md
SHA256SUMS.txt
pyproject.toml
```

No dejar en `main` builds, dist, outputs, vídeos grandes, cachés, modelos descargados, logs, scripts temporales ni experimentos descartados.

## 5. Dependencias y resolución de herramientas

Core actual:

- Python >= 3.11.
- FFmpeg.
- ffprobe.

Orden de resolución actual para FFmpeg/ffprobe:

1. `VIDEO_TUNNER_FFMPEG_DIR`;
2. `<runtime-root>/Tools/ffmpeg/bin`;
3. `PATH`.

El uso de PATH es válido sólo durante desarrollo/CI inicial. La build portable final debe demostrar que funciona con sus dependencias empaquetadas y sin depender accidentalmente del software del runner.

Antes de añadir una dependencia:

1. justificar el problema concreto que resuelve;
2. comprobar si el stack actual ya lo resuelve;
3. fijar su versión/uso de forma reproducible;
4. validar integración real.

## 6. Edit Plan schema v1

Actualmente contiene:

- `schema_version`;
- `created_utc`;
- metadatos mínimos de source sin ruta absoluta;
- `mode`;
- parámetros de análisis;
- `edits[]` con action/kind/start/end/duration/reason/confidence;
- resumen de tiempo eliminado y duración estimada.

No introducir rutas absolutas del entorno de build en el plan.

Al evolucionar el schema, mantener compatibilidad o migración explícita; no cambiar silenciosamente el significado de campos existentes.

## 7. Modos

Modo por defecto: `conservative`.

Actual:

- conservative: `noise_db=-40`, `min_silence=0.65`, `keep_pause=0.20`.
- aggressive: `noise_db=-38`, `min_silence=0.35`, `keep_pause=0.10`.

Son parámetros iniciales, no verdades de producto. Cualquier tuneo debe validarse con muestras representativas antes de afirmarlo como mejora.

## 8. Render

El render actual:

- calcula el complemento temporal de los cortes `remove`;
- fusiona cortes superpuestos;
- usa `trim/atrim + concat`;
- codifica H.264 (`libx264`) + AAC;
- cancela si el plan eliminaría todo el vídeo;
- impide que destination sea el mismo archivo que source.

Actualmente se asume al menos una pista de vídeo y una de audio para el Cleaner hablado. Ampliar esta regla sólo con tests específicos.

## 9. Validación

No dar por válida una función sólo porque compile.

Cobertura progresiva obligatoria:

- rutas con espacios;
- probe real;
- silencios;
- render real;
- sincronización A/V;
- retomas/repeticiones/correcciones cuando se implementen;
- cifras y negaciones sensibles en protección semántica;
- cierre limpio de procesos;
- portabilidad real con dependencias empaquetadas.

Preferir generación dinámica de fixtures con FFmpeg frente a almacenar vídeos grandes.

Distinguir siempre:

- test unitario;
- test automático end-to-end;
- CI;
- validación manual realizada realmente por Guille.

No atribuir pruebas manuales que no se hayan realizado.

## 10. GitHub / CI / cuota

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
- no almacenar ZIPs, vídeos, modelos o payloads grandes como artifacts ordinarios;
- mantener retención mínima cuando un artifact pesado sea imprescindible;
- ahorrar eliminando redundancia, **nunca debilitando una prueba necesaria**.

El workflow inicial es exclusivamente `workflow_dispatch` y no debe adquirir triggers automáticos sin una necesidad técnica justificada.

## 11. README y este fichero

Regla obligatoria:

**Cualquier cambio relevante que modifique funcionamiento, arquitectura, dependencias, build, packaging, validación o forma de uso debe actualizar README.md y AGENTS.md en el mismo cambio cuando les afecte.**

README = descripción viva de producto/uso/estado.
AGENTS = contexto técnico permanente.

No crear un `00.Prompt Inicial` dentro del repositorio.

## 12. Seguridad y privacidad

- Procesamiento local por defecto.
- No enviar vídeos a APIs externas silenciosamente.
- No versionar originales ni outputs del usuario.
- No almacenar secretos o tokens.
- Evitar contenido sensible en logs.
- Limpiar temporales/procesos cuando corresponda.

## 13. Releases y Archive

No publicar ninguna Release sin autorización expresa de Guille.

Release final:

- un ZIP portable por plataforma salvo necesidad funcional real;
- hashes/provenance/logs permanecen en el repo, no como assets innecesarios;
- GitHub Actions no es almacenamiento histórico.

`Archive/` contiene únicamente versiones finales realmente publicadas y posteriormente sustituidas. Nunca builds fallidas, pruebas o reconstrucciones no verificadas.

## 14. Roadmap técnico

### Fase 0 — Bootstrap

Implementada en la primera iteración.

### Fase 1 — Cleaner técnico

Actual: probe + silencios + Edit Plan + render.
Pendiente: transcripción + TXT/SRT + robustez adicional.

### Fase 2 — Cleaner inteligente

Errores, retomas, repeticiones, muletillas, niveles de confianza y protección semántica.

### Fase 3 — Calidad audiovisual

Normalización, reducción de ruido, suavizado de cortes e informe.

### Fase 4 — Portable Windows

Empaquetado completo, rutas portables, entorno limpio, ZIP, SHA-256 y manifiesto.

### Fase 5 — Adicionales

Sólo si el Cleaner ya es fiable: subtítulos incrustados, reencuadre, zooms, clips/shorts, B-roll y otras funciones.

## 15. Changelog de tuneos

### 0.1.0-dev — bootstrap inicial

- Creación de arquitectura source-first.
- CLI inicial.
- Integración FFmpeg/ffprobe.
- Primer Cleaner de silencios auditable.
- Edit Plan schema v1.
- Render desde plan.
- Tests sintéticos sin fixtures audiovisuales persistentes.
- CI manual de bajo consumo.

Mantener este changelog actualizado con cambios técnicos relevantes.