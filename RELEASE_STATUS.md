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
- Fase 2D.3.2: COMPLETADA — acoustic join validation foundation + schema v7
- Fase 2D.3.3: COMPLETADA — human-audio acoustic evidence v1
- Fase 2D.4: **SIGUIENTE — Combined Eligibility / Promotion Policy Foundation**

## Evidencia principal

```text
Portable core                    33600174568  PASS
Portable ML                      33621357438  PASS
Sync hardening                   33639009841  PASS
Master analysis                  33640872486  PASS
Target Spanish                   33656235038  PASS — WER 1.64%, RTF 0.4854
Semantic Candidates              33659725847  PASS — 48 tests
Semantic Decisions/Protection    33741195594  PASS — 55 tests
Human correction final           33750836791  PASS — corpus gate
Phase 2C.3 audio-backed final    33755013415  PASS — 3/3 semantic cases
Phase 2D.1 final                 33758185755  PASS — 88/88, schema v4
Phase 2D.2 final                 33771792867  PASS — 101/101, schema v5
Phase 2D.3.1 final               33773287106  PASS — 117/117, schema v6
Phase 2D.3.2 final               33781903986  PASS — 131/131, schema v7
Phase 2D.3.3 human acoustic      33782959293  PASS — 134/134, human gate
```

Todas mantienen `automatic_edits = 0` donde aplica y artifacts = 0.

## Fase 2D.3.2 — Acoustic Join Validation Foundation v1

`analysis.json` usa schema v7 con `acoustic_join_assessments[]`.

```text
master audio acreditado
→ decode temporal FFmpeg
→ PCM16 mono 16 kHz
→ NumPy memmap
→ ventanas locales de 80 ms
→ acoustic join assessment
```

Thresholds v1:

```text
SILENCE_DBFS                 -42.0 dBFS
MAX_RMS_DELTA_DB              12.0 dB
MAX_BOUNDARY_SAMPLE_JUMP       0.35
MAX_BOUNDARY_JUMP_RATIO        1.25
```

Final `33781903986`: 131/131 PASS en 7.401 s; schema v7; real FFmpeg/PCM; E2E FFmpeg/sync; doctor; artifacts 0.

## Fase 2D.3.3 — Human-audio Acoustic Evidence v1

Run `33782959293` reutiliza endpoints reales de `large-v3-turbo` congelados desde `33755013415` y los aplica sobre el WAV AMI original CC BY 4.0, validado por bytes y SHA-256.

```text
134/134 tests PASS en 6.803 s
cases                 3
failures              0
measured_cases        1
blocked_cases         2
automatic_edits       0
executable            0
auto_apply            0
HUMAN_ACOUSTIC_GATE   PASS
artifacts              0
```

Medición humana real:

```text
status                    acoustic_context_only
left RMS                  -35.9051 dBFS
right RMS                 -30.9682 dBFS
RMS delta                   4.9369 dB
boundary sample jump        0.030243
boundary jump ratio         0.340433
safe_for_cut                false
```

Retake humano: `repair_or_protected_context_risk` → `blocked_by_context`.

Correction humana ambigua: `ambiguous` scope → `invalid_or_unbounded_target` → `blocked_by_context`.

No se modifican thresholds v1. Esta microfase no acredita seguridad universal, continuidad espectral/prosódica ni calidad perceptual de un render.

Evidencia: `Validation/phase2d-human-acoustic-evidence.md`.

## Safety actual

```text
candidate != correction scope != filler assessment != join assessment != acoustic join assessment != semantic decision != edit
PROPOSED_CUT != executable CUT
bounded scope != safe cut
filler assessment != safe cut
join assessment != safe cut
acoustic_context_only != safe cut
low_energy_boundary_context != safe cut
semantic_decisions_executable = false
correction_scopes_safe_for_cut = false
filler_assessments_safe_for_cut = false
join_assessments_safe_for_cut = false
acoustic_join_assessments_are_not_edits = true
acoustic_join_assessments_executable = false
acoustic_join_assessments_safe_for_cut = false
join_acoustic_validation_enabled = true
join_acoustic_validation_is_not_cut_authorization = true
executable = false
auto_apply = false
automatic_edits = 0
```

## Pendiente antes de Release

- Fase 2D.4: política combinada de elegibilidad/promoción no ejecutable;
- validar `removedText` definitivo y guardas acumulativas;
- cerrar 2D antes de cualquier promoción al Edit Plan;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
