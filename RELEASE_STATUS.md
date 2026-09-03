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
- Fase 2D.2: **SIGUIENTE — fillers contextuales**
- Fase 2D.3: FUTURA — sentence boundaries + join safety

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
Phase 2D.1 foundation            33757158460  PASS — 83 tests
Phase 2D.1 benchmark             33757481376  PASS — 87 tests, scope gate PASS
Phase 2D.1 final                 33758185755  PASS — 88/88, schema v4 integration
```

Todas mantienen `automatic_edits = 0` donde aplica y artifacts pesados = 0.

## Fase 2D.1 — Correction Scope Foundation v1

Nueva separación:

```text
candidate
!= correction scope evidence
!= semantic decision
!= edit
```

`analysis.json` usa schema v4:

```text
candidates[]
correction_scopes[]
semantic_decisions[]
```

Estados de scope:

```text
bounded
ambiguous
invalid
```

Estrategias v1:

```text
repeated_corrected_prefix_anchor
local_numeric_replacement
no_deterministic_left_boundary
```

Benchmark etiquetado:

```text
12 casos
6 bounded esperados
3 ambiguous esperados
3 no-candidate controls
```

Gate:

```text
candidate contract clean
bounded_exactness == 1.0
status/strategy/attempt mismatches == 0
unsafe_bounded == 0
safety_violations == 0
```

Final `33758185755`:

```text
88/88 tests PASS en 6.711 s
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

El run `33757887930` falló únicamente porque un test legado aún esperaba `schema_version == 3`; 87/88 tests pasaron y no hubo fallo de correction scope o safety. La expectativa se actualizó a v4 y el run final quedó verde.

Evidencia: `Validation/phase2d-correction-scope.md`.

## Safety actual

```text
candidate != correction scope != semantic decision != edit
PROPOSED_CUT != executable CUT
bounded scope != safe cut
semantic_decisions_executable = false
correction_scopes_are_not_edits = true
correction_scopes_executable = false
correction_scopes_safe_for_cut = false
executable = false
auto_apply = false
automatic_edits = 0
```

Un scope `bounded` sólo describe una frontera candidata respaldada localmente. No autoriza borrado, render ni promoción al Edit Plan.

## Pendiente antes de Release

- Fase 2D.2: fillers contextuales;
- Fase 2D.3: sentence boundaries + join safety;
- no promover semantic decisions/scopes al Edit Plan hasta evidencia suficiente;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
