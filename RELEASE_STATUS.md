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
- Fase 2D.6: **COMPLETADA — Human Positive Eligibility Expansion / Close-out Gate**
- Fase 2D: **CERRADA COMO FOUNDATION/EVIDENCE**
- Fase 2E: **SIGUIENTE — Promotion to Edit Plan**

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
Phase 2D.6 repeat discovery      33892213960  PASS — 80 exact repeats, 8/4 selection
Phase 2D.6 human close-out       33894995584  PASS — CLOSE_OUT_READY
```

Todas las validaciones de 2D mantienen `automatic_edits = 0` y no suben artifacts pesados.

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

## Fase 2D.6 — Human Positive Close-out

Se seleccionaron de forma reproducible 8 repeticiones humanas AMI etiquetadas como reparandum removible, procedentes de 4 headsets individuales. La selección se realizó antes de ejecutar `large-v3-turbo`, sobre 80 exact repeats compatibles con la tokenización de producción.

Criterio fijado antes de observar el resultado:

```text
casos long evaluados                 >= 8
positivos humanos alineados          >= 3
foundation_guards_pass humanos       >= 2
fuentes/headsets con foundation pass >= 2
```

Run final `33894995584`:

```text
155 tests OK; 11 host-PATH skips
HUMAN_POSITIVE_EVIDENCE_GATE      PASS
HUMAN_POSITIVE_CLOSE_OUT_DECISION CLOSE_OUT_READY
casos evaluados                    8
positivos humanos alineados        6
foundation_guards_pass             3
fuentes con foundation pass        2
hard failures                      0
safe_for_cut                       0
executable                         0
auto_apply                         0
automatic_edits                    0
artifacts                           0
```

Diagnóstico por etapa:

```text
asr_repeat_not_preserved                 2
foundation_guards_pass                   3
downstream_blocked:blocked_join_context  3
```

En los 6 casos donde ASR conserva la repetición completa, el detector la identifica y alinea en esta muestra. Tres atraviesan las guardas foundation y tres quedan bloqueados deliberadamente por join context. No generalizar la tasa de esta muestra al producto completo.

No se relajó ningún threshold ni guarda para cerrar 2D.

Evidencia: `Validation/phase2d-human-positive-closeout.md`.

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

Cerrar 2D **no** activa promoción ni cortes. Sólo habilita el diseño de la policy de 2E.

## Pendiente antes de Release

- Fase 2E: Promotion to Edit Plan explícita y auditable;
- definir clases promocionables, approvals, thresholds por modo y límites globales;
- mantener blockers 2D como vetos acumulativos y el resto en REVIEW/KEEP;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
