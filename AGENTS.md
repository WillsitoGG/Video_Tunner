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
10. `profile selection != normalization approval != normalization execution authorization`;
11. technical normalization PASS != human perceptual PASS;
12. `preserve` audiovisual es default;
13. ningún risk finding auto-selecciona tratamiento;
14. dynamic loudnorm fallback está prohibido en la foundation validada;
15. ante duda: KEEP/REVIEW;
16. `auto_apply=false`;
17. no release sin autorización expresa de Guille.

Cadena actual:

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD
→ candidates/scopes/fillers/join/acoustic/semantic/eligibility
→ promotion → individual approval → bounded proposal
→ global execution authorization → semantic Edit Plan
→ semantic render gate → FFmpeg
→ post-render technical verification → human review → 2E closeout
→ audiovisual quality audit
→ audiovisual treatment decision
→ normalization profile decision
→ normalization approval
→ normalization plan proposal
→ normalization execution authorization
→ gated linear normalization render
→ independent normalization post-render verification
→ human perceptual review [PENDING]
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
- Fase 3.5d — independent normalization post-render verifier technical foundation.

No completado:

- human perceptual close-out de normalización;
- denoise evidence/treatment;
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

## 9. Baseline real de Fase 3

`Validation/phase3-focal-quality-baseline.json` procede del mismo bundle ORIGINAL/RENDERED escuchado por Guille en 2E.5.

La evidencia actual NO justifica:

- normalización obligatoria como reparación del renderer;
- denoise por defecto;
- crossfade/join smoothing por defecto.

Default: preservar el render validado.

## 10. Próximo trabajo — Fase 3.6

Abrir **denoise evidence/audit** antes de cualquier tratamiento:

- medir, no filtrar;
- no inferir “noise floor” desde ventanas no acreditadas;
- usar sólo ventanas no-speech/speech con provenance suficiente;
- si no hay ventanas confiables, exigirlas explícitamente en vez de adivinarlas;
- no seleccionar `afftdn`, `arnndn` u otro filtro por conveniencia;
- denoise debe permanecer `not_authorized` hasta evidencia/corpus específico;
- controles limpios son obligatorios para detectar degradación introducida por denoise.

Join smoothing/crossfade continúa bloqueado hasta evidencia A/B perceptual específica.

## 11. GitHub / CI / Release

- GitHub source of truth;
- CI deliberada;
- workflows one-shot se eliminan tras uso;
- workflows pesados manual-only normalmente;
- no subir modelos/vídeos/ZIPs como artifacts ordinarios;
- mantener README, AGENTS, ROADMAP, RELEASE_STATUS y Validation sincronizados;
- no Release sin autorización expresa de Guille.
