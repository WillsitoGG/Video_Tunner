# Validation

Esta carpeta conserva únicamente evidencia técnica y humana ligera, reproducible y auditable: hashes, provenance, decisiones y resúmenes de validación.

No usarla para almacenar vídeos, ZIPs de CI, logs voluminosos, modelos ni outputs temporales.

## Evidencia principal vigente

### Portable / ingest / analysis

- `portable-foundation-spike.md` — portable core.
- `portable-analysis-spike.md` — portable ML/análisis.
- `sync-foundation-spike.md` / `sync-hardening.md` — ingesta dual y sync.
- `spanish-large-v3-turbo-plan.md` — target Spanish.

### Fase 2

- `phase2-semantic-candidates.md` — Semantic Candidates v1.
- `phase2-semantic-protection.md` — Semantic Decisions + Protection v1.
- `phase2d-*` — Fase 2D correction scope, fillers, join/acoustic/eligibility y closeout humano.
- `phase2e-*` + `phase2e-human-closeout/` — Fase 2E promotion→approval→authorization→render→technical/human closeout.

Fase 2E está cerrada como `CLOSE_OUT_READY`; `auto_apply=false`.

### Fase 3 — audiovisual quality / audit

Foundation general:

- `phase3-audiovisual-quality-foundation.md` — 3.1 Quality Audit, focal baseline, 3.2 Treatment Decision y 3.3 Normalization Profile Contract.
- `phase3-focal-quality-baseline.json` — tres pares ORIGINAL/RENDERED ya escuchados en 2E.5.
- `phase3-normalization-foundation.md` — 3.4–3.5d normalization technical foundation.
- `phase3-noise-audit-foundation.md` — 3.6a Noise Evidence Audit measurement-only.

Denoise 3.6b–j:

- `phase3-denoise-corpus-materialization.json` — 40 pares VoiceBank+DEMAND frozen/materialized.
- `phase3-denoise-objective-baseline.json` — baseline SI-SDR/STOI 40/40.
- `phase3-denoiser-candidate-objective-comparison.json` — preserve/AFFTDN/DeepFilterNet + clean controls.
- `phase3-denoiser-human-ab-bundle-technical.json` — manifest del bundle ciego.
- `phase3-denoiser-human-ab-public-review.json` — review cegado de Guille.
- `phase3-denoiser-human-ab-review.json` — review remapeado/unblinded.
- `phase3-denoiser-human-perceptual-gate.json` / `phase3-denoiser-human-perceptual-closeout.json` — 3.6e.
- `phase3-denoiser-selection-review.json` / `phase3-denoiser-selection-closeout.json` — 3.6f.
- `phase3-denoiser-portable-runtime.json` — 3.6g runtime DeepFilterNet inmutable/offline.
- `phase3-denoise-plan-authorization-foundation.json` — 3.6h plan + authorization foundation.
- `phase3-denoise-render-foundation.json` — 3.6i gated `denoise_render_result` foundation.
- `phase3-denoise-post-render-verifier-precommit.json` — criterios 3.6j congelados antes de implementación/resultados.
- `phase3-denoise-post-render-verifier-foundation.json` — 3.6j independent post-render verifier technical foundation.
- `phase3-denoise-post-render-verifier-closeout.json` — cierre post-persistencia 3.6j, separado del artifact base y ligado al gate final.

## Runs principales

```text
34124957783  Phase 3.1 focused + real FFmpeg E2E — 8/8 PASS
34125110506  Phase 3.1 full regression — 283/283 + doctor PASS
34134893725  focal baseline exact 2E.5 bundle — PASS
34139639280  full regression through 3.5d — 337/337 + doctor PASS
34141013261  Phase 3.6a noise audit — 9/9 + real MP4/AAC E2E PASS
34141115293  full regression through 3.6a — 346/346 + doctor PASS
34142222451  Phase 3.6b corpus materialization — 40 paired cases PASS
34143456746  Phase 3.6c objective noisy baseline — 40/40 measured
34145308485  Phase 3.6d candidate objective comparison — PASS
34148410617  Phase 3.6e blinded A/B bundle — PASS
34150202283  Phase 3.6e closeout — 398/398 + doctor PASS
34150832960  Phase 3.6f final selection — 12/12 + 410/410 + doctor PASS
34211660270  Phase 3.6g portable runtime — PASS
34219441077  Phase 3.6g post-persistence — 20/20 + 424 integrated + both doctors PASS
34225276990  Phase 3.6h clean closeout — 45/45 + 452/452 + doctor PASS
34231340544  Phase 3.6i base renderer — 49/49 + 1/1 DeepFilter E2E + 466/466, 0 skips + doctor PASS
34240028080  Phase 3.6i post-persistence — 57/57 + 1/1 E2E + 474/474, 0 skips + doctor PASS
34241148527  Phase 3.6j preflight — 63/63 PASS
34241518206  Phase 3.6j foundation — 63/63 + 1/1 real render→verifier E2E + 488/488, 0 skips + doctor PASS
34336304799  Phase 3.6j persisted binder preflight — 21/21 PASS
34336891424  Phase 3.6 evidence binder sweep — 65/65 PASS
34337071421  Phase 3.6j post-persistence final — 71/71 + 1/1 real render→verifier E2E + 496/496, 0 skips + doctor PASS
```

## Denoise — interpretación acreditada

### 3.6b–f

Corpus `voicebank_demand_official_test_balanced_v1`: 40 paired noisy/clean, p232/p257, cinco ruidos, cuatro SNRs, 48 kHz, CC BY 4.0.

Baseline descriptivo:

```text
mean noisy SI-SDR = 9.16548156 dB
mean noisy STOI   = 0.95070362
```

