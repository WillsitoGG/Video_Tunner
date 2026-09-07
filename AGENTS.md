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
10. `profile selection != normalization authorization`;
11. `preserve` audiovisual es default;
12. ningún risk finding auto-selecciona tratamiento;
13. ante duda: KEEP/REVIEW;
14. `auto_apply=false`;
15. no release sin autorización expresa de Guille.

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
```

## 2. Estado

Versión `0.1.0-dev`.

Completado:

- Fase 2D cerrada como foundation/evidence;
- Fase 2E completa — `CLOSE_OUT_READY`;
- Fase 3.1 — Audiovisual Quality Audit v1 foundation;
- Fase 3 focal real sobre los 3 joins humanos 2E.5;
- Fase 3.2 — Bypass-first Treatment Decision foundation;
- Fase 3.3 — Normalization Profile Contract foundation/review-only.

No completado:

- normalización ejecutable;
- denoise;
- join smoothing/crossfade;
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

## 7. Fase 3.1 — Quality Audit

`Source/video_tunner/audiovisual_quality.py`:

- sólo acepta un output 2E técnicamente PASS y SHA vigente;
- FFmpeg `loudnorm` se usa únicamente como medidor;
- se leen input integrated LUFS, input true peak y LRA;
- no se genera media normalizado;
- risk v1: true peak > 0 dBTP;
- ningún finding crea capability.

## 8. Baseline real de Fase 3

`Validation/phase3-focal-quality-baseline.json` procede del mismo bundle ORIGINAL/RENDERED escuchado por Guille en 2E.5.

La evidencia actual NO justifica:

- normalización obligatoria como reparación del renderer;
- denoise por defecto;
- crossfade/join smoothing por defecto.

Default: preservar el render validado.

## 9. Fase 3.2 — Treatment Decision

```text
no risks → bypass_preserve_render
risk → treatment_review_required
```

Siempre:

```text
parameters_defined = false
mandatory_treatment = false
executable = false
treatment_authorized = false
auto_apply = false
```

Nunca convertir automáticamente un riesgo en parámetros de filtro.

## 10. Fase 3.3 — Normalization Profile Contract

Default:

```text
preserve
```

Perfil opt-in/review-only:

```text
ebu_r128_programme
-23 LUFS
max true peak -1 dBTP
EBU R 128 v5.0 (November 2023)
measurement basis ITU-R BS.1770-5 (November 2023)
```

No usar un supuesto “YouTube -14 LUFS” como default ni como estándar universal.

Selección EBU R128 todavía implica:

```text
explicit_opt_in_required = true
human_approval_required = true
normalization_authorized = false
parameters_executable = false
render_authorized = false
auto_apply = false
```

No elegir silenciosamente un target LRA sólo porque FFmpeg `loudnorm` requiera un parámetro LRA para tratamiento.

## 11. Próximo trabajo — Fase 3.4

Implementar un **normalization approval artifact** separado y stale-safe:

- APPROVE / REJECT explícito;
- actor + reason obligatorios;
- binding exacto al output SHA y al normalization profile decision actual;
- stale/tamper fail-closed;
- approval NO debe renderizar ni crear `auto_apply`;
- `preserve` no necesita approval para no procesar.

Después: diseñar 3.5 preview/derivative render con output 2E intacto y post-treatment audit.

## 12. GitHub / CI / Release

- GitHub source of truth;
- CI deliberada;
- workflows one-shot se eliminan tras uso;
- workflows pesados manual-only normalmente;
- no subir modelos/vídeos/ZIPs como artifacts ordinarios;
- mantener README, AGENTS, ROADMAP, RELEASE_STATUS y Validation sincronizados;
- no Release sin autorización expresa de Guille.
