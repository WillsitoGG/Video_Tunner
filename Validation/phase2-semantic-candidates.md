# Fase 2 — Semantic Candidates v1

Fecha: 2026-09-02.

## Objetivo

Añadir el primer detector semántico determinista sobre word timestamps sin convertir todavía ninguna hipótesis en edición.

Contrato de seguridad:

```text
candidate != decision != edit
```

Todo candidato de este milestone debe cumplir:

```text
decision = undecided
suggested_decision = REVIEW
auto_apply = false
span_safe_for_auto_apply = false
```

## Clases iniciales

### `possible_repetition`

Detecta una frase adyacente repetida a partir de tokens normalizados y word timestamps.

- Conservador: mínimo 3 tokens y al menos una palabra de contenido.
- Agresivo: mínimo 2 tokens.
- La evidencia identifica primera y segunda ocurrencia.
- La segunda ocurrencia queda fuera del span candidato: el principio heredado del análisis de `vcut` es conservar la lectura posterior de una retoma/repetición hasta disponer de evidencia contraria.

### `possible_retake`

Detecta un opener repetido tras un intento intermedio corto.

Ejemplo sintético:

```text
vamos a lanzar el nuevo eh vamos a lanzar el producto mañana
^^^^^^^^^^^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^
span candidato              segunda lectura conservada
```

Guardas:

- opener mínimo configurable por modo;
- máximo 8 s entre inicios;
- máximo limitado de tokens intermedios;
- al menos una palabra de contenido;
- coincidencia máxima por la izquierda para no emitir el mismo hallazgo desplazado una palabra.

El span es evidencia para REVIEW, no un corte ejecutable.

### `explicit_correction`

Detecta sólo marcadores relativamente fuertes:

- `perdón` / `perdona`;
- `mejor dicho`;
- `quiero decir`;
- `sorry`;
- `I mean`.

No se incluyen expresiones ambiguas como `o sea` o `es decir`.

El span de esta clase es **sólo el marcador**. Video_Tunner no intenta deducir todavía cuánto texto anterior era incorrecto. El contexto anterior/posterior se adjunta para la futura capa de decisión semántica.

## Evidencia por candidato

Cada candidato semántico registra como mínimo:

- `removed_text`: texto exacto dentro del span candidato;
- `context_before`;
- `context_after`;
- índices de palabras;
- detector;
- confidence;
- razón;
- evidence específica de clase;
- `requires_semantic_review=true`;
- `span_safe_for_auto_apply=false`.

`removed_text` describe el span candidato, no afirma todavía que deba eliminarse.

## Technology harvest

Referencia consultada: `Railly/vcut@2142cc54dc01a0d2272f1d99717b89cd1c7c9262`.

Patrones adoptados como criterio, no como copia de implementación:

- mantener la ocurrencia posterior en retomas/repeticiones;
- apoyar límites en word timings medidos;
- hacer visible el texto exacto del span antes de cualquier render;
- evitar que una hipótesis semántica sea automáticamente una edición.

La implementación Python de este milestone es propia de Video_Tunner.

## Tests añadidos

`tests/test_semantic_candidates.py` cubre:

1. repetición adyacente;
2. retoma con opener repetido e intento intermedio;
3. marcador explícito `perdón` sin inventar el límite de la toma errónea;
4. frase legítimamente reutilizada muy lejos => no retake;
5. énfasis de dos palabras en Conservador => no repetición;
6. todos los candidatos review-only.

`tests/test_semantic_pipeline_integration.py` comprueba que `analyze` incorpora el candidato al `analysis.json`, le asigna ID estable y conserva `automatic_edits=0`.

## Pendiente del milestone

- CI Windows ligera de source/tests;
- prueba sobre transcript real con errores/retomas deliberados;
- capa de decisión KEEP/TRIM/CUT/REVIEW;
- protección de números, negaciones, sujeto, tiempo verbal y entidades;
- ninguna promoción a Edit Plan hasta completar esas guardas.
