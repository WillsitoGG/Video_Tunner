# Phase 3.4–3.5 — Normalization Technical Foundation

Fecha: 2026-09-07

Estado: **TECHNICAL FOUNDATION PASS / HUMAN PERCEPTUAL CLOSE-OUT PENDING**.

Este documento acredita únicamente la vía opcional de normalización standards-based construida sobre un output 2E ya válido. No cambia el comportamiento audiovisual por defecto del producto.

```text
product default = preserve
normalization auto-selection = false
auto_apply = false
denoise = not authorized
join smoothing / crossfade = not authorized
```

## 1. Base normativa y de implementación

Perfil review-only:

```text
ebu_r128_programme
Programme Loudness target = -23 LUFS
Programme Loudness tolerance used by technical verifier = ±0.5 LU
Maximum True Peak Level = -1 dBTP
standard = EBU R 128 v5.0, November 2023
measurement basis = ITU-R BS.1770-5 / EBU Mode
```

Fuente primaria EBU:

- https://tech.ebu.ch/publications/r128
- https://tech.ebu.ch/docs/r/r128.pdf

EBU R 128 v5 mantiene el target de -23 LUFS; el historial oficial documenta la tolerancia de ±0.5 LU para Programme Loudness y la recomendación establece que el True Peak Level durante producción no exceda -1 dBTP.

La política de LRA de Video_Tunner **no inventa un target universal**. Para esta foundation:

```text
target_lra = measured_lra
lra_policy = preserve_measured_lra
```

FFmpeg `loudnorm` exige un LRA target para el filtro, pero EBU R 128 usa LRA como descriptor y no prescribe un único target LRA universal para toda producción. Por tanto se preserva la dinámica medida en vez de introducir compresión no justificada.

Referencia de implementación FFmpeg `loudnorm`:

- https://ffmpeg.org/ffmpeg-filters.html#loudnorm
- https://ffmpeg.org/doxygen/trunk/af__loudnorm_8c_source.html

La foundation modela fail-closed las condiciones de LINEAR_MODE: mediciones válidas/no-sentinela, target LRA compatible y cambio de loudness compatible con el true-peak target. `dynamic_fallback_allowed=false`.

## 2. Artifact chain

```text
audiovisual_quality_audit
→ audiovisual_treatment_decision
→ normalization_profile_decision
→ normalization_approval
→ normalization_plan_proposal
→ normalization_execution_authorization
→ normalization_render_result
→ normalization_post_render_verification
→ human perceptual review (PENDING)
```

Todos los artifacts nuevos son schema v1.

## 3. 3.4 — Explicit Normalization Approval

Run `34136124997`: **15/15 PASS**.

APPROVE sólo autoriza preparar el plan siguiente:

```text
normalization_plan_preparation_authorized = true
normalization_render_authorization = false
parameters_executable = false
executable = false
auto_apply = false
```

REJECT es válido y auditable. Actor/reason son obligatorios. Cambios de SHA, target/profile snapshot o capability tampering invalidan la evidencia.

## 4. 3.5a — Linear Normalization Plan Proposal

Run inicial `34136621557`: **15/15 PASS** sobre plan/approval.

Hardening posterior, cubierto por runs 3.5c y regresión final:

- rebuild exacto del plan desde quality audit + profile decision + approval;
- comparación exacta para detectar stale/tampering;
- `target_lra = measured_lra`;
- `dynamic_fallback_allowed=false`;
- bloquea si el gain lineal requerido violaría el max true peak;
- bloquea los sentinelas de FFmpeg que impiden LINEAR_MODE (`measured_I=0`, `measured_thresh=-70`);
- LRA fuera del rango aceptado por FFmpeg bloquea;
- plan ready sigue siendo no ejecutable.

## 5. 3.5b — Normalization Execution Authorization

Run `34138226442`: **15/15 PASS**.

La autorización reconstruye y valida toda la evidencia upstream antes de aceptar el plan exacto.

APPROVE válido:

```text
authorized = true
normalization_render_authorization = true
plan_render_authorization = false
parameters_executable = false
executable = false
auto_apply = false
```

