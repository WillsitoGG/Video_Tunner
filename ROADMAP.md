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
Target Spanish `33656235038`: WER `1.64%`, RTF `0.4854`, automatic edits 0.

### Fase 2A — Semantic Candidates v1
Run `33659725847` PASS.

### Fase 2B — Semantic Decisions + Protection v1
Run `33741195594` PASS.

### Fase 2C — Validación semántica real — COMPLETADA COMO BLOQUE DE EVIDENCIA v1

- 2C.1 `33743029443`: benchmark foundation PASS.
- 2C.2 `33750836791`: corpus humano bilingüe PASS.
- 2C.3 `33755013415`: audio humano real → semantic gate PASS.

## Fase 2 — Cleaner inteligente — EN CURSO

### 2D — Scope + fillers + join safety + eligibility — COMPLETADA COMO FOUNDATION/EVIDENCE

#### 2D.1 — Correction Scope Foundation v1 — COMPLETADA
Schema v4. Final `33758185755`: 88/88 PASS.

#### 2D.2 — Fillers Contextuales Foundation v1 — COMPLETADA
Schema v5. Final `33771792867`: 101/101 PASS.

#### 2D.3 — Sentence/join safety — COMPLETADA COMO BLOQUE DE EVIDENCIA v1

- 2D.3.1 join context/schema v6: `33773287106`, 117/117 PASS.
- 2D.3.2 acoustic join/schema v7: `33781903986`, 131/131 PASS.
- 2D.3.3 human acoustic: `33782959293`, 134/134 PASS, human gate PASS.

No se modificaron thresholds acústicos tras la evidencia humana.

#### 2D.4 — Combined Eligibility / Promotion Policy Foundation v1 — COMPLETADA

Schema v8 aplica guardas acumulativas fail-safe:

```text
removedText integrity
→ correction scope
→ filler context
→ semantic decision
→ join context
→ acoustic evidence
→ foundation_guards_pass OR blocker
```

`foundation_guards_pass` no es autorización de corte:

```text
future_promotion_candidate = true
safe_for_cut = false
executable = false
auto_apply = false
```

Run `33790792753`: 138/138 PASS. Detalle: `Validation/phase2d-combined-eligibility.md`.

#### 2D.5 — Human Combined Eligibility Evidence v1 — COMPLETADA

Run final `33791950505`:

```text
142/142 tests PASS
HUMAN_ELIGIBILITY_GATE=PASS
cases                    3
foundation_guards_pass   1
blocked                  2
safe_for_cut             0
executable               0
auto_apply               0
automatic_edits          0
```

Detalle: `Validation/phase2d-human-combined-eligibility.md`.

#### 2D.6 — Human Positive Eligibility Expansion / Close-out Gate — COMPLETADA

Se construyó una selección reproducible a partir de anotaciones manuales AMI de repetición/reparandum/reparans, usando tokenización equivalente a producción y headsets individuales por hablante.

Discovery ligero `33892213960`:

```text
exact repeats compatibles  80
seleccionados                8
fuentes/headsets             4
```

El criterio de suficiencia se fijó antes de observar la corrida pesada:

```text
casos long evaluados                 >= 8
positivos alineados                  >= 3
foundation_guards_pass humanos       >= 2
fuentes con foundation pass          >= 2
```

Final `33894995584`:

```text
155 tests OK (11 host-PATH skips)
HUMAN_POSITIVE_EVIDENCE_GATE     PASS
HUMAN_POSITIVE_CLOSE_OUT_DECISION CLOSE_OUT_READY
casos evaluados                   8
positivos alineados               6
foundation_guards_pass            3
fuentes con foundation pass       2
hard failures                     0
safe_for_cut                      0
executable                        0
auto_apply                        0
automatic_edits                   0
artifacts                          0
```

Diagnóstico:

```text
ASR no conserva repeat completo       2
detectado + foundation_guards_pass    3
detectado + blocked_join_context      3
```

No hubo detector miss sobre una repetición completa preservada por ASR en esta muestra. No generalizar esta observación fuera de la muestra.

**Decisión: Fase 2D cerrada como foundation/evidence.** Esto no habilita cortes: todos los `future_promotion_candidate` siguen no ejecutables.

Detalle: `Validation/phase2d-human-positive-closeout.md`.

### 2E — Promotion to Edit Plan — SIGUIENTE

Objetivo: diseñar y validar la promoción explícita desde assessments no ejecutables al Edit Plan aprobado.

Orden:

1. definir qué clases pueden ser candidatas a promoción;
2. mantener blockers de 2D como veto acumulativo;
3. definir approval/thresholds por modo sin convertir `foundation_guards_pass` en autorización automática;
4. fijar límites globales/fail-safe y reglas de REVIEW/KEEP;
5. definir contrato auditable entre eligibility y Edit Plan;
6. validar primero con corpus sintético/controlado y después con evidencia humana;
7. mantener ejecución automática desactivada hasta validar la promotion policy explícita.

## Fase 3 — Calidad audiovisual / auditoría
Normalización, join treatment, denoise controlado, join audit, post-render verification e informe.

## Fase 4 — UX mínima
Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, renderizar y abrir outputs.

## Fase 5 — Portable Release Hardening
Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras
Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. integrar/cerrar 2D.6 en `main` manteniendo el workflow de close-out manual-only;
2. arrancar 2E — Promotion to Edit Plan;
3. diseñar el contrato de promoción sin relajar ninguna guarda de 2D;
4. no convertir `future_promotion_candidate` en edición ejecutable por defecto;
5. reservar nueva CI pesada para evidencia que cambie una decisión técnica.
