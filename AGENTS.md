# AGENTS.md — Video_Tunner

Contexto técnico permanente para agentes. Referencia maestra externa vigente: `00.Contexto y Reglas de Trabajo_GitHub_Video_Tunner_v3`.

## 1. Invariantes

Video_Tunner debe producir vídeo hablado limpio, natural, fiel, sincronizado, auditable y reversible en Windows 10/11 x64.

Obligatorio:

1. portable real: ZIP → descomprimir → ejecutar;
2. vídeo con audio embebido o vídeo + audio externo;
3. resolver master audio antes de análisis temporal;
4. Whisper, VAD y acoustic join usan exactamente el mismo master acreditado;
5. auto-sync sólo con evidencia suficiente; override/manual fallback;
6. original siempre intacto;
7. cada artifact/capability es independiente y stale-safe;
8. una señal posterior favorable nunca rescata una guarda anterior bloqueada;
9. `measurement != treatment decision != treatment authorization`;
10. `noise measurement != denoise decision != denoise authorization`;
11. candidate evaluation != candidate selection != denoise authorization;
12. selected denoiser != renderer authorization;
13. `profile selection != normalization approval != normalization execution authorization`;
14. technical normalization PASS != human perceptual PASS;
15. `preserve` audiovisual es default;
16. ningún risk finding auto-selecciona tratamiento;
17. dynamic loudnorm fallback está prohibido en la foundation validada;
18. ningún valor dBFS de 3.6a es por sí solo un threshold de denoise;
19. ninguna métrica objetiva de 3.6c–d sustituye escucha humana;
20. DeepFilterNet integrado en portable no implica denoise autorizado;
21. ante duda: KEEP/REVIEW;
22. `auto_apply=false`;
23. no release sin autorización expresa de Guille.

Cadena actual:

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD
→ candidates/scopes/fillers/join/acoustic/semantic/eligibility
→ promotion → individual approval → bounded proposal
→ global execution authorization → semantic Edit Plan
→ semantic render gate → FFmpeg
→ post-render technical verification → human review → 2E closeout
→ audiovisual quality audit
   ├→ audiovisual treatment decision
   │  → normalization profile decision
   │  → normalization approval
   │  → normalization plan proposal
   │  → normalization execution authorization
   │  → gated linear normalization render
   │  → independent normalization post-render verification
   │  → human perceptual review [PENDING]
   └→ noise evidence audit
      → frozen denoise corpus
      → objective baseline
      → candidate objective comparison
      → blinded human A/B
      → candidate selection review
      → portable selected-runtime contract
      → denoise plan/authorization [NEXT; no renderer]
