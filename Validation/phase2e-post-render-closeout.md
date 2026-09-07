# Phase 2E.5 — Post-render Verification / Human Close-out

## Estado

**Technical pre-human gate: PASS.**

**Human perceptual gate: PENDING.**

**Phase 2E close-out: NOT YET READY.**

Esta evidencia acredita que el corpus precomprometido de tres repeticiones humanas AMI llega de extremo a extremo desde análisis hasta render y supera la verificación técnica post-render. No sustituye la escucha humana final y no autoriza release ni `auto_apply`.

## Corpus bloqueado antes de escuchar

Fixture: `tests/fixtures/phase2e_human_render_closeout_ami_v1.json`.

Reglas de cierre precomprometidas:

```text
minimum_rendered_human_cases = 3
minimum_distinct_audio_sources = 2
required_technical_pass_fraction = 1.0
required_human_perceptual_pass_fraction = 1.0
maximum_safety_violations = 0
all pass -> CLOSE_OUT_READY
any human fail -> INSUFFICIENT_JOIN_QUALITY
```

Casos:

| Caso | Fuente | Reparandum humano | Estado técnico post-render |
|---|---|---|---|
| `ami-es2002b-d-repeat-157` | `ES2002b-D` | `what you've just told me` | PASS — `acoustic_context_only` |
| `ami-ts3005d-c-repeat-298` | `TS3005d-C` | `And then you can` | PASS — `acoustic_context_only` |
| `ami-es2002b-d-repeat-13` | `ES2002b-D` | `a lot of` | PASS — `low_energy_boundary_context` |

Dos fuentes de audio distintas; selección bloqueada antes de la evidencia perceptual 2E.5.

## Estrategia ASR validada para este gate

La ejecución selecciona explícitamente:

```text
deterministic_overlap_12s_3s_repeat_consensus_v1
```

`single_pass` continúa siendo el default del producto. `12s/3s` es un opt-in explícito validado para esta ruta; no se amplía implícitamente a estrategias no validadas.

## Provenance inmutable

Modelo de validación:

```text
repo: rtlingo/mobiuslabsgmbh-faster-whisper-large-v3-turbo
revision: 6bd64462dd562f8062828f585c3709aa52df0083
model.bin SHA256: E76620F83D5F5B69EFD3D87E3DC180C1BD21DF9FBEBACFD4335E5E1EFCC018DA
```

FFmpeg portable:

```text
version token: n9.0.1-26-g5c8e7e2433
archive SHA256: a8ebbaf7a99185f5abc3a2d3a657521c38d7966f06b70468d7ab29a67fe8654f
```

La verificación de provenance del portable pasó antes de renderizar.

## Run técnico final

GitHub Actions:

```text
Phase 2E Human Render Closeout
run: 34119952855
job: 101735484118
result: SUCCESS
regression suite: 278 tests PASS; 13 skipped por dependencias FFmpeg no expuestas al Python host de tests
```

Secuencia superada:

```text
preflight contracts
-> locked corpus
-> licensed speaker-specific AMI sources
-> pinned model
-> analysis portable build
-> immutable FFmpeg provenance
-> current regression suite
-> analyze with explicit 12s/3s consensus
-> benchmark promotion approval
-> bounded proposal
-> global validation-only authorization
-> Semantic Edit Plan
-> gated FFmpeg render
-> post-render technical verification
-> lightweight listening bundle
```

## Resultado por caso

### 157

```text
case: ami-es2002b-d-repeat-157
source duration: 40.90 s
semantic edit: 19.86 -> 20.82
removed: 0.96 s
proposal removed fraction: 0.023471883
output duration: 39.96 s
streams: 1 video + 1 audio
join: 19.86 s output timeline
join status: acoustic_context_only
technical report SHA256: 2891cbcc2024b434020d3e77b28c0982a14f1db6828643a657a5b5d8bd4bab39
rendered output SHA256: f7577fd3c52d1b18e5a0ae7c6e8dc6500e057632c8ac89111efc00f8a5cb363c
plan fingerprint: e0e1bd72619ecc811b007bce72d51e24e504df7768719f0d13f354fe3280e035
technical_pass: true
```

### 298

```text
case: ami-ts3005d-c-repeat-298
source duration: 41.42 s
semantic edit: 19.90 -> 20.72
removed: 0.82 s
proposal removed fraction: 0.019797199
output duration: 40.62 s
streams: 1 video + 1 audio
join: 19.90 s output timeline
join status: acoustic_context_only
technical report SHA256: 99c45c1a6519838e6b19fb6833ec7b78c226e482a640830609e50802d7f411dc
rendered output SHA256: c64166879d2bae49191e9018b02123c99d05cff4564a4b9838435e6de338bfb6
plan fingerprint: 25595607a0cf8697e6d4f959e532070c6ef50acaa8bba7f0af1fd10b87172635
technical_pass: true
```

