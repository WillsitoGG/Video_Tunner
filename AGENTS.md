# AGENTS.md — Video_Tunner

Contexto técnico permanente para agentes. Referencia maestra externa vigente: `00.Contexto y Reglas de Trabajo_GitHub_Video_Tunner_v3`.

## 1. Invariantes

Video_Tunner debe producir vídeo hablado limpio, natural, fiel, sincronizado, auditable y reversible en Windows 10/11 x64.

Obligatorio:

1. Portable real: ZIP → descomprimir → ejecutar; sin admin, Python, FFmpeg ni PATH del sistema.
2. Vídeo con audio embebido o vídeo + audio externo.
3. Resolver master audio/sync antes de transcripción, VAD o decisiones temporales.
4. Whisper, VAD y capas acústicas usan el mismo master acreditado.
5. Original siempre intacto; derivados auditables y reversibles.
6. Cada artifact/capability es independiente y stale-safe.
7. Una señal posterior favorable nunca rescata una guarda anterior bloqueada.
8. `measurement != treatment decision != treatment authorization`.
9. `noise measurement != denoise decision != denoise authorization`.
10. candidate evaluation != candidate selection != denoise authorization.
11. selected denoiser/runtime availability != renderer authorization.
12. plan proposal != execution authorization.
13. Un camino APPROVE probado con fixtures != autorización real del usuario.
14. authorization artifact != renderer execution.
15. render complete != independent technical verification PASS.
16. technical PASS != human perceptual PASS cuando existe gate humano pendiente.
17. `profile selection != normalization approval != normalization execution authorization`.
18. `preserve` audiovisual es default.
19. Ningún dBFS ni métrica objetiva activa denoise automáticamente.
20. DeepFilterNet integrado en portable no implica denoise autorizado.
21. Ante duda: KEEP/REVIEW.
22. `auto_apply=false`.
23. No release sin autorización expresa de Guille.

Cadena actual:

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD
→ semantic candidates/protection/join/eligibility
→ promotion → approval → proposal → execution authorization
→ semantic Edit Plan → render gate → FFmpeg
→ technical verification → human review → Phase 2E closeout
→ audiovisual quality audit
   ├→ normalization profile/approval/plan/auth/render/verify
   │  → human perceptual normalization review [PENDING]
   └→ noise evidence audit
      → frozen denoise corpus
      → objective baseline/comparison
      → blinded human A/B
      → candidate selection review
      → portable selected-runtime contract
      → denoise plan proposal
      → explicit denoise execution authorization
      → gated DeepFilterNet denoise renderer [3.6i TECHNICAL FOUNDATION]
      → independent denoise post-render technical verifier [3.6j TECHNICAL FOUNDATION]
      → human denoise treatment closeout [3.6k NEXT]
