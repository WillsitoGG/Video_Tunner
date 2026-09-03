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

Completado hasta:

- Fase 2C.3 — audio humano real → semantic gate;
- Fase 2D.1 — correction scope/schema v4;
- Fase 2D.2 — fillers/schema v5;
- Fase 2D.3.1 — join context/schema v6;
- Fase 2D.3.2 — acoustic join/schema v7;
- Fase 2D.3.3 — human-audio acoustic evidence;
- Fase 2D.4 — combined eligibility/schema v8;
- Fase 2D.5 — human combined eligibility evidence.

Siguiente: **Fase 2D.6 — Human Positive Eligibility Expansion / Close-out Gate**.

No existe todavía promoción al Edit Plan.

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

Semantic decisions: `KEEP / REVIEW / PROPOSED_TRIM / PROPOSED_CUT`; siempre no ejecutables.

Correction scope: `bounded / ambiguous / invalid`; `bounded` no implica cut seguro.

Fillers: sólo `isolated_hesitation` puede atravesar la policy foundation; cluster, repair, boundary, uncertain ASR o invalid quedan bloqueados.

Whisper puede omitir fillers, vacilaciones o truncamientos; no inventar evidencia ausente.

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

### 2D.4 foundation

Run `33790792753`: 138/138 PASS; 12 casos, 4 rutas pass y 8 blockers; artifacts 0.

### 2D.5 evidencia humana

Baseline `33791636767`:

- 141/141 regresiones PASS;
- gate humano falló sólo por diagnóstico `invalid_removed_text` frente a `blocked_correction_scope` en correction ambigua;
- seguridad permaneció a cero.

Se cambió sólo la precedencia diagnóstica; la evidencia secundaria `removed_text_reason=missing_target_span` se conserva.

Final `33791950505`:

```text
142/142 tests PASS en 7.087 s
cases 3
foundation_guards_pass 1
blocked 2
safe_for_cut/executable/auto_apply/automatic_edits 0
HUMAN_ELIGIBILITY_GATE=PASS
artifacts 0
```

Casos:

- pausa humana control → `foundation_guards_pass`, no cut;
- retake humano → `blocked_semantic_decision`;
- correction humana ambigua → `blocked_correction_scope`.

La pausa es un control técnico; no cuenta como evidencia de que el producto deba borrarla automáticamente.

Detalle: `Validation/phase2d-human-combined-eligibility.md`.

## 9. Siguiente — 2D.6 Human Positive Eligibility Expansion / Close-out Gate

Objetivo: conseguir evidencia humana etiquetada como **realmente descartable** antes de decidir cierre de 2D.

Reglas:

1. buscar fuentes humanas trazables/licenciadas;
2. priorizar pausas limpias, fillers aislados y repeticiones/retakes claramente descartables;
3. incluir negativos cercanos;
4. aplicar la policy actual sin relajarla para fabricar positivos;
5. validar `removedText`, word timings, join y acústica real;
6. si no aparecen suficientes positivos elegibles, registrar el fallo y endurecer/tunear sólo con evidencia;
7. mantener todo `safe_for_cut=false`, `executable=false`, `auto_apply=false`, `automatic_edits=0`;
8. sólo el close-out gate de 2D puede justificar diseñar 2E.

## 10. Edit Plan / render

Edit Plan sólo contiene ediciones efectivas aprobadas; nunca candidates, scopes, assessments o future-promotion candidates no aprobados.

Pendiente: 2D.6, eventual promotion policy explícita, join treatment/audit, fades/loudness y post-render verification.

## 11. GitHub / CI / Release

GitHub es source of truth.

- CI deliberada;
- no modelos, vídeos, ZIPs o artifacts pesados ordinarios;
- workflows manual-only normalmente;
- trigger one-shot sólo cuando sea necesario y restaurar inmediatamente;
- no publicar GitHub Release sin autorización expresa de Guille.

## 12. Docs

Mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation ante cambios relevantes.
