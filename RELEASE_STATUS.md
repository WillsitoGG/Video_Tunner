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
- Fase 2E.5: **COMPLETADA — technical 3/3 + human perceptual 3/3**
- Fase 2E: **CERRADA — CLOSE_OUT_READY**

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
Phase 2E.5 technical close-out   34119952855  PASS — 278 tests + portable/provenance + 3/3 technical renders
Phase 2E.5 human close-out       offline       PASS — 3/3 valid human reviews; CLOSE_OUT_READY
```

Phase 2E.5 aggregate final:

```text
required cases                  3
valid human reviews             3
human perceptual PASS           3
human perceptual FAIL           0
invalid/stale reviews           0
distinct sources                2
status                          CLOSE_OUT_READY
phase2e_closeout_ready          true
auto_apply                      false
```

La escucha humana final fue realizada sobre las comparaciones ORIGINAL/RENDERED focalizadas de los tres casos precomprometidos. La evidencia persistente está en `Validation/phase2e-human-closeout/`.

## Artifact chain

```text
analysis.json                         schema v9
promotion_approval.json               schema v1
approved_edit_plan_proposal.json      schema v1
semantic_execution_authorization.json schema v1
semantic_edit_plan.json               schema v1
semantic_render_verification          schema v1
semantic_render_human_review          schema v1
phase2e_closeout_decision              schema v1
```

## Safety 2E.4–2E.5

```text
promotion approval APPROVE != global execution authorization
proposal_ready_for_global_review != render authorization
proposal uses proposed_edits[]
semantic plan uses edits[] only after valid global authorization
generic render rejects proposals
generic render rejects semantic Edit Plans
semantic render revalidates exact full chain + source SHA immediately before FFmpeg
post-render technical PASS != human perceptual PASS
stale/altered human evidence = INVALID_EVIDENCE, not quality PASS/FAIL
auto_apply = false
```

El cierre de Fase 2E no habilita `auto_apply` ni constituye autorización de release.

## Real FFmpeg gates

Final 2E.4 `33909625346`:

```text
202/202 tests PASS en 7.782 s
doctor PASS
real semantic FFmpeg E2E PASS
```

El E2E construye una cadena completa autorizada sobre un MP4 real de 10 s, materializa un único edit de 0.4 s, verifica que el SHA-256 del original queda intacto y que el output conserva audio+vídeo con duración esperada dentro de ±0.15 s.

Phase 2E.5 `34119952855`:

```text
278 tests PASS (13 host-only skips)
portable analysis build PASS
immutable FFmpeg provenance PASS
3/3 precommitted AMI cases render PASS
3/3 post-render technical verification PASS
2 distinct speaker-specific AMI sources
```

Per-case final status:

```text
157  technical PASS  human PASS  acoustic_context_only
298  technical PASS  human PASS  acoustic_context_only
13   technical PASS  human PASS  low_energy_boundary_context
```

Finalization hashes:

```text
source bundle manifest SHA256  d0b12929ede07c1c5a56b074008d0903a868a7cf61e5ce10801c2b682f164ed0
human decisions SHA256         867a33c87ec2154d08558a67d503535d4527cb99af07ac65458507fe73288e04
closeout decision SHA256       2cc5ae013cdcbfc53efc376d5db4f2f2f53d5a8848c019820dee6899b88c188a
```

Evidencia: `Validation/phase2e-execution-authorization.md`, `Validation/phase2e-post-render-closeout.md` y `Validation/phase2e-human-closeout/`.

## Pendiente antes de Release

- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
