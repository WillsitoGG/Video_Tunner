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
- Fase 2D.5: COMPLETADA — Human Combined Eligibility Evidence v1
- Fase 2D.6: **SIGUIENTE — Human Positive Eligibility Expansion / Close-out Gate**

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
Phase 2D.5 human eligibility     33791950505  PASS — 142/142, human gate
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

## Fase 2D.5 — Human Combined Eligibility Evidence v1

Se aplicó la policy combinada a tres casos humanos AMI trazables, usando word timings/endpoints congelados de `large-v3-turbo` del run `33755013415` y el WAV AMI original CC BY 4.0.

Baseline `33791636767`:

```text
141/141 regression tests PASS
human gate FAIL por 1 mismatch diagnóstico
safe_for_cut 0
executable 0
auto_apply 0
```

La correction humana ambigua estaba bloqueada de todos modos, pero el estado principal era `invalid_removed_text`. Se ajustó la precedencia para conservar el blocker más informativo `blocked_correction_scope` cuando el scope ya acredita ambigüedad. La ausencia de target sigue registrada en `removed_text_reason`.

Final `33791950505`:

```text
142/142 tests PASS en 7.087 s
HUMAN_ELIGIBILITY_GATE=PASS
cases                    3
foundation_guards_pass   1
blocked                  2
safe_for_cut             0
executable               0
auto_apply               0
automatic_edits          0
artifacts                 0
```

Interpretación:

- el control humano de pausa atraviesa las guardas foundation, pero no está etiquetado como ejemplo humano de removibilidad;
- el retake humano permanece `blocked_semantic_decision`;
- la correction humana ambigua permanece `blocked_correction_scope`;
- ninguna evidencia humana autoriza cortes.

Evidencia: `Validation/phase2d-human-combined-eligibility.md`.

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

- Fase 2D.6: ampliar positivos humanos de removibilidad y cerrar el close-out gate de 2D;
- no iniciar promoción al Edit Plan sin ese cierre;
- Fase 2E: promoción explícita sólo si la evidencia lo permite;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
