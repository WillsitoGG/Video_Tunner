# Release Status

## Estado actual

- Proyecto: Video_Tunner
- Versión de desarrollo: `0.1.0-dev`
- Release publicada: **no**
- ZIP portable final validado: **no**
- Windows 10/11 x64 validado manualmente por Guille como release final: **no**
- Fase 0–2C: COMPLETADAS según evidencia registrada
- Fase 2D: **CERRADA COMO FOUNDATION/EVIDENCE**
- Fase 2E: **CERRADA — CLOSE_OUT_READY**
- Fase 3.1: **COMPLETADA COMO FOUNDATION — Audiovisual Quality Audit v1**
- Fase 3 focal baseline: **COMPLETADA — 3 joins reales / 2 fuentes**
- Fase 3.2: **COMPLETADA COMO FOUNDATION — Bypass-first Treatment Decision**
- Fase 3.3: **COMPLETADA COMO FOUNDATION REVIEW-ONLY — Normalization Profile Contract**
- Fase 3.4: **COMPLETADA COMO FOUNDATION — Explicit Normalization Approval**
- Fase 3.5a–d: **TECHNICAL FOUNDATION PASS — human perceptual close-out pendiente**
- Fase 3.6a: **MEASUREMENT FOUNDATION PASS — Noise Evidence Audit**
- Fase 3.6b: **CLOSED — frozen denoise evaluation corpus**
- Fase 3.6c: **CLOSED — objective noisy baseline**
- Fase 3.6d: **CLOSED — candidate objective comparison**
- Fase 3.6e: **CLOSED — blinded human A/B**
- Fase 3.6f: **CLOSED — DeepFilterNet selected for integration review**
- Fase 3.6g: **TECHNICAL PASS — immutable/offline portable DeepFilterNet runtime**
- Denoise plan / ejecución autorizada: **NO**
- Denoise renderer: **NO IMPLEMENTADO / NO AUTORIZADO**
- Fase 3 completa: **NO**

## Evidencia principal

```text
Portable core                    33600174568  PASS
Portable ML                      33621357438  PASS
Sync hardening                   33639009841  PASS
Target Spanish                   33656235038  PASS — WER 1.64%, RTF 0.4854
Phase 2E.4 real semantic E2E     33909625346  PASS
Phase 2E.5 technical close-out   34119952855  PASS — 3/3 real AMI technical renders
Phase 2E.5 human close-out       offline       PASS — 3/3 human; CLOSE_OUT_READY
Phase 2E clean regression        34124101770  PASS — 275/275 + doctor
Phase 3.1 quality audit          34124957783  PASS — 8/8 + real FFmpeg E2E
Phase 3.1 full regression        34125110506  PASS — 283/283 + doctor
Phase 3 focal baseline           34134893725  PASS — exact 2E.5 listening bundle
Phase 3.2 treatment foundation   34135210344  PASS — 14/14
Phase 3.3 normalization profile  34135437824  PASS — 13/13
Phase 3.4 normalization approval 34136124997  PASS — 15/15
Phase 3.5a normalization plan    34136621557  PASS — 15/15 base gate
Phase 3.5b execution auth        34138226442  PASS — 15/15
Phase 3.5c real linear render    34139056626  PASS — 25/25 + real FFmpeg E2E
Phase 3.5d post-render verify    34139502187  PASS — 16/16 + real FFmpeg E2E
Phase 3 through 3.5d regression  34139639280  PASS — 337/337 + doctor
Phase 3.6a noise audit           34141013261  PASS — 9/9 + real MP4/AAC E2E
Phase 3 through 3.6a regression  34141115293  PASS — 346/346 + doctor
Phase 3.6b corpus materialize    34142222451  PASS — 40 paired noisy/clean cases
Phase 3.6c objective baseline    34143456746  PASS — 40/40 measured
DeepFilterNet temporal smoke     34144574712  PASS — 3.00 s → 2.97 s
Phase 3.6d candidate comparison  34145308485  PASS
Phase 3.6e human A/B bundle      34148410617  PASS — Guille listening completed
Phase 3.6e closeout validation   34150202283  PASS — 398/398 + doctor
Phase 3.6f selection artifact    34150663772  PASS — DeepFilterNet selected for integration review
Phase 3.6f final validation      34150832960  PASS — 12/12 + 410/410 + doctor
Phase 3.6g portable runtime      34211660270  PASS — 14/14 focused, 418 integrated, both doctors
```

## Phase 3 focal evidence

Sobre exactamente los tres pares ORIGINAL/RENDERED ya escuchados en 2E.5:

```text
cases                           3
distinct sources                2
human perceptual PASS           3/3
max observed |Δ loudness|       0.40 LU
max observed |Δ true peak|      0.04 dB
treatment_authorized            false
auto_apply                      false
```

Estos máximos son **observaciones del corpus**, no thresholds generales.

## Normalization technical foundation