```

## 2. Estado

Versión `0.1.0-dev`.

Completado:

- Fase 2D foundation/evidence;
- Fase 2E — `CLOSE_OUT_READY`;
- Fase 3.1–3.5d — quality + normalization technical foundation;
- Fase 3.6a — Noise Evidence Audit measurement-only;
- Fase 3.6b — frozen VoiceBank+DEMAND denoise corpus;
- Fase 3.6c — objective noisy baseline;
- Fase 3.6d — objective candidate comparison;
- Fase 3.6e — blinded human perceptual A/B closeout;
- Fase 3.6f — DeepFilterNet selected for integration review;
- Fase 3.6g — immutable/offline portable DeepFilterNet runtime;
- Fase 3.6h — non-executable denoise plan + explicit authorization technical foundation;
- Fase 3.6i — gated denoise renderer technical foundation sobre media sintética mono;
- Fase 3.6j — independent denoise post-render technical verifier foundation sobre media sintética.

No completado:

- human perceptual close-out de normalización;
- autorización real per-media de Guille para denoise;
- human denoise treatment closeout 3.6k;
- generalización del renderer a estéreo/multicanal;
- join smoothing/crossfade evidence/treatment;
- Fase 3 closeout;
- UX/release.

## 3. Evidencia principal

```text
33600174568  Portable core PASS
33621357438  Portable ML PASS
33639009841  Sync hardening PASS
33656235038  Target Spanish PASS — WER 1.64%, RTF 0.4854
33909625346  2E.4 real semantic render E2E PASS
34119952855  2E.5 technical closeout — 3/3 real AMI / 2 sources
human review  2E.5 — 3/3 perceptual PASS / CLOSE_OUT_READY
34124101770  clean Phase 2E — 275/275 + doctor PASS
34124957783  3.1 quality audit — 8/8 + real FFmpeg E2E PASS
34139639280  regression through 3.5d — 337/337 + doctor PASS
34141013261  3.6a noise audit — 9/9 + real MP4/AAC E2E PASS
34141115293  regression through 3.6a — 346/346 + doctor PASS
34142222451  3.6b corpus materialization — 40 paired cases PASS
34143456746  3.6c noisy baseline — 40/40 measured
34145308485  3.6d candidate objective comparison PASS
34148410617  3.6e blinded human A/B bundle
34150202283  3.6e closeout — 398/398 + doctor PASS
34150663772  3.6f selection artifact
34150832960  3.6f final — 410/410 + doctor PASS
34211660270  3.6g original portable runtime gate PASS
34219441077  3.6g post-persistence — 20/20 + 424 integrated + both doctors
34225276990  3.6h clean closeout — 45/45 + 452/452 + doctor PASS
34231340544  3.6i base renderer — 49/49 + 1/1 real DeepFilter E2E + 466/466, 0 skips + doctor PASS
34240028080  3.6i post-persistence — 57/57 + 1/1 E2E + 474/474, 0 skips + doctor PASS
34241518206  3.6j verifier foundation — 63/63 + 1/1 real render→verifier E2E + 488/488, 0 skips + doctor PASS
```

## 4. Stack / runtime fijado

```text
faster-whisper 1.2.1
CTranslate2 4.8.1
ONNX Runtime 1.29.0
tokenizers 0.23.1
NumPy 2.5.2
PyInstaller 6.22.2
```

VAD: faster-whisper + `silero_vad_v6.onnx`. Modelo objetivo: `large-v3-turbo`.

Transcripción: `single_pass` sigue siendo default. `deterministic_overlap_12s_3s_repeat_consensus_v1` es opt-in explícito validado para 2E.5. No exponer estrategias no validadas.

Denoiser seleccionado:

```text
candidate_id = deepfilternet_0_5_6_compensated_v1
DeepFilterNet = 0.5.6
asset SHA256 = 75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915
asset size = 26912256
runtime = Tools/deepfilter/bin/deep-filter.exe
args = --compensate-delay --output-dir <output_dir> <input_wav>
runtime_download_allowed = false
product_default = preserve
```

## 5. Artifacts

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
denoise_plan_proposal                     schema v1
denoise_execution_authorization           schema v1
denoise_render_result                     schema v1
denoise_post_render_verification          schema v1
```

No mutar artifacts upstream para registrar decisiones downstream.

## 6. Fase 3.6a–g — reglas vigentes

- 3.6a mide energía speech/non-speech; no decide tratamiento.
- Corpus 3.6b: `voicebank_demand_official_test_balanced_v1`, 40 noisy/clean, 2 speakers, 5 ruidos, 4 SNRs, 48 kHz, CC BY 4.0.
- 3.6c usa SI-SDR/STOI como baseline descriptivo.
- 3.6d compara preserve/AFFTDN/DeepFilterNet; evidencia objetiva auxiliar únicamente.
- 3.6e: Guille escuchó A/B ciego; DeepFilterNet 10/10 preferencias, 0 fallos; AFFTDN no avanzó.
- 3.6f selecciona `deepfilternet_0_5_6_compensated_v1` para integration review, no ejecución.
- 3.6g fija runtime portable exacto, offline y tamper-aware; runtime disponible no equivale a renderer autorizado.

No convertir métricas observadas del corpus en thresholds universales.

## 7. Fase 3.6h — Denoise Plan + Execution Authorization foundation

Código:

```text
Source/video_tunner/denoise_plan.py
Source/video_tunner/denoise_execution_authorization.py
```

`denoise_plan_proposal` exige noise evidence válido, SHA actual, selection review 3.6f exacto y runtime 3.6g exacto; liga fingerprints completos. `evidence_sufficient` sólo es coverage guard, nunca trigger de tratamiento.

La autorización es un artifact separado `APPROVE`/`REJECT`, con actor + reason y stale/tamper fail-closed. Un APPROVE válido sólo expresa permiso per-media para la ruta gated; no ejecuta tratamiento por sí mismo. Los APPROVE de foundation usan fixtures sintéticos, no una decisión de Guille.

Evidencia: `Validation/phase3-denoise-plan-authorization-foundation.json`.

