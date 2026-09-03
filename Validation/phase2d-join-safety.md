# Fase 2D.3.1 — Join boundary / timeline / lexical safety foundation

Fecha: 2026-09-03.

Estado: **COMPLETADA COMO FOUNDATION v1; NO ACREDITA SEGURIDAD ACÚSTICA NI HABILITA CORTES**.

## Objetivo

Añadir una capa auditable que describa los dos lados de un join hipotético y bloquee riesgos evidentes antes de considerar cualquier promoción al Edit Plan.

```text
candidate
→ correction scope / filler context
→ join assessment
→ semantic decision
→ future approved Edit Plan
```

Invariante:

```text
join assessment != safe cut
safe_for_cut = false
executable = false
auto_apply = false
```

## Implementación

Módulos:

```text
Source/video_tunner/join_safety.py
Source/video_tunner/join_safety_validation.py
Source/video_tunner/join_safety_report.py
```

Fixture:

```text
tests/fixtures/join_safety_v1.json
```

Tests:

```text
tests/test_join_safety.py
tests/test_join_safety_validation.py
```

## Estados v1

```text
join_context_only
sentence_boundary_risk
segment_boundary_risk
critical_lexical_context_risk
repair_or_protected_context_risk
transcript_edge
invalid_or_unbounded_target
```

`join_context_only` significa únicamente que existe contexto bilateral y ninguna guarda v1 se ha activado. **No significa que el join sea seguro.**

## Resolución del target

- `pause`: gap temporal candidato y palabras vecinas izquierda/derecha;
- `possible_filler`: matching único por token + timestamps;
- `possible_repetition` / `possible_retake`: span de palabras del candidate;
- `explicit_correction`: sólo si `correction_scope.status == bounded`; target = `attempt_span + marker_span`.

### Integridad del span

Para candidates semánticos, un target sólo se acepta cuando:

```text
word indexes válidos
removed_text == texto real del transcript normalizado
|candidate.start - word.start| <= 0.03 s
|candidate.end - word.end| <= 0.03 s
```

Un mismatch produce:

```text
invalid_or_unbounded_target
```

Una correction con scope `ambiguous` tampoco obtiene target de join.

## Guardas de contexto

Prioridad conservadora:

1. retake/correction o filler protegido → `repair_or_protected_context_risk`;
2. cifras/unidades/negación/persona/tiempo/causalidad junto al join → `critical_lexical_context_risk`;
3. cambio de segmento ASR → `segment_boundary_risk`;
4. puntuación fuerte ASR → `sentence_boundary_risk`;
5. resto con contexto bilateral → `join_context_only`.

La puntuación ASR es sólo una señal; no se trata como verdad de frontera de frase.

Cada assessment registra, cuando aplica:

```text
left_context
right_context
target_span + source
left_gap_to_target_seconds
right_gap_from_target_seconds
target_duration_seconds
segment_boundary
punctuation_boundary
critical_features_left/right
repair_kind
filler_context_status
```

## Benchmark v1

15 casos etiquetados:

- pause con contexto bilateral;
- punctuation sentence boundary;
- ASR segment boundary;
- filler aislado;
- filler protegido por reparación;
- filler cluster;
- negación cerca del join;
- cifra cerca del join;
- repetition con contexto bilateral;
- retake;
- retake humano AMI;
- correction bounded;
- correction ambiguous;
- semantic span corrupto;
- filler en borde del transcript.

Caso humano AMI reutilizado de la evidencia 2C:

```text
have a look at the uh th- have a look at the prototypes
```

El retake se clasifica como:

```text
repair_or_protected_context_risk
safe_for_cut = false
```

## Gate v1

```text
status_mismatches == 0
status_accuracy == 1.0
target_source_mismatches == 0
bilateral_mismatches == 0
safety_violations == 0
```

## Evidencia CI

### Run 33772715214 — foundation

```text
112/112 tests PASS en 6.670 s
11 tests directos de join PASS
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

### Run 33773287106 — benchmark + schema v6

```text
117/117 tests PASS en 6.891 s
join benchmark gate PASS
AMI retake join risk PASS
schema v6 pipeline integration PASS
E2E FFmpeg/sync PASS
doctor PASS
artifacts 0
```

## `analysis.json` schema v6

```text
candidates[]
correction_scopes[]
filler_assessments[]
join_assessments[]
semantic_decisions[]
```

Safety flags añadidos:

```text
join_assessments_are_not_edits = true
join_assessments_executable = false
join_assessments_safe_for_cut = false
join_acoustic_validation_enabled = false
```

## Qué demuestra

- el target de join se resuelve con integridad o falla seguro;
- existe evidencia bilateral auditable;
- se detectan riesgos de repair, léxico crítico, boundaries y edges;
- correction scopes ambiguous no se convierten en joins;
- el benchmark v1 es exacto para sus 15 casos;
- la capa está integrada en `analysis.json` sin promover edits.

## Qué NO demuestra

- que un `join_context_only` sea acústicamente natural;
- ausencia de click/pop en waveform;
- continuidad de energía, fase, DC offset o prosodia;
- que el hard concat actual de `render.py` sea adecuado para estos joins;
- seguridad universal fuera del corpus v1;
- autorización para `safe_for_cut=true`, ejecución o auto-apply.

## Siguiente — Fase 2D.3.2

Validación acústica de joins sobre **master audio**:

1. medir ventanas reales antes/después del join hipotético;
2. añadir proxies de discontinuidad de waveform/energía;
3. distinguir speech-boundary risk y acoustic discontinuity risk;
4. validar con audio sintético pequeño y, si aporta evidencia nueva, audio humano real;
5. seguir sin promover al Edit Plan durante la foundation acústica.
