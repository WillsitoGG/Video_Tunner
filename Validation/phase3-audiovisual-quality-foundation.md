# Phase 3 — Audiovisual Quality / Audit Foundation

Estado: **FOUNDATION VALIDADA; tratamiento ejecutable todavía no autorizado**.

## 1. Alcance

Esta evidencia cubre exclusivamente la foundation inicial de Fase 3 sobre outputs semánticos que ya hayan superado Fase 2E.

Invariantes heredados:

```text
Phase 3 favorable signal != rescue of failed Phase 2E evidence
measurement != treatment decision
treatment decision != treatment authorization
profile selection != normalization authorization
preserve = default
auto_apply = false
```

Fase 3 no puede aceptar un `semantic_render_verification` fallido, un join técnico fallido ni un output cuyo SHA-256 ya no coincida con la evidencia 2E.

## 2. Phase 3.1 — Audiovisual Quality Audit v1

Implementado `Source/video_tunner/audiovisual_quality.py`:

- artifact `audiovisual_quality_audit` schema v1;
- binding exacto a technical-report SHA, source SHA y output SHA de Fase 2E;
- medición de audio mediante FFmpeg `loudnorm` en modo análisis-only;
- se conservan únicamente las mediciones de entrada: integrated loudness, true peak, loudness range y threshold;
- el filtro no genera ni sustituye el media del producto;
- riesgo objetivo v1: output true peak > 0 dBTP;
- `treatment_authorized=false`;
- `auto_apply=false`.

Validación focal Windows + FFmpeg real:

```text
34124957783  PASS — 8/8, incluido E2E MP4 real
```

Regresión completa después de 3.1:

```text
34125110506  PASS — 283/283 + video-tunner doctor
```

## 3. Baseline focal real sobre los joins ya escuchados

Se reutilizó exactamente el artifact de escucha de Fase 2E.5 generado por el run `34119952855`.

El gate `34134893725`:

1. descargó el mismo artifact `phase2e-human-render-review-bundle`;
2. verificó el manifest por SHA-256;
3. verificó los tres technical reports contra el manifest;
4. verificó las tres reviews humanas persistidas como PASS y no stale;
5. midió cada par `original.wav` / `rendered.wav` con el código actual de Phase 3.1.

Resultado:

```text
cases = 3
sources = 2
human perceptual PASS = 3/3
max observed |integrated loudness delta| = 0.40 LU
max observed |true peak delta| = 0.04 dB
treatment_authorized = false
PASS
```

Detalle persistente: `Validation/phase3-focal-quality-baseline.json`.

**Interpretación limitada:** 0.40 LU y 0.04 dB son máximos observados en este corpus focal; no son thresholds generales de producto.

La evidencia actual sí permite concluir que estos tres joins reales, ya técnicos + humanos PASS, no muestran una alteración global de loudness/true peak que justifique normalización obligatoria como reparación del renderer.

La muestra tampoco justifica actualmente:

- join smoothing/crossfade por defecto;
- denoise por defecto;
- normalización obligatoria.

## 4. Phase 3.2 — Bypass-first Treatment Decision

Implementado `Source/video_tunner/audiovisual_treatment.py`:

```text
quality audit sin riesgos -> bypass_preserve_render
quality audit con riesgo  -> treatment_review_required
```

Un riesgo sólo abre una revisión. Nunca selecciona ni autoriza por sí mismo un tratamiento.

En ambos caminos:

```text
normalization = not_authorized
denoise = not_authorized
join_smoothing = not_authorized
parameters_defined = false
mandatory_treatment = false
executable = false
treatment_authorized = false
auto_apply = false
```

Validación:

```text
34135210344  PASS — 14/14 incluyendo quality E2E FFmpeg
```

## 5. Phase 3.3 — Normalization Profile Contract

El producto mantiene `preserve` como perfil por defecto.

Se registra un segundo perfil únicamente como opt-in standards-based y review-only:

```text
ebu_r128_programme
programme target = -23 LUFS
maximum permitted true peak = -1 dBTP
standard = EBU R 128 v5.0 (November 2023)
measurement basis = ITU-R BS.1770-5 (November 2023)
```

Estos valores se registran como perfil de referencia de producción broadcast. No se extrapolan silenciosamente a YouTube/web ni se convierten en default de Video_Tunner.

Un riesgo medido tampoco auto-selecciona `ebu_r128_programme`.

Incluso con selección explícita del perfil:

```text
explicit_opt_in_required = true
human_approval_required = true
normalization_requested = true
normalization_authorized = false
parameters_executable = false
render_authorized = false
auto_apply = false
```

Validación:

```text
34135437824  PASS — 13/13
```

## 6. Próximo gate

Antes de procesar audio hay que separar explícitamente:

```text
profile selection
→ human approval/rejection
→ exact treatment parameters / provenance
→ preview or derivative render
→ post-treatment technical audit
→ human perceptual comparison
```

No introducir todavía un renderer de normalización hasta cerrar un contrato stale-safe de aprobación y una política de segunda pasada que no invente parámetros no fijados por el estándar.

En particular, EBU R 128 no debe reinterpretarse como permiso para elegir silenciosamente un target LRA de FFmpeg.

## 7. No acreditado todavía

Esta foundation no acredita:

- normalización ejecutable;
- un target global para contenido web;
- denoise;
- crossfade/join smoothing;
- calidad audiovisual general fuera del corpus evaluado;
- UX;
- release.

`auto_apply=false` permanece inalterado.
