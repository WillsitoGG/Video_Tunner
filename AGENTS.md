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
7. `candidate != correction scope != filler assessment != semantic decision != edit`;
8. `PROPOSED_CUT != executable CUT`;
9. `bounded scope != safe cut`;
10. `filler assessment != safe cut`;
11. ante duda: `KEEP / REVIEW`;
12. Conservador por defecto.

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD → candidates → correction scopes + filler assessments → semantic decisions/protection → future Edit Plan → render → audit
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
- Fase 2D.2 — contextual fillers foundation v1 + schema v5.

Siguiente: **Fase 2D.3 — sentence boundaries + join safety**.

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
- Phase 2C.3 lightweight `33754755238`: 76/76 PASS; E2E FFmpeg/sync; doctor; artifacts 0.
- Phase 2C.3 audio-backed `33755013415`: 3 AMI audio cases; 0 failures; semantic gate PASS; automatic_edits/executable/auto_apply 0; artifacts 0.
- Phase 2D.1 final `33758185755`: 88/88 PASS; schema v4; E2E FFmpeg/sync; doctor; artifacts 0.
- Phase 2D.2 benchmark `33771489008`: **101/101 PASS en 7.030 s; filler context gate PASS; human AMI repair filler protected; artifacts 0.**
- Phase 2D.2 final `33771792867`: **101/101 PASS en 5.031 s; schema v5/pipeline integration PASS; E2E FFmpeg/sync; doctor; artifacts 0.**

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

Schema actual `analysis.json`: **v5**.

```text
candidates[]
correction_scopes[]
filler_assessments[]
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

Whisper puede eliminar una vacilación y fabricar una repetición textual perfecta. Regla temporal conservadora actual:

```text
min_seconds_per_token_for_repeat_proposal = 0.120
```

Timing anómalamente comprimido => `REVIEW`, aunque el texto sea idéntico.

## 9. Correction Scope — Phase 2D.1

Detección de correction y scope son capas distintas.

Estados:

```text
bounded
ambiguous
invalid
```

Reglas:

1. `bounded` = boundary local determinista encontrado; **no** = cut seguro;
2. `ambiguous` conserva correction detection pero deja `attempt_span=null`;
3. cada scope se enlaza a `candidate_id`;
4. todo scope mantiene `safe_for_cut=false`, `executable=false`, `auto_apply=false`;
5. un `bounded` incorrecto donde debía ser `ambiguous` es fallo de seguridad.

Detalle: `Validation/phase2d-correction-scope.md`.

## 10. Contextual Fillers — Phase 2D.2

`possible_filler` sigue siendo candidate acústico. La capa `filler_assessments[]` añade contexto, no ejecución.

Estados v1:

```text
isolated_hesitation
hesitation_cluster
protected_repair_context
boundary_hesitation
uncertain_asr
invalid
```

Reglas:

1. filler solapado/cercano a `possible_retake` o `explicit_correction` => `protected_repair_context`;
2. fillers adyacentes => `hesitation_cluster`;
3. transcript boundary o gap >= `0.60 s` => `boundary_hesitation`;
4. probabilidad ASR < `0.60` o ausente => `uncertain_asr`;
5. `isolated_hesitation` sólo es evidencia contextual, **no safe-for-cut**;
6. todo assessment mantiene:
   ```text
   safe_for_cut=false
   executable=false
   auto_apply=false
   ```

Benchmark v1: 15 casos ES/EN, con retake humano AMI y control humano SpanishPod.

Gate:

```text
record_count_mismatches == 0
status_mismatches == 0
status_accuracy == 1.0
repair_link_mismatches == 0
repair_protection_recall == 1.0
safety_violations == 0
```

Limitación crítica derivada del audio real de 2C.3: Whisper puede omitir un filler (`uh`). No inventar fillers que no sobreviven al ASR. La capa sólo clasifica candidates presentes.

Detalle: `Validation/phase2d-contextual-fillers.md`.

## 11. Semantic Validation gate

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

## 12. Phase 2C.3 — audio-backed evidence

AMI ES2012d Mix-Headset se descarga sólo a `RUNNER_TEMP`, se verifica por SHA-256 y no se sube como artifact.

Final `33755013415`: semantic gate PASS, automatic_edits/executable/auto_apply 0, artifacts 0.

Detalle: `Validation/phase2c-audio-backed-validation.md`.

## 13. Siguiente — Fase 2D.3 Sentence boundaries + join safety

Objetivo: demostrar que un futuro corte puede unir ambos lados sin romper frase, turno, palabra, intención o prosodia.

Reglas iniciales:

1. sentence/turn boundary es evidencia separada del candidate;
2. no usar sólo puntuación ASR como verdad absoluta;
3. proteger joins junto a negaciones, entidades, cifras, cambios de sujeto y reparaciones;
4. auditar gap, contexto izquierdo/derecho y continuidad temporal;
5. `removedText` definitivo sólo cuando el span y ambos lados estén definidos;
6. no habilitar `safe_for_cut`, execution ni auto-apply durante la foundation de 2D.3.

Hasta superar 2D:

```text
safe_for_cut=false
executable=false
auto_apply=false
automatic_edits=0
```

## 14. Edit Plan / render

Edit Plan sólo contiene ediciones efectivas aprobadas; nunca candidates, correction scopes, filler assessments o semantic decisions no ejecutables.

Pendiente: sentence/join safety, removedText definitivo, join audit, fades/loudness y post-render verification.

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