```

## 2. Estado

Versión `0.1.0-dev`.

Completado:

- Fase 2D cerrada como foundation/evidence;
- Fase 2E completa — `CLOSE_OUT_READY`;
- Fase 3.1 — Audiovisual Quality Audit v1 foundation;
- Fase 3 focal real sobre los 3 joins humanos 2E.5;
- Fase 3.2 — Bypass-first Treatment Decision foundation;
- Fase 3.3 — Normalization Profile Contract foundation/review-only;
- Fase 3.4 — Explicit Normalization Approval foundation;
- Fase 3.5a — Linear Normalization Plan Proposal foundation;
- Fase 3.5b — Normalization Execution Authorization foundation;
- Fase 3.5c — real gated linear normalization renderer technical foundation;
- Fase 3.5d — independent normalization post-render verifier technical foundation;
- Fase 3.6a — Noise Evidence Audit measurement-only foundation;
- Fase 3.6b — frozen denoise evaluation corpus + materialization evidence;
- Fase 3.6c — objective noisy baseline;
- Fase 3.6d — objective candidate comparison;
- Fase 3.6e — blinded human perceptual A/B closeout;
- Fase 3.6f — denoiser selection review: DeepFilterNet selected for integration review;
- Fase 3.6g — immutable/offline portable DeepFilterNet runtime contract.

No completado:

- human perceptual close-out de normalización;
- denoise plan + explicit execution authorization;
- denoise renderer / post-render verification;
- join smoothing/crossfade evidence/treatment;
- Fase 3 closeout;
- UX/release.

## 3. Evidencia principal

```text
33600174568  Portable core PASS
33621357438  Portable ML PASS
33639009841  Sync hardening PASS
33656235038  Target Spanish PASS — WER 1.64%, RTF 0.4854
33894995584  2D.6 Human positive close-out — CLOSE_OUT_READY
33909625346  2E.4 real FFmpeg semantic render E2E PASS
34119952855  2E.5 technical close-out — 3/3 real AMI technical PASS / 2 sources
human review  2E.5 — 3/3 human perceptual PASS / CLOSE_OUT_READY
34124101770  final clean Phase 2E — 275/275 + doctor PASS
34124957783  Phase 3.1 quality audit — 8/8 + real FFmpeg E2E PASS
34125110506  Phase 3.1 full regression — 283/283 + doctor PASS
34134893725  Phase 3 focal baseline — 3 cases / 2 sources PASS
34135210344  Phase 3.2 treatment foundation — 14/14 PASS
34135437824  Phase 3.3 normalization profile — 13/13 PASS
34136124997  Phase 3.4 normalization approval — 15/15 PASS
34136621557  Phase 3.5a normalization plan — 15/15 PASS
34138226442  Phase 3.5b execution authorization — 15/15 PASS
34139056626  Phase 3.5c real normalization render — 25/25 PASS
34139502187  Phase 3.5d technical verification — 16/16 PASS
34139639280  full regression through 3.5d — 337/337 + doctor PASS
34141013261  Phase 3.6a noise audit — 9/9 + real MP4/AAC E2E PASS
34141115293  full regression through 3.6a — 346/346 + doctor PASS
34142222451  Phase 3.6b corpus materialization — 40 paired cases PASS
34143456746  Phase 3.6c objective noisy baseline — 40/40 measured
34144574712  DeepFilterNet 0.5.6 temporal smoke — 3.00 s → 2.97 s
34145308485  Phase 3.6d candidate objective comparison — PASS
34148410617  Phase 3.6e blinded human A/B bundle
34150202283  Phase 3.6e closeout validation — 398/398 + doctor PASS
34150663772  Phase 3.6f selection artifact — DeepFilterNet selected for integration review
34150832960  Phase 3.6f final validation — 410/410 + doctor PASS
34211660270  Phase 3.6g portable runtime — 14/14 focused, 418 integrated, both doctor PASS
```

Focal baseline observed only:

```text
max |Δ integrated loudness| = 0.40 LU
max |Δ true peak| = 0.04 dB
human PASS = 3/3
```

Estos valores NO son thresholds generales. No generalizar fuera del corpus.

## 4. Stack fijado

```text
faster-whisper 1.2.1
CTranslate2 4.8.1
ONNX Runtime 1.29.0
tokenizers 0.23.1
NumPy 2.5.2
PyInstaller 6.22.2
```

VAD: faster-whisper + `silero_vad_v6.onnx`. Modelo objetivo: `large-v3-turbo`.

`single_pass` sigue siendo default de transcripción. `deterministic_overlap_12s_3s_repeat_consensus_v1` es opt-in explícito y fue validada para 2E.5. No exponer estrategias no validadas.

Denoiser seleccionado para integration review:

```text
candidate_id = deepfilternet_0_5_6_compensated_v1
upstream = DeepFilterNet 0.5.6
asset = deep-filter-0.5.6-x86_64-pc-windows-msvc.exe
sha256 = 75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915
size = 26912256 bytes
runtime = Tools/deepfilter/bin/deep-filter.exe
args = --compensate-delay --output-dir <output_dir> <input_wav>
runtime_download_allowed = false
product_default = preserve
denoise_authorized = false
renderer_authorized = false
auto_apply = false
```

## 5. Schemas / artifacts

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

No mutar artifacts upstream para registrar decisiones downstream.

## 6. Fase 2E — reglas que siguen vigentes

- approval individual != autorización global;
- proposal nunca es ejecutable;
- Semantic Edit Plan sólo se renderiza mediante semantic render gate;
- source SHA + analysis/proposal/authorization/plan deben revalidarse;
- technical post-render PASS != human perceptual PASS;
- stale evidence = INVALID_EVIDENCE;
- `auto_apply=false`.

Final evidence: `Validation/phase2e-post-render-closeout.md` y `Validation/phase2e-human-closeout/`.

## 7. Fase 3.1–3.3 — Quality / Treatment / Profile

`Source/video_tunner/audiovisual_quality.py`:

- sólo acepta un output 2E técnicamente PASS y SHA vigente;
- FFmpeg `loudnorm` se usa únicamente como medidor;
- se leen integrated LUFS, true peak, LRA y threshold;
- no se genera media tratado;
- ningún finding crea capability.

`audiovisual_treatment_decision`:

```text
no risks → bypass_preserve_render
risk → treatment_review_required
```

Default: `preserve`.

Perfil opt-in/review-only:

```text
ebu_r128_programme
-23 LUFS
max true peak -1 dBTP
EBU R 128 v5.0
measurement basis ITU-R BS.1770-5
```

No usar un supuesto “YouTube -14 LUFS” como default ni como estándar universal.

## 8. Fase 3.4–3.5d — Normalization technical foundation

### 3.4 approval

- APPROVE / REJECT explícito;
- actor + reason obligatorios;
- binding exacto al profile decision y SHA;
- APPROVE sólo habilita preparación del plan;
- stale/tamper fail-closed.

### 3.5a plan

```text
mode = linear_only_fail_closed
lra_policy = preserve_measured_lra
dynamic_fallback_allowed = false
```

El plan se reconstruye exactamente desde quality audit + profile decision + approval. Sólo queda ready si:

- mediciones son finitas;
- `measured_I != 0` y `measured_thresh != -70`;
- measured LRA entra en rango compatible con FFmpeg;
- preservar measured LRA es viable;
- el gain hacia target no viola max true peak.

Plan ready sigue sin ser ejecutable.

### 3.5b execution authorization

APPROVE válido:

```text
authorized = true
normalization_render_authorization = true
plan_render_authorization = false
parameters_executable = false
executable = false
auto_apply = false
```

El plan directo nunca se renderiza.

### 3.5c renderer

- revalida cadena exacta inmediatamente antes de FFmpeg;
- source SHA real debe ser el quality output acreditado;
- no overwrite;
- foundation actual exige exactamente 1 vídeo + 1 audio;
- vídeo stream-copy;
- audio AAC 192k tras `loudnorm` autorizado;
- `linear=true` con mediciones exactas;
- si FFmpeg reporta `normalization_type != linear`, eliminar output y fallar;
- source SHA se revalida después del render;
- render result no puede autodeclararse technical/human PASS.

### 3.5d independent verifier

Precommit técnico:

```text
Programme Loudness       -23 LUFS ±0.5 LU
Maximum True Peak        -1 dBTP
Duration delta           ≤ 0.15 s
Video streams            1
Audio streams            1
FFmpeg normalization     linear
Decoded video SHA-256    source == output
```

Distinguir siempre:

```text
invalid_evidence
technical_normalization_fail
technical_normalization_pass
```

Incluso `technical_normalization_pass` implica:

```text
human_perceptual_review_required = true
human_pass = false
auto_apply = false
```

Detalle: `Validation/phase3-normalization-foundation.md`.

## 9. Fase 3.6a–g — Denoise evidence, selection y portable runtime

### 3.6a — Noise Evidence Audit

`Source/video_tunner/noise_audit.py` es measurement-only.

Precommit de evidencia:

```text
analysis PCM              mono PCM16 @ 16 kHz
frame size                0.20 s
non-speech guard          0.15 s
minimum NS window         0.40 s
minimum NS windows        2
minimum total NS coverage 2.0 s
```

La suficiencia sólo acredita cobertura para medir. Ninguna métrica activa denoise.

### 3.6b — Frozen evaluation corpus

Corpus: `voicebank_demand_official_test_balanced_v1`.

```text
paired noisy + clean cases = 40
speakers = 2 (p232, p257)
noise classes = bus, cafe, living, office, psquare
SNRs = 17.5, 12.5, 7.5, 2.5 dB
sample rate = 48 kHz
license = CC BY 4.0
```

Los archivos reales no se versionan en Git; se persisten hashes/provenance y se materializan sólo para validación.

### 3.6c — Objective baseline

Métricas precomprometidas:

```text
SI-SDR
STOI
```

Baseline noisy descriptivo sobre 40/40 casos. No hay thresholds de aceptación ni ranking autorizado.

### 3.6d — Candidate objective comparison

Candidatos:

```text
preserve_noisy_control_v1
ffmpeg_afftdn_fixed_v1
deepfilternet_0_5_6_compensated_v1
```

DeepFilterNet, en los 40 casos noisy:

```text
mean SI-SDR delta vs preserve = +9.87013412 dB
positive SI-SDR cases = 40/40
mean STOI delta vs preserve = +0.01112968
positive STOI cases = 27/40
raw duration delta = -0.03 s
```

Clean controls DeepFilterNet:

```text
case_count = 40
mean STOI = 0.99542798
mean normalized RMSE = 0.03238068
numeric acceptance threshold applied = false
```

`ffmpeg_afftdn_fixed_v1` degradó fuertemente las métricas en este contrato concreto. La comparación objetiva fue auxiliar y no seleccionó candidato por sí sola.

### 3.6e — Human blinded A/B

Guille realizó la escucha A/B precomprometida.

DeepFilterNet:

```text
treatment preferences = 10
preserve preferences = 0
no preference = 0
speech integrity failures = 0
artifact failures = 0
status = ELIGIBLE_FOR_SELECTION_REVIEW
```

AFFTDN:

```text
treatment preferences = 3
preserve preferences = 2
no preference = 5
perceptual gate = FAIL
status = NOT_ADVANCED_PRESERVE_DEFAULT
```

El human gate sólo habilitó selection review; no autorizó denoise ni renderer.

### 3.6f — Candidate selection

Seleccionado:

```text
deepfilternet_0_5_6_compensated_v1
selection_status = SELECTED_FOR_INTEGRATION_REVIEW
```

No seleccionado: `ffmpeg_afftdn_fixed_v1`.

La selección NO cambia:

```text
product_default = preserve
denoise_authorized = false
renderer_authorized = false
auto_apply = false
```

### 3.6g — Portable runtime contract

DeepFilterNet 0.5.6 se integra como herramienta portable inmutable:

```text
Tools/deepfilter/bin/deep-filter.exe
SHA-256 75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915
26912256 bytes
runtime_download_allowed = false
```

El build descarga únicamente durante build, valida asset, copia el mismo binario y vuelve a validar. Runtime no usa PATH ni red para adquirirlo.

Gate `34211660270` acreditó:

- build portable PASS;
- provenance exacta PASS;
- ejecución de DeepFilterNet con outbound network bloqueado PASS;
- tampered binary fail-closed PASS;
- 14/14 tests focales;
- 418 tests integrados OK;
- development doctor PASS;
- portable doctor PASS.

Artifact ligero: `10050110122`, ZIP SHA-256 `c27f8a0ddfaa88bfdfa36bf8c79d6b4ec74198669f75cbfbb427648c6d04de89`.

Evidencia persistente: `Validation/phase3-denoiser-portable-runtime.json`.

## 10. Baseline real de Fase 3

`Validation/phase3-focal-quality-baseline.json` procede del mismo bundle ORIGINAL/RENDERED escuchado por Guille en 2E.5.

La evidencia actual NO justifica:

- normalización obligatoria como reparación del renderer;
- denoise por defecto;
- crossfade/join smoothing por defecto.

Default: preservar el render validado.

## 11. Próximo trabajo — Fase 3.6h

Crear primero una capa separada y stale-safe de **denoise plan proposal + explicit execution authorization**, sin renderer todavía.

Debe mantener como mínimo:

- binding exacto al output/source SHA acreditado;
- binding exacto a `deepfilternet_0_5_6_compensated_v1` y al runtime 3.6g;
- parámetros/CLI congelados y auditables;
- proposal != authorization;
- aprobación explícita con actor + reason;
- stale/tamper fail-closed;
- `preserve` como product default;
- `auto_apply=false`;
- no output tratado hasta una fase posterior de renderer explícitamente autorizada.

Join smoothing/crossfade continúa bloqueado hasta evidencia A/B perceptual específica.

## 12. GitHub / CI / Release

- GitHub source of truth;
- CI deliberada;
- workflows one-shot se eliminan tras uso;
- workflows pesados manual-only normalmente;
- no subir modelos/vídeos/ZIPs como artifacts ordinarios;
- mantener README, AGENTS, ROADMAP, RELEASE_STATUS y Validation sincronizados;
- no Release sin autorización expresa de Guille.
