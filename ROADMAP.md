# ROADMAP — Video_Tunner

## Principios

- Windows 10/11 x64 portable: ZIP → descomprimir → ejecutar.
- Vídeo con audio embebido o vídeo + audio externo.
- Master audio y sincronización antes de transcripción/VAD/semántica/acústica temporal.
- Originales intactos y decisiones auditables/reversibles.
- Ante baja confianza: REVIEW/manual, no adivinar.
- CI pesada sólo cuando aporta evidencia nueva; workflows pesados manual-only.
- `preserve` audiovisual por defecto.
- `auto_apply=false`.

## Fases completadas

### Fase 0–1C
Bootstrap, technology harvest, portable foundation, ingesta dual/sync y transcripción/VAD completados según evidencia registrada.

### Fase 2A–2D
Semantic candidates/protection/validation, correction scope, fillers, join safety, acoustic join y eligibility completados. Fase 2D cerrada como foundation/evidence.

### Fase 2E — Promotion to Edit Plan — COMPLETADA

Cadena final:

```text
promotion
→ individual approval
→ bounded proposal
→ global execution authorization
→ semantic Edit Plan
→ semantic render gate
→ FFmpeg
→ technical post-render verification
→ human perceptual review
→ corpus closeout
```

Final:

```text
34119952855  3/3 real AMI technical PASS / 2 sources
human review 3/3 PASS / 0 FAIL
status = CLOSE_OUT_READY
auto_apply = false
34124101770  275/275 + doctor PASS en rama limpia
```

Detalle: `Validation/phase2e-post-render-closeout.md` y `Validation/phase2e-human-closeout/`.

## Fase 3 — Calidad audiovisual / auditoría — EN CURSO

Objetivo: elevar y auditar la calidad audiovisual del output ya autorizado/renderizado sin debilitar la semántica, provenance ni reversibilidad.

### 3.1 — Audiovisual Quality Audit v1 — COMPLETADA COMO FOUNDATION

Artifact `audiovisual_quality_audit` schema v1.

- exige upstream `technical_post_render_pass` vigente;
- liga technical report/source/output por SHA;
- mide integrated LUFS, true peak y LRA con FFmpeg en análisis-only;
- no modifica media;
- Phase 3 nunca rescata un fallo de Phase 2E;
- `treatment_authorized=false`, `auto_apply=false`.

```text
34124957783  8/8 focused + real FFmpeg E2E PASS
34125110506  283/283 full regression + doctor PASS
```

### 3.1b — Baseline focal real — COMPLETADA

Run `34134893725` sobre exactamente los 3 pares ORIGINAL/RENDERED ya escuchados en 2E.5:

```text
cases = 3
sources = 2
human PASS = 3/3
max observed |Δ integrated loudness| = 0.40 LU
max observed |Δ true peak| = 0.04 dB
treatment_authorized = false
```

Estos valores son observados, **no thresholds generales**.

Conclusión limitada de la muestra: no existe evidencia para exigir como default normalización, denoise ni join smoothing/crossfade.

Detalle: `Validation/phase3-focal-quality-baseline.json`.

### 3.2 — Bypass-first Treatment Decision — COMPLETADA COMO FOUNDATION

Artifact `audiovisual_treatment_decision` schema v1.

```text
sin risk finding → bypass_preserve_render
con risk finding → treatment_review_required
```

Un riesgo sólo solicita evaluación; no define parámetros ni autoriza procesamiento.

```text
normalization = not_authorized
denoise = not_authorized
join_smoothing = not_authorized
executable = false
treatment_authorized = false
auto_apply = false
```

Run `34135210344`: 14/14 PASS.

### 3.3 — Normalization Profile Contract — COMPLETADA COMO FOUNDATION REVIEW-ONLY

Perfil default:

```text
preserve
```

Perfil standards-based disponible sólo para opt-in/review:

```text
ebu_r128_programme
-23 LUFS
max true peak -1 dBTP
EBU R 128 v5.0 (November 2023)
measurement basis ITU-R BS.1770-5 (November 2023)
```

No constituye target universal de web/YouTube. Incluso seleccionado explícitamente:

```text
human_approval_required = true
normalization_authorized = false
parameters_executable = false
render_authorized = false
auto_apply = false
```

Run `34135437824`: 13/13 PASS.

### 3.4 — Explicit Normalization Approval — COMPLETADA COMO FOUNDATION

