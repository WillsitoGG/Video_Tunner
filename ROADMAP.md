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

### Fase 2C — Validación semántica real
Completada como bloque de evidencia v1.

## Fase 2 — Cleaner inteligente — EN CURSO

### 2D — Scope + fillers + join safety + eligibility — COMPLETADA COMO FOUNDATION/EVIDENCE

Cierre humano `33894995584`: 8 casos AMI, 6 positivos alineados, 3 `foundation_guards_pass` en 2 fuentes, `CLOSE_OUT_READY`, 0 capacidad ejecutable.

### 2E — Promotion to Edit Plan — EN CURSO

#### 2E.1 — Promotion Policy Foundation / analysis schema v9 — COMPLETADA

`promotion_assessments[]` separa eligibility de cualquier futuro Edit Plan. Sólo `possible_repetition` puede entrar en `eligible_for_promotion_review`, por respaldo humano 2D.6.

Final `33899201093`: 166/166 PASS + doctor.

Detalle: `Validation/phase2e-promotion-foundation.md`.

#### 2E.2 — Explicit Approval Contract / approval schema v1 — COMPLETADA

La aprobación se guarda como artefacto separado `promotion_approval.json`; **no muta `analysis.json`**, que continúa en schema v9.

Contrato:

```text
eligible_for_promotion_review
+ explicit human decision
+ actor + reason
+ exact analysis SHA-256
+ canonical evidence fingerprint
→ valid_approved | valid_rejected
```

Fail-safe:

```text
analysis/evidence changed → stale
upstream blocker → approval creation blocked
tampering → invalid_record
valid_approved != Edit Plan authorization
```

Incluso `valid_approved` mantiene:

```text
edit_plan_authorization = false
edit = null
safe_for_cut = false
executable = false
auto_apply = false
```

CLI:

```text
approval create
approval validate
```

Final `33899857378`:

```text
174/174 PASS en 7.150 s
doctor PASS
```

Detalle: `Validation/phase2e-explicit-approval-contract.md`.

#### 2E.3 — Approved Edit Plan Proposal + Global Limits — SIGUIENTE

Objetivo: transformar sólo approvals `valid_approved` en una **propuesta** de Edit Plan controlada, todavía sin auto-render.

Orden:

1. revalidar approval contra analysis SHA/fingerprint;
2. aceptar sólo `possible_repetition` inicialmente;
3. materializar target aprobado como propuesta `remove` auditable;
4. validar bounds contra duración del vídeo;
5. rechazar overlaps y conflictos;
6. fijar antes de evaluar resultados límites máximos de:
   - número de semantic edits;
   - segundos totales retirados;
   - porcentaje total de duración retirado;
7. fail closed si cualquier approval es stale/rejected/invalid;
8. proposal != executable Edit Plan;
9. definir paso explícito posterior para autorizar ejecución;
10. validar con CI core antes de nueva evidencia humana pesada.

#### 2E.4 — Execution Authorization / Semantic Render Gate — FUTURA

Sólo después de 2E.3:
- contrato de autorización del plan propuesto;
- revisión global final;
- render gate;
- reversibilidad/auditoría;
- sin mezclar aprobación individual con autorización global de ejecución.

## Fase 3 — Calidad audiovisual / auditoría
Normalización, join treatment, denoise controlado, join audit, post-render verification e informe.

## Fase 4 — UX mínima
Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, aprobar/rechazar, preparar plan, renderizar y abrir outputs.

## Fase 5 — Portable Release Hardening
Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras
Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. integrar 2E.2 en `main` con workflow manual-only;
2. crear rama limpia para 2E.3;
3. predefinir límites globales antes de observar resultados;
4. implementar Approved Edit Plan Proposal sin ejecución;
5. reservar CI pesada para evidencia que cambie una decisión técnica.
