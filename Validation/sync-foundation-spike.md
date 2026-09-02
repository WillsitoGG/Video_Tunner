# Phase 1B — Sync Foundation validation

Fecha: 2026-09-02

## Alcance

Validación Windows del primer bloque de Fase 1B:

- vídeo con audio de cámara como referencia;
- audio externo con offset conocido;
- estimación automática multi-anchor;
- confidence + drift;
- materialización de `master_audio.flac` sobre la timeline del vídeo;
- rutas con espacios;
- política sin artifacts.

Convención temporal validada:

```text
video_time = offset_seconds + time_scale * external_time
```

Un offset positivo significa que el grabador externo empezó después que el vídeo.

## Runs

### Run #1 — `33633846344` — FAILURE

El código superó 32 tests, generó el fixture, `ingest` devolvió `ready_auto` y creó el master.

La validación falló porque el workflow comparaba el master contra una duración hardcoded de 90 s en vez de contra la timeline reportada del vídeo. El master medía 88.756 s.

Este run llevó a corregir la aserción, pero todavía no se había demostrado si 88.756 s era correcto.

### Run #2 — `33634121264` — FAILURE

Volvió a superar 32 tests y `ingest` devolvió `ready_auto`.

La aserción corregida reveló el defecto real:

```text
video=90.000 s
master=88.756 s
```

Causa: la cadena `apad` indefinido + `atrim` basado en timestamps no garantizaba que la duración del contenedor FLAC coincidiera con la timeline de muestras deseada. `atrim` no reescribe timestamps.

Corrección:

- regenerar PTS de audio desde número de muestras con `asetpts=N/SR/TB`;
- `apad=whole_dur=<video_duration>`;
- `atrim=duration=<video_duration>`;
- regenerar PTS final;
- `-t <video_duration>` como límite de salida;
- añadir test E2E de regresión de 4 s.

La corrección fue reproducida fuera de Actions: la cadena anterior daba 3.256 s para un caso 3 s + delay 1 s; la nueva da 4.000 s.

### Run #3 — `33634775313` — SUCCESS

Resultado final:

- Windows Server 2025 runner;
- Python 3.12.10;
- NumPy 2.5.2;
- FFmpeg/ffprobe 9.0.1;
- 33 tests: **PASS**;
- test de regresión master timeline: **PASS**;
- `ingest`: `ready_auto`;
- offset esperado: `+1.500 s`;
- offset estimado: `+1.500 s`;
- confidence: `1.000`;
- anchors: `7`;
- drift: `0 ppm`;
- duración vídeo: `90.000 s`;
- duración master FLAC: `90.000 s`;
- artifacts de Actions: `0`.

## Qué demuestra

Este spike demuestra que el primer bloque de sincronización puede:

1. recuperar un offset externo conocido;
2. exigir evidencia multi-anchor;
3. producir confidence y drift auditables;
4. materializar audio externo alineado con la timeline del vídeo;
5. mantener exactamente la duración del master en el caso validado;
6. operar sin convertir una estimación insegura en master automáticamente.

## Qué NO demuestra todavía

- robustez con grabaciones reales de cámara + grabador externo;
- ruido, reverberación o micrófonos muy distintos;
- offsets grandes fuera del fixture;
- drift real largo y no lineal;
- vídeos sin referencia acústica suficiente;
- cobertura externa parcial en E2E;
- validación portable frozen del nuevo comando `ingest`;
- post-cut A/V sync;
- uso del master audio por `analyze` y por el render final.

Esos puntos permanecen dentro de Fase 1B/1C y Release Hardening según corresponda.
