# Fase 2C.3 — Audio-backed semantic validation

Fecha: 2026-09-03.

Estado: **PRIMER GATE AUDIO REAL COMPLETADO; FASE 2C SIGUE EN CURSO**.

## Objetivo

Comprobar qué ocurre realmente cuando una reparación humana pasa por toda la cadena:

```text
AMI human audio
→ frozen Video_Tunner portable
→ pinned large-v3-turbo
→ word timestamps
→ semantic candidates
→ semantic decisions/protection
```

El objetivo no es demostrar auto-edición, sino verificar que la capa semántica sigue siendo fail-safe cuando Whisper transforma u omite señales presentes en la transcripción manual.

Invariantes durante toda la prueba:

```text
candidate != semantic decision != edit
executable = false
auto_apply = false
automatic_edits = 0
```

## Fuente de audio

Corpus: **AMI Meeting Corpus**, meeting `ES2012d`, `Mix-Headset.wav`.

```text
bytes   30388952
sha256  39FCDE566E2D1BC7EC40A31DEC19251CC253AAC54BE94713E68EEA3008AF4F8D
license CC BY 4.0
```

El WAV se descarga únicamente a `RUNNER_TEMP`; no se versiona ni se sube como artifact. Tampoco se suben modelos, vídeos temporales ni outputs de análisis.

Se reutiliza el snapshot fijado de `large-v3-turbo`:

```text
repo      rtlingo/mobiuslabsgmbh-faster-whisper-large-v3-turbo
revision  6bd64462dd562f8062828f585c3709aa52df0083
model.bin E76620F83D5F5B69EFD3D87E3DC180C1BD21DF9FBEBACFD4335E5E1EFCC018DA
```

## Casos de audio

Tres ventanas pequeñas del mismo meeting:

1. **retake humano** alrededor de `00:36`;
2. **corrección real con `I mean`** alrededor de `02:50`;
3. **`I mean` discursivo** alrededor de `03:11` como control negativo de correction.

La transcripción manual AMI sirve como etiqueta humana. La decisión se evalúa sobre el transcript real generado por Whisper, no sobre la puntuación manual.

## Run 33753369992 — NO es evidencia semántica

El primer intento pesado validó:

- descarga AMI;
- modelo fijado;
- build portable;
- regresiones.

Pero el harness PowerShell tenía un `ParserError` por interpolación de `$caseId:` y no llegó a ejecutar la inferencia semántica.

Por tanto:

```text
33753369992 != semantic evidence
```

A raíz de ello se añadió un preflight de parser PowerShell antes de cualquier descarga pesada.

## Baseline audio real — run 33753794651

Este fue el **primer run audio-backed semánticamente válido**.

Infraestructura:

- parser preflight PASS;
- AMI download PASS;
- modelo fijado PASS;
- portable frozen PASS;
- regresiones PASS;
- las tres inferencias reales se ejecutaron.

El semantic gate falló en 2 de 3 casos, sin ninguna edición automática ni decisión ejecutable.

### Hallazgo 1 — Whisper puede fabricar una repetición textual exacta

Manual:

```text
... have a look at the uh th- have a look at the prototypes ...
```

Whisper omitió la vacilación/truncamiento y produjo aproximadamente:

```text
... have a look at the have a look at the prototypes ...
```

El detector vio una `possible_repetition` textualmente exacta y, antes del hardening, produjo `PROPOSED_CUT` no ejecutable.

Conclusión: **igualdad textual del ASR no prueba igualdad del habla original**.

### Hallazgo 2 — Whisper puede borrar la frontera manual de reparación

Manual:

```text
I just wondered - I mean h- how will people put these down ...
```

Whisper produjo aproximadamente:

```text
I just wonder I mean how will people put these down ...
```

Desaparecieron `-` y `h-`, por lo que la antigua regla conservadora basada en truncamiento produjo un FN.

Conclusión: la detección no puede depender exclusivamente de guiones o tokens truncados de transcripts manuales.

### Control negativo

En el `I mean` discursivo Whisper produjo usos del marcador sin `explicit_correction`. Apareció un `possible_retake` independiente, pero quedó `REVIEW`, no ejecutable.

## Hardening guiado por el baseline audio

### 1. Exact repetition + timing anómalo

Los candidates de repetición registran ahora:

```text
first_occurrence_seconds
second_occurrence_seconds
first_seconds_per_token
second_seconds_per_token
```

Una repetición exacta sólo puede conservar la propuesta `PROPOSED_CUT` si sus timings no son anómalamente comprimidos.

Threshold conservador actual:

```text
MIN_REPEAT_SECONDS_PER_TOKEN_FOR_PROPOSAL = 0.12
```

Si cualquiera de las dos ocurrencias cae por debajo:

