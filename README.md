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

- Fase 0 — Bootstrap: ✅
- Fase 0.5 — Technology harvest: ✅
- Fase 1A — Portable Foundation: ✅
- Fase 1B — Ingesta dual + sync/drift: ✅
- Fase 1C — Transcripción/VAD + español real: ✅
- Fase 2A–2D — Semántica, protección, joins y eligibility: ✅
- Fase 2E — Promotion → approval → authorization → semantic render → human close-out: ✅ **CLOSE_OUT_READY**
- Fase 3.1–3.5d — Quality audit + normalization technical foundation: ✅
- Human perceptual close-out de normalización: ⏳ **pendiente**
- Fase 3.6a — Noise Evidence Audit: ✅ measurement-only
- Fase 3.6b — Denoise Evaluation Corpus: ✅ 40 pares clean/noisy congelados
- Fase 3.6c — Objective Baseline: ✅ 40/40
- Fase 3.6d — Candidate Objective Comparison: ✅
- Fase 3.6e — Blind Human A/B: ✅ **CLOSED**
- Fase 3.6f — Selection Review: ✅ **DeepFilterNet 0.5.6 seleccionado para integration review**
- Fase 3.6g — Portable Runtime Contract: ✅ **CLOSED**
- Tratamiento denoise ejecutable en producto: 🚫 **NO AUTORIZADO**
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
technical verification → human review → Phase 2E closeout
  ↓
audiovisual_quality_audit
  ├→ normalization review/approval/plan/auth/render/technical verify
  │  └→ human perceptual normalization review [PENDING]
  │
  └→ noise_evidence_audit
      ↓
      frozen denoise corpus
      ↓
      objective baseline
      ↓
      candidate comparison
      ↓
      blinded human A/B
      ↓
      deterministic selection review
      ↓
      immutable/offline portable DeepFilterNet runtime
      ↓
      explicit denoise plan + execution-authorization design [NEXT]
```

Invariantes:

```text
measurement != treatment decision
treatment decision != treatment authorization
noise measurement != denoise decision
denoiser selection != denoise authorization
portable runtime availability != renderer authorization
plan != execution authorization
preserve = default
auto_apply = false
original overwrite = forbidden
```

## Portable / ML validado

- Core portable `33600174568`: PASS.
- ML frozen `33621357438`: PASS.
- Sync hardening `33639009841`: PASS.
- Target Spanish `33656235038`: WER `1.64%`, RTF `0.4854`, word timestamps PASS, automatic edits 0.

Modelo objetivo: **`large-v3-turbo`**.

La estrategia de transcripción de producto sigue siendo `single_pass` por defecto. `deterministic_overlap_12s_3s_repeat_consensus_v1` está expuesta como opt-in explícito y fue la estrategia validada para el close-out 2E.5.

## Fase 3.6 — Denoise evidence → selection → portable runtime

### 3.6a–c — medición y corpus

`noise_evidence_audit` es measurement-only: ninguna métrica de ruido activa tratamiento.

El corpus denoise congelado es `voicebank_demand_official_test_balanced_v1`, derivado del test oficial VoiceBank+DEMAND, con licencia CC BY 4.0 y hashes de materialización. Contiene **40 pares clean/noisy** a 48 kHz con dos speakers, cinco categorías de ruido y cuatro niveles SNR por bloque seleccionado.

La baseline objetiva usa clean/noisy pareados y política precomprometida `paired_clean_noisy_sisdr_stoi_v1`. Las métricas son evidencia comparativa, no autorización.

### 3.6d — comparación de candidatos

Se evaluaron candidatos sobre los mismos 40 casos y clean controls. Ningún resultado objetivo podía seleccionar por sí solo un filtro ni cambiar `preserve`.

### 3.6e — A/B humano ciego

Guille escuchó el bundle ciego completo. El remapeo validado por código produjo:

```text
DeepFilterNet 0.5.6   treatment 10/10 | preserve 0 | empate 0 | gate PASS
afftdn                treatment  3/10 | preserve 2 | empate 5 | gate FAIL
speech integrity FAIL = 0
artifact FAIL         = 0
```

Run final de reconstrucción/revisión: `34150202283` — **398/398 + doctor PASS**.

### 3.6f — selección determinista

Único candidato seleccionado para integration review:

```text
deepfilternet_0_5_6_compensated_v1
mean SI-SDR delta vs preserve = +9.870134 dB
mean STOI delta vs preserve   = +0.0111297
SI-SDR positive cases         = 40/40
STOI positive cases           = 27/40
max |raw duration delta|      = 0.03 s
clean-control STOI mean       = 0.99542798
clean-control NRMSE mean      = 0.03238068
```

No se inventó un threshold numérico post hoc para clean controls. Run final `34150832960`: **410/410 + doctor PASS**.

### 3.6g — runtime portable seleccionado

DeepFilterNet quedó congelado como dependencia portable de **integration review**, no como tratamiento autorizado:

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

Validación Windows final `34211660270`:

```text
focused contract tests  14/14 PASS
portable build           PASS
provenance gate          PASS
offline smoke            PASS — outbound network blocked for exact executable
timeline smoke           3.00 s → 2.97 s; Δ=-0.03 s ≤ 0.05 s
tamper fail-closed       PASS
integrated regression    418 tests OK (13 skipped)
development doctor       PASS
portable doctor          PASS
```

Evidencia: `Validation/phase3-denoiser-portable-runtime.json`. El closeout está además ligado por tests permanentes a la selección 3.6f, policy congelada, asset, run y artifact.

## Normalización

La vía `ebu_r128_programme` sigue siendo opt-in y técnicamente validada:

```text
target              -23 LUFS
max true peak        -1 dBTP
lra policy           preserve_measured_lra
dynamic fallback     forbidden
auto_apply           false
```

Su technical PASS **no equivale a human perceptual PASS**; ese close-out humano sigue pendiente.

## Siguiente trabajo — Fase 3.6h

Diseñar y congelar la cadena **no ejecutable** de denoise:

```text
selected candidate + selection evidence + portable runtime evidence
+ accredited source/quality/noise bindings
→ denoise plan proposal
→ explicit approval / execution authorization
→ future renderer gate
```

La siguiente etapa debe ser stale/tamper-safe y mantener separados plan, aprobación y autorización. **No implementar todavía un renderer que trate audio ni cambiar el default `preserve`.**

Join smoothing/crossfade continúa bloqueado hasta evidencia A/B perceptual específica.

Después: cierre restante de Fase 3, Fase 4 UX mínima y Fase 5 Portable Release Hardening.

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
