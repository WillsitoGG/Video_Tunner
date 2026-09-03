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
- Fase 2C.1: COMPLETADA — benchmark semántico
- Fase 2C.2: COMPLETADA — evidencia humana bilingüe
- Fase 2C.3: COMPLETADA — audio humano real → `large-v3-turbo` → semantic gate PASS
- Fase 2D.1: COMPLETADA — correction scope foundation v1 + schema v4
- Fase 2D.2: COMPLETADA — contextual filler foundation v1 + schema v5
- Fase 2D.3.1: COMPLETADA — join boundary/timeline/lexical foundation + schema v6
- Fase 2D.3.2: **SIGUIENTE — acoustic join validation**

## Evidencia principal

```text
Portable core                    33600174568  PASS
Portable ML                      33621357438  PASS
Sync hardening                   33639009841  PASS
Master analysis                  33640872486  PASS
Target Spanish                   33656235038  PASS — WER 1.64%, RTF 0.4854
Semantic Candidates              33659725847  PASS — 48 tests
Semantic Decisions/Protection    33741195594  PASS — 55 tests
Human correction final           33750836791  PASS — 74 tests, corpus gate PASS
Phase 2C.3 audio-backed final    33755013415  PASS — 3/3 cases, semantic gate PASS
Phase 2D.1 final                 33758185755  PASS — 88/88, schema v4
Phase 2D.2 final                 33771792867  PASS — 101/101, schema v5
Phase 2D.3.1 foundation          33772715214  PASS — 112/112
Phase 2D.3.1 final               33773287106  PASS — 117/117, schema v6
```

Todas mantienen `automatic_edits = 0` donde aplica y artifacts = 0.

## Fase 2D.3.1 — Join boundary/timeline/lexical foundation

`analysis.json` usa schema v6:

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
semantic_decisions[]
```

Estados:

```text
join_context_only
sentence_boundary_risk
segment_boundary_risk
critical_lexical_context_risk
repair_or_protected_context_risk
transcript_edge
invalid_or_unbounded_target
```

El target del join se valida contra índices, `removed_text` y timestamps. Corrections `ambiguous` y spans inconsistentes fallan seguro sin target. Los joins próximos a repairs, cifras/unidades, negaciones, persona/tiempo/causalidad o boundaries quedan marcados como riesgo.

Benchmark etiquetado v1: 15 casos, incluyendo retake humano AMI.

Final `33773287106`:

```text
117/117 tests PASS en 6.891 s
join benchmark gate PASS
schema v6 integration PASS
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

Limitación deliberada:

```text
join_acoustic_validation_enabled = false
```

La foundation acredita resolución de target y contexto timeline/léxico/segmental. **No acredita continuidad acústica del hard concat**, ausencia de click/pop, energía, waveform o prosodia.

Evidencia: `Validation/phase2d-join-safety.md`.

## Safety actual

```text
candidate != correction scope != filler assessment != join assessment != semantic decision != edit
PROPOSED_CUT != executable CUT
bounded scope != safe cut
filler assessment != safe cut
join assessment != safe cut
semantic_decisions_executable = false
correction_scopes_safe_for_cut = false
filler_assessments_safe_for_cut = false
join_assessments_are_not_edits = true
join_assessments_executable = false
join_assessments_safe_for_cut = false
join_acoustic_validation_enabled = false
executable = false
auto_apply = false
automatic_edits = 0
```

## Pendiente antes de Release

- Fase 2D.3.2: acoustic join validation sobre master audio;
- cerrar 2D antes de cualquier promoción al Edit Plan;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