```text
product default                         preserve
normalization auto-selection            false
dynamic loudnorm fallback               forbidden
normalization technical foundation      PASS
normalization human perceptual closeout PENDING
denoise renderer                        not authorized
join smoothing / crossfade              not authorized
auto_apply                              false
```

Detalle: `Validation/phase3-normalization-foundation.md`.

## Denoise evidence and selection state

### 3.6a — measurement only

`noise_evidence_audit` mide energía sobre ventanas speech/non-speech acreditadas. La suficiencia determina únicamente si se puede medir; ningún dBFS activa tratamiento.

### 3.6b — corpus congelado

```text
corpus = voicebank_demand_official_test_balanced_v1
paired cases = 40
speakers = p232, p257
noise classes = bus, cafe, living, office, psquare
SNR = 17.5 / 12.5 / 7.5 / 2.5 dB
license = CC BY 4.0
```

### 3.6c–d — objective evidence

Baseline noisy descriptivo:

```text
mean SI-SDR = 9.16548156 dB
mean STOI   = 0.95070362
```

DeepFilterNet 0.5.6 vs preserve sobre los 40 casos:

```text
mean SI-SDR delta = +9.87013412 dB
positive SI-SDR cases = 40/40
mean STOI delta = +0.01112968
positive STOI cases = 27/40
raw duration delta = -0.03 s
```

Clean controls DeepFilterNet:

```text
mean STOI = 0.99542798
mean normalized RMSE = 0.03238068
numeric acceptance threshold = none
```

La evidencia objetiva es auxiliar y no autoriza por sí sola selección ni tratamiento.

### 3.6e — human perceptual A/B

Guille realizó la escucha A/B precomprometida.

```text
DeepFilterNet: treatment 10 / preserve 0 / no preference 0
speech integrity failures = 0
artifact failures = 0
perceptual gate = PASS

AFFTDN: treatment 3 / preserve 2 / no preference 5
perceptual gate = FAIL
```

### 3.6f — selection review

```text
selected_candidate = deepfilternet_0_5_6_compensated_v1
selection_status = SELECTED_FOR_INTEGRATION_REVIEW
```

Esto **no** significa denoise autorizado.

### 3.6g — portable runtime contract

```text
upstream = DeepFilterNet 0.5.6
runtime = Tools/deepfilter/bin/deep-filter.exe
SHA-256 = 75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915
size = 26912256 bytes
runtime download = forbidden
PATH fallback = forbidden
```

Gate `34211660270` acreditó build portable, provenance exacta, ejecución con outbound network bloqueado, tamper fail-closed, regresión y ambos `doctor`.

Artifact ligero:

```text
artifact_id = 10050110122
zip_sha256 = c27f8a0ddfaa88bfdfa36bf8c79d6b4ec74198669f75cbfbb427648c6d04de89
```

Estado efectivo tras 3.6g:

```text
selected_candidate = deepfilternet_0_5_6_compensated_v1
product_default = preserve
runtime_download_allowed = false
denoise_authorized = false
renderer_authorized = false
auto_apply = false
```

Detalle: `Validation/phase3-denoiser-portable-runtime.json`.

## Artifact chain actual

```text
analysis.json                              schema v9
promotion_approval.json                    schema v1
approved_edit_plan_proposal.json           schema v1
semantic_execution_authorization.json      schema v1
semantic_edit_plan.json                    schema v1
semantic_render_verification               schema v1
semantic_render_human_review               schema v1
phase2e_closeout_decision                  schema v1
audiovisual_quality_audit                  schema v1
audiovisual_treatment_decision             schema v1
normalization_profile_decision              schema v1
normalization_approval                      schema v1
normalization_plan_proposal                 schema v1
normalization_execution_authorization       schema v1
normalization_render_result                 schema v1
normalization_post_render_verification      schema v1
noise_evidence_audit                        schema v1
```

Aún no existe artifact ejecutable de denoise plan/authorization/renderer en el producto.

## Safety Fase 3

```text
Phase 3 cannot rescue failed Phase 2E evidence
measurement != treatment decision
treatment decision != treatment authorization
noise measurement != denoise decision
denoise evaluation != candidate selection
candidate selection != denoise authorization
selected runtime availability != renderer authorization
profile selection != normalization authorization
technical normalization PASS != human perceptual PASS
preserve = default
denoise renderer = not authorized
join smoothing = not authorized
auto_apply = false
```

## Pendiente antes de Release

1. Fase 3.6h — denoise plan proposal no ejecutable + autorización explícita stale-safe separada;
2. sólo después, renderer de denoise derivado y verificación técnica independiente;
3. human perceptual close-out del tratamiento real antes de generalizarlo;
4. human perceptual close-out de normalización si se pretende generalizar esa vía;
5. evaluación específica A/B antes de cualquier join smoothing/crossfade;
6. resto de Fase 3 quality/audit según evidencia;
7. Fase 4 UX;
8. Fase 5 Release Hardening + licencias/notices + Windows limpio real;
9. estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
