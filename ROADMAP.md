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

`voicebank_demand_official_test_balanced_v1`: 40 pares noisy/clean, speakers p232/p257, cinco noise classes, cuatro SNR, 48 kHz, CC BY 4.0. Run `34142222451`.

### 3.6c — Objective noisy baseline — COMPLETADA

Run `34143456746`, 40/40 casos.

```text
mean SI-SDR = 9.16548156 dB
mean STOI   = 0.95070362
```

Descriptivo; sin acceptance thresholds ni ranking.

### 3.6d — Candidate objective comparison — COMPLETADA

Run `34145308485`. Candidatos: preserve, fixed AFFTDN y DeepFilterNet 0.5.6.

```text
DeepFilterNet mean SI-SDR delta = +9.87013412 dB
positive SI-SDR cases = 40/40
mean STOI delta = +0.01112968
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
34150832960  12/12 + 410/410 + doctor PASS
```

Selección != autorización.

### 3.6g — Immutable/offline portable DeepFilterNet runtime — COMPLETADA

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
34211660270  original gate
34219441077  post-persistence — 20/20 + 424 integrated + both doctors
```

Runtime disponible != renderer autorizado.

### 3.6h — Denoise Plan + Explicit Execution Authorization — COMPLETADA COMO TECHNICAL FOUNDATION

`denoise_plan_proposal` liga noise evidence, output SHA, selection 3.6f, candidate/runtime exactos y fingerprints. `evidence_sufficient` sólo es coverage guard.

Un APPROVE válido sólo expresa permiso per-media para el renderer gated; el artifact no ejecuta tratamiento por sí mismo.

```text
34225276990  45/45 focused + 452/452 integrated + doctor PASS
real_user_authorization_record_created = false
real_user_media_authorized_for_denoise = false
product_default = preserve
auto_apply = false
```

### 3.6i — Gated Denoise Renderer Technical Foundation — COMPLETADA

Código: `Source/video_tunner/denoise_render.py`.

Contrato:

1. revalidar 3.6a→h, source SHA, authorization y runtime inmediatamente antes de ejecutar;
2. source nunca se sobrescribe;
3. exactamente 1 video + 1 audio;
4. foundation inicial mono; estéreo/multicanal bloqueado;
5. DeepFilter PCM16 mono 48 kHz;
6. CLI desde plan validado con `--compensate-delay`;
7. `|raw duration delta| <= 0.05 s`;
8. sólo trim/pad de cola derecha, sin alignment search/time shift/level matching;
9. video stream-copy + audio AAC 192k; `-shortest` prohibido;
10. `denoise_render_complete` no declara technical/human PASS;
11. `preserve` default; `auto_apply=false`.

```text
34231340544  49/49 + 1/1 real DeepFilter E2E + 466/466, 0 skips + doctor
34240028080  post-persistence — 57/57 + 1/1 E2E + 474/474, 0 skips + doctor
```

Observación sintética: 144000 input frames, 142560 raw output, delta -0.03 s, pad de silencio en cola derecha, 144000 final frames.

### 3.6j — Independent Denoise Post-Render Technical Verifier — COMPLETADA COMO TECHNICAL FOUNDATION

Código: `Source/video_tunner/denoise_post_render_verification.py`.

Precommit: `Validation/phase3-denoise-post-render-verifier-precommit.json`.

El verifier independiente:

1. revalida cadena autorizada y SHA actuales;
2. exige SHA del `denoise_render_result`;
3. trata claims prematuros del renderer como evidencia inválida;
4. distingue `invalid_evidence` de `technical_denoise_fail`;
5. verifica 1 video + 1 audio en source/output;
6. compara SHA del vídeo decodificado source/output;
7. exige output AAC mono 48 kHz;
8. decodifica source/output independientemente a PCM16 mono 48 kHz y exige frame-count idéntico;
9. revalida timeline y límite ±0.05 s;
10. no añade thresholds SNR/STOI/SI-SDR/loudness;
11. technical PASS sigue requiriendo human perceptual review;
12. preserve sigue default y auto_apply=false.

Gate `34241518206`:

```text
63/63 focused PASS
1/1 real DeepFilter render → verifier E2E PASS
488/488 integrated PASS
0 skips
doctor PASS
```

E2E:

```text
status = technical_denoise_pass
blockers = []
decoded_video_equal = true
source_frames = 144000
output_frames = 144000
human_pass = false
```

No hubo media real de Guille, autorización real nueva ni human treatment closeout.

### 3.6k — Human Denoise Treatment Closeout — SIGUIENTE

Objetivo: cerrar perceptualmente el tratamiento concreto antes de generalizar denoise.

Precommit mínimo:

1. technical PASS 3.6j vigente como precondición;
2. corpus/casos/criterios humanos congelados antes de escuchar;
3. decisiones humanas explícitas y auditables;
4. un A/B histórico 3.6e no sustituye el closeout de un render concreto;
5. no atribuir human PASS a Guille sin escucha real;
6. no procesar media real sin authorization per-media explícita y vigente;
7. preserve default y auto_apply=false;
8. cualquier FAIL perceptual mantiene la generalización bloqueada.

### 3.7+ — Join treatment

Smoothing/crossfade continúa bloqueado hasta evidencia A/B perceptual específica frente al join directo ya validado.

## Fase 4 — UX mínima

Selección de vídeo/audio, sync, analizar, revisar, aprobar/rechazar, autorizar, renderizar y abrir outputs. Sólo después del cierre de Fase 3.

## Fase 5 — Portable Release Hardening

Build Windows limpio, ZIP final, digests, manifest, notices/licencias, estrategia final de modelos y validación zero-install/offline.

## Fase 6 — Extras

Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. cerrar 3.6j con binder/documentación y post-persistence final;
2. diseñar 3.6k human denoise treatment closeout sin atribuir escucha inexistente;
3. no procesar media real sin autorización explícita per-media vigente de Guille;
4. mantener human normalization closeout pendiente;
5. mantener join smoothing bloqueado;
6. no publicar Release sin autorización expresa de Guille.
