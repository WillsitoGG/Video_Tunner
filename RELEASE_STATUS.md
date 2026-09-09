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
- Fase 3.1–3.5d: **TECHNICAL FOUNDATION PASS — human normalization close-out pendiente**
- Fase 3.6a: **MEASUREMENT FOUNDATION PASS — Noise Evidence Audit**
- Fase 3.6b: **CLOSED — frozen denoise evaluation corpus**
- Fase 3.6c: **CLOSED — objective noisy baseline**
- Fase 3.6d: **CLOSED — candidate objective comparison**
- Fase 3.6e: **CLOSED — blinded human A/B**
- Fase 3.6f: **CLOSED — DeepFilterNet selected for integration review**
- Fase 3.6g: **CLOSED — immutable/offline portable DeepFilterNet runtime**
- Fase 3.6h: **TECHNICAL FOUNDATION PASS — denoise plan + explicit stale-safe authorization contract**
- Fase 3.6i: **TECHNICAL FOUNDATION PASS — gated DeepFilterNet denoise renderer sobre media sintética mono**
- Fase 3.6j: **TECHNICAL FOUNDATION PASS — independent denoise post-render verifier**
- Fase 3.6j post-persistence: **CLOSED — technical foundation revalidated on persisted state**
- Autorización real de Guille para denoise sobre media concreta: **NO EMITIDA**
- Media real de Guille autorizada para denoise: **NO**
- Media real de Guille procesada con denoise: **NO**
- Human denoise treatment closeout: **PENDING — 3.6k siguiente**
- Generalización denoise a estéreo/multicanal: **NO**
- Product default audiovisual: **preserve**
- `auto_apply`: **false**
- Fase 3 completa: **NO**

## Evidencia principal

```text
Portable core                    33600174568  PASS
Portable ML                      33621357438  PASS
Sync hardening                   33639009841  PASS
Target Spanish                   33656235038  PASS — WER 1.64%, RTF 0.4854
Phase 2E.5 technical close-out   34119952855  PASS — 3/3 real AMI technical renders
Phase 2E.5 human close-out       offline       PASS — 3/3 human; CLOSE_OUT_READY
Phase 2E clean regression        34124101770  PASS — 275/275 + doctor
Phase 3.1 quality audit          34124957783  PASS — 8/8 + real FFmpeg E2E
Phase 3 through 3.5d regression  34139639280  PASS — 337/337 + doctor
Phase 3.6a noise audit           34141013261  PASS — 9/9 + real MP4/AAC E2E
Phase 3.6a regression            34141115293  PASS — 346/346 + doctor
Phase 3.6b corpus materialize    34142222451  PASS — 40 paired noisy/clean cases
Phase 3.6c objective baseline    34143456746  PASS — 40/40 measured
Phase 3.6d candidate comparison  34145308485  PASS
Phase 3.6e human A/B bundle      34148410617  PASS — Guille listening completed
Phase 3.6e closeout validation   34150202283  PASS — 398/398 + doctor
Phase 3.6f final validation      34150832960  PASS — 12/12 + 410/410 + doctor
Phase 3.6g portable runtime      34211660270  PASS
Phase 3.6g post-persistence      34219441077  PASS — 20/20 + 424 integrated + both doctors
Phase 3.6h clean closeout        34225276990  PASS — 45/45 + 452/452 + doctor
Phase 3.6i base renderer         34231340544  PASS — 49/49 + 1/1 DeepFilter E2E + 466/466, 0 skips + doctor
Phase 3.6i post-persistence      34240028080  PASS — 57/57 + 1/1 E2E + 474/474, 0 skips + doctor
Phase 3.6j verifier foundation   34241518206  PASS — 63/63 + 1/1 render→verifier E2E + 488/488, 0 skips + doctor
Phase 3.6j persisted preflight   34336304799  PASS — 21/21
Phase 3.6 evidence binder sweep  34336891424  PASS — 65/65
Phase 3.6j post-persistence      34337071421  PASS — 71/71 + 1/1 render→verifier E2E + 496/496, 0 skips + doctor
```

## Normalization technical foundation

