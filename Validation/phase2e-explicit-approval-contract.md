# Phase 2E.2 — Explicit Approval Contract

## Objetivo

Añadir una decisión humana explícita, auditable y verificable entre `promotion_assessments[]` y cualquier futura propuesta de Edit Plan, sin mutar `analysis.json` ni habilitar ejecución.

## Arquitectura

`analysis.json` permanece **schema v9**.

Nuevo artefacto separado:

```text
promotion_approval.json
schema_version = 1
record_type = promotion_approval
```

Flujo:

```text
analysis schema v9
→ eligible_for_promotion_review
→ explicit APPROVE / REJECT
→ promotion_approval.json
→ validate against current analysis
→ valid_approved | valid_rejected | stale/invalid
→ future Phase 2E.3 proposal
```

## Motivo del artefacto separado

No mutar el análisis permite:

- conservar la evidencia original intacta;
- ligar la decisión al fichero exacto mediante SHA-256;
- detectar cambios upstream posteriores;
- auditar quién decidió, qué decidió y por qué;
- separar approval individual de autorización global de plan y ejecución.

## Contrato de creación

Sólo una `promotion assessment` que siga siendo `eligible_for_promotion_review` puede recibir approval.

Se revalida:

- analysis schema >=9;
- promotion assessment existente y única;
- `promotion_review_candidate=true`;
- `requires_explicit_approval=true`;
- promotion record sin capacidad ejecutable;
- candidate ID/kind consistente;
- eligibility ID/candidate consistente;
- eligibility `foundation_guards_pass`;
- `future_promotion_candidate=true`;
- `removed_text_validation.valid=true`;
- `target_preview` idéntico al target validado upstream.

## Provenance

Cada record guarda:

```text
analysis.sha256
analysis.schema_version
promotion_assessment_id
candidate_id
candidate_kind
decision
actor
reason
created_utc
evidence_fingerprint
evidence_snapshot
```

El `evidence_fingerprint` es SHA-256 sobre JSON canónico de:

```text
analysis_schema_version
candidate_id
candidate_kind
eligibility_assessment_id
eligibility_status
promotion_assessment_id
promotion_status
mode
target
```

## Estados de validación

```text
valid_approved
valid_rejected
stale_analysis
stale_evidence
stale_or_invalid_reference
invalid_record
```

### Stale

- SHA del `analysis.json` distinto → `stale_analysis`.
- snapshot/fingerprint distinto → `stale_evidence`.
- promotion/candidate/eligibility ya no válidos → `stale_or_invalid_reference`.

### Tampering

Se invalida cualquier record que intente declarar:

```text
edit_plan_authorization = true
edit != null
safe_for_cut = true
executable = true
auto_apply = true
```

## Safety

Incluso `valid_approved` conserva:

```text
approved = true
edit_plan_authorization = false
edit = null
safe_for_cut = false
executable = false
auto_apply = false
```

Por tanto:

```text
promotion_review_candidate != approval
valid_approved approval != Edit Plan authorization
individual approval != global execution authorization
```

## CLI

```text
video-tunner approval create ANALYSIS \
  --promotion-assessment ID \
  --decision approve|reject \
  --actor ACTOR \
  --reason REASON \
  --output promotion_approval.json

video-tunner approval validate ANALYSIS promotion_approval.json
```

`approval validate` devuelve exit code 0 sólo para un record vigente y válido; stale/invalid devuelve código no-cero.

## Validación

Run `33899857378`, commit evaluado `2e973d45b6c6d8462270f9521cea7a14f576baaa`:

```text
174/174 tests PASS en 7.150 s
FFmpeg 9.0.1 PASS
ffprobe 9.0.1 PASS
doctor PASS
```

Cobertura nueva:

```text
APPROVE válido pero no Edit Plan authorization     PASS
REJECT válido y auditable                          PASS
analysis SHA cambiado → stale_analysis             PASS
evidencia upstream cambiada → stale_evidence       PASS
upstream blocked promotion → no approval            PASS
tampered edit authorization → invalid_record        PASS
decision/actor/reason obligatorios                 PASS
save/load conserva fingerprint                      PASS
```

## CI hygiene

- trigger de push sólo one-shot;
- workflow restaurado inmediatamente a `workflow_dispatch`;
- commit de restauración `a35c71efc4675093056cf2902d3257be9cd1292f`;
- artifacts pesados: 0.

## Conclusión

**Phase 2E.2 Explicit Approval Contract: PASS.**

La aplicación ya puede registrar y revalidar de forma auditable una decisión humana explícita sin convertirla en edit ni autorización de render.

## Siguiente

Phase 2E.3 — Approved Edit Plan Proposal + Global Limits:

- consumir sólo approvals `valid_approved`;
- revalidar SHA/fingerprint;
- materializar targets como propuestas de edición;
- rechazar overlaps/conflictos;
- imponer límites globales predefinidos;
- mantener proposal != execution authorization.
