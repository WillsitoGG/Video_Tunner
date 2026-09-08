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
- Fase 3.6i — Gated Denoise Renderer: ✅ **TECHNICAL FOUNDATION PASS**
- Autorización real por-media de Guille para denoise: 🚫 ninguna emitida
- Media real de Guille procesada por denoise: 🚫 ninguna
- Denoise post-render technical verifier independiente: 🚧 siguiente bloque, 3.6j
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
      denoise_execution_authorization [EXPLICIT; per-media gate]
      ↓
      gated DeepFilterNet denoise renderer [TECHNICAL FOUNDATION]
      ↓
      independent denoise post-render technical verification [NEXT]
      ↓
      human perceptual denoise closeout [LATER]
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
authorization record != successful render
render complete != technical verification PASS
technical PASS != human perceptual PASS
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

## Fase 3.6 — Denoise evidence → selection → portable runtime → authorization → renderer

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
PATH lookup              forbidden en producto
product default          preserve
denoise_authorized       false
renderer_authorized      false
auto_apply               false
```

Run técnico original `34211660270`; post-persistencia `34219441077`.

Evidencia: `Validation/phase3-denoiser-portable-runtime.json`.

### 3.6h — plan + explicit authorization contract

Artifacts:

```text
denoise_plan_proposal            schema v1
denoise_execution_authorization  schema v1
```

El plan se reconstruye exactamente y queda ligado a `noise_evidence_audit`, output SHA actual, selection review 3.6f, candidato/runtimes exactos y sus fingerprints. `evidence_sufficient=true` sólo acredita cobertura de medición suficiente para preparar parámetros; nunca significa que el vídeo necesite denoise.

Un `APPROVE` válido sólo concede permiso estrecho para el gated denoise renderer y debe ser revalidado antes de ejecutar. El artifact de autorización no ejecuta nada por sí mismo.

Cierre limpio 3.6h:

```text
34225276990
45/45 focused PASS
452/452 integrated PASS
doctor PASS
```

Evidencia: `Validation/phase3-denoise-plan-authorization-foundation.json`.

### 3.6i — gated denoise renderer technical foundation

`Source/video_tunner/denoise_render.py` implementa una ruta de tratamiento derivada y fail-closed. Sólo puede procesar si la cadena 3.6a→h sigue íntegra y existe una autorización `APPROVE` válida para el source SHA actual.

Contrato inicial:

```text
source overwrite                    forbidden
source media                        exactly 1 video + 1 audio stream
source audio                        mono only in 3.6i foundation
DeepFilter input                    PCM16 mono 48 kHz
DeepFilter CLI                      from validated plan template
                                     --compensate-delay
                                     --output-dir <output_dir> <input_wav>
raw duration tolerance              |Δ| <= 0.05 s
alignment search                    forbidden
time shift                          forbidden
level matching                      forbidden
timeline correction                 right-tail trim or digital-silence pad only
video output                        stream copy
audio output                        AAC 192k
-shortest                           forbidden
render complete                     != technical PASS
technical PASS                      != human perceptual PASS
product default                     preserve
auto_apply                          false
```

El CLI ejecutado se materializa desde el `arguments_template` del plan previamente reconstruido y validado; un template alterado o extendido falla cerrado.

Gate final 3.6i `34231340544` / job `102077969922`:

```text
immutable FFmpeg + DeepFilterNet    PASS
focused contracts                   49/49 PASS
real DeepFilter synthetic E2E       1/1 PASS
integrated regression               466/466 PASS
integrated skips                    0
doctor                              PASS
```

Timeline observada en el E2E sintético, no threshold nuevo:

```text
input frames                        144000
raw output frames                   142560
raw frame delta                     -1440
raw duration delta                  -0.030 s
normalization                       pad_right_tail_silence
final frames                        144000
alignment/time-shift/level-match    false / false / false
```

Esto acredita la **technical foundation del renderer**, no una autorización real ni un PASS perceptual. En 3.6i:

```text
real_user_authorization_record_created = false
real_user_media_authorized_for_denoise = false
real_user_media_processed              = false
real_user_treated_media_generated      = false
stereo_or_multichannel_generalized     = false
independent_post_render_verifier       = false
product_default                        = preserve
auto_apply                             = false
```

Evidencia: `Validation/phase3-denoise-render-foundation.json`.

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

## Siguiente trabajo — Fase 3.6j

Implementar el **independent denoise post-render technical verifier**.

Debe verificar de forma independiente, sin confiar en el `denoise_render_result` para declarar calidad:

- binding exacto a source, authorization, plan y output derivados;
- hashes vigentes y ausencia de overwrite;
- media layout y timeline/duración;
- preservación del vídeo esperada para `stream copy`;
- output de audio válido y auditable;
- cumplimiento del contrato temporal precomprometido;
- ausencia de claims prematuros de technical/human PASS;
- fail-closed ante evidencia stale/tampered.

Después de 3.6j seguirá siendo necesaria la ruta humana de close-out antes de generalizar denoise. **No se tratará media real de Guille sin una autorización per-media explícita y vigente.**

Join smoothing/crossfade continúa bloqueado hasta evidencia A/B perceptual específica.

Después: human denoise treatment closeout, human normalization closeout pendiente, cierre restante de Fase 3, Fase 4 UX mínima y Fase 5 Portable Release Hardening.

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
