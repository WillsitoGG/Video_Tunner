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

#### 2E.2 — Explicit Approval Contract / approval schema v1 — COMPLETADA

La aprobación se guarda como artefacto separado `promotion_approval.json`; no muta `analysis.json`.

Final `33899857378`: 174/174 PASS + doctor.

#### 2E.3 — Approved Edit Plan Proposal + Global Limits / proposal schema v1 — COMPLETADA

Transforma exclusivamente approvals que siguen siendo `valid_approved` en una propuesta globalmente limitada y todavía no ejecutable.

Límites precomprometidos e idénticos para `conservative` y `aggressive`:

```text
max_semantic_edits    = 10
max_removed_seconds   = 30.0
max_removed_fraction  = 0.05
```

Sólo `possible_repetition` está soportada.

Fail-safe total ante:

```text
stale/rejected/invalid approval
duplicados
target fuera de timeline
overlaps
clase no soportada
exceso de cualquier límite global
```

Proposal positiva:

```text
status = proposal_ready_for_global_review
proposed_edits[]
requires_global_review = true
globally_approved = false
render_authorization = false
executable = false
auto_apply = false
```

El renderer mantiene una barrera explícita: cualquier artefacto con `proposed_edits` es rechazado por `render_from_plan`.

Validación:

```text
33900544072  185/185 PASS en 5.144 s + doctor
33908500929  186/186 PASS en 7.887 s + doctor
```

Detalle: `Validation/phase2e-approved-plan-proposal.md`.

#### 2E.4 — Execution Authorization / Semantic Render Gate — SIGUIENTE

Objetivo: introducir una autorización global explícita y stale-safe sobre una proposal completa, todavía separando autorización, materialización de Edit Plan y render.

Orden:

1. definir artefacto de autorización global separado;
2. ligar autorización al SHA/fingerprint exacto de `analysis.json` y proposal;
3. actor + reason + timestamp obligatorios;
4. revalidar que proposal siga `proposal_ready_for_global_review`;
5. invalidar autorización si analysis/proposal cambian o son manipulados;
6. materializar `edits[]` ejecutables sólo desde autorización global vigente;
7. conservar provenance completa a approvals y proposal;
8. mantener renderer cerrado a proposals no autorizadas;
9. añadir semantic render gate y pre-render sanity checks;
10. definir post-render verification antes de auto-apply general.

#### 2E.5 — Semantic Render Verification / Close-out — FUTURA

Después de 2E.4:
- render controlado de semantic edits autorizados;
- comprobación post-render de duración, streams y continuidad;
- audit trail completo;
- evidencia humana perceptual de joins renderizados;
- decisión de cierre de Fase 2E.

## Fase 3 — Calidad audiovisual / auditoría
Normalización, join treatment, denoise controlado, join audit, post-render verification e informe.

## Fase 4 — UX mínima
Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, aprobar/rechazar, preparar plan, autorizar, renderizar y abrir outputs.

## Fase 5 — Portable Release Hardening
Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras
Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. integrar 2E.3 en `main` con workflow manual-only;
2. crear rama limpia para 2E.4;
3. diseñar autorización global como artefacto separado;
4. mantener proposal y renderer explícitamente incompatibles;
5. materializar Edit Plan sólo tras autorización global válida;
6. reservar CI pesada para evidencia que cambie una decisión técnica.
