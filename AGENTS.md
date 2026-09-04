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
7. `candidate != correction scope != filler assessment != join assessment != acoustic join assessment != semantic decision != eligibility assessment != edit`;
8. `PROPOSED_CUT != executable CUT`;
9. `bounded scope != safe cut`;
10. `acoustic_context_only != semantic permission to cut`;
11. `foundation_guards_pass != safe cut`;
12. `future_promotion_candidate != approved edit`;
13. una señal posterior favorable nunca rescata una guarda anterior bloqueada;
14. ante duda: `KEEP / REVIEW`;
15. conservador por defecto.

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD → candidates → scopes/fillers → join assessments → acoustic join assessments → semantic decisions → eligibility assessments → future Edit Plan → render → audit
```

## 2. Estado

Versión `0.1.0-dev`.

Completado:

- Fase 2C.3 — audio humano real → semantic gate;
- Fase 2D.1 — correction scope/schema v4;
- Fase 2D.2 — fillers/schema v5;
- Fase 2D.3.1 — join context/schema v6;
- Fase 2D.3.2 — acoustic join/schema v7;
- Fase 2D.3.3 — human-audio acoustic evidence;
- Fase 2D.4 — combined eligibility/schema v8;
- Fase 2D.5 — human combined eligibility evidence;
- Fase 2D.6 — human positive eligibility expansion / close-out.

**Fase 2D cerrada como foundation/evidence.**

Siguiente: **Fase 2E — Promotion to Edit Plan**.

No existe todavía promoción ejecutable al Edit Plan.

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

Schema actual: **v8**.

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
acoustic_join_assessments[]
semantic_decisions[]
eligibility_assessments[]
```

Siempre:

```text
eligibility_assessments_are_not_edits = true
eligibility_assessments_executable = false
eligibility_assessments_safe_for_cut = false
future_promotion_candidates_are_not_approved_edits = true
combined_eligibility_enabled = true
combined_eligibility_is_not_edit_plan_promotion = true
safe_for_cut = false
executable = false
auto_apply = false
automatic_edits = 0
```

## 6. Semantic / scope / filler guards

Semantic decisions: `KEEP / REVIEW / PROPOSED_TRIM / PROPOSED_CUT`; siempre no ejecutables en 2D.

Correction scope: `bounded / ambiguous / invalid`; `bounded` no implica cut seguro.

Fillers: sólo `isolated_hesitation` puede atravesar la policy foundation; cluster, repair, boundary, uncertain ASR o invalid quedan bloqueados.

Whisper puede omitir fillers, vacilaciones, truncamientos o incluso una repetición humana completa. No inventar evidencia ausente.

## 7. Join + acoustic guards

Join v1 pass para eligibility: sólo `join_context_only`.

Acoustic v1 pass para eligibility: sólo `acoustic_context_only` o `low_energy_boundary_context`, siempre con `measurement_available=true`.

Esto no significa seguridad perceptual ni permiso de corte.

Thresholds acústicos v1:

```text
SILENCE_DBFS                 = -42.0
MAX_RMS_DELTA_DB             = 12.0
MAX_BOUNDARY_SAMPLE_JUMP     = 0.35
MAX_BOUNDARY_JUMP_RATIO      = 1.25
```

No relajar thresholds para fabricar positivos de validación.

## 8. Combined Eligibility — 2D.4/2D.5

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

Precedencia fail-safe actual:

1. para `explicit_correction`, exigir scope `bounded` antes de interpretar la ausencia esperada de target como corrupción;
2. validar target/`removedText` cuando existe un target elegible;
3. exigir filler isolated para filler;
4. exigir semantic decision si el kind es semántico;
5. exigir semantic `PROPOSED_CUT/PROPOSED_TRIM` + `guard_status=pass`;
6. exigir `join_context_only`;
7. exigir acoustic assessment presente;
8. exigir acoustic status permitido y medición real;
9. sólo entonces `foundation_guards_pass`.

