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
- Fase 2E.3: **COMPLETADA — Approved Edit Plan Proposal / proposal schema v1**
- Fase 2E.4: **COMPLETADA — Execution Authorization / Semantic Render Gate**
- Fase 2E: **EN CURSO**
- Fase 2E.5: **SIGUIENTE — Semantic Render Verification / Close-out**

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
Phase 2E.4 execution core        33909424933  PASS — 201/201 + doctor
Phase 2E.4 real semantic E2E     33909625346  PASS — 202/202 + doctor
```

## Artifact chain

```text
analysis.json                         schema v9
promotion_approval.json               schema v1
approved_edit_plan_proposal.json      schema v1
semantic_execution_authorization.json schema v1
semantic_edit_plan.json               schema v1
```

## Safety 2E.4

```text
promotion approval APPROVE != global execution authorization
proposal_ready_for_global_review != render authorization
proposal uses proposed_edits[]
semantic plan uses edits[] only after valid global authorization
generic render rejects proposals
generic render rejects semantic Edit Plans
semantic render revalidates exact full chain + source SHA immediately before FFmpeg
auto_apply = false
```

Global execution APPROVE:

```text
authorized = true
edit_plan_materialization_authorized = true
semantic_render_authorization = true
proposal_render_authorization = false
executable = false
auto_apply = false
```

Materialized Semantic Edit Plan:

```text
globally_authorized = true
requires_semantic_render_gate = true
executable = true
auto_apply = false
```

## Real FFmpeg gate

Final `33909625346`:

```text
202/202 tests PASS en 7.782 s
doctor PASS
real semantic FFmpeg E2E PASS
```

El E2E construye una cadena completa autorizada sobre un MP4 real de 10 s, materializa un único edit de 0.4 s, verifica que el SHA-256 del original queda intacto y que el output conserva audio+vídeo con duración esperada dentro de ±0.15 s.

Esta evidencia no implica todavía calidad perceptual humana general de joins renderizados.

Evidencia: `Validation/phase2e-execution-authorization.md`.

## Pendiente antes de Release

- Fase 2E.5: post-render verification + human/perceptual semantic join close-out;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
