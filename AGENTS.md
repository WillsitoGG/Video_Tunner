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
7. `candidate != scope != assessment != semantic decision != eligibility != promotion assessment != approval != proposal != executable edit`;
8. `PROPOSED_CUT != executable CUT`;
9. `foundation_guards_pass != safe cut`;
10. `promotion_review_candidate != approval`;
11. `valid_approved approval != Edit Plan authorization`;
12. `proposal_ready_for_global_review != render authorization`;
13. `proposed_edits[] != edits[]`;
14. una señal posterior favorable nunca rescata una guarda anterior bloqueada;
15. ante duda: `KEEP / REVIEW`;
16. conservador por defecto.

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD → candidates → scopes/fillers → join → acoustic → semantic → eligibility → promotion → approval artifacts → bounded proposal → future global authorization → executable Edit Plan → render → audit
```

## 2. Estado

Versión `0.1.0-dev`.

Completado:

- Fase 2D cerrada como foundation/evidence;
- Fase 2E.1 — Promotion Policy Foundation / analysis schema v9;
- Fase 2E.2 — Explicit Approval Contract / approval schema v1;
- **Fase 2E.3 — Approved Edit Plan Proposal + Global Limits / proposal schema v1 — COMPLETADA**.

Siguiente: **Fase 2E.4 — Execution Authorization / Semantic Render Gate**.

No existe todavía autorización global ni Edit Plan semántico ejecutable derivado de approvals.

## 3. Evidencia principal

```text
33600174568  Portable core PASS
33621357438  Portable ML PASS
33639009841  Sync hardening PASS
33656235038  Target Spanish PASS — WER 1.64%, RTF 0.4854
33790792753  138/138 — eligibility/schema v8
33791950505  142/142 — human eligibility PASS
33894995584  human positive close-out — CLOSE_OUT_READY
33899201093  2E.1 schema v9 — 166/166 + doctor PASS
33899857378  2E.2 approval contract — 174/174 + doctor PASS
33900544072  2E.3 proposal foundation — 185/185 + doctor PASS
33908500929  2E.3 renderer isolation — 186/186 + doctor PASS
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

## 5. Artefactos y schemas

`analysis.json` permanece **schema v9**.

Approval separado:

```text
promotion_approval.json
schema_version = 1
record_type = promotion_approval
```

Proposal separada:

```text
approved_edit_plan_proposal.json
schema_version = 1
record_type = approved_edit_plan_proposal
```

No mutar `analysis.json` para approvals o proposals.

## 6. Eligibility / promotion

La única clase respaldada actualmente por evidencia humana positiva para promotion review y 2E.3 es:

```text
possible_repetition
```

`conservative` y `aggressive` mantienen la misma whitelist.

Todo blocker upstream sigue siendo veto absoluto.

## 7. Fase 2E.2 — Explicit Approval Contract

Comandos:

```text
video-tunner approval create ANALYSIS --promotion-assessment ID --decision approve|reject --actor ACTOR --reason REASON --output promotion_approval.json
video-tunner approval validate ANALYSIS promotion_approval.json
```

Cada approval liga la decisión a analysis SHA-256, candidate, eligibility, promotion assessment, mode, target exacto y evidence fingerprint canónico, además de actor/reason/timestamp.

Estados de validación:

```text
valid_approved
valid_rejected
stale_analysis
stale_evidence
stale_or_invalid_reference
invalid_record
```

Incluso `valid_approved`:

```text
edit_plan_authorization = false
edit = null
safe_for_cut = false
executable = false
auto_apply = false
```

## 8. Fase 2E.3 — Approved Edit Plan Proposal + Global Limits

Comando:

```text
video-tunner proposal build ANALYSIS --approval approval1.json --approval approval2.json --output approved_edit_plan_proposal.json
```

### Límites precomprometidos

Fijados antes de observar resultados y comunes a ambos modos:

```text
max_semantic_edits    = 10
max_removed_seconds   = 30.0
max_removed_fraction  = 0.05
```

### Contrato de entrada

Cada approval suministrada se revalida contra el analysis actual. Todas deben seguir siendo `valid_approved`.

Veto total ante:

```text
no approvals
stale / rejected / invalid approval
duplicate approved target
unsupported candidate kind
missing/invalid target
target outside source timeline
overlapping approved targets
max_semantic_edits exceeded
max_removed_seconds exceeded
max_removed_fraction exceeded
```

No hacer best-effort parcial: cualquiera de esos blockers vacía `proposed_edits[]` y bloquea la proposal completa.

### Proposal positiva

```text
status = proposal_ready_for_global_review
proposed_edits[]
requires_global_review = true
globally_approved = false
render_authorization = false
executable = false
auto_apply = false
```

Cada proposed edit mantiene:

```text
action = remove
globally_approved = false
render_authorized = false
executable = false
auto_apply = false
```

### Renderer boundary

El renderer ejecutable usa `edits[]`. La proposal usa `proposed_edits[]` y, además, `render_from_plan` **rechaza explícitamente** cualquier artefacto que contenga `proposed_edits`.

No quitar esta guarda al implementar 2E.4; la conversión proposal → executable Edit Plan debe ser explícita y validada.

### Validación

```text
33900544072  185/185 PASS en 5.144 s + doctor
33908500929  186/186 PASS en 7.887 s + doctor
```

El run final incluye `test_renderer_rejects_non_executable_plan_proposal` PASS.

Detalle: `Validation/phase2e-approved-plan-proposal.md`.

## 9. Siguiente — 2E.4 Execution Authorization / Semantic Render Gate

Reglas de diseño:

1. autorización global separada de approvals individuales;
2. ligar autorización al analysis exacto y a la proposal exacta con SHA/fingerprint;
3. actor + reason + timestamp obligatorios;
4. stale/tampered proposal o analysis = veto;
5. sólo autorización global válida puede materializar `edits[]` ejecutables;
6. el Edit Plan materializado debe conservar provenance a approvals/proposal;
7. renderer continúa rechazando proposals;
8. antes de auto-apply general, definir semantic render gate y post-render verification;
9. no ampliar candidate kinds ni límites sin evidencia nueva suficiente.

## 10. GitHub / CI / Release

GitHub es source of truth.

- CI deliberada;
- workflows manual-only normalmente;
- no modelos, vídeos, ZIPs o artifacts pesados ordinarios;
- trigger one-shot sólo cuando sea necesario y restaurar inmediatamente;
- no publicar GitHub Release sin autorización expresa de Guille.

## 11. Docs

Mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation ante cambios relevantes.
