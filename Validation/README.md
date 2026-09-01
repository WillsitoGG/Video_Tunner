# Validation

Esta carpeta conservará únicamente evidencia técnica ligera y reproducible: hashes, manifiestos de versiones, provenance y resúmenes de validación cuando proceda.

No usarla para almacenar vídeos, ZIPs de CI, logs voluminosos ni outputs temporales.

## Bootstrap 0.1.0-dev

Antes de incorporar el código al repositorio se ejecutaron en el entorno de desarrollo:

- 4 tests unitarios iniciales: OK.
- test end-to-end sintético adicional: OK.
- `doctor` con FFmpeg/ffprobe reales: OK.
- render real de un MP4 de 3,0 s con 1 s de silencio central: output ~2,22 s.
- Edit Plan detectó y retiró ~0,80 s manteniendo ~0,20 s de pausa.
- ruta de entrada y salida con espacios: OK en el test end-to-end.

Estas pruebas **no equivalen a validación Windows ni a validación portable**. La CI Windows manual todavía no se ha ejecutado.
