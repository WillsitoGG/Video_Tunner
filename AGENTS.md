# AGENTS.md — Video_Tunner

Contexto técnico permanente para agentes. Referencia maestra externa vigente: `00.Contexto y Reglas de Trabajo_GitHub_Video_Tunner_v3`.

## 1. Invariantes

Video_Tunner debe producir vídeo hablado limpio, natural, fiel, sincronizado, auditable y reversible en Windows 10/11 x64.

Obligatorio:

1. portable real: ZIP → descomprimir → ejecutar;
2. vídeo con audio embebido o vídeo + audio externo;
3. master audio antes de análisis temporal;
4. auto-sync sólo con evidence/confidence suficiente;
5. offset manual/override;
6. drift corregido sólo tras validación;
7. originales intactos;
8. candidate ≠ decision ≠ edit;
9. ante duda: KEEP/REVIEW.

```text
sources → ingest/sync → MASTER AUDIO + timeline → analysis → candidates → decisions → Edit Plan → render → audit
```

## 2. Estado

Versión `0.1.0-dev`.

Completado:

- Fase 0 bootstrap;
- Fase 0.5 technology harvest;
- Cleaner de silencios + Edit Plan + render;
- transcript TXT/JSON/SRT word-level;
- Candidate Analysis review-only;
- Fase 1A Portable Foundation core + ML PASS Windows;
- Fase 1B dual ingest + master audio + sync/drift COMPLETADA y hardening Windows PASS;
- Fase 1C `analyze` sobre master audio + `large-v3-turbo` en español real COMPLETADA;
- Fase 2A **Semantic Candidates v1**: repetition/retake/explicit-correction review-only, Windows tests PASS.

Pendiente inmediato: **Fase 2B semantic decisions + semantic protection**, todavía sin promoción al Edit Plan.

## 3. Evidencia principal

- Core portable `33600174568`: PASS.
- ML portable `33621357438`: PASS.
- Sync hardening `33639009841`: PASS.
- Master-audio analysis `33640872486`: PASS.
- Target-model Spanish `33656235038`: PASS — WER 1.64%, RTF 0.4854, peak 1818.7 MiB, modelo 1546.5 MiB, 0 automatic edits.
- Semantic Candidates v1 `33659725847`: PASS — 48 tests, doctor PASS, 0 artifacts.

Run `33659514611` falló porque Manual CI ejecutaba E2E de sync sin instalar NumPy. Todos los tests semánticos pasaron. Manual CI queda corregida para instalar `numpy==2.5.2` sin añadir Whisper/CTranslate2/ONNX al perfil ligero.

PyInstaller `onedir` continúa como base provisional. No evaluar Nuitka sin problema/ventaja medible.

## 4. Stack de análisis

Pins:

```text
faster-whisper 1.2.1
CTranslate2 4.8.1
ONNX Runtime 1.29.0
tokenizers 0.23.1
NumPy 2.5.2
PyInstaller 6.22.2
```

VAD usa faster-whisper + `silero_vad_v6.onnx`; no standalone Torch sin nueva evidencia.

Modelo objetivo: `large-v3-turbo`. `tiny` sólo es fixture barato de runtime/CI.

Validación reproducible de target model:

```text
repo: rtlingo/mobiuslabsgmbh-faster-whisper-large-v3-turbo
revision: 6bd64462dd562f8062828f585c3709aa52df0083
model.bin bytes: 1617884929
model.bin sha256: e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da
```

Este pin pertenece al harness de validación; no obliga al producto a usar ese mirror.

## 5. Portable / modelos

```text
Video_Tunner/
├── Video_Tunner.exe
├── _internal/
├── Tools/ffmpeg/bin/
├── Models/whisper/
├── Config/
├── Temp/
├── Cache/
├── Logs/
├── Output/
└── portable-manifest.json
```

Frozen => portable strict. Sin fallback silencioso a PATH o cache global.

Modelo completo mínimo: `config.json`, `model.bin`, `tokenizer.json`.

