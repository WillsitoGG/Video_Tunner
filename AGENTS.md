# AGENTS.md — Video_Tunner

Contexto técnico permanente para agentes. Referencia maestra externa vigente: `00.Contexto y Reglas de Trabajo_GitHub_Video_Tunner_v3`.

## 1. Invariantes

Video_Tunner debe producir vídeo hablado limpio, natural, fiel, sincronizado, auditable y reversible en Windows 10/11 x64.

Obligatorio:

1. portable real: ZIP → descomprimir → ejecutar;
2. vídeo con audio embebido o vídeo + audio externo;
3. resolver master audio antes de análisis temporal;
4. Whisper, VAD y acoustic join validation usan exactamente el mismo master acreditado;
5. auto-sync sólo con evidencia suficiente; override/manual fallback;
6. original siempre intacto;
7. `candidate != correction scope != filler assessment != join assessment != acoustic join assessment != semantic decision != edit`;
8. `PROPOSED_CUT != executable CUT`;
9. `bounded scope != safe cut`;
10. `filler assessment != safe cut`;
11. `join context != acoustically safe join`;
12. `acoustic_context_only != semantic permission to cut`;
13. ante duda: `KEEP / REVIEW`;
14. conservador por defecto.

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD → candidates → correction scopes + filler assessments → join assessments → acoustic join assessments → semantic decisions/protection → future combined eligibility → future Edit Plan → render → audit
```

## 2. Estado

Versión `0.1.0-dev`.

Completado:

- Fase 0 — Bootstrap;
- Fase 0.5 — Technology Harvest;
- Fase 1A — Portable Foundation;
- Fase 1B — ingest + sync/drift;
- Fase 1C — Whisper/VAD sobre master + `large-v3-turbo` español real;
- Fase 2A — Semantic Candidates v1;
- Fase 2B — Semantic Decisions + Protection v1;
- Fase 2C.1 — benchmark foundation;
- Fase 2C.2 — evidencia humana bilingüe;
- Fase 2C.3 — audio humano real → `large-v3-turbo` → semantic gate;
- Fase 2D.1 — correction scope foundation v1 + schema v4;
- Fase 2D.2 — contextual fillers foundation v1 + schema v5;
- Fase 2D.3.1 — sentence/join context foundation v1 + schema v6;
- Fase 2D.3.2 — acoustic join validation foundation v1 + schema v7;
- Fase 2D.3.3 — human-audio acoustic evidence v1.

Siguiente: **Fase 2D.4 — Combined Eligibility / Promotion Policy Foundation**.

No existe promoción semántica/acústica al Edit Plan.

## 3. Evidencia principal

```text
33600174568  Portable core PASS
33621357438  Portable ML PASS
33639009841  Sync hardening PASS
33656235038  Target Spanish PASS — WER 1.64%, RTF 0.4854
33750836791  Human correction corpus PASS
33755013415  3 AMI audio-backed semantic cases PASS
33758185755  88/88 — correction scope/schema v4
33771792867  101/101 — fillers/schema v5
33773287106  117/117 — join context/schema v6
33781903986  131/131 — acoustic join/schema v7
33782959293  134/134 — human acoustic evidence PASS
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

## 5. Portable / ingest

Frozen => portable strict. Sin fallback silencioso a PATH/caches globales.

```text
video_time = offset_seconds + time_scale * external_time
```

Evidencia insuficiente => `review_required`, sin master. Nunca mezclar implícitamente audio de cámara en huecos del externo.

## 6. Analysis / schema

