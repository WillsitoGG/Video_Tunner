# ROADMAP — Video_Tunner

## Principios

- Windows 10/11 x64 portable: ZIP → descomprimir → ejecutar.
- Vídeo con audio embebido o vídeo + audio externo.
- Master audio y sincronización antes de transcripción/VAD/semántica.
- Originales intactos y decisiones auditables/reversibles.
- Ante baja confianza: REVIEW/manual, no adivinar.
- CI pesada sólo cuando aporta evidencia nueva.

## Fases completadas

### Fase 0 — Bootstrap
CLI, FFmpeg/ffprobe, probe, Cleaner de silencios, Edit Plan, render y tests.

### Fase 0.5 — Technology Harvest
Repo propio, no fork. Upstreams sólo como referencias/integraciones trazables.

### Fase 1A — Portable Foundation
- core `33600174568` PASS;
- ML frozen `33621357438` PASS.

### Fase 1B — Ingesta dual + sincronización A/V
- master FLAC;
- offset positivo/negativo;
- drift;
- confidence/residual/coverage;
- manual override y `review_required`.

Hardening `33639009841` PASS.

### Fase 1C — Transcripción + VAD sobre master
Whisper y Silero VAD reciben exactamente el mismo master.

Target Spanish `33656235038`: WER `1.64%`, word timestamps PASS, RTF `0.4854`, automatic edits 0.

### Fase 2A — Semantic Candidates v1
`possible_repetition`, `possible_retake`, `explicit_correction`, todo review-only.

Run `33659725847`: 48 tests PASS.

### Fase 2B — Semantic Decisions + Protection v1

```text
candidate → semantic decision/protection → future approved edit
```

```text
KEEP / REVIEW / PROPOSED_TRIM / PROPOSED_CUT
executable = false
auto_apply = false
```

Run `33741195594`: 55 tests PASS, artifacts 0.

## Fase 2 — Cleaner inteligente — EN CURSO

### 2C — Validación semántica real — EN CURSO

#### 2C.1 — Benchmark/Validation Foundation v1 — COMPLETADA

Harness TP/FP/FN + precision/recall/F1 + safety.

Baseline `33742519997`:

```text
60 tests
FP 2 / FN 0
precision 84.62%
recall 100%
unsafe proposals 0
```

Tuneo conservador basado sólo en FP observados.

`33743029443`:

```text
64 tests
21 casos / 11 eventos
FP 0 / FN 0
precision = recall = F1 = 100% en ese corpus
unsafe proposals 0
executable 0
auto_apply 0
```

#### 2C.2 — Positivos/negativos humanos — EN CURSO, BLOQUE BILINGÜE COMPLETADO

Primer retake humano AMI:

`33743638690` — 65 tests PASS, `possible_retake → REVIEW`, 0 FP/FN.

Extensión bilingüe:

- AMI EN: `I mean` reparación real + `I mean` discursivo negativo;
- CORMA ES: `Perdón` tras fragmento abandonado + `perdón eh` disculpa negativa.

Baseline `33750475437`:

```text
69 tests PASS
26 casos / 14 eventos
14 TP / 2 FP / 0 FN
precision 87.50%
recall 100%
F1 93.33%
unsafe proposals 0
```

Los dos FP fueron los dos usos humanos ambiguos de marcador; gate falló sólo por precision.

Tuneo Conservador:

- `I mean / quiero decir`: exigir frontera de reparación o sustitución numérica;
- `perdón / perdona / sorry`: rechazar patrón de disculpa/hesitación sin intento interrumpido;
- fragmento truncado + marcador sigue `REVIEW`;
- Agresivo conserva detección más amplia.

Final `33750836791`:

```text
74 tests PASS en 6.729 s
26 casos / 14 eventos
FP 0 / FN 0
precision = recall = F1 = 100% en el corpus actual
unsafe proposals 0
decision mismatches 0
missing safe proposals 0
executable 0
auto_apply 0
artifacts 0
```

El corpus combinado incluye actualmente 3 positivos humanos y 2 negativos humanos explícitos, además de 4 controles SpanishPod.

**El 100% sólo vale para el corpus etiquetado actual.**

#### 2C.3 — Audio real → Whisper → semántica — SIGUIENTE

Objetivo: comprobar qué señales manuales de reparación sobreviven al ASR real.

Orden:

1. seleccionar pocos clips humanos con licencia/provenance clara, priorizando español;
2. ejecutar `large-v3-turbo` sólo si aporta evidencia nueva;
3. comparar transcript manual vs transcript Whisper para truncamientos, pausas y marcadores;
4. alimentar el mismo semantic gate;
5. registrar FP/FN sin mover thresholds;
6. endurecer sólo problemas observados.

### 2D — Scope de correcciones + fillers contextuales — FUTURA

- inferir con seguridad el span `intento incorrecto → corrección válida`;
- no confundir marker-only con scope de borrado;
- distinguir fillers eliminables de elementos semánticos/naturales;
- límites de frase y join safety.

### 2E — Promotion to Edit Plan — FUTURA

Sólo después de 2C/2D:

- decidir clases auto-aplicables;
- thresholds por modo;
- verificar joins y removedText;
- límite global de eliminación y fail-safe;
- resto en `REVIEW / KEEP`.

## Fase 3 — Calidad audiovisual / auditoría
Normalización, joins, denoise controlado, join audit, post-render verification e informe.

## Fase 4 — UX mínima
Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, renderizar y abrir outputs.

## Fase 5 — Portable Release Hardening
Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras
Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. preparar 2C.3 con pocos clips humanos reales y trazables;
2. priorizar español y casos donde truncamiento/puntuación puedan perderse en Whisper;
3. medir transcript real + semantic gate;
4. después resolver correction scope;
5. fillers contextuales;
6. sentence/join safety;
7. mantener `executable=false`;
8. no promover al Edit Plan hasta superar la evidencia.
