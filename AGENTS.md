# AGENTS.md — Video_Tunner

Contexto técnico permanente para agentes. Referencia maestra externa vigente: `00.Contexto y Reglas de Trabajo_GitHub_Video_Tunner_v3`.

## 1. Invariantes

Video_Tunner debe producir vídeo hablado limpio, natural, fiel, sincronizado, auditable y reversible en Windows 10/11 x64.

Obligatorio:

1. portable real: ZIP → descomprimir → ejecutar;
2. vídeo con audio embebido o vídeo + audio externo;
3. resolver master audio antes de análisis temporal;
4. Whisper, VAD y acoustic join validation usan exactamente el mismo master acreditado;
5. auto-sync sólo con evidencia suficiente; override/manual fallback;
6. original siempre intacto;
7. `candidate != correction scope != filler assessment != join assessment != acoustic join assessment != semantic decision != eligibility assessment != promotion assessment != edit`;
8. `PROPOSED_CUT != executable CUT`;
9. `bounded scope != safe cut`;
10. `acoustic_context_only != semantic permission to cut`;
11. `foundation_guards_pass != safe cut`;
12. `future_promotion_candidate != approved edit`;
13. `promotion_review_candidate != approved edit`;
14. una señal posterior favorable nunca rescata una guarda anterior bloqueada;
15. ante duda: `KEEP / REVIEW`;
16. conservador por defecto.

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD → candidates → scopes/fillers → join → acoustic join → semantic decisions → eligibility → promotion assessments → future approved Edit Plan → render → audit
```

## 2. Estado

Versión `0.1.0-dev`.

Completado:

- Fase 2C.3 — audio humano real → semantic gate;
- Fase 2D.1 — correction scope/schema v4;
- Fase 2D.2 — fillers/schema v5;
- Fase 2D.3 — join/acoustic + evidencia humana;
- Fase 2D.4 — combined eligibility/schema v8;
- Fase 2D.5 — human combined eligibility evidence;
- Fase 2D.6 — human positive eligibility close-out;
- **Fase 2D cerrada como foundation/evidence**;
- **Fase 2E.1 — Promotion Policy Foundation/schema v9 — COMPLETADA**.

Siguiente: **Fase 2E.2 — Explicit Approval Contract**.

No existe todavía promoción aprobada ni ejecutable al Edit Plan.

## 3. Evidencia principal

```text
33600174568  Portable core PASS
33621357438  Portable ML PASS
33639009841  Sync hardening PASS
33656235038  Target Spanish PASS — WER 1.64%, RTF 0.4854
33750836791  Human correction corpus PASS
33755013415  3 AMI audio-backed semantic cases PASS
33758185755  88/88 — correction scope/schema v4
33771792867  101/101 — fillers/schema v5
33773287106  117/117 — join context/schema v6
33781903986  131/131 — acoustic join/schema v7
33782959293  134/134 — human acoustic evidence PASS
33790792753  138/138 — combined eligibility/schema v8 PASS
33791950505  142/142 — human combined eligibility PASS
33892213960  AMI repeat discovery PASS — 80 compatible exact repeats
33894995584  Human positive close-out PASS — CLOSE_OUT_READY
33896244733  2E.1 isolated promotion policy PASS — 165/165
33899201093  2E.1 integrated schema v9 PASS — 166/166 + doctor
```

No generalizar métricas de corpus fuera de su muestra.

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

## 5. Analysis / schema

Schema actual: **v9**.

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
acoustic_join_assessments[]
semantic_decisions[]
eligibility_assessments[]
promotion_assessments[]
```

Siempre en 2E.1:

```text
promotion_assessments_are_not_edits = true
promotion_review_requires_explicit_approval = true
promotion_assessments_approved = false
edit_plan_promotion_enabled = false
promotion_assessments_executable = false
promotion_assessments_safe_for_cut = false
approved = false
edit = null
safe_for_cut = false
executable = false
auto_apply = false
automatic_edits = 0
```

## 6. Semantic / scope / filler guards

Semantic decisions: `KEEP / REVIEW / PROPOSED_TRIM / PROPOSED_CUT`; siguen no ejecutables.

Correction scope: `bounded / ambiguous / invalid`; `bounded` no implica cut seguro.

Fillers: sólo `isolated_hesitation` puede atravesar eligibility foundation; cluster, repair, boundary, uncertain ASR o invalid quedan bloqueados.

Whisper puede omitir fillers, truncamientos o incluso una repetición humana completa. No inventar evidencia ausente.

## 7. Join + acoustic guards

Join pass para eligibility: sólo `join_context_only`.

Acoustic pass para eligibility: sólo `acoustic_context_only` o `low_energy_boundary_context`, siempre con `measurement_available=true`.

Thresholds acústicos v1:

