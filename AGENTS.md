# AGENTS.md — Video_Tunner

Contexto técnico permanente para agentes. Referencia maestra externa vigente: `00.Contexto y Reglas de Trabajo_GitHub_Video_Tunner_v3`.

## 1. Invariantes

Video_Tunner debe producir vídeo hablado limpio, natural, fiel, sincronizado, auditable y reversible en Windows 10/11 x64.

Obligatorio:

1. portable real: ZIP → descomprimir → ejecutar;
2. vídeo con audio embebido o vídeo + audio externo;
3. resolver master audio antes de cualquier análisis temporal;
4. Whisper y VAD usan exactamente el mismo master audio;
5. auto-sync sólo con evidencia suficiente; fallback/override manual;
6. original siempre intacto;
7. `candidate != semantic decision != edit`;
8. `PROPOSED_CUT != executable CUT`;
9. ante duda: `KEEP / REVIEW`;
10. modo Conservador por defecto.

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD → candidates → semantic decisions/protection → future Edit Plan → render → audit
```

## 2. Estado

Versión `0.1.0-dev`.

Completado:

- Fase 0 — Bootstrap;
- Fase 0.5 — Technology Harvest;
- Fase 1A — Portable Foundation;
- Fase 1B — dual ingest + master audio + sync/drift;
- Fase 1C — Whisper/VAD sobre master + `large-v3-turbo` español real;
- Fase 2A — Semantic Candidates v1;
- Fase 2B — Semantic Decisions + Protection v1;
- Fase 2C — **benchmark/validation foundation v1 + primer retake humano positivo**.

Fase 2C completa sigue **EN CURSO**: sólo existe todavía un positivo humano espontáneo real; faltan más retomas/autocorrecciones, positivos en español, scope de correcciones/fillers y join safety. No existe promoción semántica al Edit Plan.

## 3. Evidencia principal

- Portable core `33600174568`: PASS.
- Portable ML `33621357438`: PASS.
- Sync hardening `33639009841`: PASS.
- Master-audio analysis `33640872486`: PASS.
- Target-model Spanish `33656235038`: PASS — WER 1.64%, RTF 0.4854, peak 1818.7 MiB, modelo 1546.5 MiB, automatic edits 0.
- Semantic Candidates `33659725847`: PASS — 48 tests, doctor PASS, artifacts 0.
- Semantic Decisions/Protection `33741195594`: PASS — 55 tests en 6.671 s, doctor PASS, artifacts 0.
- Semantic validation baseline `33742519997`: PASS — 60 tests; 2 FP / 0 FN, precision 84.62%, recall 100%, F1 91.67%, unsafe proposals 0.
- Semantic validation ajustada `33743029443`: PASS — 64 tests en 6.588 s; 21 casos, 0 FP / 0 FN, precision/recall/F1 100%, unsafe proposals 0, executable 0, auto-apply 0, artifacts 0.
- Primer positivo humano `33743638690`: PASS — 65 tests en 6.789 s; corpus 22 casos / 12 eventos, retake humano AMI detectado como `possible_retake → REVIEW`, 0 FP / 0 FN, unsafe proposals 0, executable 0, auto-apply 0, artifacts 0.

El 100% de 2C corresponde exclusivamente al corpus v1 etiquetado; no generalizar a habla real arbitraria.

## 4. Stack fijado

```text
faster-whisper 1.2.1
CTranslate2 4.8.1
ONNX Runtime 1.29.0
tokenizers 0.23.1
NumPy 2.5.2
PyInstaller 6.22.2
```

VAD: faster-whisper + `silero_vad_v6.onnx`. No standalone Torch.

Modelo objetivo: `large-v3-turbo`; `tiny` sólo para fixtures baratos.

Validación target-model:

```text
repo: rtlingo/mobiuslabsgmbh-faster-whisper-large-v3-turbo
revision: 6bd64462dd562f8062828f585c3709aa52df0083
model.bin sha256: e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da
```

## 5. Portable

```text
Video_Tunner/
├── Video_Tunner.exe
├── _internal/
├── Tools/ffmpeg/bin/
├── Models/whisper/
├── Config/
├── Temp/
├── Cache/
├── Logs/
├── Output/
└── portable-manifest.json
```

Frozen => portable strict. Sin fallback silencioso a PATH o caches globales.

## 6. Ingesta / sync

Convención temporal inmutable:

```text
video_time = offset_seconds + time_scale * external_time
```

Auto-sync actual: log-RMS → ZNCC coarse → anchors multi-window → offset/scale → MAD outliers → confidence/residual/coverage.

Evidencia insuficiente => `review_required`, sin master. Huecos del audio externo son silencio; nunca mezclar implícitamente audio de cámara.

Outputs:

```text
<stem>_master_audio.flac
<stem>_ingest.json
```

## 7. Analysis / schema

`analyze` siempre usa master audio acreditado. Master pre-resuelto exige `ingest.json` y SHA-256 del vídeo fuente coincidente.

**Schema actual de `analysis.json`: v3.**

```text
candidates[]
semantic_decisions[]
```

Safety flags obligatorios:

```text
semantic_protection_enabled = true
semantic_decisions_are_not_edits = true
semantic_decisions_executable = false
```

`automatic_edits` permanece `0`.

## 8. Fase 2A — Semantic Candidates v1

Módulo: `Source/video_tunner/semantic_candidates.py`.

Clases:

```text
possible_repetition
possible_retake
explicit_correction
```

Todo candidate semántico:

```text
decision = undecided
suggested_decision = REVIEW
auto_apply = false
span_safe_for_auto_apply = false
```

Conservar normalmente la lectura posterior. En `explicit_correction` el span es sólo el marcador; detectar `perdón` no demuestra qué texto anterior debe borrarse.

Referencia conceptual: `Railly/vcut@2142cc54dc01a0d2272f1d99717b89cd1c7c9262`. Implementación Python propia.

## 9. Fase 2B — Semantic Decisions + Protection v1

Módulos:

```text
Source/video_tunner/semantic_decisions.py
Source/video_tunner/semantic_report.py
```

Decisiones posibles:

```text
KEEP
REVIEW
PROPOSED_TRIM
PROPOSED_CUT
```

Todas siguen:

```text
executable = false
auto_apply = false
```

Guardas deterministas v1:

- integridad de word indices/timestamps;
- `removed_text` debe coincidir con transcript;
- cifras;
- importes, porcentajes y unidades;
- negaciones;
- persona/sujeto;
- tiempo/aspecto y marcadores temporales;
- causalidad/contraste;
- señal heurística de entidades/nombres.

Span inconsistente => `KEEP` + `guard_status=blocked`.

Política:

- repetición adyacente exactamente equivalente puede producir `PROPOSED_CUT`, nunca ejecutable;
- retake con material real/conflicto protegido => `REVIEW`;
- `explicit_correction` => siempre `REVIEW` en v1 y registra relación intento/corrección;
- no inferir equivalencias ni conversiones;
- no reparar silenciosamente candidates inválidos.

## 10. Fase 2C — Semantic Validation Foundation v1

Módulo/harness:

```text
Source/video_tunner/semantic_validation.py
```

Corpus:

```text
tests/fixtures/semantic_corpus_v1.json
```

Tests:

```text
tests/test_semantic_validation.py
```

### Métricas separadas

Medir siempre:

- candidate TP / FP / FN;
- precision / recall / F1;
- decision mismatches;
- unsafe proposals;
- missing safe proposals;
- executable decisions;
- auto-apply decisions.

Una FP que queda `REVIEW` es ruido; una `PROPOSED_CUT` incorrecta es fallo de seguridad. No mezclarlas.

### Corpus v1 actual

```text
22 casos
11 constructed_positive
6 constructed_negative
4 human_speech_reference
1 human_speech_positive
12 eventos esperados
```

Los 4 controles `human_speech_reference` reutilizan diálogos SpanishPod ya acreditados por `33656235038`; son negativos humanos.

El primer `human_speech_positive` procede de AMI Meeting Corpus ES2012d: un retake espontáneo manualmente transcrito. Su procedencia y URL quedan en `source_reference` del fixture. Se mantiene `REVIEW`.

El harness genera timings deterministas para aislar semántica de ASR; esos timings no son ground truth temporal ni prueban todavía audio AMI → Whisper → semántica.

### Baseline medido

`33742519997`:

```text
2 FP
0 FN
precision 84.62%
recall 100%
F1 91.67%
unsafe proposals 0
```

FP observados:

- reutilización legítima cercana de opener;
- `quiero decir` literal.

### Tuneos derivados del baseline

Conservador:

- retake: rechazar reutilización del opener separada por marcadores normales de continuación si no existe evidencia de reparación;
- registrar `repair_evidence`;
- `quiero decir` / `I mean` son ambiguos: no corrección al inicio ni en frames literales `lo que quiero decir` / `what I mean`; siguen disponibles tras intento previo.

### Validación ajustada

`33743029443`:

```text
64 tests PASS
21 casos
11 expected / 11 actual
0 FP
0 FN
precision 100%
recall 100%
F1 100%
unsafe proposals 0
decision mismatches 0
missing safe proposals 0
executable decisions 0
auto_apply decisions 0
artifacts 0
```

### Primer positivo humano

`33743638690`:

```text
65 tests PASS en 6.789 s
22 casos
12 expected / 12 actual
0 FP
0 FN
precision 100%
recall 100%
F1 100%
unsafe proposals 0
decision mismatches 0
missing safe proposals 0
executable decisions 0
auto_apply decisions 0
artifacts 0
```

El caso AMI se detecta como:

```text
possible_retake → REVIEW
guard_status = review
```

Gate v1:

```text
precision >= 0.95
recall >= 0.95
unsafe proposals == 0
decision mismatches == 0
missing safe proposals == 0
executable decisions == 0
auto_apply decisions == 0
```

No mover thresholds para acomodar fallos futuros. Ampliar corpus y corregir causas.

Ver `Validation/phase2c-semantic-validation.md`.

## 11. Pendiente dentro de Fase 2C

1. ampliar positivos humanos reales con retomas/reinicios/autocorrecciones;
2. incorporar la autocorrección humana AMI con `I mean` ya localizada como siguiente fixture;
3. buscar positivos humanos equivalentes en español con fuente/licencia adecuada;
4. ejecutar Whisper real sólo cuando aporte evidencia nueva;
5. medir con el mismo harness y conservar fallos visibles;
6. inferir scope `intento incorrecto → corrección válida`;
7. validar fillers contextuales;
8. añadir límites de frase y join safety;
9. mantener `executable=false` hasta evidencia suficiente.

Cualquier modelo semántico futuro debe estar bounded por candidates deterministas y guardas; local-first y fail-safe.

## 12. Edit Plan / render

Edit Plan sólo contiene ediciones efectivas aprobadas; nunca candidates o semantic decisions no ejecutables.

Renderer actual: merge overlaps, trim/atrim+concat, H.264/AAC, no overwrite, abort si elimina todo.

Pendiente: source hash, removedText definitivo del edit aprobado, join audit, edge fades, loudness y post-render verification.

## 13. Technology harvest

Video_Tunner NO es fork. Referencias principales: Railly/vcut, Cadence-Lab, ai-video-editor y SYSTRAN/faster-whisper. Ver `UPSTREAM_SOURCES.md`.

Antes de adoptar código: licencia + commit + motivo + validación propia.

## 14. GitHub / CI / Release

GitHub es source of truth.

- CI deliberada; no Actions como debugger;
- no polling frecuente;
- no modelos, vídeos, ZIPs o artifacts pesados ordinarios;
- Manual CI ligera = paquete base + NumPy + FFmpeg; no sustituye validaciones ML/portable;
- workflows manual-only normalmente;
- si el conector no puede `workflow_dispatch`, usar sólo mecanismo one-shot, restaurando inmediatamente `workflow_dispatch` y eliminando marker;
- no publicar GitHub Release sin autorización expresa de Guille.

## 15. Repo / docs

No versionar builds, modelos, vídeos, caches, outputs ni ZIPs.

Cambios relevantes => mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation.

## 16. Changelog técnico

- Bootstrap: CLI, tools, silence Cleaner, Edit Plan, render.
- Portable core/ML: PyInstaller onedir, tools/modelos locales, frozen/offline PASS.
- Sync: dual ingest, offset/drift, confidence/coverage, manual override, master FLAC alineado.
- Master analysis: mismo master para Whisper + VAD, provenance.
- Target Spanish: `large-v3-turbo`, WER 1.64%, RTF 0.4854.
- Semantic Candidates v1: repetitions/retakes/explicit corrections review-only.
- Semantic Decisions + Protection v1: schema v3, guardas deterministas, ninguna decision ejecutable.
- Semantic Validation Foundation v1: harness TP/FP/FN + safety, baseline medido, tuneo conservador guiado por 2 FP, corpus actual 22 casos con primer retake humano AMI positivo y 0 FP/0 FN/0 unsafe proposals; Fase 2C continúa abierta para ampliar evidencia humana.
