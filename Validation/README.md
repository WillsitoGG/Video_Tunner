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
- `phase2c-semantic-validation.md` / `phase2c-audio-backed-validation.md` — validación semántica real.
- `phase2d-correction-scope.md`, `phase2d-contextual-fillers.md`, `phase2d-join-safety.md`, `phase2d-acoustic-join.md`, `phase2d-human-acoustic-evidence.md`, `phase2d-combined-eligibility.md`, `phase2d-human-combined-eligibility.md`, `phase2d-human-positive-closeout.md` — Fase 2D.
- `phase2e-promotion-foundation.md` — 2E.1.
- `phase2e-explicit-approval-contract.md` — 2E.2.
- `phase2e-approved-plan-proposal.md` — 2E.3.
- `phase2e-execution-authorization.md` — 2E.4.
- `phase2e-post-render-closeout.md` — 2E.5 technical + human closeout.
- `phase2e-human-closeout/` — decisiones/reviews/hash manifest de 2E.5.

Fase 2E está cerrada como `CLOSE_OUT_READY`; `auto_apply=false`.

### Fase 3 — audiovisual quality / audit

Foundation general:

- `phase3-audiovisual-quality-foundation.md` — 3.1 Quality Audit, baseline focal real, 3.2 Treatment Decision y 3.3 Normalization Profile Contract.
- `phase3-focal-quality-baseline.json` — medición persistente exacta de los tres pares ORIGINAL/RENDERED ya escuchados en 2E.5.
- `phase3-normalization-foundation.md` — 3.4 Explicit Normalization Approval + 3.5a–d plan/authorization/renderer/post-render technical verification.
- `phase3-noise-audit-foundation.md` — 3.6a Noise Evidence Audit measurement-only.

Denoise 3.6b–h:

- `phase3-denoise-corpus-materialization.json` — corpus VoiceBank+DEMAND congelado y materializado: 40 pares noisy/clean, hashes y provenance.
- `phase3-denoise-objective-baseline.json` — baseline noisy objetivo SI-SDR/STOI sobre 40/40 casos.
- `phase3-denoiser-candidate-objective-comparison.json` — comparación objetiva preserve / AFFTDN / DeepFilterNet y clean controls.
- `phase3-denoiser-human-ab-bundle-technical.json` — manifest técnico del bundle A/B cegado.
- `phase3-denoiser-human-ab-public-review.json` — review público/cegado de Guille.
- `phase3-denoiser-human-ab-review.json` — review remapeado/unblinded con fingerprints.
- `phase3-denoiser-human-perceptual-gate.json` — gate perceptual precomprometido.
- `phase3-denoiser-human-perceptual-closeout.json` — closeout 3.6e.
- `phase3-denoiser-selection-review.json` — decisión de selection review 3.6f.
- `phase3-denoiser-selection-closeout.json` — closeout y provenance de selección.
- `phase3-denoiser-portable-runtime.json` — contrato/provenance 3.6g del runtime DeepFilterNet portable inmutable/offline.
- `phase3-denoise-plan-authorization-foundation.json` — foundation 3.6h: `denoise_plan_proposal` no ejecutable + `denoise_execution_authorization` stale/tamper-safe, sin autorización real por-media ni renderer.

## Runs principales

