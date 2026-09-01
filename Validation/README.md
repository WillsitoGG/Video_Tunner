# Validation

Esta carpeta conserva únicamente evidencia técnica ligera y reproducible: hashes, manifiestos de versiones, provenance y resúmenes de validación cuando proceda.

No usarla para almacenar vídeos, ZIPs de CI, logs voluminosos ni outputs temporales.

## Bootstrap 0.1.0-dev

Antes de incorporar el bootstrap inicial al repositorio se ejecutaron en el entorno de desarrollo:

- tests unitarios iniciales: OK.
- test end-to-end sintético adicional: OK.
- `doctor` con FFmpeg/ffprobe reales: OK.
- render real de un MP4 de 3,0 s con 1 s de silencio central: output ~2,22 s.
- Edit Plan detectó y retiró ~0,80 s manteniendo ~0,20 s de pausa.
- ruta de entrada y salida con espacios: OK en el test end-to-end.

## Transcription/VAD candidate layer

Validación realizada antes de la incorporación:

- 16 tests automáticos totales: OK.
- serialización de transcript word-level: OK.
- TXT/JSON/SRT: OK.
- timestamps SRT: OK.
- complemento y fusión de speech intervals: OK.
- Candidate Analysis: ningún candidato se auto-aplica: OK.
- enriquecimiento VAD + word-gap: OK.
- SHA-256 del source: OK.
- orquestación del pipeline con backends simulados: OK.
- extracción real WAV mono 16 kHz PCM16 con FFmpeg: OK.
- regresión end-to-end del Cleaner de silencios previo: OK.
- `python -m compileall`: OK.
- `doctor`: FFmpeg/ffprobe reales detectados; dependencias ML reportadas como ausentes en el entorno de validación.

No se pudo validar en este entorno:

- inferencia real `faster-whisper`;
- carga/descarga real `large-v3-turbo`;
- inferencia real `silero-vad`;
- pipeline completo `video-tunner analyze` sobre voz real.

Estas pruebas **no equivalen a validación Windows ni a validación portable**. La CI Windows manual todavía no se ha ejecutado.
