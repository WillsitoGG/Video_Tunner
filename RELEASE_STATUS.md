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
- Fase 2D.3: **SIGUIENTE — sentence boundaries + join safety**

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
Phase 2C.3 lightweight           33754755238  PASS — 76/76, FFmpeg/sync E2E
Phase 2C.3 audio-backed final    33755013415  PASS — 3/3 cases, semantic gate PASS
Phase 2D.1 final                 33758185755  PASS — 88/88, schema v4 integration
Phase 2D.2 benchmark             33771489008  PASS — 101/101, filler context gate
Phase 2D.2 final                 33771792867  PASS — 101/101, schema v5 integration
```

Todas mantienen `automatic_edits = 0` donde aplica y artifacts pesados = 0.

## Fase 2D.2 — Contextual Fillers Foundation v1

Nueva separación:

```text
possible_filler candidate
!= filler assessment
!= semantic decision
!= edit
```

`analysis.json` usa schema v5:

```text
candidates[]
correction_scopes[]
filler_assessments[]
semantic_decisions[]
```

Estados v1:

```text
isolated_hesitation
hesitation_cluster
protected_repair_context
boundary_hesitation
uncertain_asr
invalid
```

Reglas principales:

- filler dentro/junto a retake o correction => `protected_repair_context`;
- fillers adyacentes => `hesitation_cluster`;
- transcript boundary o gap >= `0.60 s` => `boundary_hesitation`;
- probabilidad ASR < `0.60` => `uncertain_asr`;
- incluso `isolated_hesitation` permanece `safe_for_cut=false`.

Benchmark etiquetado v1:

```text
15 casos ES/EN
fillers aislados y clusters
repair context
boundaries
baja confianza ASR
retake humano AMI
control humano SpanishPod
```

Gate:

```text
record_count_mismatches == 0
status_mismatches == 0
status_accuracy == 1.0
repair_link_mismatches == 0
repair_protection_recall == 1.0
safety_violations == 0
```

Evidencia:

```text
33771489008
101/101 tests PASS en 7.030 s
filler context benchmark PASS
human AMI repair filler protected
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0

33771792867
101/101 tests PASS en 5.031 s
analysis schema v5 integration PASS
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

Limitación importante derivada del audio real de 2C.3: `large-v3-turbo` puede omitir una vacilación como `uh`. Por tanto, 2D.2 clasifica fillers que sobreviven al ASR; **no inventa fillers ausentes del transcript**. La protección del retake colapsado por ASR permanece en la capa semántica/timing.

Evidencia: `Validation/phase2d-contextual-fillers.md`.

## Safety actual

```text
candidate != correction scope != filler assessment != semantic decision != edit
PROPOSED_CUT != executable CUT
bounded scope != safe cut
filler assessment != safe cut
semantic_decisions_executable = false
correction_scopes_are_not_edits = true
correction_scopes_executable = false
correction_scopes_safe_for_cut = false
filler_assessments_are_not_edits = true
filler_assessments_executable = false
filler_assessments_safe_for_cut = false
executable = false
auto_apply = false
automatic_edits = 0
```

Ni un correction scope `bounded` ni un `isolated_hesitation` autorizan borrado, render o promoción al Edit Plan.

## Pendiente antes de Release

- Fase 2D.3: sentence boundaries + join safety;
- no promover semantic decisions/scopes/filler assessments al Edit Plan hasta evidencia suficiente;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