Schema actual `analysis.json`: **v7**.

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
acoustic_join_assessments[]
semantic_decisions[]
```

Siempre:

```text
semantic_decisions_executable = false
correction_scopes_safe_for_cut = false
filler_assessments_safe_for_cut = false
join_assessments_safe_for_cut = false
acoustic_join_assessments_are_not_edits = true
acoustic_join_assessments_executable = false
acoustic_join_assessments_safe_for_cut = false
join_acoustic_validation_enabled = true
join_acoustic_validation_is_not_cut_authorization = true
automatic_edits = 0
```

## 7. Semántica / correction scope / fillers

Candidates: `possible_repetition`, `possible_retake`, `explicit_correction`.

Semantic decisions: `KEEP / REVIEW / PROPOSED_TRIM / PROPOSED_CUT`; todas no ejecutables.

Correction scope: `bounded / ambiguous / invalid`; `bounded` no implica cut seguro.

Fillers contextuales: `isolated_hesitation / hesitation_cluster / protected_repair_context / boundary_hesitation / uncertain_asr / invalid`; ningún estado es permiso de corte.

Whisper puede omitir fillers, vacilaciones o truncamientos; no inventar evidencia ausente.

## 8. Join Context Safety — 2D.3.1

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

`join_context_only` sólo significa que ninguna guarda timeline/léxica v1 se activó.

Detalle: `Validation/phase2d-join-safety.md`.

## 9. Acoustic Join Validation — 2D.3.2

```text
master acreditado
→ decode temporal PCM16 mono 16 kHz
→ NumPy memmap
→ 80 ms antes + 80 ms después
→ RMS / edge RMS / peak / sample jump / jump ratio
```

Thresholds v1:

```text
SILENCE_DBFS                 = -42.0
MAX_RMS_DELTA_DB             = 12.0
MAX_BOUNDARY_SAMPLE_JUMP     = 0.35
MAX_BOUNDARY_JUMP_RATIO      = 1.25
```

Estados:

```text
blocked_by_context
insufficient_audio_context
low_energy_boundary_context
level_discontinuity_risk
waveform_discontinuity_risk
combined_discontinuity_risk
acoustic_context_only
```

Reglas: no medir joins ya bloqueados; no cargar horas completas en RAM; `acoustic_context_only` y low-energy siguen no ejecutables; renderer hard-concat no cambia.

Detalle: `Validation/phase2d-acoustic-join.md`.

## 10. Human-audio Acoustic Evidence — 2D.3.3

Run `33782959293` reutiliza timestamps reales de `large-v3-turbo` de `33755013415` y mide el WAV AMI original validado por tamaño/SHA-256.

```text
134/134 tests PASS en 6.803 s
cases 3
measured 1
blocked 2
failures 0
HUMAN_ACOUSTIC_GATE=PASS
artifacts 0
```

Control medido:

```text
acoustic_status       acoustic_context_only
RMS delta             4.9369 dB
boundary jump         0.030243
boundary jump ratio   0.340433
safe_for_cut          false
```

Retake humano y correction ambigua permanecen `blocked_by_context`. La acústica nunca rescata un join ya bloqueado.

No mover thresholds v1 por este run. Una sola medición humana no prueba seguridad universal ni calidad perceptual.

Detalle: `Validation/phase2d-human-acoustic-evidence.md`.

## 11. Siguiente — 2D.4 Combined Eligibility / Promotion Policy Foundation

Objetivo: combinar todas las guardas sin promover todavía edits.

Reglas iniciales:

1. la elegibilidad debe ser una capa separada del Edit Plan;
2. todos los requisitos previos deben cumplirse acumulativamente;
3. cualquier riesgo, scope ambiguo, contexto protegido o inconsistencia => REVIEW/bloqueo;
4. `removedText` debe verificarse contra índices, transcript y timestamps;
5. benchmark debe incluir fallos deliberados de cada capa;
6. durante la foundation: `safe_for_cut=false`, `executable=false`, `auto_apply=false`;
7. no permitir que una señal acústica limpia anule una guarda semántica/contextual.

## 12. Edit Plan / render

Edit Plan sólo contiene ediciones efectivas aprobadas; nunca candidates, scopes o assessments no ejecutables.

Pendiente: combined eligibility, `removedText` definitivo, promoción explícita futura, join treatment/audit, fades/loudness y post-render verification.

## 13. GitHub / CI / Release

GitHub es source of truth.

- CI deliberada; no usar Actions como debugger;
- no modelos, vídeos, ZIPs o artifacts pesados ordinarios;
- workflows manual-only normalmente;
- trigger one-shot sólo cuando sea necesario y restaurar inmediatamente;
- no publicar GitHub Release sin autorización expresa de Guille.

## 14. Docs

Mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation ante cambios relevantes.
