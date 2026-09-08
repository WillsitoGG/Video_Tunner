# ROADMAP — Video_Tunner

## Principios

- Windows 10/11 x64 portable: ZIP → descomprimir → ejecutar.
- Vídeo con audio embebido o vídeo + audio externo.
- Master audio/sync antes de transcripción, VAD y decisiones temporales.
- Originales intactos; derivados auditables y reversibles.
- Ante baja confianza: KEEP/REVIEW/manual; no adivinar.
- CI pesada sólo cuando aporta evidencia nueva; gates pesados manual-only.
- `preserve` audiovisual por defecto.
- `auto_apply=false`.
- `measurement != decision != authorization`.
- candidate evaluation != candidate selection != execution authorization.
- plan proposal != execution authorization.

## Fases 0–2 — COMPLETADAS

Fases 0–1C: bootstrap, harvest, portable foundation, ingesta dual/sync y transcripción/VAD.

Fases 2A–2D: semantic candidates/protection/validation, correction scope, fillers, join safety, acoustic join y eligibility. 2D cerrada como foundation/evidence.

Fase 2E: promotion → individual approval → bounded proposal → global execution authorization → semantic Edit Plan → gated FFmpeg render → technical verification → human review → closeout.

```text
34119952855  3/3 real AMI technical PASS / 2 sources
human review 3/3 perceptual PASS / 0 FAIL
status = CLOSE_OUT_READY
34124101770  275/275 + doctor PASS
```

## Fase 3 — Calidad audiovisual — EN CURSO

### 3.1–3.5d — Quality + normalization technical foundation — COMPLETADA TÉCNICAMENTE

Incluye Audiovisual Quality Audit, bypass-first Treatment Decision, EBU R128 profile review-only, explicit normalization approval, linear plan, execution authorization, gated linear renderer e independent post-render verification.

```text
34124957783  3.1 quality audit — 8/8 + real FFmpeg E2E
34125110506  regression — 283/283 + doctor
34134893725  focal baseline — 3 human-passed joins / 2 sources
34136124997  3.4 approval — 15/15
34136621557  3.5a plan — 15/15
34138226442  3.5b authorization — 15/15
34139056626  3.5c real linear render — 25/25
34139502187  3.5d independent verify — 16/16
34139639280  regression through 3.5d — 337/337 + doctor
```

Estado:

```text
normalization technical foundation = PASS
human perceptual normalization closeout = PENDING
product default = preserve
auto_apply = false
```

### 3.6a — Noise Evidence Audit — COMPLETADA

Measurement-only. La suficiencia sólo acredita cobertura para medir; ningún dBFS activa tratamiento.

```text
34141013261  9/9 + real MP4/AAC E2E
34141115293  346/346 + doctor
```

### 3.6b — Frozen denoise evaluation corpus — COMPLETADA

`voicebank_demand_official_test_balanced_v1`:

```text
40 pares noisy/clean
2 speakers: p232, p257
5 noise classes: bus, cafe, living, office, psquare
4 SNRs: 17.5, 12.5, 7.5, 2.5 dB
48 kHz
CC BY 4.0
```

Run `34142222451`.

### 3.6c — Objective noisy baseline — COMPLETADA

Run `34143456746`, 40/40 casos.

```text
mean SI-SDR = 9.16548156 dB
mean STOI   = 0.95070362
```

Descriptivo; sin acceptance thresholds ni ranking.

### 3.6d — Candidate objective comparison — COMPLETADA

Run `34145308485`.

Candidatos: preserve, fixed AFFTDN y DeepFilterNet 0.5.6.

DeepFilterNet observado:

```text
mean SI-SDR delta vs preserve = +9.87013412 dB
positive SI-SDR cases = 40/40
mean STOI delta vs preserve = +0.01112968
positive STOI cases = 27/40
raw duration delta = -0.03 s
clean-control STOI mean = 0.99542798
clean-control NRMSE mean = 0.03238068
numeric clean-control threshold = none
```

La evidencia objetiva no seleccionó ni autorizó tratamiento por sí sola.

### 3.6e — Blinded Human A/B — COMPLETADA

Guille completó la escucha ciega precomprometida.

```text
DeepFilterNet: treatment 10 / preserve 0 / no preference 0 / gate PASS
AFFTDN:        treatment  3 / preserve 2 / no preference 5 / gate FAIL
speech integrity failures = 0
artifact failures = 0
```

```text
34148410617  listening bundle
34150202283  398/398 + doctor PASS
```

### 3.6f — Denoiser Selection Review — COMPLETADA

```text
selected_candidate_id = deepfilternet_0_5_6_compensated_v1
selection_status = SELECTED_FOR_INTEGRATION_REVIEW
```

```text
34150663772  selection artifact
34150832960  12/12 + 410/410 + doctor PASS
```

Selección != autorización.

