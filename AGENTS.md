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
sources → ingest/sync → MASTER AUDIO → Whisper/VAD → candidates → correction scopes + filler assessments → join assessments → acoustic join assessments → semantic decisions/protection → future Edit Plan → render → audit
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
- Fase 2C.2 — retake humano + correcciones humanas bilingües;
- Fase 2C.3 — audio humano real → `large-v3-turbo` → semantic gate;
- Fase 2D.1 — correction scope foundation v1 + schema v4;
- Fase 2D.2 — contextual fillers foundation v1 + schema v5;
- Fase 2D.3.1 — sentence/join context foundation v1 + schema v6;
- Fase 2D.3.2 — acoustic join validation foundation v1 + schema v7.

Siguiente: **Fase 2D.3.3 — human-audio acoustic join evidence**.

No existe promoción semántica/acústica al Edit Plan.

## 3. Evidencia principal

- Portable core `33600174568`: PASS.
- Portable ML `33621357438`: PASS.
- Sync hardening `33639009841`: PASS.
- Master analysis `33640872486`: PASS.
- Target Spanish `33656235038`: PASS — WER 1.64%, RTF 0.4854, automatic edits 0.
- Semantic Candidates `33659725847`: PASS — 48 tests.
- Semantic Decisions/Protection `33741195594`: PASS — 55 tests.
- Human correction final `33750836791`: corpus gate PASS; unsafe/executable/auto_apply 0.
- Phase 2C.3 audio-backed `33755013415`: 3 AMI audio cases; semantic gate PASS; artifacts 0.
- Phase 2D.1 final `33758185755`: 88/88 PASS; schema v4; artifacts 0.
- Phase 2D.2 final `33771792867`: 101/101 PASS; schema v5; artifacts 0.
- Phase 2D.3.1 final `33773287106`: 117/117 PASS; schema v6; artifacts 0.
- Phase 2D.3.2 foundation `33781430382`: 131/131 PASS en 6.998 s; real FFmpeg/PCM tests + acoustic gate PASS; artifacts 0.
- Phase 2D.3.2 final `33781903986`: **131/131 PASS en 7.401 s; schema v7/pipeline integration; real FFmpeg/PCM tests; E2E FFmpeg/sync; doctor; artifacts 0.**

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

Convención sync:

```text
video_time = offset_seconds + time_scale * external_time
```

Evidencia insuficiente => `review_required`, sin master. Nunca mezclar implícitamente audio de cámara en huecos del externo.

## 6. Analysis / schema

`analyze` siempre usa master acreditado. Master pre-resuelto exige `ingest.json` y SHA-256 coincidente.

Schema actual `analysis.json`: **v7**.

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
acoustic_join_assessments[]
semantic_decisions[]
```

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

## 7. Semantic Candidates / Decisions

Kinds:

```text
possible_repetition
possible_retake
explicit_correction
```

Candidate:

```text
decision = undecided
suggested_decision = REVIEW
auto_apply = false
span_safe_for_auto_apply = false
```

Semantic decisions:

```text
KEEP
REVIEW
PROPOSED_TRIM
PROPOSED_CUT
```

Siempre `executable=false`, `auto_apply=false`.

## 8. Correcciones y retakes

`I mean / quiero decir` requiere evidencia local adicional. `perdón / perdona / sorry` exige contexto léxico. Whisper puede eliminar vacilaciones/truncamientos; timing anómalamente comprimido => REVIEW.

## 9. Correction Scope — 2D.1

Estados `bounded / ambiguous / invalid`. `bounded` = boundary local determinista, no cut seguro.

Detalle: `Validation/phase2d-correction-scope.md`.

## 10. Contextual Fillers — 2D.2

Estados:

```text
isolated_hesitation
hesitation_cluster
protected_repair_context
boundary_hesitation
uncertain_asr
invalid
```

Todo assessment permanece no ejecutable. Whisper puede omitir un filler; no inventar tokens ausentes.

Detalle: `Validation/phase2d-contextual-fillers.md`.

## 11. Join Context Safety — 2D.3.1

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

`join_context_only` sólo significa que ninguna guarda timeline/léxica v1 se activó. No autoriza corte.

Detalle: `Validation/phase2d-join-safety.md`.

## 12. Acoustic Join Validation — 2D.3.2

La capa mide el **master real** sólo para joins con `join_context_only`.

Implementación:

```text
master acreditado
→ un decode FFmpeg temporal a PCM16 mono 16 kHz
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

Reglas:

1. no medir un join que ya está bloqueado por contexto;
2. no cargar horas de audio completas en RAM; usar `memmap`;
3. `acoustic_context_only` no equivale a join perceptualmente limpio ni safe-for-cut;
4. `low_energy_boundary_context` tampoco equivale a safe-for-cut;
5. todo acoustic assessment conserva `safe_for_cut=false`, `executable=false`, `auto_apply=false`;
6. no modificar thresholds para ocultar FP/FN;
7. renderer hard-concat no cambia en esta fase.

Benchmark v1: 11 casos reproducibles. Gate: status exact, measurement contract exact, risk recall 1.0, safety violations 0.

Detalle: `Validation/phase2d-acoustic-join.md`.

## 13. Siguiente — 2D.3.3 Human-audio Acoustic Evidence

Antes de cerrar todo 2D:

1. usar audio humano real con procedencia/licencia trazable;
2. aplicar la capa a endpoints derivados de joins reales;
3. medir comportamiento de thresholds v1;
4. documentar FP/FN y ajustar sólo si la evidencia lo exige;
5. no promover todavía al Edit Plan;
6. después diseñar política combinada + `removedText` definitivo.

## 14. Edit Plan / render

Edit Plan sólo contiene ediciones efectivas aprobadas; nunca candidates, scopes o assessments no ejecutables.

Pendiente: evidencia acústica humana, promotion policy, removedText definitivo, join treatment/audit, fades/loudness y post-render verification.

## 15. Technology harvest

Video_Tunner NO es fork. Referencias: Railly/vcut, Cadence-Lab, ai-video-editor, SYSTRAN/faster-whisper. Antes de adoptar código: licencia + commit + motivo + validación propia.

## 16. GitHub / CI / Release

GitHub es source of truth.

- CI deliberada; no usar Actions como debugger;
- no modelos, vídeos, ZIPs o artifacts pesados ordinarios;
- Manual CI ligera no sustituye ML/portable;
- workflows manual-only normalmente;
- trigger one-shot sólo cuando sea necesario y restaurar inmediatamente;
- no publicar GitHub Release sin autorización expresa de Guille.

## 17. Docs

Mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation ante cambios relevantes.
