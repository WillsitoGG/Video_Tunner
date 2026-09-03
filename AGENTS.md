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
7. `candidate != semantic decision != edit`;
8. `PROPOSED_CUT != executable CUT`;
9. ante duda: `KEEP / REVIEW`;
10. Conservador por defecto.

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD → candidates → semantic decisions/protection → future Edit Plan → render → audit
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
- Fase 2C.2 — retake humano + bloque de correcciones humanas bilingüe;
- Fase 2C.3 — audio humano real → portable frozen → `large-v3-turbo` → semantic gate.

Siguiente: **Fase 2D — correction scope + fillers contextuales + sentence/join safety**.

No existe promoción semántica al Edit Plan.

## 3. Evidencia principal

- Portable core `33600174568`: PASS.
- Portable ML `33621357438`: PASS.
- Sync hardening `33639009841`: PASS.
- Master analysis `33640872486`: PASS.
- Target Spanish `33656235038`: PASS — WER 1.64%, RTF 0.4854, automatic edits 0.
- Semantic Candidates `33659725847`: PASS — 48 tests.
- Semantic Decisions/Protection `33741195594`: PASS — 55 tests.
- Semantic validation baseline `33742519997`: 2 FP / 0 FN, precision 84.62%, unsafe 0.
- Semantic validation ajustada `33743029443`: 21 casos, 0 FP/FN, unsafe 0.
- Primer retake humano `33743638690`: 65 tests, AMI `possible_retake → REVIEW`.
- Human correction baseline `33750475437`: 69 tests; 26 casos / 14 eventos; 14 TP / 2 FP / 0 FN; precision 87.5%, recall 100%; unsafe 0.
- Human correction final `33750836791`: **74 tests en 6.729 s; 26 casos / 14 eventos; 0 FP / 0 FN; precision/recall/F1 100% en corpus etiquetado; unsafe 0; executable 0; auto_apply 0; artifacts 0.**
- Phase 2C.3 lightweight `33754755238`: **76/76 tests PASS en 5.561 s; E2E FFmpeg/sync PASS; doctor PASS; artifacts 0.**
- Phase 2C.3 audio-backed final `33755013415`: **3 casos AMI reales; 0 failures; 53.810 s; semantic gate PASS; automatic_edits 0; executable 0; auto_apply 0; artifacts 0.**

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

Schema actual `analysis.json`: **v3**.

```text
candidates[]
semantic_decisions[]
```

```text
semantic_protection_enabled = true
semantic_decisions_are_not_edits = true
semantic_decisions_executable = false
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

`explicit_correction` sigue siendo **marker-only**. Detectar un marcador no identifica todavía el span incorrecto anterior.

### Marcadores ambiguos

En Conservador, `I mean / quiero decir` requiere evidencia local adicional:

- frontera explícita de reparación/truncamiento; o
- sustitución numérica; o
- `question_reframe_cue` cuando la reformulación interrogativa sobrevive al ASR aunque desaparezcan guiones/truncamientos.

`perdón / perdona / sorry`:

- exige contexto léxico a izquierda/derecha;
- patrón de disculpa + vacilación (`perdón eh ...`) sin intento interrumpido => no correction candidate;
- después de fragmento truncado sí => `explicit_correction → REVIEW`.

### Repeticiones exactas tras ASR

Audio real demostró que Whisper puede eliminar una vacilación y fabricar una repetición textual adyacente perfecta.

Por ello, una `possible_repetition` con timing anómalamente comprimido se degrada a `REVIEW` aunque el texto coincida exactamente.

Regla conservadora actual:

```text
min_seconds_per_token_for_repeat_proposal = 0.120
```

Caso AMI real:

```text
first_seconds_per_token = 0.112
→ timing compressed
→ REVIEW
```

No usar este threshold como verdad universal; es una guarda conservadora derivada de evidencia real y debe seguir validándose con corpus adicional.

## 9. Semantic Validation gate

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

Una FP review-only es ruido. Un `PROPOSED_CUT` incorrecto es fallo de seguridad. No mezclar.

No mover thresholds para esconder nuevos fallos.

## 10. Phase 2C.3 — audio-backed evidence

Workflow permanente: `.github/workflows/semantic-audio-spike.yml`, normalmente manual-only.

Scripts:

```text
.github/scripts/download_ami_semantic_fixture.ps1
.github/scripts/run_semantic_audio_validation.ps1
```

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

Resultados:

```text
retake real       → possible_repetition → REVIEW
I mean correction → explicit_correction → REVIEW
I mean discourse  → 0 explicit_correction
```

Detalle: `Validation/phase2c-audio-backed-validation.md`.

## 11. Siguiente — Fase 2D

### 2D.1 Correction scope

Objetivo: determinar de forma auditable qué span anterior corresponde al intento incorrecto en una corrección.

Reglas:

1. no convertir `marker-only` en un corte por intuición;
2. candidate scope y semantic decision scope deben seguir separados;
3. si el boundary anterior no se puede demostrar, mantener `REVIEW`;
4. proteger cifras, unidades, negaciones, persona/sujeto, tiempo/aspecto, entidades y causalidad;
5. no crear edits ejecutables durante 2D.1;
6. medir scope exactness por separado de marker detection.

Después: fillers contextuales y sentence/join safety.

Hasta superar 2D:

```text
executable=false
auto_apply=false
automatic_edits=0
```

## 12. Edit Plan / render

Edit Plan sólo contiene ediciones efectivas aprobadas; nunca candidates o semantic decisions no ejecutables.

Pendiente: correction scope real, removedText definitivo, join audit, fades/loudness y post-render verification.

## 13. Technology harvest

Video_Tunner NO es fork. Referencias: Railly/vcut, Cadence-Lab, ai-video-editor, SYSTRAN/faster-whisper. Antes de adoptar código: licencia + commit + motivo + validación propia.

## 14. GitHub / CI / Release

GitHub es source of truth.

- CI deliberada; no usar Actions como debugger;
- no modelos, vídeos, ZIPs o artifacts pesados ordinarios;
- Manual CI ligera no sustituye ML/portable;
- workflows manual-only normalmente;
- si no hay `workflow_dispatch` en conector, trigger one-shot y restauración inmediata;
- no publicar GitHub Release sin autorización expresa de Guille.

## 15. Docs

Mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation ante cambios relevantes.
