# Fase 2B — Semantic Decisions + Protection

Fecha: 2026-09-02.

## Objetivo

Introducir una capa explícita entre `candidate` y `edit` que evalúe guardas semánticas deterministas antes de permitir siquiera una propuesta de corte.

```text
candidate → semantic decision → future approved edit
```

En este milestone **ninguna semantic decision es ejecutable**.

## Contrato

Decisiones posibles:

```text
KEEP
REVIEW
PROPOSED_TRIM
PROPOSED_CUT
```

Invariantes actuales:

```text
executable = false
auto_apply = false
```

`PROPOSED_CUT` significa únicamente que una heurística pasó las guardas deterministas disponibles. No modifica Edit Plan ni render.

## Schema

`analysis.json` pasa a schema v3 y mantiene bloques separados:

```text
candidates[]
semantic_decisions[]
```

Cada decision referencia `candidate_id` y registra:

- decision y confidence;
- guard status (`pass`, `review`, `blocked`);
- proposed span;
- `removed_text`;
- validación de word indices/timestamps;
- rasgos semánticos protegidos;
- rationale;
- `executable=false`;
- `auto_apply=false`.

## Guardas v1

### Span integrity

Antes de razonar sobre significado:

- word indices deben existir y estar dentro del transcript;
- `removed_text` normalizado debe coincidir con las palabras del span;
- start/end deben coincidir con los word timestamps dentro de tolerancia.

Mismatch => **KEEP fail-safe**.

### Cifras

Detectar:

- dígitos/decimales;
- porcentajes;
- palabras numéricas comunes ES/EN.

Ejemplo crítico:

```text
la facturación fue de 200 perdón de 250 mil euros
```

`200` y `250` se registran como valores distintos a ambos lados del marcador y la decisión queda `REVIEW`.

### Unidades / importes

Detectar de forma conservadora símbolos y unidades comunes:

- `%`, `€`, `$`, `£`;
- euro/dólar;
- kg/g/l/ml;
- m/km;
- segundos/minutos/horas;
- equivalentes básicos EN.

No inferir conversiones/equivalencias.

### Negaciones

Protección de `no`, `nunca`, `jamás`, `sin`, `not`, `never`, etc.

Cambio de negación alrededor de una autocorrección => `REVIEW`.

### Persona / sujeto

Pronombres personales básicos ES/EN se registran como rasgo protegido. Esta heurística no sustituye a un parser lingüístico.

### Tiempo / aspecto

Se registran auxiliares y marcadores temporales básicos (por ejemplo `fue`, `era`, `será`, `ayer`, `mañana`, `was`, `will`). Es una guardia conservadora, no análisis morfosintáctico completo.

### Entidades

Se registra una señal heurística de tokens capitalizados. No se afirma NER fiable todavía; cualquier uso de esta señal debe seguir siendo review-only.

## Política por candidate kind

### `possible_repetition`

Si ambas ocurrencias son exactamente equivalentes tras normalización y la segunda queda fuera del proposed span:

```text
PROPOSED_CUT
executable=false
```

Incluso si la frase contiene cifras/negaciones, la propuesta no es ejecutable; la equivalencia exacta conserva una copia de esos rasgos.

### `possible_retake`

Si existe material intermedio no trivial o conflicto protegido:

```text
REVIEW
```

Sólo material compuesto por tokens de vacilación/corrección muy restringidos podría llegar a `PROPOSED_CUT`, todavía no ejecutable.

### `explicit_correction`

Siempre `REVIEW` en v1. Detectar `perdón` no demuestra automáticamente dónde empieza la toma incorrecta.

Se registra una `correction_relation` con ventanas de intento/corrección y cambios protegidos.

## Tests de riesgo

La suite específica cubre:

1. repetición exacta → `PROPOSED_CUT`, no ejecutable;
2. `200 → perdón → 250 mil euros` → REVIEW + cifra/unidad crítica;
3. `10% → perdón → 15%` → protección de número y `%`;
4. cambio de negación → REVIEW;
5. retoma con contenido no trivial → REVIEW;
6. candidate span corrupto → KEEP fail-safe;
7. todas las semantic decisions permanecen no ejecutables;
8. pipeline integra decisions separadas de candidates y mantiene `automatic_edits=0`.

## Pendiente antes de promover edits

- validación Windows de este milestone;
- fixture hablado real con errores/retomas deliberados;
- ampliar guardas lingüísticas sólo con evidencia;
- join safety y límites de frase;
- decisión explícita de qué clases podrían ser auto-aplicables por modo;
- ningún Edit Plan automático hasta superar esas validaciones.
