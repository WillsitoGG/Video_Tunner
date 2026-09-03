# AGENTS.md — Video_Tunner

Contexto técnico permanente para agentes. Referencia maestra externa vigente: `00.Contexto y Reglas de Trabajo_GitHub_Video_Tunner_v3`.

## 1. Invariantes

Video_Tunner debe producir vídeo hablado limpio, natural, fiel, sincronizado, auditable y reversible en Windows 10/11 x64.

Obligatorio:

1. portable real: ZIP → descomprimir → ejecutar;
2. vídeo con audio embebido o vídeo + audio externo;
3. resolver master audio antes de análisis temporal;
4. Whisper y VAD usan exactamente el mismo master;
5. auto-sync sólo con evidencia suficiente; override/manual fallback;
6. original siempre intacto;
7. `candidate != correction scope != filler assessment != join assessment != semantic decision != edit`;
8. `PROPOSED_CUT != executable CUT`;
9. `bounded scope != safe cut`;
10. `filler assessment != safe cut`;
11. `join context != acoustically safe join`;
12. ante duda: `KEEP / REVIEW`;
13. conservador por defecto.

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD → candidates → correction scopes + filler assessments → join assessments → semantic decisions/protection → future Edit Plan → render → audit
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
- Fase 2C.3 — audio humano real → portable frozen → `large-v3-turbo` → semantic gate;
- Fase 2D.1 — correction scope foundation v1 + schema v4;
- Fase 2D.2 — contextual fillers foundation v1 + schema v5;
- Fase 2D.3.1 — sentence/join context foundation v1 + schema v6.

Siguiente: **Fase 2D.3.2 — Acoustic Join Validation**.

No existe promoción semántica al Edit Plan.

## 3. Evidencia principal

- Portable core `33600174568`: PASS.
- Portable ML `33621357438`: PASS.
- Sync hardening `33639009841`: PASS.
- Master analysis `33640872486`: PASS.
- Target Spanish `33656235038`: PASS — WER 1.64%, RTF 0.4854, automatic edits 0.
- Semantic Candidates `33659725847`: PASS — 48 tests.
- Semantic Decisions/Protection `33741195594`: PASS — 55 tests.
- Human correction final `33750836791`: 74 tests; corpus gate PASS; unsafe 0; executable 0; auto_apply 0; artifacts 0.
- Phase 2C.3 audio-backed `33755013415`: 3 AMI audio cases; semantic gate PASS; automatic_edits/executable/auto_apply 0; artifacts 0.
- Phase 2D.1 final `33758185755`: 88/88 PASS; schema v4; E2E FFmpeg/sync; doctor; artifacts 0.
- Phase 2D.2 final `33771792867`: 101/101 PASS en 5.031 s; schema v5; E2E FFmpeg/sync; doctor; artifacts 0.
- Phase 2D.3.1 foundation `33772715214`: 112/112 PASS en 6.670 s; join foundation; artifacts 0.
- Phase 2D.3.1 final `33773287106`: **117/117 PASS en 6.891 s; benchmark + schema v6 integration; E2E FFmpeg/sync; doctor; artifacts 0.**

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

Schema actual `analysis.json`: **v6**.

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
semantic_decisions[]
```

```text
semantic_protection_enabled = true
semantic_decisions_are_not_edits = true
semantic_decisions_executable = false
correction_scopes_are_not_edits = true
correction_scopes_executable = false
correction_scopes_safe_for_cut = false
filler_assessments_are_not_edits = true
filler_assessments_executable = false
filler_assessments_safe_for_cut = false
join_assessments_are_not_edits = true
join_assessments_executable = false
join_assessments_safe_for_cut = false
join_acoustic_validation_enabled = false
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

Siempre:

```text
executable = false
auto_apply = false
```

Guardas: span/timestamps/removed_text, cifras/unidades/importes/%, negación, sujeto/persona, tiempo/aspecto, causalidad/contraste, señal de entidades.

## 8. Correcciones y retakes — reglas derivadas de evidencia humana

En Conservador, `I mean / quiero decir` requiere evidencia local adicional: frontera de reparación, sustitución numérica o `question_reframe_cue`.

`perdón / perdona / sorry` exige contexto léxico a ambos lados; disculpa + vacilación sin intento interrumpido no es correction candidate.

Whisper puede eliminar una vacilación y fabricar una repetición textual perfecta. Timing anómalamente comprimido => `REVIEW`.

## 9. Correction Scope — Phase 2D.1

Detección de correction y scope son capas distintas.

Estados:

```text
bounded
ambiguous
invalid
```

`bounded` = boundary local determinista encontrado; **no** = cut seguro. Todo scope mantiene `safe_for_cut=false`, `executable=false`, `auto_apply=false`.