```text
product default                         preserve
normalization auto-selection            false
dynamic loudnorm fallback               forbidden
normalization technical foundation      PASS
normalization human perceptual closeout PENDING
auto_apply                              false
```

## Denoise chain

### 3.6a–f — evidence / evaluation / human selection

Noise evidence es measurement-only. Corpus congelado: 40 pares VoiceBank+DEMAND. DeepFilterNet 0.5.6 mostró evidencia objetiva favorable y Guille completó el A/B ciego precomprometido: treatment 10/10, 0 fallos perceptuales registrados. Selection review eligió `deepfilternet_0_5_6_compensated_v1` para integration review. Ninguno de estos pasos autorizó media concreta por sí solo.

### 3.6g — portable runtime

```text
runtime = Tools/deepfilter/bin/deep-filter.exe
SHA-256 = 75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915
size = 26912256 bytes
CLI = --compensate-delay --output-dir <output_dir> <input_wav>
runtime download = forbidden
PATH fallback in product = forbidden
```

### 3.6h — plan + explicit authorization

`denoise_plan_proposal` y `denoise_execution_authorization` schema v1. Un APPROVE válido sólo registra permiso per-media para la ruta gated y debe mantenerse vigente; no ejecuta DeepFilterNet por sí mismo.

### 3.6i — renderer

`denoise_render_result` schema v1. Foundation inicial:

```text
source overwrite = forbidden
exactly 1 video + 1 audio
source audio = mono only
DeepFilter input = PCM16 mono 48 kHz
raw duration tolerance = ±0.05 s
alignment/time-shift/level-match = forbidden
right-tail trim/pad only
video = stream copy
audio = AAC 192k
-shortest = forbidden
render complete != technical PASS
render complete != human PASS
```

### 3.6j — independent post-render verifier

Artifact:

```text
denoise_post_render_verification schema v1
```

El verifier revalida provenance/hash actuales, no acepta self-PASS del renderer y distingue `invalid_evidence` de `technical_denoise_fail`.

Contrato técnico:

```text
source/output streams = exactly 1 video + 1 audio
decoded video SHA source == output
output audio = AAC mono 48 kHz
independent decode = PCM16 mono 48 kHz
source/output decoded audio frame count must match
reported final frames == input frames
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

E2E post-persistencia observado:

```text
status = technical_denoise_pass
blockers = []
decoded_video_equal = true
source_frames = 144000
output_frames = 144000
human_pass = false
```

Evidencia persistente:

```text
Validation/phase3-denoise-post-render-verifier-foundation.json
Validation/phase3-denoise-post-render-verifier-closeout.json
```

Estado efectivo:

```text
selected_candidate = deepfilternet_0_5_6_compensated_v1
renderer_technical_foundation = PASS
independent_verifier_technical_foundation = CLOSED
product_default = preserve
real_user_authorization_record_created = false
real_user_media_authorized_for_denoise = false
real_user_media_processed_with_denoise = false
real_user_treated_media_generated = false
human_denoise_treatment_closeout = false
stereo_or_multichannel_generalized = false
auto_apply = false
```

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
denoise_plan_proposal                       schema v1
denoise_execution_authorization             schema v1
denoise_render_result                       schema v1
denoise_post_render_verification            schema v1
```

## Safety Fase 3

```text
measurement != treatment decision
treatment decision != treatment authorization
candidate selection != denoise authorization
authorization artifact != renderer execution
render complete != independent technical PASS
technical PASS != human perceptual PASS
preserve = default
join smoothing = not authorized
auto_apply = false
```

## Pendiente antes de Release

1. Fase 3.6k — human perceptual denoise treatment closeout, con criterios precomprometidos y sin atribuir escucha inexistente;
2. autorización real válida y vigente antes de cualquier tratamiento de media real;
3. extensión específica con evidencia antes de generalizar a estéreo/multicanal;
4. human perceptual close-out de normalización si se pretende generalizar esa vía;
5. evaluación específica A/B antes de cualquier join smoothing/crossfade;
6. resto de Fase 3 quality/audit según evidencia;
7. Fase 4 UX;
8. Fase 5 Release Hardening + licencias/notices + Windows limpio real;
9. estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