Un plan bloqueado, stale, manipulado o con mediciones upstream modificadas no puede recibir execution authorization.

## 6. 3.5c — Gated Linear Normalization Renderer

Run `34139056626`: **25/25 PASS**, incluyendo FFmpeg real.

Contrato del renderer:

1. revalida la cadena completa inmediatamente antes de FFmpeg;
2. exige que el source real coincida por SHA con el quality output 2E auditado;
3. exige exactamente 1 vídeo + 1 audio para esta foundation;
4. nunca sobrescribe el source;
5. vídeo: stream copy;
6. audio: AAC 192 kb/s tras `loudnorm` autorizado;
7. pasa a `loudnorm` las mediciones y targets exactos con `linear=true`;
8. no pasa un offset calculado con otro perfil;
9. inspecciona el summary JSON final de FFmpeg;
10. si `normalization_type != linear`, elimina el output y falla cerrado;
11. re-hashea el source después del render;
12. el propio render result no puede reclamar technical/human PASS.

E2E sintético real: MP4 12 s con 1 vídeo y audio de dos niveles distintos para obtener LRA real. La cadena completa approval→plan→authorization→render produjo un derivado lineal que alcanzó el target dentro de la tolerancia comprometida, respetó el max true peak, preservó duración y dejó intacto el SHA del source.

## 7. 3.5d — Independent Post-render Verification

Run `34139502187`: **16/16 PASS**, incluyendo el mismo E2E real extendido hasta verification.

Se distinguen expresamente:

```text
invalid_evidence
technical_normalization_fail
technical_normalization_pass
```

Evidencia stale/tampered nunca se reetiqueta como simple fallo perceptual/técnico.

Technical gate precomprometido:

```text
Programme Loudness target        -23 LUFS
Programme Loudness tolerance     ±0.5 LU
Maximum True Peak                -1 dBTP (sin relajación post hoc)
Duration tolerance               ±0.15 s
Video stream count               1
Audio stream count               1
FFmpeg normalization_type        linear
Decoded video SHA-256            source == output
```

El verifier vuelve a medir independently el output con FFmpeg y calcula SHA-256 del vídeo **decodificado** source/output, de modo que una operación de audio no puede pasar si cambia la imagen.

Incluso con technical PASS:

```text
human_perceptual_review_required = true
human_pass = false
auto_apply = false
```

## 8. Regresión integrada

Run `34139639280`:

```text
337/337 tests PASS
runtime doctor PASS
FFmpeg 9.0.1 available
FFprobe 9.0.1 available
```

No se detectaron regressions en ingesta/sync, transcripción, semántica, approvals 2E, semantic render ni post-render 2E.

## 9. Interpretación correcta

Esta evidencia sí permite afirmar:

- existe una vía de normalización `ebu_r128_programme` explícitamente opt-in y técnicamente fail-closed;
- la vía puede producir un derivado real y verificarlo técnicamente;
- el renderer detecta y prohíbe fallback dinámico;
- la imagen permanece técnicamente inalterada en el E2E validado;
- la cadena es stale/tamper-aware;
- `preserve` continúa siendo el comportamiento por defecto.

Esta evidencia **no** permite afirmar todavía:

- que normalizar mejore perceptualmente cualquier vídeo hablado;
- que el perfil EBU sea el target correcto para YouTube/web/general use;
- que el AAC 192 kb/s sea ya la política final de release para todos los inputs;
- que la vía de normalización tenga human perceptual close-out;
- que denoise o crossfade estén justificados;
- que Fase 3 esté cerrada;
- que exista autorización de release.

## 10. Siguiente trabajo

1. mantener 3.5 como opt-in technical foundation mientras falta close-out perceptual real;
2. abrir 3.6 con **denoise evidence/audit**, no con un filtro activado;
3. no seleccionar denoise automáticamente sin un corpus que contenga ruido real y controles limpios;
4. no habilitar join smoothing/crossfade salvo evidencia A/B perceptual específica;
5. mantener `preserve` y `auto_apply=false`.
