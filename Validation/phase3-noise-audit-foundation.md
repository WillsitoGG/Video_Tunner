# Phase 3.6a — Noise Evidence Audit Foundation

Fecha: 2026-09-07

Estado: **MEASUREMENT FOUNDATION PASS / DENOISE NOT AUTHORIZED**.

Este bloque añade evidencia acústica reproducible sobre un output Phase 2E ya acreditado. No selecciona filtros, no decide que un vídeo "necesita denoise" y no modifica media.

```text
measurement != denoise decision
denoise decision != denoise authorization
preserve = default
denoise_authorized = false
auto_apply = false
```

## 1. Artifact

```text
record_type = noise_evidence_audit
schema_version = 1
```

Cadena:

```text
Phase 2E technical PASS output
→ audiovisual_quality_audit
→ explicit speech timing evidence
→ guarded non-speech windows
→ noise_evidence_audit
→ [future: corpus-backed denoise evaluation]
```

El artifact exige:

- `audiovisual_quality_audit` completo y válido;
- output Phase 2E vigente por SHA-256;
- `quality_audit_sha256` válido;
- `speech_evidence_sha256` explícito;
- speech intervals no solapados y dentro de la timeline real;
- output inmutable durante la medición.

## 2. Measurement contract precomprometido

Antes de observar resultados del gate se fijó:

```text
analysis PCM              mono PCM16 @ 16 kHz
frame size                0.20 s
non-speech guard          0.15 s respecto a cada borde speech
minimum NS window         0.40 s
minimum NS windows        2
minimum total NS coverage 2.0 s
```

Estos valores son criterios de **suficiencia de evidencia**, no thresholds de ruido ni parámetros de denoise.

El audit calcula por separado:

```text
non-speech energy
- frame count
- nonzero RMS frame count
- digital silence frame count
- median RMS dBFS
- p90 RMS dBFS
- max peak dBFS

speech energy
- mismas métricas

speech_to_non_speech_median_rms_delta_db
```

La diferencia speech/non-speech se etiqueta explícitamente como **energy proxy**, no como SNR perceptual.

Digital silence no recibe un floor dBFS inventado: un frame RMS exactamente cero queda registrado como digital silence y su dBFS es `null`.

## 3. Evidence sufficiency

```text
sufficient =
  non_speech_window_count >= 2
  AND non_speech_seconds >= 2.0
  AND at least one complete 200 ms analysis frame exists
```

Estados:

```text
noise_measurement_complete
insufficient_noise_evidence
```

`insufficient_noise_evidence` significa únicamente que falta cobertura temporal fiable para medir; **no** implica que exista ruido ni que se necesite denoise.

## 4. Treatment firewall

Siempre:

```text
denoise_evaluated = false
denoise_authorized = false
filter_selected = false
parameters_defined = false
normalization_authorized = false
join_smoothing_authorized = false
executable = false
treatment_authorized = false
auto_apply = false
```

3.6a no contiene ningún threshold que convierta automáticamente dBFS, energy delta o cobertura en tratamiento.

## 5. Focused validation

Run `34141013261`:

```text
9/9 tests PASS
real FFmpeg MP4 + AAC E2E PASS
PHASE3_NOISE_AUDIT=PASS
```

Casos cubiertos:

- output SHA stale bloqueado antes de medir;
- speech evidence SHA inválido bloqueado;
- speech intervals solapados bloqueados;
- speech intervals fuera de timeline bloqueados;
- guard exacto de 150 ms alrededor de speech;
- cobertura insuficiente conserva denoise bloqueado;
- digital silence sin floor dBFS artificial;
- medición suficiente sigue siendo no ejecutable;
- E2E real con MP4/AAC, extracción FFmpeg a PCM y output SHA intacto.

El E2E sintético contiene background acústico bajo y dos regiones de señal speech-like más energéticas. Se utiliza sólo para comprobar que la cadena de medición distingue correctamente las ventanas conocidas; la diferencia observada no se convierte en política de producto.

## 6. Full regression

Run `34141115293`:

```text
346/346 tests PASS
doctor PASS
FFmpeg 9.0.1 available
FFprobe 9.0.1 available
```

No se detectaron regresiones en:

- portable/ingest/sync;
- Whisper/VAD contracts;
- semantic candidates/protection;
- Phase 2D/2E approval + render + closeout;
- Phase 3 quality audit/treatment decision;
- normalization 3.4–3.5d.

## 7. Interpretación correcta

Esta evidencia sí permite afirmar:

- Video_Tunner puede medir energía speech/non-speech de un output acreditado sin modificarlo;
- las ventanas non-speech se mantienen alejadas de bordes speech mediante un guard precomprometido;
- la cadena es SHA-aware y fail-closed ante timing evidence inválida;
- cobertura insuficiente se distingue de ruido medido;
- no se inventa un noise floor para silencio digital;
- no se crea ninguna capability de denoise.

Esta evidencia **no** permite afirmar todavía:

- que un determinado valor dBFS implique ruido molesto;
- que el energy delta sea SNR perceptual;
- que cualquier denoiser mejore calidad;
- que exista un threshold general de denoise;
- que denoise deba aplicarse por defecto;
- que Fase 3 esté cerrada.

## 8. Siguiente trabajo — 3.6b

Construir primero corpus/evidencia de evaluación con:

1. noisy speech real o reproduciblemente degradado;
2. clean/control comparable;
3. provenance y licencia compatibles con el proyecto;
4. diversidad suficiente de tipos de ruido y niveles;
5. métricas objetivas usadas sólo como evidencia auxiliar;
6. comparación perceptual humana antes de aprobar cualquier filtro o parámetros.

No implementar todavía un renderer de denoise.