### 3.6g — Immutable/offline portable DeepFilterNet runtime — COMPLETADA

Contrato:

```text
DeepFilterNet 0.5.6
Tools/deepfilter/bin/deep-filter.exe
SHA-256 75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915
size 26912256 bytes
CLI --compensate-delay --output-dir <output_dir> <input_wav>
runtime download = forbidden
PATH fallback = forbidden
```

```text
34211660270  original gate — 14/14 focused, 418 integrated, portable/offline/tamper PASS
34219441077  post-persistence — 20/20 focused, 424 integrated, both doctors PASS
```

Runtime disponible != renderer autorizado.

### 3.6h — Denoise Plan Proposal + Explicit Execution Authorization — COMPLETADA COMO TECHNICAL FOUNDATION

Código:

```text
Source/video_tunner/denoise_plan.py
Source/video_tunner/denoise_execution_authorization.py
```

Artifacts:

```text
denoise_plan_proposal            schema v1
denoise_execution_authorization  schema v1
```

El plan se liga de forma exacta a:

- `noise_evidence_audit` + fingerprint completo;
- output SHA actual y quality binding;
- selection review 3.6f + fingerprint;
- candidate `deepfilternet_0_5_6_compensated_v1`;
- runtime contract 3.6g + fingerprint;
- asset/ruta/CLI exactos;
- `--compensate-delay`;
- tolerancia temporal raw `0.05 s`.

`evidence_sufficient` sólo actúa como **measurement-coverage guard**. No significa que un vídeo necesite denoise. Cobertura insuficiente bloquea el plan.

Plan ready:

```text
parameters_defined = true
parameters_executable = false
denoise_authorized = false
denoise_render_authorization = false
plan_render_authorization = false
renderer_available = false
executable = false
auto_apply = false
```

La autorización es un artifact separado `APPROVE`/`REJECT` con actor + reason y revalidación stale/tamper-safe. Un APPROVE válido sólo puede expresar permiso para un **futuro gated renderer**; el propio artifact sigue no ejecutable.

```text
authorized = true
denoise_render_authorization = true
plan_render_authorization = false
parameters_executable = false
renderer_available = false
executable = false
auto_apply = false
```

Gate inicial:

```text
34220351609  38/38 focused + 445/445 integrated + doctor PASS
```

Importante: los APPROVE del gate usan fixtures sintéticos (`Test Reviewer`). En 3.6h:

```text
real_user_authorization_record_created = false
real_user_media_authorized_for_denoise = false
denoise_renderer_implemented = false
treated_media_generated = false
product_default = preserve
auto_apply = false
```

Evidencia: `Validation/phase3-denoise-plan-authorization-foundation.json`.

### 3.6i — Gated Denoise Renderer Technical Foundation — SIGUIENTE

Objetivo: implementar un renderer derivado que **sólo** pueda ejecutar DeepFilterNet si recibe una `denoise_execution_authorization` APPROVE válida y revalidada inmediatamente antes del tratamiento.

Precommit mínimo:

1. revalidar plan, authorization, output/source SHA, selection 3.6f y runtime 3.6g;
2. verificar binario DeepFilterNet exacto justo antes de usarlo;
3. no runtime download ni PATH fallback;
4. nunca overwrite del source;
5. contrato DeepFilter input/output: mono PCM16, 48 kHz;
6. `--compensate-delay` obligatorio;
7. `|raw duration delta| ≤ 0.05 s`, fail-closed;
8. derivado auditable y hashes registrados;
9. no autodeclarar technical/human PASS en el render result;
10. tests pueden usar authorization sintética, pero eso no autoriza media real de Guille;
11. `preserve` sigue default y `auto_apply=false`.

### 3.6j+ — Independent verification + human treatment closeout

Después del renderer técnico:

- verificación técnica independiente del derivado;
- human perceptual closeout antes de generalizar el tratamiento;
- ningún PASS técnico sustituye escucha humana cuando ésta sea requisito del closeout.

### 3.7+ — Join treatment

Smoothing/crossfade continúa bloqueado hasta evidencia A/B perceptual específica frente al join directo ya validado.

## Fase 4 — UX mínima

Selección de vídeo/audio, sync, analizar, revisar, aprobar/rechazar, autorizar, renderizar y abrir outputs. Sólo después del cierre de Fase 3.

## Fase 5 — Portable Release Hardening

Build Windows limpio, ZIP final, digests, manifest, notices/licencias, estrategia final de modelos y validación zero-install/offline.

## Fase 6 — Extras

Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. ejecutar post-persistence gate 3.6h con binder permanente;
2. cerrar 3.6h sin mutar la evidencia ligada después del gate final;
3. diseñar e implementar 3.6i gated denoise renderer technical foundation;
4. mantener human closeout de normalización pendiente;
5. mantener join smoothing bloqueado;
6. no publicar Release sin autorización expresa de Guille.
