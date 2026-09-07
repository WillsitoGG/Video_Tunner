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

Objetivo: elevar y auditar la calidad audiovisual del output ya autorizado/renderizado sin debilitar semántica, provenance ni reversibilidad.

### 3.1 — Audiovisual Quality Audit v1 — COMPLETADA COMO FOUNDATION

```text
34124957783  8/8 focused + real FFmpeg E2E PASS
34125110506  283/283 full regression + doctor PASS
```

### 3.1b — Baseline focal real — COMPLETADA

Run `34134893725` sobre los 3 pares ORIGINAL/RENDERED ya escuchados en 2E.5:

```text
cases = 3
sources = 2
human PASS = 3/3
max observed |Δ integrated loudness| = 0.40 LU
max observed |Δ true peak| = 0.04 dB
```

Son observaciones, **no thresholds generales**. No justifican normalización, denoise ni smoothing por defecto.

### 3.2 — Bypass-first Treatment Decision — COMPLETADA COMO FOUNDATION

Run `34135210344`: 14/14 PASS.

```text
sin risk finding → bypass_preserve_render
con risk finding → treatment_review_required
```

Un riesgo abre revisión; no define ni autoriza tratamiento.

### 3.3 — Normalization Profile Contract — COMPLETADA COMO FOUNDATION REVIEW-ONLY

Run `34135437824`: 13/13 PASS.

Default: `preserve`.

Opt-in standards-based:

```text
ebu_r128_programme
-23 LUFS
max true peak -1 dBTP
EBU R 128 v5.0
measurement basis ITU-R BS.1770-5
```

### 3.4 — Explicit Normalization Approval — COMPLETADA COMO FOUNDATION

Run `34136124997`: 15/15 PASS.

APPROVE sólo autoriza preparar el siguiente plan; nunca render directo ni `auto_apply`.

### 3.5a — Linear Normalization Plan Proposal — COMPLETADA COMO FOUNDATION

Run base `34136621557`: 15/15 PASS.

```text
target_lra = measured_lra
lra_policy = preserve_measured_lra
dynamic_fallback_allowed = false
```

### 3.5b — Normalization Execution Authorization — COMPLETADA COMO FOUNDATION

Run `34138226442`: 15/15 PASS.

Rebuild exacto del plan y cadena stale/tamper-aware antes de conceder únicamente `normalization_render_authorization=true`.

### 3.5c — Gated Linear Normalization Renderer — COMPLETADA TÉCNICAMENTE

Run `34139056626`: 25/25 PASS, incluido E2E FFmpeg real.

- derivado, nunca overwrite;
- vídeo stream copy;
- audio `loudnorm` lineal autorizado;
- fallback dinámico prohibido;
- source SHA revalidado.

### 3.5d — Independent Post-render Verification — COMPLETADA TÉCNICAMENTE

Run `34139502187`: 16/16 PASS, incluido E2E real.

```text
Programme Loudness       -23 LUFS ±0.5 LU
Maximum True Peak        -1 dBTP
Duration tolerance       ±0.15 s
Decoded video SHA-256    source == output
```

Regresión integrada:

```text
34139639280  337/337 + doctor PASS
```

Estado correcto de 3.5:

```text
technical foundation = PASS
human perceptual close-out = PENDING
product default = preserve
auto_apply = false
```

Detalle: `Validation/phase3-normalization-foundation.md`.

### 3.6a — Noise Evidence Audit — COMPLETADA COMO MEASUREMENT FOUNDATION

Artifact `noise_evidence_audit` schema v1.

Precommit:

```text
analysis PCM              mono PCM16 @ 16 kHz
frame size                0.20 s
non-speech guard          0.15 s
minimum NS window         0.40 s
minimum NS windows        2
minimum total NS coverage 2.0 s
```

La suficiencia sólo acredita que hay cobertura para medir. No existe threshold de dBFS que active denoise.

```text
34141013261  9/9 + real MP4/AAC E2E PASS
34141115293  346/346 full regression + doctor PASS
```

Siempre:

```text
denoise_evaluated = false
denoise_authorized = false
filter_selected = false
parameters_defined = false
executable = false
auto_apply = false
```

Detalle: `Validation/phase3-noise-audit-foundation.md`.

### 3.6b — Denoise Evaluation Corpus — SIGUIENTE

Antes de implementar filtros:

1. seleccionar/congelar noisy speech + clean/control comparable;
2. verificar provenance y licencias;
3. cubrir varios tipos de ruido y niveles;
4. mantener clean controls para detectar degradación introducida;
5. definir métricas objetivas como evidencia auxiliar, no como sustituto de escucha;
6. no seleccionar `afftdn`, `arnndn` u otro algoritmo por conveniencia;
7. no crear renderer de denoise hasta que exista evidencia comparativa real.

### 3.7+ — Denoise treatment / join treatment

- denoise sólo después de corpus + comparación objetiva + perceptual;
- smoothing/crossfade sólo si existe evidencia A/B perceptual de mejora respecto al join directo;
- no introducir procesamiento por defecto porque “parezca profesional”.

## Fase 4 — UX mínima

Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, aprobar/rechazar, autorizar, renderizar y abrir outputs. Sólo después de cerrar Fase 3.

## Fase 5 — Portable Release Hardening

Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras

Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. investigar y congelar corpus 3.6b con licencia/provenance clara;
2. definir fixture/manifiesto ligero y criterios precomprometidos antes de mirar resultados de algoritmos;
3. validar que 3.6a puede medir los casos seleccionados sin inventar ventanas;
4. sólo después comparar candidatos de denoise;
5. mantener 3.5 como opt-in technical foundation mientras su human close-out siga pendiente;
6. mantener join smoothing bloqueado hasta evidencia A/B específica.

No relajar thresholds post hoc y no publicar Release sin autorización expresa de Guille.