Detalle: `Validation/phase2d-correction-scope.md`.

## 10. Contextual Fillers — Phase 2D.2

`possible_filler` sigue siendo candidate acústico. `filler_assessments[]` añade contexto, no ejecución.

Estados v1:

```text
isolated_hesitation
hesitation_cluster
protected_repair_context
boundary_hesitation
uncertain_asr
invalid
```

Todo assessment mantiene `safe_for_cut=false`, `executable=false`, `auto_apply=false`.

Limitación: Whisper puede omitir un filler; no inventar fillers ausentes del transcript.

Detalle: `Validation/phase2d-contextual-fillers.md`.

## 11. Join Context Safety — Phase 2D.3.1

`join_assessments[]` describe los dos lados de un hipotético join sobre la timeline y el transcript. No analiza todavía el waveform.

Estados v1:

```text
join_context_only
sentence_boundary_risk
segment_boundary_risk
critical_lexical_context_risk
repair_or_protected_context_risk
transcript_edge
invalid_or_unbounded_target
```

Reglas:

1. validar target span antes de estudiar el join;
2. scope de correction `ambiguous` => sin target de join;
3. span semántico incoherente => `invalid_or_unbounded_target`;
4. edge de transcript => `transcript_edge`;
5. cambio de segmento ASR => riesgo;
6. puntuación fuerte => evidencia de sentence boundary, no verdad absoluta;
7. cifras/unidades/negación/persona/tiempo/causalidad alrededor del join => riesgo;
8. retake/correction o filler protegido => riesgo de reparación;
9. `join_context_only` sólo significa ausencia de guardas v1 activadas; **no** significa safe-for-cut;
10. todo assessment mantiene:
   ```text
   safe_for_cut=false
   executable=false
   auto_apply=false
   ```

Benchmark v1: 15 casos, incluido retake humano AMI.

Gate:

```text
record_count_mismatches == 0
status_mismatches == 0
target_source_mismatches == 0
bilateral_context_mismatches == 0
safety_violations == 0
status_accuracy == 1.0
```

Final `33773287106`: 117/117 PASS en 6.891 s; artifacts 0.

Detalle: `Validation/phase2d-join-safety.md`.

## 12. Semantic Validation gate

Medir siempre TP/FP/FN, precision/recall/F1, decision mismatches, unsafe proposals, missing safe proposals, executable y auto-apply.

```text
precision >= 0.95
recall >= 0.95
unsafe proposals == 0
decision mismatches == 0
missing safe proposals == 0
executable decisions == 0
auto_apply decisions == 0
```

Una FP review-only es ruido. Un `PROPOSED_CUT` incorrecto es fallo de seguridad. No mover thresholds para esconder nuevos fallos.

## 13. Siguiente — Phase 2D.3.2 Acoustic Join Validation

Objetivo: medir sobre el **master audio real** los bordes de un hipotético join sin confundir limpieza acústica con permiso semántico.

Reglas iniciales:

1. usar el mismo master audio acreditado que Whisper/VAD;
2. analizar ventanas reales alrededor de `target_span.start/end`;
3. detectar contexto insuficiente, saltos de nivel/waveform y discontinuidades obvias;
4. registrar métricas y thresholds auditables;
5. construir fixtures sintéticos antes de cualquier promoción;
6. audio humano real sólo cuando aporte evidencia nueva y con procedencia clara;
7. un join acústicamente limpio **no** autoriza por sí solo un corte;
8. durante 2D.3.2:
   ```text
   safe_for_cut=false
   executable=false
   auto_apply=false
   automatic_edits=0
   ```

## 14. Edit Plan / render

Edit Plan sólo contiene ediciones efectivas aprobadas; nunca candidates, correction scopes, filler assessments, join assessments o semantic decisions no ejecutables.

Pendiente: acoustic join validation, removedText definitivo, join audit, fades/loudness y post-render verification.

## 15. Technology harvest

Video_Tunner NO es fork. Referencias: Railly/vcut, Cadence-Lab, ai-video-editor, SYSTRAN/faster-whisper. Antes de adoptar código: licencia + commit + motivo + validación propia.

## 16. GitHub / CI / Release

GitHub es source of truth.

- CI deliberada; no usar Actions como debugger;
- no modelos, vídeos, ZIPs o artifacts pesados ordinarios;
- Manual CI ligera no sustituye ML/portable;
- workflows manual-only normalmente;
- si no hay `workflow_dispatch` en conector, trigger one-shot y restauración inmediata;
- no publicar GitHub Release sin autorización expresa de Guille.

## 17. Docs

Mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation ante cambios relevantes.
