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

Detalle de 3.1–3.3: `Validation/phase3-audiovisual-quality-foundation.md`.

### 3.4 — Explicit Normalization Approval — SIGUIENTE

Objetivo inmediato: artifact stale-safe separado que permita APPROVE/REJECT de un perfil de normalización no-preserve sin convertir la selección de perfil en permiso de render.

Debe ligar al menos:

```text
quality output SHA
quality audit evidence
bypass/review treatment decision
normalization profile decision
actor + reason
```

APPROVE de 3.4 podrá autorizar como máximo la preparación del siguiente gate; no `auto_apply`, no semantic edits y no overwrite del output 2E.

### 3.5 — Normalization Preview / Derivative Render — DESPUÉS DE 3.4

Sólo después de cerrar 3.4:

1. definir parámetros ejecutables de forma explícita y auditable;
2. no inventar un LRA target porque FFmpeg lo requiera;
3. crear derivado, nunca sobrescribir output 2E;
4. verificar SHA/provenance;
5. post-treatment technical audit;
6. comparación perceptual humana antes de generalizar.

### 3.6+ — Advanced A/V audit / denoise / join treatment

- ampliar continuidad A/V y quality report end-to-end;
- denoise sólo con corpus/evidencia que demuestre valor;
- smoothing/crossfade sólo si existe evidencia perceptual de mejora respecto al join directo;
- no introducir procesamiento por defecto porque “parezca profesional”.

## Fase 4 — UX mínima

Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, aprobar/rechazar, autorizar, renderizar y abrir outputs. Sólo después de cerrar Fase 3.

## Fase 5 — Portable Release Hardening

Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras

Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. cerrar documentación/evidencia de 3.1–3.3;
2. implementar 3.4 Explicit Normalization Approval Contract;
3. validar stale/tamper/reject/approve sin capacidad de render directa;
4. ejecutar regresión completa;
5. sólo entonces diseñar 3.5 preview/derivative normalization;
6. mantener denoise y join smoothing bloqueados hasta evidencia específica.

No relajar thresholds post hoc y no publicar Release sin autorización expresa de Guille.
