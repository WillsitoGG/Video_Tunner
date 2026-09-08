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
- measurement != decision != authorization.
- candidate evaluation != candidate selection != renderer authorization.

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

La suficiencia sólo acredita cobertura para medir. No existe threshold de dBFS que active denoise.

```text
34141013261  9/9 + real MP4/AAC E2E PASS
34141115293  346/346 full regression + doctor PASS
```

### 3.6b — Denoise Evaluation Corpus — COMPLETADA

Corpus congelado: `voicebank_demand_official_test_balanced_v1`.

```text
40 pares noisy/clean
2 speakers: p232, p257
5 noise classes: bus, cafe, living, office, psquare
4 SNRs: 17.5, 12.5, 7.5, 2.5 dB
48 kHz
CC BY 4.0
```

Materialización reproducible y hash-bound:

```text
34142222451  corpus materialization PASS
```

Los audios del corpus no se versionan en Git; sólo fixtures, hashes, provenance y evidencia ligera.

### 3.6c — Objective Noisy Baseline — COMPLETADA

Run `34143456746` sobre 40/40 casos.

Métricas precomprometidas:

```text
SI-SDR
STOI
```

Baseline descriptivo observado:

```text
mean SI-SDR = 9.16548156 dB
mean STOI   = 0.95070362
```

Sin acceptance thresholds, ranking ni selección de algoritmo.

### 3.6d — Candidate Objective Comparison — COMPLETADA

Run `34145308485`.

Candidatos evaluados:

```text
preserve_noisy_control_v1
ffmpeg_afftdn_fixed_v1
deepfilternet_0_5_6_compensated_v1
```

DeepFilterNet 0.5.6 sobre los 40 casos noisy:

```text
mean SI-SDR delta vs preserve = +9.87013412 dB
positive SI-SDR cases         = 40/40
mean STOI delta vs preserve   = +0.01112968
positive STOI cases           = 27/40
raw duration delta            = -0.03 s
```

Clean controls:

```text
cases = 40
mean STOI = 0.99542798
mean normalized RMSE = 0.03238068
numeric acceptance threshold = none
```

`ffmpeg_afftdn_fixed_v1` degradó de forma fuerte las métricas bajo este contrato fijo. La comparación objetiva siguió siendo **auxiliar** y no autorizó selección ni tratamiento por sí sola.

Smoke temporal DeepFilterNet previo: `34144574712`, 3.00 s → 2.97 s con `--compensate-delay`.

### 3.6e — Blinded Human A/B — COMPLETADA

Bundle técnico: run `34148410617`.

Guille completó la escucha A/B precomprometida.

DeepFilterNet:

```text
treatment preference     10/10
preserve preference       0/10
no preference             0/10
speech integrity failures 0
artifact failures         0
perceptual gate            PASS
```

AFFTDN:

```text
treatment preference 3
preserve preference  2
no preference        5
perceptual gate       FAIL
```

Closeout integrado:

```text
34150202283  398/398 + doctor PASS
```

Resultado: DeepFilterNet quedó **eligible for selection review**. Todavía no había autorización de denoise ni renderer.

### 3.6f — Denoiser Selection Review — COMPLETADA

Run de selección `34150663772`.

```text
selected_candidate_id = deepfilternet_0_5_6_compensated_v1
selection_status      = SELECTED_FOR_INTEGRATION_REVIEW
```

Validación final:

```text
34150832960  12/12 focused + 410/410 integrated + doctor PASS
```

La selección no cambió:

```text
product_default = preserve
denoise_authorized = false
renderer_authorized = false
auto_apply = false
```

### 3.6g — Immutable / Offline Portable DeepFilterNet Runtime — COMPLETADA TÉCNICAMENTE

DeepFilterNet 0.5.6 se integra en el portable mediante un contrato exacto:

```text
candidate = deepfilternet_0_5_6_compensated_v1
runtime path = Tools/deepfilter/bin/deep-filter.exe
asset SHA-256 = 75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915
asset size = 26912256 bytes
runtime download = forbidden
PATH fallback = forbidden
```

Run `34211660270`:

```text
14/14 focused PASS
portable build PASS
exact provenance PASS
offline execution with outbound network blocked PASS
tampered binary fail-closed PASS
418 integrated tests OK
development doctor PASS
portable doctor PASS
```

Artifact ligero `10050110122`, ZIP SHA-256 `c27f8a0ddfaa88bfdfa36bf8c79d6b4ec74198669f75cbfbb427648c6d04de89`.

**3.6g no implementa renderer y no autoriza denoise.**

Siempre:

```text
product_default = preserve
denoise_authorized = false
renderer_authorized = false
auto_apply = false
```

Detalle persistente: `Validation/phase3-denoiser-portable-runtime.json`.

### 3.6h — Denoise Plan Proposal + Explicit Execution Authorization — SIGUIENTE

Antes de cualquier renderer:

1. crear un `denoise_plan_proposal` independiente y no ejecutable;
2. bind exacto al source/output acreditado y su SHA vigente;
3. bind exacto al candidato `deepfilternet_0_5_6_compensated_v1` y al contrato runtime 3.6g;
4. congelar CLI/parámetros y política temporal de forma auditable;
5. crear autorización explícita separada con actor + reason;
6. stale/tamper fail-closed;
7. proposal != authorization;
8. no producir media tratado todavía;
9. mantener `preserve` y `auto_apply=false`.

### 3.6i+ — Denoise Renderer / Verification / Human Closeout

Sólo después de 3.6h y de una autorización válida:

- renderer derivado, nunca overwrite;
- revalidación completa inmediatamente antes de ejecución;
- verificación técnica independiente;
- human perceptual close-out antes de generalizar la vía de tratamiento.

### 3.7+ — Join treatment

Smoothing/crossfade sólo si existe evidencia A/B perceptual específica de mejora respecto al join directo ya validado. No introducir procesamiento por defecto por conveniencia estética.

## Fase 4 — UX mínima

Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, aprobar/rechazar, autorizar, renderizar y abrir outputs. Sólo después de cerrar Fase 3.

## Fase 5 — Portable Release Hardening

Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras

Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. cerrar documentalmente y validar post-persistencia 3.6g;
2. crear 3.6h plan proposal no ejecutable;
3. crear autorización explícita stale-safe separada;
4. sólo después plantear renderer 3.6i;
5. mantener human close-out de normalización pendiente;
6. mantener join smoothing bloqueado hasta evidencia A/B específica.

No relajar thresholds post hoc y no publicar Release sin autorización expresa de Guille.