CLI:

```text
video-tunner model status MODEL
video-tunner model fetch MODEL [--replace]
```

## 6. Fase 1B — ingesta/sync — COMPLETADA

Contrato temporal inmutable:

```text
video_time = offset_seconds + time_scale * external_time
```

- offset > 0: externo empieza después del vídeo;
- offset < 0: externo empieza antes;
- drift ppm = `(time_scale - 1) * 1e6`.

`sync.py`: audio mono 8 kHz → log-RMS envelope 50 Hz → coarse ZNCC → anchors → fit offset/scale → MAD outliers → confidence/residual/coverage.

Política actual:

```text
confidence >= 0.65
anchors >= 3
residual RMS <= 0.08 s
abs(drift) <= 2000 ppm
coverage >= 0.98
uncovered edge <= 5 s
```

Thresholds provisionales. Evidencia insuficiente => `review_required`, sin master. Manual override permitido. Huecos de external audio son silencio, nunca mezcla implícita de camera audio.

Master output:

```text
<stem>_master_audio.flac
<stem>_ingest.json
```

## 7. Fase 1C — master audio + STT/VAD — COMPLETADA

`analyze` siempre usa master audio acreditado.

Reglas:

- Whisper y Silero consumen el mismo master;
- timestamps viven en timeline de vídeo;
- master pre-resuelto exige ingest provenance;
- SHA-256 fuente debe coincidir;
- `review_required` detiene antes de ML;
- `analysis.json` schema v2 registra provenance;
- candidates no son edits.

Target Spanish validation `33656235038`:

```text
fixture              46.58025 s
reference words      61
hypothesis words     62
word errors          1
WER                  1.64%
word timestamps      PASS
analyze              22.609 s
RTF                  0.4854
peak working set     1818.7 MiB
model                1546.5 MiB
automatic edits      0
```

## 8. Fase 2A — Semantic Candidates v1 — COMPLETADA

Módulo: `Source/video_tunner/semantic_candidates.py`.

Clases:

```text
possible_repetition
possible_retake
explicit_correction
```

### Contrato obligatorio

Todo hallazgo de esta capa:

```text
decision = undecided
suggested_decision = REVIEW
auto_apply = false
span_safe_for_auto_apply = false
```

Evidence mínima:

- `removed_text` exacto del span candidato;
- context_before/context_after;
- word indices y timestamps;
- detector y confidence;
- evidencia específica de clase;
- `requires_semantic_review=true`.

### Repeticiones/retomas

- por defecto conservar la ocurrencia posterior;
- la segunda lectura debe quedar fuera del span candidato;
- Conservador exige más tokens que Agresivo;
- limitar proximidad temporal;
- exigir palabras de contenido;
- evitar openers desplazados/sufijos duplicados;
- repetición intencional/lejana no debe convertirse automáticamente en retake.

Referencia conceptual: `Railly/vcut@2142cc54dc01a0d2272f1d99717b89cd1c7c9262`. Implementación Python propia.

### Correcciones explícitas

Marcadores v1:

- `perdón` / `perdona`;
- `mejor dicho`;
- `quiero decir`;
- `sorry`;
- `I mean`.

No tratar `o sea`/`es decir` como error por defecto.

El span de `explicit_correction` es sólo el marcador. Ejemplo:

```text
la facturación fue de 200 perdón de 250 mil euros
```

No asumir todavía que `200` debe eliminarse; la capa de decisiones debe probar cuál es intento y cuál corrección antes de proponer un corte.

### Evidencia

Run `33659725847`: 48 tests PASS, incluidos 7 tests nuevos de semantic candidates/integración, E2E de sync y doctor. Artifacts 0.

Ver `Validation/phase2-semantic-candidates.md`.

## 9. Fase 2B — Semantic Decisions + Protection — SIGUIENTE

Crear estructura explícita candidate → decision. Inicialmente ninguna decisión será ejecutable.

Salida permitida:

