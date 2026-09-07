# Video_Tunner

**Video_Tunner** es una aplicación portable para Windows 10/11 x64 orientada a la limpieza automática, inteligente, auditable y reversible de vídeo hablado.

Acepta vídeo con audio embebido o vídeo + audio externo. Antes de transcripción, VAD o decisiones temporales debe existir un **master audio** correctamente asociado a la timeline del vídeo. Los originales nunca se sobrescriben.

## Requisitos estructurales

```text
ZIP → descomprimir → ejecutar
```

Sin instalador, permisos de administrador, Python preinstalado ni FFmpeg/ffprobe preinstalados. Herramientas, modelos, configuración, temporales, caches y logs se resuelven desde el árbol portable.

```text
A) vídeo + audio embebido → master audio
B) vídeo + audio externo → sync → master audio
```

Sin referencia suficiente, Video_Tunner no inventa la sincronización.

## Estado actual

**Versión:** `0.1.0-dev`

- Fase 0 — Bootstrap: ✅
- Fase 0.5 — Technology harvest: ✅
- Fase 1A — Portable Foundation: ✅
- Fase 1B — Ingesta dual + sync/drift: ✅
- Fase 1C — Transcripción/VAD + español real: ✅
- Fase 2A–2C — Semántica + protección + validación real: ✅
- Fase 2D — Scope + fillers + join + eligibility: ✅ **foundation/evidence cerrada**
- Fase 2E — Promotion → approval → proposal → authorization → semantic render → human close-out: ✅ **CLOSE_OUT_READY**
- Fase 3.1 — Audiovisual Quality Audit v1: ✅ **foundation validada**
- Fase 3 focal real — ORIGINAL/RENDERED sobre los 3 joins 2E.5: ✅
- Fase 3.2 — Bypass-first Treatment Decision: ✅ **foundation validada**
- Fase 3.3 — Normalization Profile Contract: ✅ **review-only foundation**
- Fase 3.4 — Explicit Normalization Approval: ✅ **foundation validada**
- Fase 3.5a–d — plan → execution authorization → real linear render → technical verification: ✅ **technical foundation validada**
- Human perceptual close-out de normalización: ⏳ **pendiente**
- Fase 3.6a — Noise Evidence Audit: ✅ **measurement-only foundation validada**
- Denoise ejecutable: 🚫 **no autorizado**
- Fase 3 completa: 🚧 **en curso**
- Release pública: ninguna

Video_Tunner es producto/repo propio, no un fork.

## Arquitectura actual

```text
sources
  ↓
ingest / sync
  ↓
MASTER AUDIO + video timeline
  ↓
Whisper word-level + Silero VAD
  ↓
candidates → scopes/fillers → join → acoustic join → semantic decisions
  ↓
eligibility → promotion → individual approval
  ↓
bounded proposal → global execution authorization
  ↓
semantic_edit_plan → semantic render gate → FFmpeg
  ↓
semantic_render_verification → semantic_render_human_review
  ↓
phase2e_closeout_decision
  ↓
audiovisual_quality_audit
  ├→ audiovisual_treatment_decision
  │   ↓
  │ normalization_profile_decision
  │   ↓
  │ normalization_approval
  │   ↓
  │ normalization_plan_proposal
  │   ↓
  │ normalization_execution_authorization
  │   ↓
  │ gated linear normalization render
  │   ↓
  │ normalization_post_render_verification
  │   ↓
  │ human perceptual review [PENDING]
  │
  └→ noise_evidence_audit [MEASUREMENT-ONLY]
      ↓
      denoise corpus/evaluation [NEXT; no renderer]
```

Invariantes:

```text
measurement != treatment decision
treatment decision != treatment authorization
noise measurement != denoise decision
denoise decision != denoise authorization
profile selection != normalization approval
normalization approval != execution authorization
technical normalization PASS != human perceptual PASS
Phase 3 favorable signal != rescue of failed Phase 2E
preserve = default
auto_apply = false
```

## Portable / ML validado

- Core portable `33600174568`: PASS.
- ML frozen `33621357438`: PASS.
- Sync hardening `33639009841`: PASS.
- Target Spanish `33656235038`: WER `1.64%`, RTF `0.4854`, word timestamps PASS, automatic edits 0.

Modelo objetivo: **`large-v3-turbo`**.

La estrategia de transcripción de producto sigue siendo `single_pass` por defecto. `deterministic_overlap_12s_3s_repeat_consensus_v1` está expuesta como opt-in explícito y fue la estrategia validada para el close-out 2E.5.

## Artifacts principales

```text
analysis.json                            schema v9
promotion_approval.json                  schema v1
approved_edit_plan_proposal.json         schema v1
semantic_execution_authorization.json    schema v1
semantic_edit_plan.json                  schema v1
semantic_render_verification             schema v1
semantic_render_human_review             schema v1
phase2e_closeout_decision                 schema v1
audiovisual_quality_audit                 schema v1
audiovisual_treatment_decision            schema v1
normalization_profile_decision            schema v1
normalization_approval                    schema v1
normalization_plan_proposal               schema v1
normalization_execution_authorization     schema v1
normalization_render_result               schema v1
normalization_post_render_verification    schema v1
noise_evidence_audit                      schema v1
```