## 8. Fase 3.6i — Gated Denoise Renderer technical foundation

Código: `Source/video_tunner/denoise_render.py`.

Reglas:

- revalidar cadena completa 3.6a→h justo antes de procesar;
- exigir source SHA actual y authorization APPROVE vigente;
- verificar binario DeepFilterNet exacto;
- materializar CLI desde el plan validado;
- template CLI alterado/extendido => fail-closed;
- nunca overwrite del source;
- exactamente 1 vídeo + 1 audio;
- foundation inicial mono; estéreo/multicanal bloqueado;
- DeepFilter layer PCM16 mono 48 kHz;
- `|raw duration delta| <= 0.05 s`;
- única corrección temporal trim/pad de cola derecha;
- no alignment search, time shift ni level matching;
- vídeo stream-copy, audio AAC 192k, sin `-shortest`;
- source SHA revalidado tras render;
- `denoise_render_complete` no declara technical ni human PASS.

Base `34231340544`: 49/49 + 1/1 E2E + 466/466. Post-persistence `34240028080`: 57/57 + 1/1 E2E + 474/474. Ambos con 0 skips y doctor PASS.

Evidencia: `Validation/phase3-denoise-render-foundation.json`.

## 9. Fase 3.6j — Independent Denoise Post-Render Technical Verifier

Código: `Source/video_tunner/denoise_post_render_verification.py`.

Precommit: `Validation/phase3-denoise-post-render-verifier-precommit.json`.

El verifier:

- revalida la cadena autorizada vigente;
- exige SHA del render result y SHA actuales de source/output;
- rechaza claims prematuros de technical/human PASS o `auto_apply=true` en el renderer;
- distingue `invalid_evidence` de `technical_denoise_fail`;
- verifica layout exacto de streams;
- verifica vídeo decodificado idéntico source/output;
- exige output AAC mono 48 kHz;
- decodifica independientemente source/output a PCM16 mono 48 kHz y compara frames;
- revalida coherencia de timeline y límite ±0.05 s;
- no permite alignment search/time shift/level matching;
- no añade thresholds SNR/STOI/SI-SDR/loudness;
- `technical_denoise_pass` continúa exigiendo human perceptual review.

Run `34241518206`:

```text
63/63 focused PASS
1/1 real DeepFilter render → independent verifier E2E PASS
488/488 integrated PASS
0 skips
doctor PASS
```

E2E:

```text
status = technical_denoise_pass
blockers = []
decoded_video_equal = true
source_frames = 144000
output_frames = 144000
human_pass = false
```

Estado real tras 3.6j:

```text
real_user_authorization_record_created = false
real_user_media_authorized_for_denoise = false
real_user_media_processed = false
real_user_treated_media_generated = false
human_denoise_treatment_closeout = false
stereo_or_multichannel_generalized = false
product_default = preserve
auto_apply = false
```

Evidencia: `Validation/phase3-denoise-post-render-verifier-foundation.json`.
Binder: `tests/test_phase3_denoise_post_render_verifier_evidence.py`.
Permanent gate: `.github/workflows/phase3-denoise-post-render-verifier.yml`, manual-only.

## 10. Normalization foundation

La vía EBU R128 sigue opt-in. El renderer técnico está validado pero el human perceptual close-out de normalización sigue pendiente. No generalizar technical PASS como perceptual PASS.

## 11. Próximo trabajo — Fase 3.6k

Human **denoise treatment closeout**.

Requisitos mínimos:

- partir sólo de evidencia con technical PASS 3.6j vigente;
- congelar criterios perceptuales antes de escuchar;
- decisiones humanas explícitas/auditables;
- no reutilizar el A/B histórico 3.6e como aprobación automática de un render concreto;
- no crear autorización real ni procesar media real sin decisión per-media explícita de Guille;
- no atribuir human PASS a Guille hasta que realmente escuche el material concreto;
- `preserve` sigue default y `auto_apply=false`.

Join smoothing/crossfade continúa bloqueado. Human normalization closeout sigue pendiente.

## 12. GitHub / CI / Release

- GitHub source of truth;
- workflows pesados/manual gates sólo cuando aportan evidencia;
- one-shot triggers se eliminan tras uso;
- no subir modelos/vídeos/ZIPs grandes como evidencia ordinaria;
- mantener README, AGENTS, ROADMAP, RELEASE_STATUS y Validation sincronizados;
- no Release sin autorización expresa de Guille.