### 13

```text
case: ami-es2002b-d-repeat-13
source duration: 40.46 s
semantic edit: 20.00 -> 20.40
removed: 0.40 s
proposal removed fraction: 0.009886307
output duration: 40.06 s
streams: 1 video + 1 audio
join: 20.00 s output timeline
join status: low_energy_boundary_context
technical report SHA256: a548f397c7968235a9a3ddb7bd3e6af1d6025286c390be9c34de9e168b74715c
rendered output SHA256: 2190f507b30a135e6d1799cb54218f4a1be8d62c0aed816d07e6737e35a66b5b
plan fingerprint: ab56912a7bdd3c908450650c565dcd24543bcd80d69f16f0342582fd0637ea70
technical_pass: true
```

Aggregate del run:

```text
PHASE2E_HUMAN_RENDER_PRE_HUMAN_GATE=PASS
PHASE2E_HUMAN_RENDER_CASES=3
PHASE2E_HUMAN_RENDER_SOURCES=2
PHASE2E_HUMAN_RENDER_TECHNICAL_PASS=3
PHASE2E_HUMAN_PERCEPTUAL_PENDING=3
PHASE2E_CLOSE_OUT_DECISION=PENDING_HUMAN_LISTENING
```

## Listening artifact

El run publicó únicamente audio corto de revisión y evidencia JSON ligera; no publicó fuentes AMI completas, modelo ni portable.

```text
artifact name: phase2e-human-render-review-bundle
artifact id: 10018184287
artifact SHA256 digest: 9fb84b32b12e6ae74b4260eb116f10dde5e7238992f393fb4e922525bc9dfb70
```

La conservación de GitHub Actions es temporal; el estado auditable permanente se basa en los hashes/provenance de esta página y, tras la escucha, en las reviews humanas y decisión de corpus generadas por el finalizador offline.

## Verificación técnica v1

Cada caso debe mantener simultáneamente:

- cadena semántica y authorization provenance válida;
- original sin modificación;
- output distinto del original;
- duración coherente con el Semantic Edit Plan dentro de la tolerancia precomprometida;
- un stream de vídeo y uno de audio;
- auditoría acústica de cada join con estado técnico permitido;
- `auto_apply = false`.

Los tres casos cumplen este gate.

## Incidente de harness previo

Run `34118999640` no constituye evidencia de fallo de join. El caso 157 llegó a renderizar MP4, pero el Python host encargado de la verificación heredó `VIDEO_TUNNER_PORTABLE_STRICT=1` y resolvió `ffprobe` contra el runtime del repositorio en lugar del directorio FFmpeg del portable construido.

Corrección:

- no se cambió `Source/video_tunner/tools.py`;
- el comportamiento portable strict del producto permanece intacto;
- el helper host valida que la carpeta explícita contiene `ffmpeg` y `ffprobe`, desactiva strict únicamente dentro de ese proceso host y usa esa carpeta ya validada;
- focused Windows preflight `34119810244`: PASS;
- run corregido `34119952855`: SUCCESS completo.

Por tanto el incidente se clasifica como **validation-harness plumbing**, no como defecto perceptual ni técnico del join.

## Human gate pendiente

Cada ORIGINAL/RENDERED debe escucharse realmente por Guille. Un PASS requiere que la comparación no revele:

- click/pop audible;
- fonema o palabra recortados;
- salto antinatural de timing/ritmo;
- pérdida de significado causada por el join.

La decisión humana se registra mediante `human_render_review` con SHA del technical report, SHA del output, plan fingerprint y `join_id`. El corpus sólo puede producir `CLOSE_OUT_READY` con tres reviews humanas válidas PASS en las dos fuentes.

Un único FAIL produce `INSUFFICIENT_JOIN_QUALITY`. Evidencia alterada/stale produce `INVALID_EVIDENCE`. No se relajan thresholds post hoc.

## Ruta de finalización

`.github/scripts/finalize_phase2e_human_closeout.py` consume exclusivamente:

1. el bundle técnico inmutable;
2. un JSON de decisiones humanas explícitas con actor, razón y decisión/reason por join.

Vuelve a comprobar el SHA de cada technical report contra el manifest, materializa las tres reviews y ejecuta `build_phase2e_closeout_decision`. No analiza audio, no ejecuta Whisper, no renderiza y no puede inventar el juicio humano.

Hasta que esa evidencia humana exista:

```text
Phase 2E.5 technical pre-human gate = PASS
Phase 2E.5 human perceptual gate = PENDING
Phase 2E = OPEN
Release = NOT AUTHORIZED
```
