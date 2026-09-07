# AGENTS.md — Video_Tunner

Contexto técnico permanente para agentes. Referencia maestra externa vigente: `00.Contexto y Reglas de Trabajo_GitHub_Video_Tunner_v3`.

## 1. Invariantes

Video_Tunner debe producir vídeo hablado limpio, natural, fiel, sincronizado, auditable y reversible en Windows 10/11 x64.

Obligatorio:

1. portable real: ZIP → descomprimir → ejecutar;
2. vídeo con audio embebido o vídeo + audio externo;
3. resolver master audio antes de análisis temporal;
4. Whisper, VAD y acoustic join usan exactamente el mismo master acreditado;
5. auto-sync sólo con evidencia suficiente; override/manual fallback;
6. original siempre intacto;
7. `candidate != scope != assessment != semantic decision != eligibility != promotion != approval != proposal != execution authorization != semantic edit plan != rendered output != post-render verification != human review`;
8. `PROPOSED_CUT != executable CUT`;
9. `foundation_guards_pass != safe cut`;
10. `promotion_review_candidate != approval`;
11. `valid_approved promotion approval != global execution authorization`;
12. `proposal_ready_for_global_review != render authorization`;
13. `proposed_edits[] != edits[]`;
14. global APPROVE nunca implica `auto_apply`;
15. `semantic_edit_plan` sólo puede renderizarse por semantic render gate;
16. cualquier cambio de analysis/proposal/authorization/plan/source invalida la cadena correspondiente;
17. technical post-render PASS nunca sustituye human perceptual PASS;
18. evidencia humana stale/alterada = `INVALID_EVIDENCE`;
19. una señal posterior favorable nunca rescata una guarda anterior bloqueada;
20. ante duda: `KEEP / REVIEW`;
21. conservador por defecto.

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD → candidates → scopes/fillers → join → acoustic → semantic → eligibility → promotion → individual approval → bounded proposal → global execution authorization → semantic Edit Plan → semantic render gate → FFmpeg → post-render verification → human review → corpus closeout
```

## 2. Estado

Versión `0.1.0-dev`.

Completado:

- Fase 2D cerrada como foundation/evidence;
- Fase 2E.1 — Promotion Policy Foundation / analysis schema v9;
- Fase 2E.2 — Explicit Approval Contract / approval schema v1;
- Fase 2E.3 — Approved Edit Plan Proposal + Global Limits / proposal schema v1;
- Fase 2E.4 — Execution Authorization / Semantic Render Gate;
- **Fase 2E.5 — Post-render Verification / Human Close-out — COMPLETADA**;
- **Fase 2E — `CLOSE_OUT_READY`**.

Auto-apply semántico sigue deshabilitado. El cierre 2E no autoriza release.

Siguiente bloque: **Fase 3 — calidad audiovisual / auditoría**.

## 3. Evidencia principal

```text
33600174568  Portable core PASS
33621357438  Portable ML PASS
33639009841  Sync hardening PASS
33656235038  Target Spanish PASS — WER 1.64%, RTF 0.4854
33894995584  2D.6 Human positive close-out — CLOSE_OUT_READY
33899201093  2E.1 — 166/166 + doctor PASS
33899857378  2E.2 — 174/174 + doctor PASS
33900544072  2E.3 proposal — 185/185 + doctor PASS
33908500929  2E.3 renderer isolation — 186/186 + doctor PASS
33909424933  2E.4 core — 201/201 + doctor PASS
33909625346  2E.4 real FFmpeg E2E — 202/202 + doctor PASS
34119952855  2E.5 technical close-out — 278 tests + portable/provenance + 3/3 technical renders PASS
34121684853  2E.5 offline human-finalizer contract PASS
```

Final human close-out:

```text
cases = 3
sources = 2
valid human reviews = 3
human perceptual PASS = 3
human FAIL = 0
invalid/stale reviews = 0
status = CLOSE_OUT_READY
auto_apply = false
```

Evidencia permanente: `Validation/phase2e-post-render-closeout.md` y `Validation/phase2e-human-closeout/`.

No generalizar métricas fuera del corpus evaluado.

## 4. Stack fijado

```text
faster-whisper 1.2.1
CTranslate2 4.8.1
ONNX Runtime 1.29.0
tokenizers 0.23.1
NumPy 2.5.2
PyInstaller 6.22.2
```

VAD: faster-whisper + `silero_vad_v6.onnx`. Modelo objetivo: `large-v3-turbo`.

`single_pass` sigue siendo default del producto. `deterministic_overlap_12s_3s_repeat_consensus_v1` está expuesta como opt-in explícito y fue la estrategia validada en 2E.5. No exponer estrategias no validadas por CLI.

## 5. Schemas / artifacts

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

No mutar `analysis.json` para approvals, proposal, authorization, plan, verification o human review.

## 6. Promotion + approvals

Sólo `possible_repetition` está respaldada actualmente por evidencia humana positiva para promotion/semantic execution.

Un approval individual `valid_approved` sigue sin ser autorización global.

## 7. Proposal 2E.3

Límites precomprometidos e iguales para `conservative/aggressive`:

```text
max_semantic_edits    = 10
max_removed_seconds   = 30.0
max_removed_fraction  = 0.05
```

Una proposal válida sigue:

```text
status = proposal_ready_for_global_review
proposed_edits[]
requires_global_review = true
globally_approved = false
render_authorization = false
executable = false
auto_apply = false
```

Cualquier approval stale/rejected/invalid, duplicado, overlap, target inválido/out-of-timeline o límite global excedido bloquea la proposal completa.

## 8. Fase 2E.4 — Global execution authorization

Artefacto `semantic_execution_authorization.json` schema v1.

APPROVE válido:

```text
authorized = true
edit_plan_materialization_authorized = true
semantic_render_authorization = true
proposal_render_authorization = false
executable = false
auto_apply = false
```

La proposal nunca se vuelve renderizable.

## 9. Semantic Edit Plan

Artefacto `semantic_edit_plan.json` schema v1. Sólo se materializa desde `valid_authorized` y conserva source SHA, analysis/proposal/authorization SHA, evidence fingerprint, edits exactos y plan fingerprint.

```text
globally_authorized = true
requires_semantic_render_gate = true
executable = true
auto_apply = false
```

Cualquier cambio invalida la cadena.

## 10. Semantic render gate

El renderer genérico rechaza proposals y `semantic_edit_plan`. La vía pública correcta es:

```text
video-tunner execution render INPUT ANALYSIS PROPOSAL AUTHORIZATION PLAN OUTPUT
```

Antes de FFmpeg debe revalidar plan, authorization, hashes/fingerprints y source SHA real. No eliminar ni puentear esta revalidación.

## 11. CLI / transcription strategy

Execution:

```text
execution authorize
execution validate
execution materialize
execution plan-validate
execution render-check
execution render
```

El `render` legacy no acepta Semantic Edit Plans.

`analyze` mantiene `single_pass` como default; 12s/3s sólo se activa mediante `--transcription-strategy` explícito.

## 12. E2E real 2E.4

Run `33909625346`: MP4 real 10 s A/V, cadena completa autorizada, un edit de 0.4 s, original SHA preservado, duración esperada ±0.15 s, 1 stream vídeo + 1 audio, 202/202 PASS + doctor.

Detalle: `Validation/phase2e-execution-authorization.md`.

## 13. Fase 2E.5 — cierre final

Technical gate `34119952855`:

```text
3 cases / 2 sources
3/3 technical PASS
157 -> acoustic_context_only
298 -> acoustic_context_only
13  -> low_energy_boundary_context
```

Human gate final:

```text
3/3 valid human PASS
0 FAIL
0 invalid/stale reviews
CLOSE_OUT_READY
```

El finalizador offline liga cada review al SHA del technical report, SHA del output, plan fingerprint y `join_id`; no vuelve a ejecutar Whisper ni FFmpeg y no sustituye el juicio humano.

Final hashes:

```text
source bundle manifest SHA256  d0b12929ede07c1c5a56b074008d0903a868a7cf61e5ce10801c2b682f164ed0
human decisions SHA256         867a33c87ec2154d08558a67d503535d4527cb99af07ac65458507fe73288e04
closeout decision SHA256       2cc5ae013cdcbfc53efc376d5db4f2f2f53d5a8848c019820dee6899b88c188a
```

Detalle: `Validation/phase2e-post-render-closeout.md` y `Validation/phase2e-human-closeout/`.

## 14. GitHub / CI / Release

- GitHub source of truth;
- CI deliberada;
- workflows pesados manual-only normalmente;
- triggers one-shot se eliminan tras uso;
- no modelos/vídeos/ZIPs artifacts ordinarios;
- no Release sin autorización expresa de Guille.

## 15. Docs / siguiente trabajo

Mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation ante cambios relevantes.

Trabajo inmediato tras integrar 2E: iniciar **Fase 3 — calidad audiovisual / auditoría**, sin habilitar `auto_apply` y sin anticipar UX/release hardening.
