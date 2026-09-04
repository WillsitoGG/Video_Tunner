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

### Fase 2C — Validación semántica real — COMPLETADA COMO BLOQUE DE EVIDENCIA v1

- 2C.1 `33743029443`: benchmark foundation PASS.
- 2C.2 `33750836791`: corpus humano bilingüe PASS.
- 2C.3 `33755013415`: audio humano real → semantic gate PASS.

## Fase 2 — Cleaner inteligente — EN CURSO

### 2D — Scope + fillers + join safety + eligibility — COMPLETADA COMO FOUNDATION/EVIDENCE

- 2D.1 correction scope/schema v4: `33758185755`, 88/88 PASS.
- 2D.2 fillers/schema v5: `33771792867`, 101/101 PASS.
- 2D.3.1 join context/schema v6: `33773287106`, 117/117 PASS.
- 2D.3.2 acoustic join/schema v7: `33781903986`, 131/131 PASS.
- 2D.3.3 human acoustic: `33782959293`, 134/134 PASS.
- 2D.4 combined eligibility/schema v8: `33790792753`, 138/138 PASS.
- 2D.5 human eligibility: `33791950505`, 142/142 PASS.
- 2D.6 human positive close-out: `33894995584`, `CLOSE_OUT_READY`.

2D terminó con 8 casos humanos AMI, 6 positivos alineados, 3 `foundation_guards_pass` en 2 fuentes y 0 capacidad ejecutable. No se relajaron thresholds.

### 2E — Promotion to Edit Plan — EN CURSO

#### 2E.1 — Promotion Policy Foundation / schema v9 — COMPLETADA

Se introduce `promotion_assessments[]` entre eligibility y un futuro Edit Plan aprobado.

La primera whitelist respaldada por evidencia humana es deliberadamente estrecha:

```text
possible_repetition
```

`conservative` y `aggressive` usan la misma whitelist. No se amplían clases por modo sin evidencia.

Estados:

```text
eligible_for_promotion_review
blocked_upstream_eligibility
blocked_removed_text_validation
blocked_unvalidated_candidate_kind
invalid_candidate_reference
```

Un `eligible_for_promotion_review` sigue siendo sólo revisión:

```text
requires_explicit_approval = true
approved = false
edit = null
safe_for_cut = false
executable = false
auto_apply = false
```

Validación:

```text
33896244733  165/165 PASS — policy/report aislados
33898758391  165/166 — fixture bloqueado correctamente por `hoy`
33898967491  165/166 — fixture bloqueado correctamente por `vamos`
33899201093  166/166 PASS en 7.079 s + doctor PASS
```

Los dos fallos intermedios fueron errores de construcción del fixture positivo y confirmaron el funcionamiento de las join guards. Sólo se cambiaron fixtures; no producto ni thresholds.

Detalle: `Validation/phase2e-promotion-foundation.md`.

#### 2E.2 — Explicit Approval Contract — SIGUIENTE

Objetivo: definir cómo una promotion assessment puede recibir una aprobación explícita, íntegra y auditable, manteniendo separado approval de Edit Plan y ejecución.

Orden:

1. definir schema/objeto de aprobación explícita;
2. ligar approval a candidate + promotion assessment + target exactos;
3. incluir fingerprints/provenance para invalidar approvals obsoletos;
4. mantener blockers upstream como veto absoluto;
5. definir estados de aprobación/rechazo/revisión;
6. no crear todavía auto-apply por defecto;
7. añadir contrato para una futura conversión approval → Edit Plan proposal;
8. validar en CI core antes de cualquier evidencia humana pesada adicional.

#### 2E.3 — Approved Edit Plan Proposal / Global Limits — FUTURA

Después de 2E.2:
- convertir sólo approvals válidos en propuestas de Edit Plan;
- límites globales de número/duración/porcentaje retirado;
- conflictos/overlaps;
- fail-safe y reversibilidad;
- mantener ejecución automática separada.

## Fase 3 — Calidad audiovisual / auditoría
Normalización, join treatment, denoise controlado, join audit, post-render verification e informe.

## Fase 4 — UX mínima
Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, renderizar y abrir outputs.

## Fase 5 — Portable Release Hardening
Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras
Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. integrar 2E.1 en `main` con schema v9 y workflow manual-only;
2. arrancar 2E.2 desde `main` limpio;
3. diseñar approval explícito sin convertir review candidates en edits;
4. añadir fingerprints/provenance y fail-safe de stale approvals;
5. reservar CI pesada para evidencia que cambie una decisión técnica.