```text
possible_repetition → REVIEW
```

No se borra el candidate: se conserva la evidencia y se rebaja la decisión por seguridad.

### 2. `I mean / quiero decir` tras pérdida de puntuación

Además de frontera explícita o sustitución numérica, el modo Conservador admite una señal estrecha de **reformulación interrogativa** cuando el token inmediatamente posterior es, por ejemplo:

```text
EN: how / what / when / where / who / which / why
ES: como / cuando / donde / quien / cual / cuanto
```

`que` no se incluye en español por su alta ambigüedad como complementizador.

La nueva señal sólo crea `explicit_correction`; la decisión sigue siendo `REVIEW` y marker-only.

## Regresión ligera — run 33754755238

Antes de volver a descargar el modelo se ejecutó la CI Windows ligera completa:

```text
76 tests PASS en 5.561 s
FFmpeg E2E PASS
sync/drift E2E PASS
semantic corpus previo PASS
human correction corpus PASS
doctor PASS
artifacts 0
```

Esto verifica que las nuevas guardas no rompen el comportamiento anterior.

## Gate final audio real — run 33755013415

**SUCCESS**.

Infraestructura:

```text
PowerShell parser preflight PASS
AMI download/hash PASS
pinned large-v3-turbo PASS
frozen portable build PASS
semantic audio gate PASS
artifacts 0
```

El regression step del workflow pesado ejecutó 76 tests con 8 skips porque el runner no expone FFmpeg externo en PATH en ese step; los mismos E2E FFmpeg/sync ya habían pasado inmediatamente antes en `33754755238`.

### Caso 1 — retake real colapsado por ASR

Whisper:

```text
... have a look at the have a look at the prototypes ...
```

Candidate:

```text
possible_repetition
first occurrence = 0.56 s / 5 tokens = 0.112 s/token
second occurrence = 1.18 s / 5 tokens = 0.236 s/token
```

Como:

```text
0.112 < 0.120
```

Resultado:

```text
possible_repetition → REVIEW
guard_status = review
executable = false
auto_apply = false
```

La falsa exactitud textual ya no alcanza `PROPOSED_CUT`.

### Caso 2 — corrección real `I mean`

Whisper:

```text
... i just wonder i mean how will people put these down ...
```

Resultado:

```text
explicit_correction
question_reframe_cue = true
repair_boundary_before = false
numeric_replacement_cue = false
→ REVIEW
```

Se recupera el evento aunque Whisper haya eliminado la puntuación/truncamiento manual.

### Caso 3 — `I mean` discursivo

Whisper conserva dos usos discursivos de `I mean`.

Resultado:

```text
explicit_correction matches = 0
```

Aparece un `possible_retake` independiente para `I mean, it's ... I mean, it's ...`, pero contiene material no trivial y queda:

```text
possible_retake → REVIEW
executable = false
auto_apply = false
```

### Resumen final

```text
cases                    3
failures                 0
total analyze       53.810 s
automatic_edits           0
executable decisions      0
auto_apply decisions      0
artifacts                  0
SEMANTIC_AUDIO_GATE     PASS
```

Tiempos por caso:

```text
retake             17.451 s
I mean correction  17.533 s
I mean discourse   18.827 s
```

## Qué demuestra

- el frozen portable puede procesar audio humano real con el modelo objetivo y llegar a semantic decisions;
- Whisper puede borrar disfluencias y puntuación relevantes para semántica;
- una repetición textual exacta del ASR no debe considerarse por sí sola evidencia suficiente de corte;
- los word timestamps pueden actuar como señal de seguridad adicional;
- la reformulación interrogativa recupera este caso real de `I mean` sin convertir los usos discursivos del mismo clip en correction candidates;
- las tres decisiones relevantes permanecen `REVIEW` o fuera de correction;
- no hay semantic auto-edit.

## Qué NO demuestra

- seguridad general del threshold `0.12 s/token` en habla arbitraria;
- robustez sobre hablantes, idiomas, micrófonos o estilos diversos;
- audio-backed correction positivo en español;
- scope seguro del intento incorrecto anterior;
- join safety;
- que ninguna repetición pueda llegar todavía a un `PROPOSED_CUT` equivocado en un corpus mayor;
- que ninguna clase semántica sea apta para auto-apply.

## Siguiente trabajo

1. ampliar audio-backed positives/negatives con fuentes legalmente reutilizables;
2. priorizar español con audio cuya licencia permita esta validación;
3. tensionar el threshold temporal con más repeticiones reales y legítimas antes de considerarlo estable;
4. ampliar variantes de correction/reframe;
5. después pasar a scope de correcciones, fillers contextuales y join safety;
6. mantener `executable=false`.
