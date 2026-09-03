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
- Fase 2C.2 — primer retake humano + bloque de correcciones humanas bilingüe.

Fase 2C completa sigue **EN CURSO**. No existe promoción semántica al Edit Plan.

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
- Human correction baseline `33750475437`: 69 tests; 26 casos / 14 eventos; 14 TP / 2 FP / 0 FN; precision 87.5%, recall 100%; gate falla sólo precision; unsafe 0.
- Human correction final `33750836791`: **74 tests en 6.729 s; 26 casos / 14 eventos; 0 FP / 0 FN; precision/recall/F1 100% en corpus actual; unsafe 0; executable 0; auto_apply 0; artifacts 0.**

No generalizar el 100% fuera del corpus etiquetado.

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

## 8. Correcciones — regla actual de Phase 2C

`explicit_correction` sigue siendo **marker-only**. Detectar un marcador no identifica todavía el span incorrecto anterior.

La evidencia humana demostró que el marcador por sí solo no basta:

### Conservador

`I mean / quiero decir` sólo genera correction candidate con evidencia local adicional:

- frontera explícita de reparación/truncamiento antes del marcador; o
- sustitución numérica detectable a ambos lados.

`perdón / perdona / sorry`:

- exige contexto léxico a izquierda/derecha;
- patrón de disculpa + vacilación (`perdón eh ...`) sin intento interrumpido => no correction candidate;
- después de fragmento truncado sí => `explicit_correction → REVIEW`.

### Agresivo

Mantiene detección más amplia; sigue sin auto-apply.

Fixtures humanos actuales:

- AMI retake positivo;
- AMI `I mean` correction positivo;
- AMI `I mean` discourse negativo;
- CORMA `Perdón` correction positivo;
- CORMA `perdón eh` apology negativo;
- 4 controles humanos SpanishPod.

Provenance: `Validation/phase2c-semantic-validation-sources.md`.

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

## 10. Siguiente — Fase 2C.3

Validación **audio real → `large-v3-turbo` → semantic layer** sobre pocos clips trazables.

Objetivos:

1. priorizar español;
2. comprobar si Whisper conserva señales como truncamientos/dashes/pausas;
3. comparar transcript manual vs ASR;
4. alimentar el mismo gate;
5. corregir sólo problemas observados;
6. después abordar correction scope, fillers y join safety.

Hasta entonces:

```text
executable=false
auto_apply=false
automatic_edits=0
```

## 11. Edit Plan / render

Edit Plan sólo contiene ediciones efectivas aprobadas; nunca candidates o semantic decisions no ejecutables.

Pendiente: correction scope real, removedText definitivo, join audit, fades/loudness y post-render verification.

## 12. Technology harvest

Video_Tunner NO es fork. Referencias: Railly/vcut, Cadence-Lab, ai-video-editor, SYSTRAN/faster-whisper. Antes de adoptar código: licencia + commit + motivo + validación propia.

## 13. GitHub / CI / Release

GitHub es source of truth.

- CI deliberada; no usar Actions como debugger;
- no modelos, vídeos, ZIPs o artifacts pesados ordinarios;
- Manual CI ligera no sustituye ML/portable;
- workflows manual-only normalmente;
- si no hay `workflow_dispatch` en conector, trigger one-shot y restauración inmediata;
- no publicar GitHub Release sin autorización expresa de Guille.

## 14. Docs

Mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation ante cambios relevantes.