```text
34124957783  Phase 3.1 focused + real FFmpeg E2E — 8/8 PASS
34125110506  Phase 3.1 full regression — 283/283 + doctor PASS
34134893725  focal baseline exact 2E.5 bundle — PASS
34135210344  Phase 3.2 bypass-first treatment — 14/14 PASS
34135437824  Phase 3.3 normalization profile — 13/13 PASS
34136124997  Phase 3.4 explicit normalization approval — 15/15 PASS
34136621557  Phase 3.5a plan proposal base gate — 15/15 PASS
34138226442  Phase 3.5b execution authorization — 15/15 PASS
34139056626  Phase 3.5c gated linear render — 25/25 + real FFmpeg E2E PASS
34139502187  Phase 3.5d independent post-render verification — 16/16 + real FFmpeg E2E PASS
34139639280  full regression through 3.5d — 337/337 + doctor PASS
34141013261  Phase 3.6a noise evidence audit — 9/9 + real MP4/AAC E2E PASS
34141115293  full regression through 3.6a — 346/346 + doctor PASS
34142222451  Phase 3.6b corpus materialization — 40 paired cases PASS
34143456746  Phase 3.6c objective noisy baseline — 40/40 measured
34144574712  DeepFilterNet temporal smoke — 3.00 s → 2.97 s
34145308485  Phase 3.6d candidate objective comparison — PASS
34148410617  Phase 3.6e blinded A/B bundle — PASS
34150202283  Phase 3.6e closeout validation — 398/398 + doctor PASS
34150663772  Phase 3.6f selection artifact — DeepFilterNet selected for integration review
34150832960  Phase 3.6f final validation — 12/12 focused + 410/410 + doctor PASS
34211660270  Phase 3.6g portable runtime contract — 14/14 focused + 418 integrated + both doctors PASS
34219441077  Phase 3.6g post-persistence — 20/20 focused + 424 integrated + both doctors PASS
34220351609  Phase 3.6h plan/authorization contract — 38/38 focused + 445/445 integrated + doctor PASS
```

## Fase 3 focal — observaciones

```text
cases = 3
sources = 2
human perceptual PASS = 3/3
max observed |Δ integrated loudness| = 0.40 LU
max observed |Δ true peak| = 0.04 dB
```

**0.40 LU y 0.04 dB son observaciones de la muestra, no thresholds de producto.**

## Denoise 3.6b–h — interpretación acreditada

### Corpus 3.6b

```text
corpus_id = voicebank_demand_official_test_balanced_v1
cases = 40 paired noisy/clean
speakers = p232, p257
noise = bus, cafe, living, office, psquare
SNRs = 17.5, 12.5, 7.5, 2.5 dB
sample rate = 48000 Hz
license = CC BY 4.0
```

### Baseline 3.6c

```text
mean noisy SI-SDR = 9.16548156 dB
mean noisy STOI   = 0.95070362
```

Es baseline descriptivo; no define aceptación ni ranking.

### Comparación 3.6d

DeepFilterNet 0.5.6 sobre 40 casos noisy:

```text
mean SI-SDR delta vs preserve = +9.87013412 dB
positive SI-SDR cases = 40/40
mean STOI delta vs preserve = +0.01112968
positive STOI cases = 27/40
raw duration delta = -0.03 s
```

Clean controls:

```text
case_count = 40
mean STOI = 0.99542798
mean normalized RMSE = 0.03238068
numeric acceptance threshold applied = false
```

Las métricas objetivas son auxiliares. La comparación no seleccionó ni autorizó tratamiento por sí sola.

### Human A/B 3.6e

Guille completó la escucha cegada precomprometida:

```text
DeepFilterNet
  treatment preference = 10
  preserve preference = 0
  no preference = 0
  speech integrity failures = 0
  artifact failures = 0
  perceptual gate = PASS

AFFTDN
  treatment preference = 3
  preserve preference = 2
  no preference = 5
  perceptual gate = FAIL
```

El gate humano sólo habilitó selection review.

### Selection 3.6f

```text
selected_candidate_id = deepfilternet_0_5_6_compensated_v1
selection_status = SELECTED_FOR_INTEGRATION_REVIEW
```

Selección != autorización de denoise.

### Portable runtime 3.6g

Contrato exacto:

```text
DeepFilterNet = 0.5.6
runtime = Tools/deepfilter/bin/deep-filter.exe
SHA-256 = 75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915
size = 26912256 bytes
runtime_download_allowed = false
product_default = preserve
denoise_authorized = false
renderer_authorized = false
auto_apply = false
```

