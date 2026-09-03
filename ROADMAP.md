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

Schema v8 añade:

```text
eligibility_assessments[]
```

La policy aplica guardas acumulativas y fail-safe:

```text
removedText integrity
→ correction scope
→ filler context
→ semantic decision
→ join context
→ acoustic evidence
→ foundation_guards_pass OR blocker
```

Estados:

```text
foundation_guards_pass
blocked_acoustic_context
blocked_filler_context
blocked_semantic_decision
blocked_join_context
blocked_correction_scope
invalid_removed_text
missing_required_evidence
```

`foundation_guards_pass` **no** es cut authorization:

```text
future_promotion_candidate = true
safe_for_cut = false
executable = false
auto_apply = false
```

Benchmark: 12 casos, 4 rutas foundation positivas y 8 bloqueos deliberados cubriendo todas las capas.

Run `33790792753`:

```text
138/138 tests PASS en 7.035 s
status contract PASS
removedText contract PASS
schema v8 integration PASS
FFmpeg/sync + doctor PASS
artifacts 0
```

Detalle: `Validation/phase2d-combined-eligibility.md`.

#### 2D.5 — Human Combined Eligibility Evidence — SIGUIENTE

Objetivo: comprobar la policy combinada con evidencia humana real antes de cerrar 2D.

Orden:

1. reutilizar endpoints humanos reales y procedencia ya fijada;
2. reconstruir las capas necesarias hasta `eligibility_assessments`;
3. confirmar que retakes/corrections/contextos protegidos siguen bloqueados;
4. validar `removedText` final con timings humanos reales;
5. medir si aparece alguna ruta humana `foundation_guards_pass` sin relajar policy;
6. si no aparece, registrar la ausencia y no fabricar un positivo;
7. mantener `safe_for_cut=false`, `executable=false`, `auto_apply=false`, `automatic_edits=0`.

### 2E — Promotion to Edit Plan — FUTURA

Sólo después de cerrar 2D con evidencia suficiente:
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

1. mergear 2D.4 combined eligibility/schema v8;
2. arrancar 2D.5 Human Combined Eligibility Evidence;
3. no relajar guardas para conseguir positivos humanos;
4. mantener toda elegibilidad no ejecutable;
5. decidir cierre de 2D sólo con evidencia humana suficiente.
