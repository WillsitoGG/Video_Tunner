# Release Status

## Estado actual

- Proyecto: Video_Tunner
- Versión de desarrollo: `0.1.0-dev`
- Release publicada: **no**
- ZIP portable final validado: **no**
- Windows 10/11 x64 validado manualmente por Guille: **no**
- Fase 0: COMPLETADA
- Fase 0.5: COMPLETADA
- Fase 1A: COMPLETADA — Portable Foundation core + ML PASS
- Fase 1B: COMPLETADA — dual ingest + sync/drift PASS
- Fase 1C: COMPLETADA — master → Whisper/VAD + target Spanish PASS
- Fase 2A: COMPLETADA — Semantic Candidates v1
- Fase 2B: COMPLETADA — Semantic Decisions + Protection v1
- Fase 2C: **EN CURSO — benchmark foundation + retake humano + correcciones humanas bilingües PASS**

## Evidencia principal

```text
Portable core                    33600174568  PASS
Portable ML                      33621357438  PASS
Sync hardening                   33639009841  PASS
Master analysis                  33640872486  PASS
Target Spanish                   33656235038  PASS — WER 1.64%, RTF 0.4854
Semantic Candidates              33659725847  PASS — 48 tests
Semantic Decisions/Protection    33741195594  PASS — 55 tests
```

Todas mantienen `automatic_edits = 0` donde aplica y artifacts pesados = 0.

## Fase 2C

### Foundation baseline — `33742519997`

```text
60 tests PASS
FP 2 / FN 0
precision 84.62%
recall 100%
F1 91.67%
unsafe proposals 0
```

### Foundation ajustada — `33743029443`

```text
64 tests PASS
21 casos / 11 eventos
FP 0 / FN 0
precision = recall = F1 = 100% en ese corpus
unsafe proposals 0
executable 0
auto_apply 0
artifacts 0
```

### Primer retake humano — `33743638690`

```text
65 tests PASS
22 casos / 12 eventos
possible_retake → REVIEW
FP 0 / FN 0
unsafe proposals 0
artifacts 0
```

### Correcciones humanas bilingües — baseline `33750475437`

Se añadieron:

- AMI EN: `I mean` correction positivo y `I mean` discourse negativo;
- CORMA ES: `Perdón` correction positivo y `perdón eh` apology negativo.

Baseline:

```text
69 tests PASS en 6.718 s
26 casos / 14 eventos
14 TP / 2 FP / 0 FN
precision 87.50%
recall 100%
F1 93.33%
unsafe proposals 0
executable 0
auto_apply 0
```

El gate falló únicamente por precision; los 2 FP eran los dos usos humanos ambiguos de marcador.

### Tuneo Conservador

- `I mean / quiero decir`: exige frontera explícita de reparación o sustitución numérica;
- `perdón / perdona / sorry`: rechaza patrón de disculpa/hesitación sin intento interrumpido;
- fragmento truncado + marcador sigue siendo `explicit_correction → REVIEW`;
- modo Agresivo mantiene detección más amplia.

### Final — `33750836791`

```text
74 tests PASS en 6.729 s
26 casos
14 eventos esperados / 14 candidates
FP 0
FN 0
precision 100%
recall 100%
F1 100%
decision mismatches 0
unsafe proposals 0
missing safe proposals 0
executable decisions 0
auto_apply decisions 0
artifacts 0
```

Además:

- `video-tunner doctor` PASS;
- E2E FFmpeg/sync PASS;
- workflow restaurado a manual-only;
- trigger marker eliminado.

**El 100% acredita únicamente el corpus etiquetado actual.** El harness usa timings deterministas y no prueba todavía que el transcript de Whisper preserve las mismas señales manuales de reparación.

## Safety actual

```text
candidate != semantic decision != edit
PROPOSED_CUT != executable CUT
semantic_decisions_executable = false
executable = false
auto_apply = false
automatic_edits = 0
```

`explicit_correction` sigue siendo marker-only: todavía no se infiere qué span anterior debe eliminarse.

## Pendiente antes de Release

- Fase 2C.3: pocos clips humanos reales → `large-v3-turbo` → semantic gate;
- priorizar evidencia en español;
- comprobar pérdida de truncamientos/puntuación por ASR;
- correction scope seguro;
- fillers contextuales;
- límites de frase y join safety;
- no promover semantic decisions al Edit Plan hasta evidencia suficiente;
- Fase 3 calidad audiovisual/audit;
- Fase 4 UX;
- Fase 5 Release Hardening + licencias/notices + Windows limpio real;
- estrategia final de distribución/adquisición del modelo.

No existe todavía paquete final para `SHA256SUMS.txt` ni versión para `Archive/`.

**No publicar una GitHub Release sin autorización expresa de Guille.**
