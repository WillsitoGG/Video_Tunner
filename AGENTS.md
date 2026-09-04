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
7. `candidate != scope != assessment != semantic decision != eligibility != promotion assessment != approval != edit`;
8. `PROPOSED_CUT != executable CUT`;
9. `foundation_guards_pass != safe cut`;
10. `future_promotion_candidate != approved edit`;
11. `promotion_review_candidate != approval`;
12. `valid_approved approval != Edit Plan authorization`;
13. una señal posterior favorable nunca rescata una guarda anterior bloqueada;
14. ante duda: `KEEP / REVIEW`;
15. conservador por defecto.

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD → candidates → scopes/fillers → join → acoustic join → semantic → eligibility → promotion → explicit approval artifact → future Edit Plan proposal → future execution → audit
```

## 2. Estado

Versión `0.1.0-dev`.

Completado:

- Fase 2D cerrada como foundation/evidence;
- Fase 2E.1 — Promotion Policy Foundation / analysis schema v9;
- **Fase 2E.2 — Explicit Approval Contract / approval artifact schema v1 — COMPLETADA**.

Siguiente: **Fase 2E.3 — Approved Edit Plan Proposal + Global Limits**.

No existe todavía autorización de Edit Plan ni ejecución automática derivada de approvals.

## 3. Evidencia principal

```text
33600174568  Portable core PASS
33621357438  Portable ML PASS
33639009841  Sync hardening PASS
33656235038  Target Spanish PASS — WER 1.64%, RTF 0.4854
33750836791  Human correction corpus PASS
33755013415  Audio-backed semantic PASS
33758185755  88/88 — correction scope/schema v4
33771792867  101/101 — fillers/schema v5
33773287106  117/117 — join/schema v6
33781903986  131/131 — acoustic/schema v7
33782959293  134/134 — human acoustic PASS
33790792753  138/138 — eligibility/schema v8
33791950505  142/142 — human eligibility PASS
33894995584  human positive close-out — CLOSE_OUT_READY
33899201093  2E.1 schema v9 — 166/166 + doctor PASS
33899857378  2E.2 approval contract — 174/174 + doctor PASS
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

## 5. Analysis schema v9

`analysis.json` **permanece v9 tras 2E.2**:

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

No mutar `analysis.json` para registrar approvals.

## 6. Eligibility / promotion

La única clase actualmente respaldada por evidencia humana positiva para `eligible_for_promotion_review` es:

```text
possible_repetition
```

Conservative y aggressive mantienen la misma whitelist.

Todo blocker upstream sigue siendo veto absoluto.

## 7. Fase 2E.2 — Explicit Approval Contract

Artefacto separado:

```text
promotion_approval.json
schema_version = 1
record_type = promotion_approval
```

Comandos:

```text
video-tunner approval create ANALYSIS --promotion-assessment ID --decision approve|reject --actor ACTOR --reason REASON --output promotion_approval.json
video-tunner approval validate ANALYSIS promotion_approval.json
```

### Requisitos para crear approval

Sólo puede crearse sobre una promotion assessment que siga siendo:

```text
status = eligible_for_promotion_review
promotion_review_candidate = true
requires_explicit_approval = true
approved = false
edit = null
safe_for_cut = false
executable = false
auto_apply = false
```

Además deben seguir siendo coherentes candidate, eligibility, promotion y target.

### Provenance e integridad

Cada approval almacena:

- SHA-256 del `analysis.json` exacto;
- candidate ID/kind;
- eligibility assessment ID/status;
- promotion assessment ID/status;
- mode;
- target exacto;
- fingerprint SHA-256 de snapshot JSON canónico;
- actor;
- reason;
- timestamp.

### Validación

Estados:

```text
valid_approved
valid_rejected
stale_analysis
stale_evidence
stale_or_invalid_reference
invalid_record
```

Un approval `APPROVE` válido **sigue sin ser edit ni autorización de Edit Plan**:

```text
approved = true
edit_plan_authorization = false
edit = null
safe_for_cut = false
executable = false
auto_apply = false
```

Manipular el record para declarar autorización/edición/capacidad ejecutable lo invalida fail-safe.

Run `33899857378`:

```text
174/174 PASS en 7.150 s
doctor PASS
stale analysis/evidence PASS
tampering blocked PASS
upstream blocker veto PASS
```

Detalle: `Validation/phase2e-explicit-approval-contract.md`.

## 8. Siguiente — 2E.3 Approved Edit Plan Proposal + Global Limits

Diseñar un artefacto de **propuesta**, todavía separado de ejecución.

Reglas mínimas:

1. sólo consumir approvals que `approval validate` marque `valid_approved`;
2. revalidar contra analysis SHA + evidence fingerprint;
3. sólo `possible_repetition` inicialmente;
4. target dentro de timeline;
5. rechazar overlaps/conflictos;
6. límites máximos predefinidos de número de edits, segundos retirados y porcentaje de duración;
7. propuesta != autorización de render;
8. stale/rejected/invalid = veto;
9. no ampliar clases sin evidencia humana nueva;
10. ejecución/render en capa posterior.

## 9. Edit Plan / render

El Edit Plan ejecutable no puede aceptar directamente candidates, promotion assessments o approval artifacts. 2E.3 deberá mediar mediante una propuesta validada y con límites globales.

## 10. GitHub / CI / Release

GitHub es source of truth.

- CI deliberada;
- workflows manual-only normalmente;
- no modelos, vídeos, ZIPs o artifacts pesados ordinarios;
- trigger one-shot sólo cuando sea necesario y restaurar inmediatamente;
- no publicar GitHub Release sin autorización expresa de Guille.

## 11. Docs

Mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation ante cambios relevantes.
