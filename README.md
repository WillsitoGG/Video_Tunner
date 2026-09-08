# Video_Tunner

**Video_Tunner** es una aplicación portable para Windows 10/11 x64 orientada a la limpieza automática, inteligente, auditable y reversible de vídeo hablado.

Acepta vídeo con audio embebido o vídeo + audio externo. Antes de transcripción, VAD o decisiones temporales debe existir un **master audio** correctamente asociado a la timeline del vídeo. Los originales nunca se sobrescriben.

## Requisitos estructurales

```text
ZIP → descomprimir → ejecutar
```

Sin instalador, permisos de administrador, Python preinstalado ni FFmpeg/ffprobe del sistema. Herramientas, modelos, configuración, temporales, caches y logs se resuelven desde el árbol portable.

```text
A) vídeo + audio embebido → master audio
B) vídeo + audio externo → sync → master audio
```

Sin referencia suficiente, Video_Tunner no inventa la sincronización.

## Estado actual

**Versión:** `0.1.0-dev`

- Fase 0–1C — bootstrap, portable, ingesta/sync y transcripción/VAD: ✅
- Fase 2A–2D — semántica, protección, joins y eligibility: ✅
- Fase 2E — promotion → approval → authorization → semantic render → human close-out: ✅ **CLOSE_OUT_READY**
- Fase 3.1–3.5d — quality audit + normalization technical foundation: ✅
- Human perceptual close-out de normalización: ⏳ pendiente
- Fase 3.6a — Noise Evidence Audit: ✅ measurement-only
- Fase 3.6b — Denoise Evaluation Corpus: ✅ 40 pares clean/noisy congelados
- Fase 3.6c — Objective Baseline: ✅ 40/40
- Fase 3.6d — Candidate Objective Comparison: ✅
- Fase 3.6e — Blind Human A/B: ✅ CLOSED
- Fase 3.6f — Selection Review: ✅ DeepFilterNet 0.5.6 seleccionado para integration review
- Fase 3.6g — Portable Runtime Contract: ✅ CLOSED
- Fase 3.6h — Denoise Plan + Explicit Authorization Contract: ✅ **TECHNICAL FOUNDATION PASS**
- Autorización real por-media para denoise: 🚫 ninguna
- Denoise renderer: 🚫 no implementado
- Fase 3 completa: 🚧 en curso
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
technical verification → human review → Phase 2E closeout
  ↓
audiovisual_quality_audit
  ├→ normalization review/approval/plan/auth/render/technical verify
  │  └→ human perceptual normalization review [PENDING]
  │
  └→ noise_evidence_audit
      ↓
      frozen denoise corpus → objective baseline → candidate comparison
      ↓
      blinded human A/B → deterministic selection review
      ↓
      immutable/offline portable DeepFilterNet runtime
      ↓
      denoise_plan_proposal [NON-EXECUTABLE]
      ↓
      denoise_execution_authorization [EXPLICIT; future gated renderer only]
      ↓
      gated denoise renderer [NEXT; not implemented]