Gate `34211660270` verificó build portable, provenance, ejecución offline con outbound network bloqueado, rechazo fail-closed de binario manipulado, regresión integrada y ambos `doctor`. Post-persistence `34219441077`: 20/20 focales + 424 integrados PASS.

Artifact ligero:

```text
artifact_id = 10050110122
zip_sha256 = c27f8a0ddfaa88bfdfa36bf8c79d6b4ec74198669f75cbfbb427648c6d04de89
```

La presencia del binario seleccionado dentro del portable **no crea un renderer ni autoriza denoise**.

### Plan + authorization design 3.6h

Artifacts schema v1:

```text
denoise_plan_proposal
denoise_execution_authorization
```

El plan sólo puede quedar `ready` si la evidencia 3.6a tiene cobertura suficiente y toda la cadena exacta sigue vigente. `evidence_sufficient` significa **measurement coverage suficiente**, no “denoise necesario”.

El plan fija criptográficamente:

- `noise_evidence_audit` completo y su fingerprint;
- output SHA acreditado;
- selection review 3.6f y fingerprint;
- candidato DeepFilterNet exacto;
- runtime 3.6g y fingerprint, incluida CLI/timeline contract.

El plan continúa sin capability:

```text
parameters_executable = false
denoise_authorized = false
denoise_render_authorization = false
plan_render_authorization = false
renderer_available = false
executable = false
auto_apply = false
```

La autorización separada exige `APPROVE`/`REJECT`, actor y reason. Un APPROVE sólo representa permiso para una **futura** ruta gated y no ejecuta tratamiento por sí mismo.

Gate `34220351609`:

```text
38/38 focused PASS
445/445 integrated PASS
doctor PASS
```

Los APPROVE del gate son fixtures sintéticos. Estado real persistido de 3.6h:

```text
real_user_authorization_record_created = false
real_user_media_authorized_for_denoise = false
denoise_renderer_implemented = false
treated_media_generated = false
product_default = preserve
auto_apply = false
```

En particular, **Guille no emitió una autorización real por-media de denoise en 3.6h**.

Binder permanente: `tests/test_phase3_denoise_plan_authorization_evidence.py`.

## Regla de interpretación

Una validación PASS acredita únicamente el alcance descrito en su documento. No implica por sí sola:

- release publicable;
- generalización de seguridad/calidad fuera del corpus;
- que un número observado se convierta en threshold;
- que una medición autorice tratamiento;
- que technical normalization PASS equivalga a human perceptual PASS;
- que un dBFS medido implique necesidad de denoise;
- que una métrica objetiva seleccione automáticamente un algoritmo;
- que selección de candidato autorice ejecución;
- que disponibilidad offline del runtime autorice renderer;
- que la existencia de un authorization schema equivalga a una autorización real emitida por Guille;
- denoise o smoothing automáticos;
- validación final del ZIP portable en Windows limpio.

Cadena conceptual actual:

```text
Phase 2E output PASS
→ audiovisual_quality_audit
   ├→ audiovisual_treatment_decision
   │  → normalization_profile_decision
   │  → normalization_approval
   │  → normalization_plan_proposal
   │  → normalization_execution_authorization
   │  → normalization_render_result
   │  → normalization_post_render_verification
   │  → human perceptual normalization review (PENDING)
   └→ noise_evidence_audit
      → frozen denoise corpus
      → objective noisy baseline
      → candidate objective comparison
      → blinded human A/B
      → candidate selection review
      → portable selected-runtime contract
      → denoise_plan_proposal
      → denoise_execution_authorization
      → gated denoise renderer technical foundation (NEXT)
```

Invariantes:

```text
Phase 3 favorable signal != rescue of failed Phase 2E
measurement != treatment decision
treatment decision != treatment authorization
noise measurement != denoise decision
denoise evaluation != candidate selection
candidate selection != denoise authorization
selected runtime availability != renderer authorization
denoise plan != denoise execution authorization
authorization artifact != renderer execution
profile selection != normalization authorization
technical PASS != human perceptual PASS
preserve = default
auto_apply = false
```
