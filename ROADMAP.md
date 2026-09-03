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

### 2C — Validación semántica real — COMPLETADA COMO BLOQUE DE EVIDENCIA v1

#### 2C.1 — Benchmark/Validation Foundation v1 — COMPLETADA

`33743029443`: 21 casos / 11 eventos, 0 FP/FN, unsafe 0.

#### 2C.2 — Positivos/negativos humanos bilingües — COMPLETADA

Final `33750836791`:

```text
74 tests PASS en 6.729 s
26 casos / 14 eventos
FP 0 / FN 0
precision = recall = F1 = 100% en el corpus etiquetado actual
unsafe proposals 0
executable 0
auto_apply 0
artifacts 0
```

#### 2C.3 — Audio real → Whisper → semántica — COMPLETADA

Final pesada `33755013415`:

```text
3 casos reales
0 failures
53.810 s análisis total
SEMANTIC_AUDIO_GATE=PASS
automatic_edits 0
executable 0
auto_apply 0
artifacts 0
```

Evidencia nueva:

- Whisper puede borrar una vacilación y fabricar una repetición textual perfecta;
- timing anómalamente comprimido => `REVIEW`;
- Whisper puede eliminar guiones/truncamientos de una autocorrección;
- `question_reframe_cue` recupera `I mean how...` conservadoramente;
- `I mean` discursivo sigue sin ser `explicit_correction`.

**El 100% de 2C.2 sólo vale para ese corpus; 2C.3 demuestra tres casos audio-backed, no seguridad universal.**

### 2D — Scope de correcciones + fillers contextuales + join safety — EN CURSO

#### 2D.1 — Correction Scope Foundation v1 — COMPLETADA

`analysis.json` schema v4:

```text
candidates[]
correction_scopes[]
semantic_decisions[]
```

Estados:

```text
bounded
ambiguous
invalid
```

Todo scope conserva `safe_for_cut=false`, `executable=false`, `auto_apply=false`.

Benchmark: 12 casos. Final `33758185755`: **88/88 tests PASS en 6.711 s**, E2E FFmpeg/sync + doctor PASS, artifacts 0.

Detalle: `Validation/phase2d-correction-scope.md`.

#### 2D.2 — Fillers contextuales foundation v1 — COMPLETADA

Nueva separación:

```text
possible_filler candidate
→ filler assessment
→ future join/safety decision
```

`analysis.json` pasa a schema v5:

```text
candidates[]
correction_scopes[]
filler_assessments[]
semantic_decisions[]
```

Estados v1:

```text
isolated_hesitation
hesitation_cluster
protected_repair_context
boundary_hesitation
uncertain_asr
invalid
```

Reglas principales:

- filler dentro/junto a retake/correction => protegido;
- cluster => evaluación conjunta;
- transcript boundary o gap >= 0.60 s => boundary hesitation;
- ASR < 0.60 => uncertain;
- ninguna clase es `safe_for_cut` todavía.

Benchmark v1:

```text
15 casos ES/EN
retakes/corrections
clusters
boundaries
baja confianza
AMI humano + SpanishPod control
```

Evidencia:

```text
33771489008  101/101 PASS en 7.030 s — contextual benchmark
33771792867  101/101 PASS en 5.031 s — schema v5 + pipeline integration
```

E2E FFmpeg/sync y doctor PASS; artifacts 0.

Limitación: audio real 2C.3 demostró que Whisper puede omitir un filler. 2D.2 sólo clasifica fillers que sobreviven al ASR; no debe inventarlos.

Detalle: `Validation/phase2d-contextual-fillers.md`.

#### 2D.3 — Sentence boundaries + join safety — SIGUIENTE

Objetivo: demostrar que los dos lados de un futuro corte pueden unirse sin romper palabras, frase, turno, intención o prosodia.

Orden:

1. representar evidencia de boundary izquierdo/derecho por separado del candidate;
2. no confiar sólo en puntuación ASR;
3. medir distancia temporal a palabras, gaps y contexto léxico;
4. proteger joins adyacentes a negaciones, cifras, entidades, cambios de sujeto y reparaciones;
5. construir corpus positivo/negativo de join safety;
6. definir `removedText` exacto sólo cuando span + ambos lados sean auditables;
7. mantener `safe_for_cut=false`, `executable=false`, `auto_apply=false` durante la foundation.

### 2E — Promotion to Edit Plan — FUTURA

Sólo después de 2D:

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

1. mergear 2D.2 contextual fillers foundation;
2. arrancar 2D.3 sentence boundaries + join safety;
3. construir benchmark de joins antes de promover nada;
4. mantener `safe_for_cut=false`, `executable=false`, `auto_apply=false`;
5. no promover al Edit Plan hasta superar 2D.
