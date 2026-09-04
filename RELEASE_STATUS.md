# Release Status

## Estado actual

- Proyecto: Video_Tunner
- Versión de desarrollo: `0.1.0-dev`
- Release publicada: **no**
- ZIP portable final validado: **no**
- Windows 10/11 x64 validado manualmente por Guille: **no**
- Fase 0: COMPLETADA
- Fase 0.5: COMPLETADA
- Fase 1A: COMPLETADA — Portable Foundation core + ML PASS
- Fase 1B: COMPLETADA — dual ingest + sync/drift PASS
- Fase 1C: COMPLETADA — master → Whisper/VAD + target Spanish PASS
- Fase 2A: COMPLETADA — Semantic Candidates v1
- Fase 2B: COMPLETADA — Semantic Decisions + Protection v1
- Fase 2C: COMPLETADA COMO BLOQUE DE EVIDENCIA v1
- Fase 2D: **CERRADA COMO FOUNDATION/EVIDENCE**
- Fase 2E.1: **COMPLETADA — Promotion Policy Foundation / schema v9**
- Fase 2E: **EN CURSO**
- Fase 2E.2: **SIGUIENTE — Explicit Approval Contract**

## Evidencia principal

```text
Portable core                    33600174568  PASS
Portable ML                      33621357438  PASS
Sync hardening                   33639009841  PASS
Target Spanish                   33656235038  PASS — WER 1.64%, RTF 0.4854
Human correction final           33750836791  PASS
Phase 2C.3 audio-backed final    33755013415  PASS
Phase 2D.1 final                 33758185755  PASS — 88/88, schema v4
Phase 2D.2 final                 33771792867  PASS — 101/101, schema v5
Phase 2D.3.1 final               33773287106  PASS — 117/117, schema v6
Phase 2D.3.2 final               33781903986  PASS — 131/131, schema v7
Phase 2D.3.3 human acoustic      33782959293  PASS — 134/134
Phase 2D.4 combined eligibility  33790792753  PASS — 138/138, schema v8
Phase 2D.5 human eligibility     33791950505  PASS — 142/142
Phase 2D.6 human close-out       33894995584  PASS — CLOSE_OUT_READY
Phase 2E.1 isolated policy       33896244733  PASS — 165/165
Phase 2E.1 integrated schema v9  33899201093  PASS — 166/166 + doctor
```

## Schema v9

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

## Fase 2E.1 — Promotion Policy Foundation

Primera policy explícita entre eligibility y un futuro Edit Plan aprobado.

Clase promocionable **sólo a revisión** en esta fase:

```text
possible_repetition
```

Motivo: es la única clase que cuenta con evidencia humana positiva suficiente en el close-out 2D.6. No se amplía la whitelist en aggressive.

Contrato de entrada positivo:

```text
candidate válido y kind consistente
+ eligibility = foundation_guards_pass
+ future_promotion_candidate = true
+ removed_text_validation.valid = true
+ candidate kind respaldado por evidencia humana
→ eligible_for_promotion_review
```

Contrato de seguridad:

```text
promotion_review_candidate != approved edit
requires_explicit_approval = true
approval_state = required
approved = false
edit = null
safe_for_cut = false
executable = false
auto_apply = false
automatic_edits = 0
```

El mecanismo de aprobación explícita todavía no está implementado.

### Validación

`33896244733` validó policy/report aislados con 165/165 PASS.

Dos primeros intentos de integración fallaron únicamente en el nuevo fixture positivo:

- `33898758391`: `hoy` activaba correctamente la guarda temporal del join;
- `33898967491`: `vamos` activaba correctamente la guarda verbal/temporal del join.

Se corrigió únicamente el fixture a una repetición y contexto léxicamente neutros. No se tocaron detector, semantic, join, acoustic, eligibility ni promotion thresholds.

Final `33899201093`:

```text
166/166 tests PASS en 7.079 s
doctor PASS
schema v9 integrado
promotion positive review path PASS
upstream blocker propagation PASS
approved                           0
edits                              0
safe_for_cut                       0
executable                         0
auto_apply                         0
automatic_edits                    0
```

Evidencia: `Validation/phase2e-promotion-foundation.md`.

## Safety actual

```text
candidate != assessment != promotion assessment != edit
PROPOSED_CUT != executable CUT
foundation_guards_pass != safe cut
future_promotion_candidate != approved edit
promotion_review_candidate != approved edit
promotion_assessments_are_not_edits = true
promotion_review_requires_explicit_approval = true
promotion_assessments_approved = false
edit_plan_promotion_enabled = false
promotion_assessments_executable = false
promotion_assessments_safe_for_cut = false
safe_for_cut = false
executable = false
auto_apply = false
automatic_edits = 0
```

## Pendiente antes de Release

- Fase 2E.2: Explicit Approval Contract;
- después: approved Edit Plan proposals + límites globales/fail-safe;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
