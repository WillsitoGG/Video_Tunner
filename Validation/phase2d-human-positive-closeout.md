# Phase 2D.6 — Human Positive Eligibility Expansion / Close-out Gate

## Resultado

**CLOSE_OUT_READY — Fase 2D cerrada como foundation/evidence.**

La validación final se ejecutó en GitHub Actions sobre Windows con el portable frozen, `large-v3-turbo` fijado y audio humano AMI speaker-specific.

- Run final: `33894995584`
- Commit evaluado: `aecea4a35ed204d877b02937d5746a41d41af5d7`
- Workflow: `Human Positive Closeout Spike`
- Modelo: `large-v3-turbo`
- Device / compute: CPU / int8
- Analysis schema: v8
- Regression suite: **155 tests OK**, 11 skipped por no disponer de FFmpeg/ffprobe en el PATH del host; el FFmpeg portable y el build portable sí pasaron en el mismo job.
- `HUMAN_POSITIVE_EVIDENCE_GATE=PASS`
- `HUMAN_POSITIVE_CLOSE_OUT_DECISION=CLOSE_OUT_READY`
- Artifacts subidos: 0

## Criterio de cierre precomprometido

Los umbrales de suficiencia se fijaron en `tests/fixtures/human_positive_closeout_ami_v2.json` **antes de observar el resultado**:

```text
casos long evaluados                 >= 8
positivos humanos alineados          >= 3
foundation_guards_pass humanos       >= 2
fuentes/headsets con foundation pass >= 2
```

Resultado:

```text
casos long evaluados                  8
positivos humanos alineados           6
foundation_guards_pass humanos        3
fuentes/headsets con foundation pass  2
hard failures                         0
safe_for_cut                          0
executable                            0
auto_apply                            0
automatic_edits                       0
```

No se modificó ningún threshold de detector, semántica, join, acústica o eligibility para alcanzar el gate.

## Procedencia y selección

La evidencia procede de las anotaciones manuales del **AMI Meeting Corpus**, licencia CC BY 4.0. Para evitar contaminar la selección con el resultado del modelo:

1. se construyó un descubridor reproducible sobre la capa AMI de disfluencias;
2. se corrigió su tokenización para que coincidiera con producción, incluidas contracciones inglesas (`you've` → `youve` como un token);
3. run ligero de discovery `33892213960`;
4. se localizaron **80 exact repeats** compatibles con el detector conservador actual;
5. antes de ejecutar Whisper se seleccionaron determinísticamente 8 casos, máximo 2 por fuente y 4 fuentes;
6. cada caso se validó desde el **headset individual del hablante**, no desde `Mix-Headset`.

Mirror de inspección fijado:

```text
ColingPaper2018/DialogueAct-Tagger
commit 4307e9899ed9058e80d0861530de124d4f134317
```

Ontología usada:

```text
repeat      ami_dsfl_12
reparans    ami_dsfl_18
reparandum  ami_dsfl_19
```

## Fuentes de audio

Los WAV se descargaron sólo de forma efímera en el runner y no se subieron como artifacts.

```text
ES2002c-A  ES2002c.Headset-0.wav
  bytes   77,558,826
  SHA256  8EBE721E36DF28A27B2C83BD987B16052018C22AE382FA49AE3A100D4BA530E7

ES2002b-D  ES2002b.Headset-3.wav
  bytes   72,951,852
  SHA256  B94F7B20C7B633AA37ED23CEB644C8376968CFAB1FADAA23FE47460194A46253

TS3005d-C  TS3005d.Headset-2.wav
  bytes   85,510,444
  SHA256  1EC6AC109D322940E17D807213A95EE946AA5C160992628D8475FB0D7C60E3E3

ES2006b-C  ES2006b.Headset-2.wav
  bytes   69,860,056
  SHA256  D668D2953E596540F755B1BF4E511E9284DC9A9F40248F358A93DDFEF1ACB28F
```

## Resultado por caso

| Caso | Reparandum humano | Resultado |
|---|---|---|
| `ami-es2002c-a-repeat-209` | `what would we` | ASR no conserva la repetición completa |
| `ami-es2002b-d-repeat-157` | `what you've just told me` | `foundation_guards_pass` |
| `ami-ts3005d-c-repeat-298` | `And then you can` | `foundation_guards_pass` |
| `ami-es2006b-c-repeat-38` | `There we go` | detectado/alineado; `blocked_join_context` |
| `ami-es2002c-a-repeat-173` | `Are you thinking` | ASR no conserva la repetición completa |
| `ami-es2002b-d-repeat-13` | `a lot of` | `foundation_guards_pass` |
| `ami-ts3005d-c-repeat-148` | `the next question` | detectado/alineado; `blocked_join_context` |
| `ami-es2006b-c-repeat-41` | `if you press` | detectado/alineado; `blocked_join_context` |

### Diagnóstico por etapa

```text
asr_repeat_not_preserved                 2
foundation_guards_pass                   3
downstream_blocked:blocked_join_context  3
```

En esta muestra no apareció ningún:

```text
detector_miss_on_preserved_repeat
candidate_span_mismatch
timing_mismatch
```

Por tanto, cuando el ASR conserva la repetición humana completa, el detector actual la identifica en los 6/6 casos de esta muestra. Tres pasan las guardas foundation y tres se bloquean deliberadamente por contexto de join.

Esto **no** autoriza a generalizar una tasa de detección de 100% fuera de esta muestra.

## Safety

El cierre de 2D sólo acredita que existe evidencia humana positiva suficiente para empezar a diseñar 2E.

Incluso en `foundation_guards_pass`:

```text
future_promotion_candidate = true
safe_for_cut = false
executable = false
auto_apply = false
```

Y en todo el run final:

```text
safe_for_cut       0
executable         0
auto_apply         0
automatic_edits    0
```

No existe todavía promoción automática al Edit Plan ni corte automático derivado de estas evaluaciones.

## Decisión

**Cerrar Fase 2D** y pasar a **Fase 2E — Promotion to Edit Plan**.

2E debe diseñar explícitamente qué clases pueden promocionarse, con qué approval/thresholds/límites y qué condiciones siguen en REVIEW/KEEP. El hecho de que un caso sea `future_promotion_candidate` no supone aprobación de edición.
