# Phase 2E.5 — Post-render Verification / Human Close-out

## Estado final

**Technical pre-human gate: PASS.**

**Human perceptual gate: PASS — 3/3.**

**Phase 2E close-out: `CLOSE_OUT_READY`.**

`auto_apply` permanece `false`. Este cierre no autoriza release ni sustituye las fases posteriores de calidad audiovisual, UX o release hardening.

## Corpus bloqueado antes de escuchar

Fixture: `tests/fixtures/phase2e_human_render_closeout_ami_v1.json`.

Reglas precomprometidas:

```text
minimum_rendered_human_cases = 3
minimum_distinct_audio_sources = 2
required_technical_pass_fraction = 1.0
required_human_perceptual_pass_fraction = 1.0
maximum_safety_violations = 0
all pass -> CLOSE_OUT_READY
any human fail -> INSUFFICIENT_JOIN_QUALITY
```

| Caso | Fuente | Reparandum humano | Técnico | Humano |
|---|---|---|---|---|
| `ami-es2002b-d-repeat-157` | `ES2002b-D` | `what you've just told me` | PASS — `acoustic_context_only` | PASS |
| `ami-ts3005d-c-repeat-298` | `TS3005d-C` | `And then you can` | PASS — `acoustic_context_only` | PASS |
| `ami-es2002b-d-repeat-13` | `ES2002b-D` | `a lot of` | PASS — `low_energy_boundary_context` | PASS |

Dos fuentes de audio distintas; selección y thresholds quedaron fijados antes de la escucha.

## Estrategia ASR validada para este gate

```text
deterministic_overlap_12s_3s_repeat_consensus_v1
```

`single_pass` continúa siendo el default del producto. `12s/3s` es un opt-in explícito validado para esta ruta.

## Provenance inmutable

Modelo:

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

## Run técnico final

```text
workflow: Phase 2E Human Render Closeout
run: 34119952855
result: SUCCESS
regression suite: 278 tests PASS; 13 host-only skips
portable analysis build: PASS
immutable FFmpeg provenance: PASS
3/3 semantic renders: PASS
3/3 post-render technical verification: PASS
```

Cadena validada:

```text
locked corpus
-> pinned AMI source + model + FFmpeg
-> analyze with explicit 12s/3s consensus
-> promotion approval
-> bounded proposal
-> global validation-only authorization
-> Semantic Edit Plan
-> semantic render gate
-> FFmpeg
-> post-render technical verification
-> human listening
-> human_render_review x3
-> phase2e_closeout_decision
```

## Resultado técnico por caso

### 157

```text
semantic edit: 19.86 -> 20.82
removed: 0.96 s
output duration: 39.96 s
join status: acoustic_context_only
technical report SHA256: 2891cbcc2024b434020d3e77b28c0982a14f1db6828643a657a5b5d8bd4bab39
rendered output SHA256: f7577fd3c52d1b18e5a0ae7c6e8dc6500e057632c8ac89111efc00f8a5cb363c
plan fingerprint: e0e1bd72619ecc811b007bce72d51e24e504df7768719f0d13f354fe3280e035
```

### 298

```text
semantic edit: 19.90 -> 20.72
removed: 0.82 s
output duration: 40.62 s
join status: acoustic_context_only
technical report SHA256: 99c45c1a6519838e6b19fb6833ec7b78c226e482a640830609e50802d7f411dc
rendered output SHA256: c64166879d2bae49191e9018b02123c99d05cff4564a4b9838435e6de338bfb6
plan fingerprint: 25595607a0cf8697e6d4f959e532070c6ef50acaa8bba7f0af1fd10b87172635
```

### 13

```text
semantic edit: 20.00 -> 20.40
removed: 0.40 s
output duration: 40.06 s
join status: low_energy_boundary_context
technical report SHA256: a548f397c7968235a9a3ddb7bd3e6af1d6025286c390be9c34de9e168b74715c
rendered output SHA256: 2190f507b30a135e6d1799cb54218f4a1be8d62c0aed816d07e6737e35a66b5b
plan fingerprint: ab56912a7bdd3c908450650c565dcd24543bcd80d69f16f0342582fd0637ea70
```

## Listening artifact

```text
artifact name: phase2e-human-render-review-bundle
artifact id: 10018184287
artifact SHA256 digest: 9fb84b32b12e6ae74b4260eb116f10dde5e7238992f393fb4e922525bc9dfb70
```

El artifact de Actions es temporal; la evidencia ligera permanente está en `Validation/phase2e-human-closeout/`.

## Evidencia humana final

El revisor humano dio OK explícito a las tres comparaciones focalizadas ORIGINAL/RENDERED. El finalizador registra ese juicio sin añadir observaciones perceptuales no declaradas.

Resultado agregado:

```text
required_cases: 3
evaluated_cases: 3
required_sources: 2
distinct_sources: 2
valid_review_count: 3
human_perceptual_pass_count: 3
human_perceptual_fail_count: 0
invalid_or_stale_review_count: 0
status: CLOSE_OUT_READY
phase2e_closeout_ready: true
auto_apply: false
```

Finalization hashes:

```text
source bundle manifest SHA256  d0b12929ede07c1c5a56b074008d0903a868a7cf61e5ce10801c2b682f164ed0
human decisions SHA256         867a33c87ec2154d08558a67d503535d4527cb99af07ac65458507fe73288e04
review 157 SHA256              dc1215715c493849ab8e458ef78b01a06b0c2f5c314521923862eeae3757ba46
review 298 SHA256              4bf78d934c039aac329a7bd96a1752ac5545ee59ec4a536fea55e6fa1163d02e
review 13 SHA256               3234bf79509bec6920a347912014deae5ea77c96043721d9d5f5299d56aad74d
closeout decision SHA256       2cc5ae013cdcbfc53efc376d5db4f2f2f53d5a8848c019820dee6899b88c188a
```

## Incidente de harness previo

Run `34118999640` fue un fallo de plumbing del harness, no un fallo de join. El host verifier heredó `VIDEO_TUNNER_PORTABLE_STRICT=1` y resolvió `ffprobe` contra el runtime equivocado. La corrección quedó limitada al helper host; no se cambió `Source/video_tunner/tools.py` ni el comportamiento portable strict del producto. Focused Windows preflight `34119810244` PASS; run corregido `34119952855` SUCCESS.

## Decisión

```text
Phase 2E.5 technical gate = PASS
Phase 2E.5 human perceptual gate = PASS
Phase 2E = CLOSE_OUT_READY
Release = NOT AUTHORIZED
Auto-apply = false
```

El siguiente bloque planificado es **Fase 3 — calidad audiovisual / auditoría**.
