# ROADMAP — Video_Tunner

## Principios

- Windows 10/11 x64 portable: ZIP → descomprimir → ejecutar.
- Vídeo con audio embebido o vídeo + audio externo.
- Master audio y sincronización antes de transcripción/VAD/semántica/acústica temporal.
- Originales intactos y decisiones auditables/reversibles.
- Ante baja confianza: REVIEW/manual, no adivinar.
- CI pesada sólo cuando aporta evidencia nueva.

## Fases completadas

### Fase 0 — Bootstrap
CLI, FFmpeg/ffprobe, probe, Cleaner de silencios, Edit Plan, render y tests.

### Fase 0.5 — Technology Harvest
Repo propio, no fork. Upstreams sólo como referencias/integraciones trazables.

### Fase 1A — Portable Foundation
Core `33600174568` PASS; ML frozen `33621357438` PASS.

### Fase 1B — Ingesta dual + sincronización A/V
Master FLAC, offset +/-, drift, confidence/residual/coverage, manual override y `review_required`. Hardening `33639009841` PASS.

### Fase 1C — Transcripción + VAD sobre master
Whisper y Silero VAD reciben exactamente el mismo master. Target Spanish `33656235038`: WER `1.64%`, RTF `0.4854`, automatic edits 0.

### Fase 2A — Semantic Candidates v1
`possible_repetition`, `possible_retake`, `explicit_correction`, review-only. Run `33659725847` PASS.

### Fase 2B — Semantic Decisions + Protection v1
`KEEP / REVIEW / PROPOSED_TRIM / PROPOSED_CUT`, siempre no ejecutable. Run `33741195594` PASS.

## Fase 2 — Cleaner inteligente — EN CURSO

### 2C — Validación semántica real — COMPLETADA COMO BLOQUE DE EVIDENCIA v1

- 2C.1 `33743029443`: benchmark foundation PASS.
- 2C.2 `33750836791`: corpus humano bilingüe PASS.
- 2C.3 `33755013415`: 3 casos de audio humano real → semantic gate PASS; artifacts 0.

No generalizar métricas de corpus a habla arbitraria.

### 2D — Scope + fillers + join safety — EN CURSO

#### 2D.1 — Correction Scope Foundation v1 — COMPLETADA
Schema v4; `bounded / ambiguous / invalid`; todo scope no ejecutable. Final `33758185755`: 88/88 PASS.

#### 2D.2 — Fillers Contextuales Foundation v1 — COMPLETADA
Schema v5; contextual filler assessments. Final `33771792867`: 101/101 PASS.

#### 2D.3 — Sentence boundaries + join safety — COMPLETADA COMO BLOQUE DE EVIDENCIA v1

##### 2D.3.1 — Boundary/timeline/lexical foundation v1 — COMPLETADA

Schema v6 con `join_assessments[]`. Protege spans corruptos/ambiguos, repairs, transcript edges, boundaries ASR y tokens críticos.

Final `33773287106`: 117/117 PASS; benchmark + schema v6; artifacts 0.

##### 2D.3.2 — Acoustic join validation foundation v1 — COMPLETADA

Schema v7 añade `acoustic_join_assessments[]`.

Flujo acústico:

```text
join_context_only
→ master acreditado
→ un decode FFmpeg a PCM16 mono 16 kHz temporal
→ NumPy memmap
→ ventanas de 80 ms por lado
→ métricas RMS/waveform
→ acoustic join assessment no ejecutable
```

Estados:

```text
blocked_by_context
insufficient_audio_context
low_energy_boundary_context
level_discontinuity_risk
waveform_discontinuity_risk
combined_discontinuity_risk
acoustic_context_only
```

Thresholds v1:

```text
silence                  -42.0 dBFS
max RMS delta             12.0 dB
max boundary sample jump   0.35
max boundary jump ratio    1.25
```

Evidencia:

```text
33781430382  131/131 PASS en 6.998 s — acoustic foundation
33781903986  131/131 PASS en 7.401 s — schema v7 + pipeline integration
```

E2E FFmpeg/sync + doctor PASS; artifacts 0.

Detalle: `Validation/phase2d-acoustic-join.md`.

##### 2D.3.3 — Human-audio acoustic evidence v1 — COMPLETADA

Reutiliza endpoints de `large-v3-turbo` del run real `33755013415` sobre el WAV AMI original CC BY 4.0, sin volver a descargar ni ejecutar el modelo.

Run `33782959293`:

```text
134/134 tests PASS en 6.803 s
3 casos humanos
1 medición acústica real
2 joins bloqueados por contexto
failures 0
automatic_edits 0
executable 0
auto_apply 0
HUMAN_ACOUSTIC_GATE=PASS
artifacts 0
```

Control humano medido:

```text
status               acoustic_context_only
RMS delta            4.9369 dB
boundary jump        0.030243
boundary jump ratio  0.340433
safe_for_cut          false
```

Retake humano → `repair_or_protected_context_risk` → `blocked_by_context`.

Correction humana con scope ambiguo → `invalid_or_unbounded_target` → `blocked_by_context`.

No se modifican thresholds v1. Una única medición humana limpia no prueba seguridad general ni calidad perceptual.

Detalle: `Validation/phase2d-human-acoustic-evidence.md`.

#### 2D.4 — Combined Eligibility / Promotion Policy Foundation — SIGUIENTE

Objetivo: definir una política acumulativa y auditable que combine semántica, scope, fillers, join context y acoustics **sin ejecutar todavía ningún corte**.

Orden:

1. definir estados de elegibilidad independientes del Edit Plan;
2. exigir que todas las guardas previas pasen antes de considerar una propuesta elegible;
3. tratar cualquier ambigüedad/riesgo como `REVIEW`/bloqueo;
4. validar `removedText` definitivo contra transcript/span/timestamps;
5. crear benchmark con positivos/negativos y fallos deliberados de cada capa;
6. mantener `safe_for_cut=false`, `executable=false`, `auto_apply=false` durante la foundation;
7. sólo después decidir si alguna clase puede pasar a 2E.

### 2E — Promotion to Edit Plan — FUTURA

Sólo después de cerrar 2D con evidencia suficiente:
- decidir clases realmente auto-aplicables;
- thresholds por modo;
- verificar joins y `removedText`;
- límites globales y fail-safe;
- resto en REVIEW / KEEP.

## Fase 3 — Calidad audiovisual / auditoría
Normalización, join treatment, denoise controlado, join audit, post-render verification e informe.

## Fase 4 — UX mínima
Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, renderizar y abrir outputs.

## Fase 5 — Portable Release Hardening
Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras
Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. mergear 2D.3.3 human-audio acoustic evidence;
2. arrancar 2D.4 Combined Eligibility / Promotion Policy Foundation;
3. validar `removedText` definitivo y guardas acumulativas sin ejecutar cuts;
4. mantener `safe_for_cut=false`, `executable=false`, `auto_apply=false`;
5. no promover al Edit Plan antes de cerrar 2D.
