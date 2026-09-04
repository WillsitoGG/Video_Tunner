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
- Fase 2E.2: **COMPLETADA — Explicit Approval Contract / approval artifact schema v1**
- Fase 2E: **EN CURSO**
- Fase 2E.3: **SIGUIENTE — Approved Edit Plan Proposal + Global Limits**

## Evidencia principal

```text
Portable core                    33600174568  PASS
Portable ML                      33621357438  PASS
Sync hardening                   33639009841  PASS
Target Spanish                   33656235038  PASS — WER 1.64%, RTF 0.4854
Phase 2D.4 combined eligibility  33790792753  PASS — 138/138, schema v8
Phase 2D.5 human eligibility     33791950505  PASS — 142/142
Phase 2D.6 human close-out       33894995584  PASS — CLOSE_OUT_READY
Phase 2E.1 integrated schema v9  33899201093  PASS — 166/166 + doctor
Phase 2E.2 explicit approval     33899857378  PASS — 174/174 + doctor
```

## Analysis schema v9

`analysis.json` permanece v9 después de 2E.2:

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
acoustic_join_assessments[]
semantic_decisions[]
eligibility_assessments[]
promotion_assessments[]
```

## Approval artifact schema v1

Nuevo artefacto separado:

```text
promotion_approval.json
schema_version = 1
record_type = promotion_approval
```

No se muta el análisis para registrar la decisión.

Un approval liga:

```text
analysis SHA-256
candidate ID/kind
eligibility ID/status
promotion assessment ID/status
mode
target exacto
canonical evidence fingerprint
actor
reason
timestamp
```

Estados de validación:

```text
valid_approved
valid_rejected
stale_analysis
stale_evidence
stale_or_invalid_reference
invalid_record
```

Safety:

```text
valid_approved != Edit Plan authorization
edit_plan_authorization = false
edit = null
safe_for_cut = false
executable = false
auto_apply = false
```

Records manipulados que intenten declarar autorización de plan, edit o ejecución son inválidos.

## Validación 2E.2

Run `33899857378`:

```text
174/174 tests PASS en 7.150 s
doctor PASS
APPROVE valid/no-edit-authority PASS
REJECT auditability PASS
analysis SHA stale detection PASS
upstream evidence stale detection PASS
upstream blocker veto PASS
tampered edit authorization blocked PASS
mandatory actor/reason PASS
fingerprint roundtrip PASS
```

Workflow restaurado a `workflow_dispatch`. No se subieron artifacts pesados.

Evidencia: `Validation/phase2e-explicit-approval-contract.md`.

## Safety actual

```text
candidate != promotion assessment != approval != edit
foundation_guards_pass != safe cut
promotion_review_candidate != approval
valid_approved approval != Edit Plan authorization
edit_plan_authorization = false
safe_for_cut = false
executable = false
auto_apply = false
automatic_edits = 0
```

## Pendiente antes de Release

- Fase 2E.3: Approved Edit Plan Proposal + Global Limits;
- posterior autorización global/semantic render gate;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