Run `34136124997`: 15/15 PASS.

Artifact stale-safe con APPROVE/REJECT explícito, actor + reason obligatorios y binding al output/profile evidence actual.

APPROVE autoriza como máximo preparar el siguiente plan:

```text
normalization_plan_preparation_authorized = true
normalization_render_authorization = false
parameters_executable = false
executable = false
auto_apply = false
```

### 3.5a — Linear Normalization Plan Proposal — COMPLETADA COMO FOUNDATION

Run base `34136621557`: 15/15 PASS. Hardening incluido en los gates posteriores.

Política:

```text
target_lra = measured_lra
lra_policy = preserve_measured_lra
dynamic_fallback_allowed = false
```

El plan bloquea mediciones no finitas/sentinela, LRA incompatible y cualquier gain lineal que rompería el max true peak. Un plan ready sigue siendo no ejecutable.

### 3.5b — Normalization Execution Authorization — COMPLETADA COMO FOUNDATION

Run `34138226442`: 15/15 PASS.

Rebuild exacto de plan + cadena stale/tamper-aware antes de conceder únicamente:

```text
normalization_render_authorization = true
plan_render_authorization = false
parameters_executable = false
executable = false
auto_apply = false
```

### 3.5c — Gated Linear Normalization Renderer — COMPLETADA TÉCNICAMENTE

Run `34139056626`: 25/25 PASS, incluido E2E FFmpeg real.

- crea derivado, nunca sobrescribe output 2E;
- vídeo por stream copy;
- audio sólo mediante `loudnorm` lineal autorizado;
- `normalization_type != linear` → output eliminado + fail-closed;
- source SHA revalidado antes/después;
- render result no puede autoproclamarse technical/human PASS.

### 3.5d — Independent Post-render Verification — COMPLETADA TÉCNICAMENTE

Run `34139502187`: 16/16 PASS, incluido E2E real.

Gate precomprometido:

```text
Programme Loudness target        -23 LUFS
Programme Loudness tolerance     ±0.5 LU
Maximum True Peak                -1 dBTP
Duration tolerance               ±0.15 s
Video streams                    1
Audio streams                    1
normalization_type               linear
Decoded video SHA-256            source == output
```

Distingue `invalid_evidence` de `technical_normalization_fail`.

Regresión integrada posterior:

```text
34139639280  337/337 tests PASS + doctor PASS
```

Estado correcto de 3.5:

```text
technical foundation = PASS
human perceptual close-out = PENDING
product default = preserve
auto_apply = false
```

Detalle: `Validation/phase3-normalization-foundation.md`.

### 3.6 — Denoise Evidence / Noise Audit — SIGUIENTE

Primero **measurement-only**, no un filtro.

Objetivo inmediato:

1. medir evidencia de ruido sobre audio acreditado sin modificar media;
2. separar cuando sea posible ventanas speech/non-speech usando evidencia temporal existente;
3. registrar métricas reproducibles y provenance por SHA;
4. no convertir una métrica de ruido en recomendación automática de denoise;
5. si la evidencia es insuficiente o las ventanas no son fiables, devolver REVIEW/insufficient evidence;
6. construir corpus con ruido real + controles limpios antes de evaluar filtros;
7. mantener `denoise_authorized=false` y `auto_apply=false`.

### 3.7+ — Denoise treatment / join treatment

- denoise sólo después de corpus/evidencia y comparación perceptual que demuestre valor;
- smoothing/crossfade sólo si existe evidencia A/B perceptual de mejora respecto al join directo;
- no introducir procesamiento por defecto porque “parezca profesional”.

## Fase 4 — UX mínima

Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, aprobar/rechazar, autorizar, renderizar y abrir outputs. Sólo después de cerrar Fase 3.

## Fase 5 — Portable Release Hardening

Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras

Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. cerrar 3.6a Noise Audit measurement-only;
2. validarlo con tests focales + FFmpeg real/sintético cuando aporte evidencia;
3. construir/seleccionar corpus de ruido real y controles limpios antes de denoise ejecutable;
4. mantener 3.5 como opt-in technical foundation mientras su human perceptual close-out siga pendiente;
5. no habilitar denoise ni join smoothing sin evidencia específica;
6. ejecutar regresión completa tras cada bloque que cambie contratos de Fase 3.

No relajar thresholds post hoc y no publicar Release sin autorización expresa de Guille.