```

Invariantes:

```text
measurement != treatment decision
treatment decision != treatment authorization
noise measurement != denoise decision
denoiser evaluation != denoiser selection
denoiser selection != denoise authorization
portable runtime availability != renderer authorization
plan proposal != execution authorization
APPROVE contract capability != actual user authorization record
preserve = default
auto_apply = false
original overwrite = forbidden
```

## Portable / ML validado

```text
33600174568  portable core PASS
33621357438  portable ML PASS
33639009841  sync hardening PASS
33656235038  target Spanish PASS — WER 1.64%, RTF 0.4854
```

Modelo objetivo: **`large-v3-turbo`**.

La estrategia de transcripción de producto sigue siendo `single_pass` por defecto. `deterministic_overlap_12s_3s_repeat_consensus_v1` está expuesta como opt-in explícito y fue la estrategia validada para el close-out 2E.5.

## Fase 3.6 — Denoise evidence → selection → portable runtime → authorization contract

### 3.6a–c — medición y corpus

`noise_evidence_audit` es measurement-only: ninguna métrica de ruido activa tratamiento.

Corpus congelado: `voicebank_demand_official_test_balanced_v1`, derivado del test oficial VoiceBank+DEMAND, licencia CC BY 4.0, **40 pares clean/noisy** a 48 kHz, dos speakers, cinco clases de ruido y cuatro niveles SNR.

Baseline objetivo 3.6c:

```text
mean noisy SI-SDR = 9.16548156 dB
mean noisy STOI   = 0.95070362
```

Son observaciones descriptivas, no thresholds de producto.

### 3.6d–f — comparación, escucha y selección

DeepFilterNet 0.5.6 frente a preserve sobre 40 casos noisy:

```text
mean SI-SDR delta vs preserve = +9.87013412 dB
positive SI-SDR cases         = 40/40
mean STOI delta vs preserve   = +0.01112968
positive STOI cases           = 27/40
raw duration delta            = -0.03 s
clean-control STOI mean       = 0.99542798
clean-control NRMSE mean      = 0.03238068
```

No se inventó threshold numérico post hoc para clean controls.

Guille completó el A/B humano ciego precomprometido:

```text
DeepFilterNet  treatment 10/10 | preserve 0 | empate 0 | gate PASS
AFFTDN         treatment  3/10 | preserve 2 | empate 5 | gate FAIL
speech integrity failures = 0
artifact failures         = 0
```

Resultado 3.6f:

```text
selected_candidate_id = deepfilternet_0_5_6_compensated_v1
selection_status      = SELECTED_FOR_INTEGRATION_REVIEW
```

Selección no equivale a autorización.

### 3.6g — runtime portable seleccionado

```text
version                0.5.6
asset                   deep-filter-0.5.6-x86_64-pc-windows-msvc.exe
SHA-256                 75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915
size                    26,912,256 bytes
portable path           Tools/deepfilter/bin/deep-filter.exe
CLI                     --compensate-delay --output-dir <output_dir> <input_wav>
runtime download        forbidden
PATH lookup              forbidden
product default          preserve
denoise_authorized       false
renderer_authorized      false
auto_apply               false
```

Run técnico original `34211660270`; post-persistencia `34219441077`:

```text
20/20 focused PASS
424 integrated tests OK
13 skipped
offline smoke PASS
tamper fail-closed PASS
development doctor PASS
portable doctor PASS
```

Evidencia: `Validation/phase3-denoiser-portable-runtime.json`.

### 3.6h — plan + explicit authorization contract

Nuevos artifacts de foundation:

```text
denoise_plan_proposal            schema v1
denoise_execution_authorization  schema v1
```

El plan se reconstruye exactamente y queda ligado a:

```text
noise_evidence_audit + fingerprint
quality output SHA actual
selection review 3.6f + fingerprint
selected candidate exact
runtime contract 3.6g + fingerprint
DeepFilterNet asset identity
CLI --compensate-delay
temporal tolerance 0.05 s
```

`evidence_sufficient=true` sólo acredita **cobertura de medición suficiente para preparar parámetros**. Nunca significa que el vídeo necesite denoise. Cobertura insuficiente bloquea el plan sin reclasificarse como problema de ruido.

Plan ready sigue siendo no ejecutable:

```text
parameters_defined = true
parameters_executable = false
denoise_authorized = false
denoise_render_authorization = false
plan_render_authorization = false
renderer_available = false
executable = false
auto_apply = false
```

La autorización exige `APPROVE`/`REJECT`, actor y reason. Un `APPROVE` válido sólo puede conceder una autorización estrecha para un **futuro renderer gated** que deberá revalidar toda la cadena:

```text
authorized = true
denoise_render_authorization = true
plan_render_authorization = false
parameters_executable = false
renderer_available = false
executable = false
auto_apply = false
```

Esto es una **capability contractual**, no una autorización real ya emitida. En 3.6h:

```text
real_user_authorization_record_created = false
real_user_media_authorized_for_denoise = false
denoise_renderer_implemented = false
treated_media_generated = false
product_default = preserve
auto_apply = false
```

Run `34220351609`:

```text
focused contracts = 38/38 PASS
integrated regression = 445/445 PASS
doctor = PASS
```

Evidencia: `Validation/phase3-denoise-plan-authorization-foundation.json`.

## Normalización

La vía `ebu_r128_programme` sigue siendo opt-in y técnicamente validada:

```text
target          -23 LUFS
max true peak    -1 dBTP
lra policy       preserve_measured_lra
dynamic fallback forbidden
auto_apply       false
```

Su technical PASS **no equivale a human perceptual PASS**; ese close-out humano sigue pendiente.

## Siguiente trabajo — Fase 3.6i

Diseñar e implementar la **technical foundation del gated denoise renderer**, usando únicamente autorización 3.6h válida y revalidada inmediatamente antes de ejecutar DeepFilterNet.

Debe seguir siendo:

- derivado, nunca overwrite;
- stale/tamper fail-closed;
- source SHA revalidado;
- candidate/runtime/CLI exactos;
- sin runtime download ni PATH fallback;
- temporal contract `|Δ raw duration| ≤ 0.05 s`;
- con resultado auditable independiente;
- sin convertir tests sintéticos en autorización real de media de Guille;
- `preserve` como default y `auto_apply=false`.

Join smoothing/crossfade continúa bloqueado hasta evidencia A/B perceptual específica.

Después: verificación técnica/human close-out del tratamiento real, cierre restante de Fase 3, Fase 4 UX mínima y Fase 5 Portable Release Hardening.

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