## Evidencia principal Fase 2E

```text
33909424933  2E.4 authorization/render-gate core — 201/201 + doctor PASS
33909625346  2E.4 real FFmpeg semantic render E2E — 202/202 + doctor PASS
34119952855  2E.5 real AMI technical close-out — 3/3 technical PASS, 2 sources
human close-out                       — 3/3 perceptual PASS, 0 FAIL, CLOSE_OUT_READY
34124101770  cleaned Phase 2E branch — 275/275 + doctor PASS
```

Evidencia permanente: `Validation/phase2e-post-render-closeout.md` y `Validation/phase2e-human-closeout/`.

## Fase 3 — estado actual

### 3.1–3.3 — measurement / policy foundation

`audiovisual_quality_audit` mide loudness integrado, true peak y LRA sin tratamiento. El baseline focal real reutilizó exactamente los 3 pares ya escuchados en 2E.5:

```text
cases = 3
sources = 2
human PASS = 3/3
max observed |Δ loudness| = 0.40 LU
max observed |Δ true peak| = 0.04 dB
```

**0.40 LU y 0.04 dB son observaciones del corpus, no thresholds de producto.** Esa muestra no justifica normalización obligatoria, denoise ni smoothing/crossfade por defecto.

El comportamiento por defecto de Fase 3 es `preserve`. Un riesgo sólo abre revisión.

Perfil standards-based disponible únicamente como opt-in:

```text
ebu_r128_programme
target = -23 LUFS
max true peak = -1 dBTP
EBU R 128 v5.0 (November 2023)
measurement basis = ITU-R BS.1770-5
```

No se extrapola como target universal de web/YouTube.

### 3.4–3.5d — normalization technical foundation

Cadena explícita y stale-safe:

```text
profile decision
→ explicit normalization approval
→ linear normalization plan proposal
→ normalization execution authorization
→ gated FFmpeg render
→ independent technical post-render verification
```

Política de tratamiento:

```text
lra_policy = preserve_measured_lra
dynamic_fallback_allowed = false
source overwrite = forbidden
video = stream copy
auto_apply = false
```

El plan sólo queda ready si FFmpeg puede trabajar en modo lineal sin violar el true-peak target. El renderer vuelve a validar toda la cadena inmediatamente antes de FFmpeg y elimina el derivado si `normalization_type != linear`.

El verificador independiente comprueba además:

```text
Programme Loudness       -23 LUFS ±0.5 LU
Maximum True Peak        -1 dBTP
Duration delta           ≤ 0.15 s
Video streams            1
Audio streams            1
Decoded video SHA-256    source == output
```

Evidencia:

```text
34136124997  3.4 approval contract — 15/15 PASS
34136621557  3.5a linear plan foundation — 15/15 PASS
34138226442  3.5b execution authorization — 15/15 PASS
34139056626  3.5c real gated normalization render — 25/25 PASS
34139502187  3.5d independent post-render verification — 16/16 PASS
34139639280  full regression through 3.5d — 337/337 + doctor PASS
```

**Technical PASS no equivale a human perceptual PASS.** La normalización sigue siendo opt-in y su close-out perceptual humano está pendiente.

### 3.6a — Noise Evidence Audit

Foundation measurement-only sobre un output 2E acreditado:

```text
analysis PCM              mono PCM16 @ 16 kHz
frame size                0.20 s
non-speech guard          0.15 s
minimum NS window         0.40 s
minimum NS windows        2
minimum total NS coverage 2.0 s
```

La suficiencia sólo decide si **hay evidencia medible**. No existe threshold de dBFS que active denoise.

Métricas:

```text
speech/non-speech median RMS dBFS
p90 RMS dBFS
max peak dBFS
digital silence frame count
speech-to-non-speech median RMS delta (energy proxy only)
```

Evidencia:

```text
34141013261  focused noise audit + real MP4/AAC E2E — 9/9 PASS
34141115293  full regression through 3.6a — 346/346 + doctor PASS
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

## Siguiente trabajo — Fase 3.6b

Seleccionar y congelar primero un **corpus de evaluación denoise** con noisy speech + clean/control comparable, provenance/licencia clara y diversidad de ruido. Las métricas objetivas serán evidencia auxiliar; antes de autorizar cualquier filtro deberá existir comparación perceptual humana.

No implementar todavía un renderer de denoise.

Join smoothing/crossfade continúa bloqueado: los joins 2E.5 ya pasaron escucha humana sin smoothing y no existe evidencia A/B que justifique añadir procesamiento.

Después: Fase 4 UX mínima y Fase 5 Portable Release Hardening.

## Principios

- portable por diseño;
- local-first;
- originales intactos;
- sync fiable antes de IA temporal;
- conservador por defecto;
- ante duda: KEEP/REVIEW;
- GitHub como source of truth;
- CI deliberada y workflows pesados manual-only;
- `preserve` audiovisual por defecto;
- `auto_apply=false`;
- no GitHub Release sin autorización expresa de Guille.

Consulta `AGENTS.md`, `ROADMAP.md`, `RELEASE_STATUS.md`, `UPSTREAM_SOURCES.md` y `Validation/`.
