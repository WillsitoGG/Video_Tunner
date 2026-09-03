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
- Fase 2D.1: COMPLETADA — correction scope/schema v4
- Fase 2D.2: COMPLETADA — contextual filler/schema v5
- Fase 2D.3.1: COMPLETADA — join context/schema v6
- Fase 2D.3.2: COMPLETADA — acoustic join/schema v7
- Fase 2D.3.3: COMPLETADA — human-audio acoustic evidence
- Fase 2D.4: COMPLETADA — combined eligibility/schema v8
- Fase 2D.5: **SIGUIENTE — Human Combined Eligibility Evidence**

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
```

Todas mantienen `automatic_edits = 0` donde aplica y artifacts = 0.

## Schema v8

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
acoustic_join_assessments[]
semantic_decisions[]
eligibility_assessments[]
```

## Fase 2D.4 — Combined Eligibility Foundation v1

La policy v1 combina guardas acumulativas. Una capa favorable posterior nunca anula una anterior bloqueada.

Estados:

```text
foundation_guards_pass
blocked_acoustic_context
blocked_filler_context
blocked_semantic_decision
blocked_join_context
blocked_correction_scope
invalid_removed_text
missing_required_evidence
```

Benchmark: 12 casos; 4 rutas `foundation_guards_pass` y 8 bloqueos deliberados.

La capa vuelve a validar target/`removedText` contra transcript, índices y timestamps antes de declarar una ruta candidata a futura promoción.

Final `33790792753`:

```text
138/138 tests PASS en 7.035 s
combined eligibility gate PASS
schema v8 integration PASS
removedText contract PASS
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

Incluso `foundation_guards_pass` conserva:

```text
future_promotion_candidate = true
safe_for_cut = false
executable = false
auto_apply = false
```

Evidencia: `Validation/phase2d-combined-eligibility.md`.

## Safety actual

```text
candidate != scope != assessment != semantic decision != edit
PROPOSED_CUT != executable CUT
foundation_guards_pass != safe cut
future_promotion_candidate != approved edit
eligibility_assessments_are_not_edits = true
eligibility_assessments_executable = false
eligibility_assessments_safe_for_cut = false
future_promotion_candidates_are_not_approved_edits = true
combined_eligibility_enabled = true
combined_eligibility_is_not_edit_plan_promotion = true
safe_for_cut = false
executable = false
auto_apply = false
automatic_edits = 0
```

## Pendiente antes de Release

- Fase 2D.5: validar combined eligibility sobre evidencia humana real;
- cerrar 2D antes de cualquier promoción al Edit Plan;
- Fase 2E: promoción explícita sólo si la evidencia lo permite;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
