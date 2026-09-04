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
7. `candidate != scope != assessment != semantic decision != eligibility != promotion != approval != proposal != execution authorization != semantic edit plan != rendered output`;
8. `PROPOSED_CUT != executable CUT`;
9. `foundation_guards_pass != safe cut`;
10. `promotion_review_candidate != approval`;
11. `valid_approved promotion approval != global execution authorization`;
12. `proposal_ready_for_global_review != render authorization`;
13. `proposed_edits[] != edits[]`;
14. global APPROVE nunca implica `auto_apply`;
15. `semantic_edit_plan` sólo puede renderizarse por semantic render gate;
16. cualquier cambio de analysis/proposal/authorization/plan/source invalida la cadena correspondiente;
17. una señal posterior favorable nunca rescata una guarda anterior bloqueada;
18. ante duda: `KEEP / REVIEW`;
19. conservador por defecto.

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD → candidates → scopes/fillers → join → acoustic → semantic → eligibility → promotion → individual approval → bounded proposal → global execution authorization → semantic Edit Plan → semantic render gate → FFmpeg → verification/audit
```

## 2. Estado

Versión `0.1.0-dev`.

Completado:

- Fase 2D cerrada como foundation/evidence;
- Fase 2E.1 — Promotion Policy Foundation / analysis schema v9;
- Fase 2E.2 — Explicit Approval Contract / approval schema v1;
- Fase 2E.3 — Approved Edit Plan Proposal + Global Limits / proposal schema v1;
- **Fase 2E.4 — Execution Authorization / Semantic Render Gate — COMPLETADA**.

Siguiente: **Fase 2E.5 — Semantic Render Verification / Close-out**.

Auto-apply semántico sigue deshabilitado.

## 3. Evidencia principal

```text
33600174568  Portable core PASS
33621357438  Portable ML PASS
33639009841  Sync hardening PASS
33656235038  Target Spanish PASS — WER 1.64%, RTF 0.4854
33894995584  Human positive close-out — CLOSE_OUT_READY
33899201093  2E.1 — 166/166 + doctor PASS
33899857378  2E.2 — 174/174 + doctor PASS
33900544072  2E.3 proposal — 185/185 + doctor PASS
33908500929  2E.3 renderer isolation — 186/186 + doctor PASS
33909424933  2E.4 core — 201/201 in 7.310 s + doctor PASS
33909625346  2E.4 real FFmpeg E2E — 202/202 in 7.782 s + doctor PASS
```

No generalizar métricas de corpus fuera de su muestra.

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

## 5. Schemas / artifacts

```text
analysis.json                         schema v9
promotion_approval.json               schema v1
approved_edit_plan_proposal.json      schema v1
semantic_execution_authorization.json schema v1
semantic_edit_plan.json               schema v1
```

No mutar `analysis.json` para approvals, proposal, authorization o plan.

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

Artefacto:

```text
semantic_execution_authorization.json
schema_version = 1
record_type = semantic_execution_authorization
```

Requisitos:

1. proposal vigente y `proposal_ready_for_global_review`;
2. analysis SHA-256 exacto;
3. proposal SHA-256 exacto;
4. proposal execution snapshot/fingerprint exactos;
5. actor + reason + timestamp;
6. decisión global explícita APPROVE/REJECT.

Estados principales:

```text
valid_authorized
valid_rejected
stale_analysis
stale_proposal
stale_evidence
stale_or_invalid_proposal
invalid_record
```

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

Artefacto:

```text
semantic_edit_plan.json
schema_version = 1
record_type = semantic_edit_plan
```

Sólo se materializa desde `valid_authorized`.

Debe conservar:

- source file/duration/SHA-256;
- mode;
- límites 2E.3;
- analysis SHA-256;
- proposal SHA-256;
- authorization SHA-256;
- proposal evidence fingerprint;
- edits derivados exactamente de `proposed_edits[]`;
- plan fingerprint;
- summary.

Contrato:

```text
globally_authorized = true
requires_semantic_render_gate = true
executable = true
auto_apply = false
```

Cualquier cambio del plan invalida el fingerprint.

## 10. Semantic render gate

El renderer genérico:

- rechaza cualquier artifact con `proposed_edits`;
- rechaza `record_type=semantic_edit_plan` salvo llamada interna con semantic gate autorizado.

La vía pública correcta es:

```text
video-tunner execution render INPUT ANALYSIS PROPOSAL AUTHORIZATION PLAN OUTPUT
```

Antes de FFmpeg debe revalidar:

1. plan contra analysis/proposal/authorization actuales;
2. authorization global;
3. hashes de analysis/proposal/authorization;
4. plan fingerprint;
5. source SHA-256 real contra analysis/proposal/plan.

No eliminar ni puentear esta revalidación.

## 11. CLI 2E.4

```text
execution authorize
execution validate
execution materialize
execution plan-validate
execution render-check
execution render
```

El `render` legacy no acepta Semantic Edit Plans.

## 12. E2E real 2E.4

Run `33909625346`:

- crea MP4 real 10 s A/V;
- cadena completa analysis → individual approval → proposal → global authorization → semantic plan → render gate → FFmpeg;
- un único semantic edit de 0.4 s;
- original SHA-256 preservado;
- output duration esperada dentro de ±0.15 s;
- 1 stream vídeo + 1 audio;
- 202/202 PASS + doctor.

Esto valida ruta técnica, no calidad perceptual general de joins.

Detalle: `Validation/phase2e-execution-authorization.md`.

## 13. Siguiente — 2E.5 Semantic Render Verification / Close-out

1. post-render structural verification;
2. duración esperada vs real;
3. streams/output provenance;
4. audit local de cada join renderizado;
5. evidencia perceptual humana de joins semánticos;
6. audit report end-to-end;
7. decidir cierre de 2E.

## 14. GitHub / CI / Release

- GitHub source of truth;
- CI deliberada;
- workflows manual-only normalmente;
- no modelos/vídeos/ZIPs artifacts ordinarios;
- no Release sin autorización expresa de Guille.

## 15. Docs

Mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation ante cambios relevantes.
