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
- Denoise ejecutable: **NO AUTORIZADO**
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
denoise                                 not authorized
join smoothing / crossfade              not authorized
auto_apply                              false
```

Detalle: `Validation/phase3-normalization-foundation.md`.

## Noise measurement foundation

`noise_evidence_audit` mide únicamente energía sobre ventanas speech/non-speech acreditadas.

Precommit:

```text
PCM analysis                mono PCM16 @ 16 kHz
frame                       0.20 s
non-speech guard            0.15 s
minimum NS window           0.40 s
minimum NS windows          2
minimum total NS coverage   2.0 s
```

Estas condiciones determinan si la evidencia es suficiente para **medir**, no si el vídeo necesita denoise.

Siempre:

```text
denoise_evaluated = false
denoise_authorized = false
filter_selected = false
parameters_defined = false
executable = false
treatment_authorized = false
auto_apply = false
```

Detalle: `Validation/phase3-noise-audit-foundation.md`.

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

## Safety Fase 3

```text
Phase 3 cannot rescue failed Phase 2E evidence
measurement != treatment decision
treatment decision != treatment authorization
noise measurement != denoise decision
denoise decision != denoise authorization
risk != automatic filter selection
profile selection != normalization authorization
technical normalization PASS != human perceptual PASS
preserve = default
denoise = not authorized
join smoothing = not authorized
auto_apply = false
```

## Pendiente antes de Release

1. Fase 3.6b — corpus de evaluación denoise con noisy speech + clean/control y licencias claras;
2. evaluación objetiva + perceptual antes de cualquier denoise ejecutable;
3. human perceptual close-out de normalización si se pretende generalizar esa vía;
4. evaluación específica A/B antes de cualquier join smoothing/crossfade;
5. resto de Fase 3 quality/audit según evidencia;
6. Fase 4 UX;
7. Fase 5 Release Hardening + licencias/notices + Windows limpio real;
8. estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
