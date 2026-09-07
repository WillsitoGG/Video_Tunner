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
- Fase 3 — tratamiento audiovisual ejecutable: 🚧 **todavía no autorizado**
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
  ↓
audiovisual_treatment_decision
  ↓
normalization_profile_decision
```

Invariantes:

```text
measurement != treatment decision
treatment decision != treatment authorization
profile selection != normalization authorization
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

### 3.1 Quality Audit v1

`audiovisual_quality_audit` mide loudness integrado, true peak y LRA mediante FFmpeg sin aplicar tratamiento. Está ligado por SHA a un output que ya debe haber pasado el gate técnico 2E.

```text
34124957783  focused Windows + real FFmpeg — 8/8 PASS
34125110506  full regression — 283/283 + doctor PASS
```

### Baseline focal real

Run `34134893725`, reutilizando exactamente el bundle que Guille escuchó en 2E.5:

```text
cases = 3
sources = 2
human PASS = 3/3
max observed |Δ loudness| = 0.40 LU
max observed |Δ true peak| = 0.04 dB
treatment_authorized = false
```

**0.40 LU y 0.04 dB son observaciones del corpus, no thresholds de producto.** Esta muestra no justifica normalización obligatoria, denoise ni smoothing/crossfade por defecto.

Detalle: `Validation/phase3-focal-quality-baseline.json`.

### 3.2 Bypass-first Treatment Decision

```text
audit sin riesgo → bypass_preserve_render
audit con riesgo → treatment_review_required
```

Un riesgo abre revisión; no elige ni autoriza un tratamiento. Run `34135210344`: 14/14 PASS.

### 3.3 Normalization Profile Contract

Perfil de producto por defecto: **`preserve`**.

Existe `ebu_r128_programme` únicamente como opt-in standards-based y review-only:

```text
target = -23 LUFS
max true peak = -1 dBTP
EBU R 128 v5.0 (November 2023)
measurement basis = ITU-R BS.1770-5 (November 2023)
```

No se extrapola como target universal de web/YouTube. Seleccionarlo exige opt-in y revisión humana y todavía **no autoriza render ni parámetros ejecutables**. Run `34135437824`: 13/13 PASS.

Detalle global: `Validation/phase3-audiovisual-quality-foundation.md`.

## Siguiente trabajo — Fase 3.4

Construir primero el **contrato explícito stale-safe de aprobación/rechazo de normalización**. Después, y sólo con evidencia propia, definir preview/derivative render y post-treatment audit. El output 2E original debe permanecer intacto.

No introducir todavía denoise ni join smoothing por defecto: la evidencia actual no los justifica.

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
