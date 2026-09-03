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
7. `candidate != correction scope != semantic decision != edit`;
8. `PROPOSED_CUT != executable CUT`;
9. `bounded scope != safe cut`;
10. ante duda: `KEEP / REVIEW`;
11. Conservador por defecto.

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD → candidates → correction scopes → semantic decisions/protection → future Edit Plan → render → audit
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
- Fase 2D.1 — correction scope foundation v1 + schema v4.

Siguiente: **Fase 2D.2 — fillers contextuales**. Después: sentence/join safety.

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
- Phase 2D.1 foundation `33757158460`: 83 tests PASS en 6.767 s; artifacts 0.
- Phase 2D.1 benchmark `33757481376`: 87 tests PASS en 6.595 s; scope gate PASS; artifacts 0.
- Phase 2D.1 final `33758185755`: **88/88 tests PASS en 6.711 s; schema v4/pipeline integration PASS; E2E FFmpeg/sync PASS; doctor PASS; artifacts 0.**

Run `33757887930` fue rojo sólo por un test legado que esperaba schema v3 tras introducir deliberadamente schema v4; 87/88 tests pasaron y no falló lógica de scope/safety.

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

Schema actual `analysis.json`: **v4**.

```text
candidates[]
correction_scopes[]
semantic_decisions[]
```

```text
semantic_protection_enabled = true
semantic_decisions_are_not_edits = true
semantic_decisions_executable = false
correction_scopes_are_not_edits = true
correction_scopes_executable = false
correction_scopes_safe_for_cut = false
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

### Marcadores ambiguos

En Conservador, `I mean / quiero decir` requiere evidencia local adicional:

- frontera explícita de reparación/truncamiento; o
- sustitución numérica; o
- `question_reframe_cue` cuando la reformulación interrogativa sobrevive al ASR aunque desaparezcan guiones/truncamientos.

`perdón / perdona / sorry`:

- exige contexto léxico a izquierda/derecha;
- disculpa + vacilación (`perdón eh ...`) sin intento interrumpido => no correction candidate;
- después de fragmento truncado sí => `explicit_correction → REVIEW`.

### Repeticiones exactas tras ASR

Whisper puede eliminar una vacilación y fabricar una repetición textual adyacente perfecta.

Regla conservadora actual:

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

Estrategias v1:

```text
repeated_corrected_prefix_anchor
local_numeric_replacement
no_deterministic_left_boundary
```

Reglas:

1. `bounded` = boundary local determinista encontrado; **no** = cut seguro;
2. `ambiguous` conserva correction detection pero deja `attempt_span=null`;
3. cada scope se enlaza a `candidate_id`;
4. todo scope mantiene:
   ```text
   safe_for_cut=false
   executable=false
   auto_apply=false
   ```
5. un `bounded` incorrecto donde debía ser `ambiguous` es fallo de seguridad.

Benchmark v1:

```text
12 casos
6 bounded
3 ambiguous
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

Detalle: `Validation/phase2d-correction-scope.md`.

## 10. Semantic Validation gate

Medir siempre:

- TP / FP / FN;
- precision / recall / F1;
- decision mismatches;
- unsafe proposals;
- missing safe proposals;
- executable decisions;
- auto-apply decisions.

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

## 11. Phase 2C.3 — audio-backed evidence

AMI ES2012d Mix-Headset se descarga sólo a `RUNNER_TEMP`, se verifica por SHA-256 y no se sube como artifact.

Final `33755013415`:

```text
3 cases
0 failures
SEMANTIC_AUDIO_GATE=PASS
automatic_edits=0
executable=0
auto_apply=0
artifacts=0
```

Detalle: `Validation/phase2c-audio-backed-validation.md`.

## 12. Siguiente — Fase 2D.2 Fillers contextuales

La detección acústica actual sólo marca tokens de vacilación obvios (`eh`, `um`, etc.) como `possible_filler`, siempre review-only.

Objetivo 2D.2:

1. no asumir que el token aislado es eliminable;
2. evaluar contexto léxico, temporal y relación con retakes/corrections;
3. distinguir vacilación local de elemento discursivo natural;
4. crear positivos/negativos etiquetados y medir FP/FN;
5. no habilitar `safe_for_cut`, execution ni auto-apply;
6. después abordar sentence boundaries + join safety.

Hasta superar 2D:

```text
safe_for_cut=false
executable=false
auto_apply=false
automatic_edits=0
```

## 13. Edit Plan / render

Edit Plan sólo contiene ediciones efectivas aprobadas; nunca candidates, correction scopes o semantic decisions no ejecutables.

Pendiente: fillers contextuales, sentence/join safety, removedText definitivo, join audit, fades/loudness y post-render verification.

## 14. Technology harvest

Video_Tunner NO es fork. Referencias: Railly/vcut, Cadence-Lab, ai-video-editor, SYSTRAN/faster-whisper. Antes de adoptar código: licencia + commit + motivo + validación propia.

## 15. GitHub / CI / Release

GitHub es source of truth.

- CI deliberada; no usar Actions como debugger;
- no modelos, vídeos, ZIPs o artifacts pesados ordinarios;
- Manual CI ligera no sustituye ML/portable;
- workflows manual-only normalmente;
- si no hay `workflow_dispatch` en conector, trigger one-shot y restauración inmediata;
- no publicar GitHub Release sin autorización expresa de Guille.

## 16. Docs

Mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation ante cambios relevantes.