```text
SILENCE_DBFS                 = -42.0
MAX_RMS_DELTA_DB             = 12.0
MAX_BOUNDARY_SAMPLE_JUMP     = 0.35
MAX_BOUNDARY_JUMP_RATIO      = 1.25
```

No relajar thresholds para fabricar positivos.

## 8. Combined Eligibility — Fase 2D

Estados:

```text
foundation_guards_pass
blocked_acoustic_context
blocked_filler_context
blocked_semantic_decision
blocked_join_context
blocked_correction_scope
invalid_removed_text
missing_required_evidence
```

Precedencia fail-safe:

1. corrections requieren scope `bounded`;
2. validar target/`removedText`;
3. exigir filler isolated cuando aplica;
4. exigir semantic decision cuando aplica;
5. exigir semantic `PROPOSED_CUT/PROPOSED_TRIM` + `guard_status=pass`;
6. exigir `join_context_only`;
7. exigir acoustic assessment presente;
8. exigir acoustic status permitido y medición real;
9. sólo entonces `foundation_guards_pass`.

`foundation_guards_pass` produce únicamente un `future_promotion_candidate`; no autoriza corte.

## 9. Fase 2D.6 — Human Positive Close-out

AMI manual disfluency annotations, CC BY 4.0; headsets individuales por hablante; selección fijada antes de ASR.

Final `33894995584`:

```text
155 tests OK; 11 host-PATH skips
cases                             8
aligned human positives           6
foundation human positives        3
foundation sources                2
hard failures                     0
HUMAN_POSITIVE_EVIDENCE_GATE      PASS
HUMAN_POSITIVE_CLOSE_OUT_DECISION CLOSE_OUT_READY
safe_for_cut/executable/auto_apply/automatic_edits 0
artifacts                          0
```

No extrapolar las tasas de esta muestra.

Detalle: `Validation/phase2d-human-positive-closeout.md`.

## 10. Fase 2E.1 — Promotion Policy Foundation

Objetivo: introducir una capa explícita de **revisión de promoción**, todavía separada del Edit Plan.

### Clase respaldada inicialmente

```text
possible_repetition
```

Es la única clase con evidencia humana positiva suficiente procedente del close-out 2D.6. `conservative` y `aggressive` usan la misma whitelist en 2E.1.

### Estados

```text
eligible_for_promotion_review
blocked_upstream_eligibility
blocked_removed_text_validation
blocked_unvalidated_candidate_kind
invalid_candidate_reference
```

Para `eligible_for_promotion_review` exigir simultáneamente:

1. candidate existente;
2. candidate kind consistente con eligibility;
3. eligibility `foundation_guards_pass`;
4. `future_promotion_candidate=true`;
5. `removed_text_validation.valid=true`;
6. kind respaldado por evidencia humana positiva.

Incluso el positivo queda:

```text
requires_explicit_approval = true
approval_state = required
promotion_review_candidate = true
approved = false
edit = null
safe_for_cut = false
executable = false
auto_apply = false
```

No existe aún API/CLI ni objeto de aprobación explícita.

### Validación

- `33896244733`: 165/165 PASS — policy/report aislados.
- `33898758391`: 165/166; fixture con `hoy` correctamente bloqueado por contexto temporal crítico.
- `33898967491`: 165/166; `vamos a lanzar` correctamente bloqueado por contexto verbal crítico.
- Sólo se corrigieron fixtures; producto/thresholds/guards permanecieron intactos.
- `33899201093`: **166/166 PASS en 7.079 s + doctor PASS**.

Detalle: `Validation/phase2e-promotion-foundation.md`.

## 11. Siguiente — Fase 2E.2 Explicit Approval Contract

Reglas de diseño:

1. una promotion assessment nunca se autoaprueba;
2. la aprobación debe referenciar candidate + promotion assessment + target exactos;
3. debe existir evidencia de integridad/provenance que invalide aprobaciones obsoletas;
4. blockers upstream siguen siendo veto absoluto;
5. separar `approval` de `Edit Plan proposal` y de ejecución/render;
6. fijar límites globales/fail-safe antes de habilitar ejecución;
7. mantener el default en REVIEW/KEEP;
8. ninguna ampliación de clases promocionables sin nueva evidencia humana suficiente.

## 12. Edit Plan / render

Edit Plan sólo contiene ediciones efectivas aprobadas. Candidates, assessments y promotion review candidates no aprobados nunca entran en él.

Pendiente después de 2E: join treatment/audit, fades/loudness, post-render verification y capas posteriores del roadmap.

## 13. GitHub / CI / Release

GitHub es source of truth.

- CI deliberada;
- no modelos, vídeos, ZIPs o artifacts pesados ordinarios;
- workflows manual-only normalmente;
- trigger one-shot sólo cuando sea necesario y restaurar inmediatamente;
- no publicar GitHub Release sin autorización expresa de Guille.

## 14. Docs

Mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation ante cambios relevantes.
