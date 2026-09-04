# Release Status

## Estado actual

- Proyecto: Video_Tunner
- Versión de desarrollo: `0.1.0-dev`
- Release publicada: **no**
- ZIP portable final validado: **no**
- Windows 10/11 x64 validado manualmente por Guille: **no**
- Fase 0–2C: COMPLETADAS según evidencia registrada
- Fase 2D: **CERRADA COMO FOUNDATION/EVIDENCE**
- Fase 2E.1: **COMPLETADA — Promotion Policy Foundation / analysis schema v9**
- Fase 2E.2: **COMPLETADA — Explicit Approval Contract / approval schema v1**
- Fase 2E.3: **COMPLETADA — Approved Edit Plan Proposal + Global Limits / proposal schema v1**
- Fase 2E: **EN CURSO**
- Fase 2E.4: **SIGUIENTE — Execution Authorization / Semantic Render Gate**

## Evidencia principal

```text
Portable core                    33600174568  PASS
Portable ML                      33621357438  PASS
Sync hardening                   33639009841  PASS
Target Spanish                   33656235038  PASS — WER 1.64%, RTF 0.4854
Phase 2D.6 human close-out       33894995584  PASS — CLOSE_OUT_READY
Phase 2E.1 integrated schema v9  33899201093  PASS — 166/166 + doctor
Phase 2E.2 explicit approval     33899857378  PASS — 174/174 + doctor
Phase 2E.3 proposal foundation   33900544072  PASS — 185/185 + doctor
Phase 2E.3 renderer isolation    33908500929  PASS — 186/186 + doctor
```

## Analysis schema v9

`analysis.json` permanece v9.

## Approval artifact schema v1

```text
promotion_approval.json
schema_version = 1
record_type = promotion_approval
```

## Proposal artifact schema v1

```text
approved_edit_plan_proposal.json
schema_version = 1
record_type = approved_edit_plan_proposal
```

La proposal usa `proposed_edits[]`, no `edits[]`.

## Fase 2E.3 — contrato de seguridad

Sólo consume approvals que sigan validando como `valid_approved` frente al `analysis.json` actual.

Límites globales precomprometidos:

```text
max_semantic_edits    = 10
max_removed_seconds   = 30.0
max_removed_fraction  = 0.05
```

Sólo `possible_repetition` está soportada inicialmente.

Cualquier blocker invalida la proposal completa:

```text
no approvals
stale/rejected/invalid approval
duplicate target
unsupported candidate kind
invalid/out-of-timeline target
overlapping targets
max edit count exceeded
max removed seconds exceeded
max removed fraction exceeded
```

Proposal lista:

```text
status = proposal_ready_for_global_review
requires_global_review = true
globally_approved = false
render_authorization = false
executable = false
auto_apply = false
```

Cada proposed edit también permanece no autorizado/no ejecutable.

## Renderer boundary

El renderer ejecutable sólo trabaja con Edit Plans materializados. Además, `render_from_plan` rechaza explícitamente cualquier artefacto que contenga `proposed_edits`, por lo que una proposal no puede atravesar accidentalmente el renderer como plan ejecutable.

## Validación 2E.3

`33900544072`:

```text
185/185 tests PASS en 5.144 s
doctor PASS
all global limit tests PASS
overlap/duplicate/stale/rejected/timeline blockers PASS
valid proposal stays review-only PASS
```

Hardening final `33908500929`:

```text
186/186 tests PASS en 7.887 s
doctor PASS
renderer rejects non-executable proposal PASS
```

Workflow restaurado a `workflow_dispatch`. No se habilitó auto-render ni auto-apply semántico.

Evidencia: `Validation/phase2e-approved-plan-proposal.md`.

## Safety actual

```text
candidate != promotion assessment != approval != proposal != executable edit
valid_approved approval != Edit Plan authorization
proposal_ready_for_global_review != render authorization
proposed_edits[] != edits[]
globally_approved = false
render_authorization = false
executable = false
auto_apply = false
automatic_edits = 0
```

## Pendiente antes de Release

- Fase 2E.4: Execution Authorization / Semantic Render Gate;
- Fase 2E.5: semantic render verification / close-out;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
