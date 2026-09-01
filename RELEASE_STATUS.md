# Release Status

## Estado actual

- Proyecto: Video_Tunner
- Versión de desarrollo: `0.1.0-dev`
- Release publicada: **no**
- ZIP portable validado: **no**
- Windows 10/11 x64 validado manualmente: **no**
- Audio externo soportado: **no todavía**
- Auto-sync A/V validado: **no**
- Drift detection/correction validado: **no**
- Fase 0: bootstrap implementado
- Fase 0.5: technology harvest y estrategia de upstream definida
- Fase 1A: Portable Foundation — siguiente bloque crítico
- Fase 1B: ingesta dual + sincronización A/V — pendiente
- Fase 1C: transcripción/VAD — parcial; código implementado, runtime real y adaptación a master audio pendientes

## Requisitos de producto ya fijados

Video_Tunner no se considerará producto final hasta cumplir simultáneamente:

1. **Portable Windows 10/11 x64**: ZIP → descomprimir → ejecutar, sin Python/FFmpeg externos ni instalación.
2. **Ingesta dual**: vídeo con audio embebido o vídeo + audio externo.
3. **Sincronización externa**: auto-sync cuando exista referencia suficiente, fallback/override manual y tratamiento validado del drift en grabaciones largas.
4. El audio elegido/sincronizado debe convertirse en `master audio` común a análisis y render.

La portabilidad ya no se planifica como una fase tardía: debe demostrarse desde Fase 1A y endurecerse antes de Release.

No existe todavía ningún paquete que deba figurar en `SHA256SUMS.txt` ni ninguna versión sustituida que deba entrar en `Archive/`.

No publicar una GitHub Release sin autorización expresa de Guille.