```text
KEEP
REVIEW
proposed TRIM
proposed CUT
```

con:

```text
executable = false
auto_apply = false
```

Guardas mínimas antes de cualquier promoción:

- números/importes/porcentajes/unidades;
- negaciones;
- sujeto/persona;
- tiempo verbal/aspecto;
- entidades/nombres relevantes;
- conectores de causalidad/contraste;
- relación intento → versión corregida;
- word boundaries medidos;
- `removed_text` debe coincidir exactamente con el span;
- ocurrencia buena nunca dentro del span eliminado.

Ante conflicto o incertidumbre: KEEP/REVIEW.

No añadir API cloud obligatoria. Si más adelante se usa modelo semántico, debe ser bounded, local-first y posterior a guardas deterministas.

## 10. Edit Plan / render

Edit Plan contiene ediciones efectivas, nunca candidates sin decision layer.

Renderer actual: merge overlaps, trim/atrim+concat, H.264/AAC, no overwrite, abort si elimina todo.

Pendiente futuro: source hash, removedText de edit aprobado, join audit, edge fades, loudness y post-render verification.

## 11. Technology harvest

Video_Tunner NO es fork.

Principales referencias: Railly/vcut, Cadence-Lab, ai-video-editor, SYSTRAN/faster-whisper. Ver `UPSTREAM_SOURCES.md`.

Antes de copiar: licencia + commit + razón. Preferir API pública o reimplementación propia.

## 12. GitHub / cuota

GitHub = source of truth.

- heavy CI deliberada;
- workflows pesados manual-only normalmente;
- no polling frecuente;
- no modelos/vídeos/ZIPs como artifacts ordinarios;
- evidence ligera en `Validation/`;
- no Release sin autorización expresa.

Manual CI ligero instala paquete base + NumPy para cubrir sync; no instala el stack ML completo.

El conector no expone `workflow_dispatch`. Procedimiento excepcional one-shot:

1. push temporal limitado a marker path;
2. crear marker una vez;
3. confirmar un run;
4. restaurar manual-only inmediatamente;
5. borrar marker;
6. verificar que no aparece run extra.

No usar como trigger normal.

## 13. Repo / docs

No versionar builds, binarios, modelos, vídeos, caches, outputs ni ZIPs.

Cambios de arquitectura/dependencias/build/validación => README + AGENTS sincronizados.

- `ROADMAP.md`: planificación;
- `UPSTREAM_SOURCES.md`: provenance;
- `Validation/`: evidencia;
- `Archive/`: releases publicadas sustituidas.

## 14. Orden inmediato

1. crear `semantic_decisions.py` / contrato equivalente;
2. implementar guardas deterministas de números/negaciones/sujeto/tiempo verbal;
3. modelar intento → corrección;
4. validar `removed_text` y boundaries;
5. crear fixtures de riesgo semántico y habla real con retomas deliberadas;
6. mantener `executable=false` y `auto_apply=false`;
7. no promover a Edit Plan hasta superar estas guardas.

## 15. Changelog técnico

### bootstrap
CLI, tools, silence Cleaner, Edit Plan, render.

### analysis layer
Word timestamps, transcript artifacts, Silero VAD, candidates.

### portable core/ML
PyInstaller onedir, local tools/models, offline frozen inference Windows PASS.

### sync foundation + hardening
Dual ingest, multi-anchor offset/drift estimator, confidence/coverage policy, manual override, failure-safe review y master FLAC alineado.

### master-audio analysis
`analyze` resuelve/verifica master audio, preserva provenance y usa el mismo master para Whisper + VAD.

### target-model Spanish validation
`large-v3-turbo` validado en frozen Windows: WER 1.64%, timestamps PASS, RTF 0.4854, 0 automatic edits.

### Semantic Candidates v1
Detector determinista review-only de repetitions/retakes/explicit corrections integrado en `analysis.json`; 48-test Windows run PASS. Fase 2A completada sin auto-apply.
