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
- authorization != render success.
- render complete != independent technical PASS != human perceptual PASS.

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
PATH fallback = forbidden in product
```

```text
34211660270  original gate — 14/14 focused, 418 integrated, portable/offline/tamper PASS
34219441077  post-persistence — 20/20 focused, 424 integrated, both doctors PASS
```

Runtime disponible != renderer autorizado.

### 3.6h — Denoise Plan Proposal + Explicit Execution Authorization — COMPLETADA COMO TECHNICAL FOUNDATION

Artifacts:

```text
denoise_plan_proposal            schema v1
denoise_execution_authorization  schema v1
```

El plan se liga a `noise_evidence_audit`, output SHA actual, selection review 3.6f, candidate/runtime exactos y fingerprints. `evidence_sufficient` sólo es measurement-coverage guard, nunca tratamiento necesario.

Un APPROVE válido sólo expresa permiso per-media para el renderer gated; el artifact no ejecuta tratamiento por sí mismo.

Cierre limpio:

```text
34225276990  45/45 focused + 452/452 integrated + doctor PASS
```

Estado real:

```text
real_user_authorization_record_created = false
real_user_media_authorized_for_denoise = false
product_default = preserve
auto_apply = false
```

Evidencia: `Validation/phase3-denoise-plan-authorization-foundation.json`.

### 3.6i — Gated Denoise Renderer Technical Foundation — COMPLETADA

Código: `Source/video_tunner/denoise_render.py`.

El renderer sólo avanza si revalida justo antes del tratamiento la cadena 3.6a→h, el source SHA actual, una autorización APPROVE vigente y el runtime DeepFilterNet exacto.

Contrato inicial:

1. source nunca se sobrescribe;
2. exactamente 1 video + 1 audio stream;
3. source audio mono; estéreo/multicanal se bloquea en esta foundation;
4. DeepFilter input PCM16 mono 48 kHz;
5. CLI materializada desde el plan validado: `--compensate-delay --output-dir <output_dir> <input_wav>`;
6. cualquier template CLI alterado o extendido falla cerrado;
7. `|raw duration delta| <= 0.05 s`;
8. sólo trim/pad de cola derecha; no alignment search/time shift/level matching;
9. video `stream copy` + audio AAC 192k; `-shortest` prohibido;
10. source SHA vuelve a comprobarse al final;
11. `denoise_render_complete` no declara technical PASS ni human PASS;
12. `preserve` sigue default y `auto_apply=false`.

Gate final `34231340544` / job `102077969922`:

```text
49/49 focused PASS
1/1 real DeepFilter synthetic E2E PASS
466/466 integrated PASS
0 skips
doctor PASS
```

Observación E2E sintética:

```text
input frames = 144000
raw output frames = 142560
raw frame delta = -1440
raw duration delta = -0.030 s
normalization = pad_right_tail_silence
final frames = 144000
alignment search = false
time shift = false
level matching = false
```

No convertir `-0.030 s` en threshold nuevo: el límite ya estaba precomprometido en 3.6g como ±0.05 s.

Estado real tras 3.6i:

```text
renderer technical foundation = PASS
real user authorization = none
real user media processed = none
real treated user media generated = none
stereo/multichannel generalized = false
independent post-render verifier = not implemented
product default = preserve
auto_apply = false
```

Evidencia: `Validation/phase3-denoise-render-foundation.json`.

### 3.6j — Independent Denoise Post-Render Technical Verifier — SIGUIENTE

Objetivo: verificar el derivado de denoise desde una capa independiente del renderer.

Precommit mínimo:

1. bind exacto a source, noise evidence, selection, plan, authorization y render result;
2. comprobar hashes actuales y detectar evidence stale/tampered;
3. no aceptar claims de PASS procedentes del renderer;
4. distinguir `INVALID_EVIDENCE` de `QUALITY_FAIL`;
5. comprobar media layout y duración/timeline del derivado;
6. verificar preservación esperada del vídeo para `stream copy`;
7. verificar output de audio válido y auditable;
8. revalidar la política temporal precomprometida;
9. technical PASS no crea human PASS;
10. ninguna media real se trata sin autorización explícita per-media vigente de Guille.

### 3.6k+ — Human denoise treatment closeout

Después del verifier técnico:

- preparar evidencia perceptual precomprometida;
- escucha humana antes de generalizar el tratamiento;
- un PASS técnico nunca sustituye al human perceptual gate.

### 3.7+ — Join treatment

Smoothing/crossfade continúa bloqueado hasta evidencia A/B perceptual específica frente al join directo ya validado.

## Fase 4 — UX mínima

Selección de vídeo/audio, sync, analizar, revisar, aprobar/rechazar, autorizar, renderizar y abrir outputs. Sólo después del cierre de Fase 3.

## Fase 5 — Portable Release Hardening

Build Windows limpio, ZIP final, digests, manifest, notices/licencias, estrategia final de modelos y validación zero-install/offline.

## Fase 6 — Extras

Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. ejecutar post-persistence final 3.6i con evidence binder y documentación ya sincronizada;
2. si pasa limpio, cerrar 3.6i sin mutar después la evidencia ligada;
3. diseñar e implementar 3.6j independent denoise post-render technical verifier;
4. no procesar media real sin autorización explícita per-media vigente de Guille;
5. mantener human denoise treatment closeout pendiente hasta evidencia perceptual específica;
6. mantener human normalization closeout pendiente;
7. mantener join smoothing bloqueado;
8. no publicar Release sin autorización expresa de Guille.
