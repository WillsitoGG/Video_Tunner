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

La muestra actual no justifica tratamiento obligatorio para reparar el renderer: no habilita normalización por defecto, denoise ni join smoothing/crossfade.

Evidencia: `Validation/phase3-focal-quality-baseline.json` y `Validation/phase3-audiovisual-quality-foundation.md`.

## Artifact chain actual

```text
analysis.json                         schema v9
promotion_approval.json               schema v1
approved_edit_plan_proposal.json      schema v1
semantic_execution_authorization.json schema v1
semantic_edit_plan.json               schema v1
semantic_render_verification          schema v1
semantic_render_human_review          schema v1
phase2e_closeout_decision              schema v1
audiovisual_quality_audit              schema v1
audiovisual_treatment_decision         schema v1
normalization_profile_decision         schema v1
```

## Safety Fase 3

```text
Phase 3 cannot rescue failed Phase 2E evidence
measurement != treatment decision
treatment decision != treatment authorization
risk != automatic filter selection
profile selection != normalization authorization
preserve = default
normalization executable = not yet implemented
denoise = not authorized
join smoothing = not authorized
auto_apply = false
```

`ebu_r128_programme` está registrado únicamente como perfil opt-in/review-only basado en EBU R 128 v5.0 / ITU-R BS.1770-5. No es default ni se extrapola como target universal para web.

## Pendiente antes de Release

1. Fase 3.4 — explicit normalization approval stale-safe;
2. Fase 3.5 — preview/derivative normalization sólo tras approval + parámetros validados;
3. post-treatment technical + perceptual validation;
4. resto de Fase 3 quality/audit según evidencia;
5. Fase 4 UX;
6. Fase 5 Release Hardening + licencias/notices + Windows limpio real;
7. estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
