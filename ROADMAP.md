# ROADMAP — Video_Tunner

## Principios

- Windows 10/11 x64 portable: ZIP → descomprimir → ejecutar.
- Vídeo con audio embebido o vídeo + audio externo.
- Master audio y sincronización antes de transcripción/VAD/semántica/acústica temporal.
- Originales intactos y decisiones auditables/reversibles.
- Ante baja confianza: REVIEW/manual, no adivinar.
- CI pesada sólo cuando aporta evidencia nueva.

## Fases completadas

### Fase 0 — Bootstrap
CLI, FFmpeg/ffprobe, probe, Cleaner de silencios, Edit Plan, render y tests.

### Fase 0.5 — Technology Harvest
Repo propio, no fork. Upstreams sólo como referencias/integraciones trazables.

### Fase 1A — Portable Foundation
Core `33600174568` PASS; ML frozen `33621357438` PASS.

### Fase 1B — Ingesta dual + sincronización A/V
Master FLAC, offset +/-, drift, confidence/residual/coverage, manual override y `review_required`. Hardening `33639009841` PASS.

### Fase 1C — Transcripción + VAD sobre master
Target Spanish `33656235038`: WER `1.64%`, RTF `0.4854`, automatic edits 0.

### Fase 2A — Semantic Candidates v1
Run `33659725847` PASS.

### Fase 2B — Semantic Decisions + Protection v1
Run `33741195594` PASS.

## Fase 2 — Cleaner inteligente — EN CURSO

### 2C — Validación semántica real — COMPLETADA COMO BLOQUE DE EVIDENCIA v1

- 2C.1 `33743029443`: benchmark foundation PASS.
- 2C.2 `33750836791`: corpus humano bilingüe PASS.
- 2C.3 `33755013415`: audio humano real → semantic gate PASS.

### 2D — Scope + fillers + join safety + eligibility — EN CURSO

#### 2D.1 — Correction Scope Foundation v1 — COMPLETADA
Schema v4. Final `33758185755`: 88/88 PASS.

#### 2D.2 — Fillers Contextuales Foundation v1 — COMPLETADA
Schema v5. Final `33771792867`: 101/101 PASS.

#### 2D.3 — Sentence/join safety — COMPLETADA COMO BLOQUE DE EVIDENCIA v1

- 2D.3.1 join context/schema v6: `33773287106`, 117/117 PASS.
- 2D.3.2 acoustic join/schema v7: `33781903986`, 131/131 PASS.
- 2D.3.3 human acoustic: `33782959293`, 134/134 PASS, human gate PASS.

No se modificaron thresholds acústicos tras la evidencia humana.

#### 2D.4 — Combined Eligibility / Promotion Policy Foundation v1 — COMPLETADA

Schema v8 añade `eligibility_assessments[]` y aplica guardas acumulativas fail-safe:

```text
removedText integrity
→ correction scope
→ filler context
→ semantic decision
→ join context
→ acoustic evidence
→ foundation_guards_pass OR blocker
```

`foundation_guards_pass` no es autorización de corte:

```text
future_promotion_candidate = true
safe_for_cut = false
executable = false
auto_apply = false
```

Benchmark: 12 casos, 4 rutas foundation positivas y 8 bloqueos deliberados.

Run `33790792753`: 138/138 PASS en 7.035 s; schema v8, removedText contract, FFmpeg/sync y doctor PASS; artifacts 0.

Detalle: `Validation/phase2d-combined-eligibility.md`.

#### 2D.5 — Human Combined Eligibility Evidence v1 — COMPLETADA

Se aplicó schema v8 sobre 3 casos AMI reales, reutilizando los endpoints de `large-v3-turbo` del run `33755013415` y el WAV AMI original CC BY 4.0.

Baseline `33791636767`:

```text
141/141 regression tests PASS
1 control foundation_guards_pass
2 casos bloqueados
0 safe_for_cut / executable / auto_apply
human gate FAIL únicamente por precedencia diagnóstica
```

El caso de correction ambigua quedaba bloqueado como `invalid_removed_text` antes de expresar el blocker más específico `blocked_correction_scope`. Se corrigió sólo la precedencia diagnóstica; no se relajó ninguna guarda ni cambió la capacidad de promoción.

Final `33791950505`:

```text
142/142 tests PASS en 7.087 s
HUMAN_ELIGIBILITY_GATE=PASS
cases                    3
foundation_guards_pass   1
blocked                  2
safe_for_cut             0
executable               0
auto_apply               0
automatic_edits          0
artifacts                 0
```

Resultados humanos:

- pausa de control → `foundation_guards_pass`; sigue no ejecutable y no es un positivo humano de removibilidad;
- retake humano → `blocked_semantic_decision`;
- correction humana ambigua → `blocked_correction_scope`, conservando `removed_text_reason=missing_target_span`.

Detalle: `Validation/phase2d-human-combined-eligibility.md`.

#### 2D.6 — Human Positive Eligibility Expansion / Close-out Gate — SIGUIENTE

Objetivo: reunir evidencia humana positiva específicamente etiquetada como **contenido realmente prescindible** antes de cerrar 2D o diseñar 2E.

Orden:

1. localizar varios clips humanos reales con licencia y procedencia claras;
2. priorizar español y habla espontánea; usar inglés como control si aporta cobertura;
3. exigir etiquetas humanas explícitas de `removable` vs `must_keep/review`, no inferirlas sólo porque la policy pase;
4. reconstruir ASR/timestamps + guardas completas hasta `eligibility_assessments`;
5. medir cuántos positivos humanos realmente removibles llegan a `foundation_guards_pass` y cuántos negativos quedan bloqueados;
6. no relajar thresholds o guardas para alcanzar una métrica objetivo;
7. mantener `safe_for_cut=false`, `executable=false`, `auto_apply=false`, `automatic_edits=0`;
8. sólo con evidencia suficiente decidir cierre de 2D y diseño de 2E.

### 2E — Promotion to Edit Plan — FUTURA

Sólo después del close-out gate de 2D:
- decidir clases realmente promocionables;
- definir aprobación y thresholds por modo;
- límites globales y fail-safe;
- resto en REVIEW / KEEP.

## Fase 3 — Calidad audiovisual / auditoría
Normalización, join treatment, denoise controlado, join audit, post-render verification e informe.

## Fase 4 — UX mínima
Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, renderizar y abrir outputs.

## Fase 5 — Portable Release Hardening
Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras
Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. mergear 2D.5 Human Combined Eligibility Evidence;
2. arrancar 2D.6 Human Positive Eligibility Expansion / Close-out Gate;
3. obtener positivos humanos de removibilidad, no meros controles técnicos;
4. no relajar guardas para fabricar positivos;
5. no iniciar 2E hasta cerrar 2D con evidencia suficiente.