DeepFilterNet observado:

```text
mean SI-SDR delta vs preserve = +9.87013412 dB
positive SI-SDR = 40/40
mean STOI delta = +0.01112968
positive STOI = 27/40
raw duration delta = -0.03 s
clean-control STOI mean = 0.99542798
clean-control NRMSE mean = 0.03238068
```

Estas métricas son auxiliares y no autorizan tratamiento.

Guille completó el A/B ciego 3.6e:

```text
DeepFilterNet treatment preference = 10/10
preserve preference = 0
no preference = 0
speech integrity failures = 0
artifact failures = 0
perceptual gate = PASS
```

3.6f seleccionó `deepfilternet_0_5_6_compensated_v1` para integration review. Selección != autorización.

### 3.6g — runtime portable

```text
DeepFilterNet = 0.5.6
runtime = Tools/deepfilter/bin/deep-filter.exe
SHA-256 = 75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915
size = 26912256 bytes
runtime_download_allowed = false
product_default = preserve
auto_apply = false
```

Runtime disponible != renderer autorizado.

### 3.6h — plan + authorization

`denoise_plan_proposal` y `denoise_execution_authorization`, ambos schema v1. Cobertura suficiente sólo significa evidencia suficiente para preparar parámetros; no “denoise necesario”. Los APPROVE de foundation son fixtures sintéticos. Guille no emitió autorización real per-media en 3.6h.

### 3.6i — gated renderer

`denoise_render_result` schema v1.

```text
source overwrite = forbidden
source layout = 1 video + 1 audio
initial audio support = mono
DeepFilter input = PCM16 mono 48 kHz
CLI from validated plan template
--compensate-delay required
raw duration delta limit = ±0.05 s
alignment/time-shift/level-match = forbidden
right-tail trim or digital-silence pad only
video = stream copy
audio = AAC 192k
-shortest = forbidden
render complete != technical PASS
render complete != human PASS
preserve = default
auto_apply = false
```

E2E 3.6i observado: 144000 input frames → 142560 raw output (`-0.03 s`) → `pad_right_tail_silence` → 144000 final frames. `-0.03 s` no es threshold nuevo.

### 3.6j — independent post-render verifier

El contrato se congeló en `phase3-denoise-post-render-verifier-precommit.json` antes de implementar y antes de observar el E2E.

Artifact de producto:

```text
denoise_post_render_verification schema v1
```

El verifier:

```text
revalidate current authorized chain = required
render_result SHA/current source SHA/current output SHA = required
renderer self technical/human PASS = invalid evidence
source/output same path = invalid evidence
source/output layout = exactly 1 video + 1 audio
decoded video SHA source == output
output audio = AAC mono 48 kHz
independent source/output decode = PCM16 mono 48 kHz
independent frame counts must match
reported timeline must be internally consistent
raw duration delta limit = ±0.05 s
alignment search = false
time shift = false
level matching = false
SNR/STOI/SI-SDR/loudness thresholds added = none
technical PASS != human PASS
```

Gate base `34241518206`:

```text
63/63 focused PASS
1/1 real DeepFilter render + independent verifier E2E PASS
488/488 integrated PASS
0 skips
doctor PASS
```

Cierre post-persistencia `34337071421`:

```text
71/71 focused PASS
1/1 real DeepFilter render + independent verifier E2E PASS
496/496 integrated PASS
0 skips
doctor PASS
scope PASS
```

E2E post-persistencia:

```text
status = technical_denoise_pass
technical_pass = true
blockers = []
decoded_video_equal = true
source_frames = 144000
output_frames = 144000
human_pass = false
```

Estado real persistido tras el cierre 3.6j:

```text
independent_denoise_post_render_verifier_technical_foundation_closed = true
real_user_authorization_record_created = false
real_user_media_authorized_for_denoise = false
real_user_media_processed_by_denoise_renderer = false
real_user_treated_media_generated = false
human_denoise_treatment_closeout = false
stereo_or_multichannel_generalized = false
product_default = preserve
auto_apply = false
```

Binder: `tests/test_phase3_denoise_post_render_verifier_evidence.py`.
Permanent gate: `.github/workflows/phase3-denoise-post-render-verifier.yml`, manual-only.
Closeout: `Validation/phase3-denoise-post-render-verifier-closeout.json`.

## Regla de interpretación

Una validación PASS acredita únicamente el alcance descrito en su documento. No implica por sí sola:

- release publicable;
- generalización fuera del corpus/contrato;
- que una observación se convierta en threshold;
- que measurement autorice treatment;
- que selección autorice ejecución;
- que runtime disponible autorice renderer;
- que autorización contractual equivalga a autorización real emitida por Guille;
- que render complete equivalga a technical PASS;
- que technical denoise PASS equivalga a human perceptual PASS;
- que el A/B 3.6e sustituya el human closeout de un render concreto;
- denoise o smoothing automáticos;
- validación final del ZIP portable en Windows limpio.

Cadena actual:

```text
noise_evidence_audit
→ frozen denoise corpus
→ objective baseline/comparison
→ blinded human A/B
→ candidate selection review
→ portable selected-runtime contract
→ denoise_plan_proposal
→ denoise_execution_authorization
→ gated denoise renderer technical foundation
→ independent denoise post-render technical verifier foundation [3.6j CLOSED]
→ human denoise treatment closeout (NEXT)
```

Invariantes:

```text
measurement != treatment decision
treatment decision != treatment authorization
candidate selection != denoise authorization
authorization artifact != renderer execution
render complete != independent technical PASS
technical PASS != human perceptual PASS
preserve = default
auto_apply = false
```