Para spans textuales, `removedText` exige índices válidos + transcript normalizado coincidente + timestamps dentro de `0.03 s`. Para pausas exige gap temporal vacío y start/end coincidentes. Corrections bounded pueden usar `attempt + marker`.

`foundation_guards_pass` produce únicamente:

```text
future_promotion_candidate = true
safe_for_cut = false
executable = false
auto_apply = false
```

## 9. Fase 2D.6 — Human Positive Close-out

### Procedencia

- Corpus: AMI Meeting Corpus, anotaciones manuales de disfluencias, CC BY 4.0.
- Mirror de inspección fijado: `ColingPaper2018/DialogueAct-Tagger@4307e9899ed9058e80d0861530de124d4f134317`.
- Ontología: repeat `ami_dsfl_12`, reparans `ami_dsfl_18`, reparandum `ami_dsfl_19`.
- Audio: siempre headset individual del hablante; no `Mix-Headset` para etiquetas speaker-specific.
- Tokenización del discovery/harness debe ser equivalente a producción: normalización dentro de cada token separado por whitespace; una contracción como `you've` cuenta como `youve`, un token.

### Selección

Run ligero `33892213960`:

```text
80 exact repeats compatibles con detector conservador
8 casos seleccionados
4 fuentes/headsets
máximo 2 casos por fuente
```

La selección se fija antes de ejecutar `large-v3-turbo` para no escoger ejemplos por resultado ASR.

### Gate precomprometido

```text
minimum_evaluated_long_cases        8
minimum_aligned_human_positives     3
minimum_foundation_human_positives  2
minimum_foundation_sources          2
```

Son thresholds de **suficiencia de evidencia**, no thresholds del producto.

### Final

Run `33894995584`, commit evaluado `aecea4a35ed204d877b02937d5746a41d41af5d7`:

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

Diagnóstico:

```text
asr_repeat_not_preserved                 2
foundation_guards_pass                   3
downstream_blocked:blocked_join_context  3
```

En esta muestra:

- no hay `detector_miss_on_preserved_repeat`;
- no hay `candidate_span_mismatch`;
- no hay `timing_mismatch`;
- 6/6 repeats completos preservados por ASR se detectan/alinean;
- 3/6 quedan bloqueados por join context, que es comportamiento conservador esperado;
- 3/6 alcanzan `foundation_guards_pass`, pero siguen no ejecutables.

No extrapolar 6/6 como tasa global del detector.

Detalle: `Validation/phase2d-human-positive-closeout.md`.

## 10. Siguiente — 2E Promotion to Edit Plan

2E debe introducir un contrato explícito entre eligibility y Edit Plan sin invalidar los blockers de 2D.

Reglas de diseño:

1. ninguna `eligibility_assessment` se convierte por sí sola en edit;
2. `future_promotion_candidate` sólo permite evaluación de promoción;
3. blockers previos son veto acumulativo;
4. definir clases promocionables, approval/thresholds por modo, límites globales y fail-safe;
5. REVIEW/KEEP siguen siendo fallback;
6. validar la promotion policy antes de habilitar ejecución automática;
7. la validación debe incluir positivos humanos y negativos cercanos;
8. cada promoción al Edit Plan debe ser auditable y reproducible.

## 11. Edit Plan / render

Edit Plan sólo contiene ediciones efectivas aprobadas; nunca candidates, scopes, assessments o future-promotion candidates no aprobados.

Pendiente después de 2E: join treatment/audit, fades/loudness, post-render verification y capas posteriores del roadmap.

## 12. GitHub / CI / Release

GitHub es source of truth.

- CI deliberada;
- no modelos, vídeos, ZIPs o artifacts pesados ordinarios;
- workflows manual-only normalmente;
- trigger one-shot sólo cuando sea necesario y restaurar inmediatamente;
- `human-positive-closeout-spike.yml` queda manual-only tras el run final;
- no dejar workflows temporales de discovery en `main`;
- no publicar GitHub Release sin autorización expresa de Guille.

## 13. Docs

Mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation ante cambios relevantes.
