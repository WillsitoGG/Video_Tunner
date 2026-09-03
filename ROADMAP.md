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
Master FLAC, offset +/-, drift, confidence/residual/coverage, manual override y `review_required`. Hardening `33639009841` PASS.

### Fase 1C — Transcripción + VAD sobre master
Whisper y Silero VAD reciben exactamente el mismo master. Target Spanish `33656235038`: WER `1.64%`, word timestamps PASS, RTF `0.4854`, automatic edits 0.

### Fase 2A — Semantic Candidates v1
`possible_repetition`, `possible_retake`, `explicit_correction`, todo review-only. Run `33659725847`: 48 tests PASS.

### Fase 2B — Semantic Decisions + Protection v1

```text
candidate → semantic decision/protection → future approved edit
KEEP / REVIEW / PROPOSED_TRIM / PROPOSED_CUT
executable = false
auto_apply = false
```

Run `33741195594`: 55 tests PASS, artifacts 0.

## Fase 2 — Cleaner inteligente — EN CURSO

### 2C — Validación semántica real — COMPLETADA COMO BLOQUE DE EVIDENCIA v1

- 2C.1 final `33743029443`: 21 casos / 11 eventos, 0 FP/FN, unsafe 0.
- 2C.2 final `33750836791`: 74 tests; 26 casos / 14 eventos; 0 FP/FN en corpus etiquetado; unsafe/executable/auto_apply 0.
- 2C.3 audio-backed `33755013415`: 3 casos reales AMI; semantic gate PASS; automatic_edits/executable/auto_apply 0; artifacts 0.

No generalizar las métricas del corpus a habla arbitraria.

### 2D — Scope + fillers + join safety — EN CURSO

#### 2D.1 — Correction Scope Foundation v1 — COMPLETADA

Schema v4 con `correction_scopes[]`. Estados `bounded / ambiguous / invalid`. Todo scope conserva `safe_for_cut=false`, `executable=false`, `auto_apply=false`.

Benchmark 12 casos. Final `33758185755`: **88/88 PASS en 6.711 s**, E2E FFmpeg/sync + doctor PASS, artifacts 0.

Detalle: `Validation/phase2d-correction-scope.md`.

#### 2D.2 — Fillers contextuales Foundation v1 — COMPLETADA

Schema v5 con `filler_assessments[]`.

Estados:

```text
isolated_hesitation
hesitation_cluster
protected_repair_context
boundary_hesitation
uncertain_asr
invalid
```

Benchmark 15 casos ES/EN. Final `33771792867`: **101/101 PASS en 5.031 s**, E2E FFmpeg/sync + doctor PASS, artifacts 0.

Limitación: si Whisper omite un filler, la capa no lo inventa.

Detalle: `Validation/phase2d-contextual-fillers.md`.

#### 2D.3 — Sentence boundaries + join safety — EN CURSO

##### 2D.3.1 — Boundary/timeline/lexical foundation v1 — COMPLETADA

Schema v6:

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
semantic_decisions[]
```

Estados de join:

```text
join_context_only
sentence_boundary_risk
segment_boundary_risk
critical_lexical_context_risk
repair_or_protected_context_risk
transcript_edge
invalid_or_unbounded_target
```

Principios:

- target corrupto o correction scope ambiguous => no join target;
- proteger repairs, cifras/unidades/negación/persona/tiempo/causalidad;
- puntuación ASR = señal, no verdad;
- `join_context_only` = contexto bilateral sin guarda v1, **no cut seguro**;
- todo join assessment sigue `safe_for_cut=false`, `executable=false`, `auto_apply=false`.

Benchmark 15 casos, incluyendo retake humano AMI.

Evidencia:

```text
33772715214  112/112 PASS en 6.670 s — foundation
33773287106  117/117 PASS en 6.891 s — benchmark + schema v6
```

E2E FFmpeg/sync + doctor PASS; artifacts 0.

`join_acoustic_validation_enabled=false`: esta foundation no acredita continuidad de waveform/energía/prosodia.

Detalle: `Validation/phase2d-join-safety.md`.

##### 2D.3.2 — Acoustic join validation — SIGUIENTE

Objetivo: evaluar el join hipotético sobre **master audio**, sin promover todavía edits.

Orden:

1. extraer/analizar ventanas reales antes y después de los endpoints del join;
2. medir energía/RMS, salto de waveform/DC y otros proxies conservadores;
3. detectar speech-boundary y discontinuity risk;
4. benchmark sintético pequeño y reproducible;
5. usar audio humano real sólo si aporta evidencia nueva;
6. mantener `safe_for_cut=false`, `executable=false`, `auto_apply=false` durante esta foundation;
7. no modificar aún el hard concat de `render.py` ni promover al Edit Plan.

### 2E — Promotion to Edit Plan — FUTURA

Sólo después de cerrar 2D con evidencia suficiente:
- decidir clases auto-aplicables;
- thresholds por modo;
- verificar joins y removedText;
- límites globales y fail-safe;
- resto en `REVIEW / KEEP`.

## Fase 3 — Calidad audiovisual / auditoría
Normalización, join treatment, denoise controlado, join audit, post-render verification e informe.

## Fase 4 — UX mínima
Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, renderizar y abrir outputs.

## Fase 5 — Portable Release Hardening
Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras
Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. mergear 2D.3.1 join boundary/timeline/lexical foundation;
2. arrancar 2D.3.2 acoustic join validation;
3. medir waveform/energy risk sin habilitar cortes;
4. mantener `safe_for_cut=false`, `executable=false`, `auto_apply=false`;
5. no promover al Edit Plan hasta superar 2D.
