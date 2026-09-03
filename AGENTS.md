# AGENTS.md — Video_Tunner

Contexto técnico permanente para agentes. Referencia maestra externa vigente: `00.Contexto y Reglas de Trabajo_GitHub_Video_Tunner_v3`.

## 1. Invariantes

Video_Tunner debe producir vídeo hablado limpio, natural, fiel, sincronizado, auditable y reversible en Windows 10/11 x64.

Obligatorio:

1. portable real: ZIP → descomprimir → ejecutar;
2. vídeo con audio embebido o vídeo + audio externo;
3. resolver master audio antes de cualquier análisis temporal;
4. Whisper y VAD usan exactamente el mismo master audio;
5. auto-sync sólo con evidencia suficiente; fallback/override manual;
6. original siempre intacto;
7. `candidate != semantic decision != edit`;
8. `PROPOSED_CUT != executable CUT`;
9. ante duda: `KEEP / REVIEW`;
10. modo Conservador por defecto.

```text
sources → ingest/sync → MASTER AUDIO → Whisper/VAD → candidates → semantic decisions/protection → future Edit Plan → render → audit
```

## 2. Estado

Versión `0.1.0-dev`.

Completado:

- Fase 0 — Bootstrap;
- Fase 0.5 — Technology Harvest;
- Fase 1A — Portable Foundation;
- Fase 1B — dual ingest + master audio + sync/drift;
- Fase 1C — Whisper/VAD sobre master + `large-v3-turbo` español real;
- Fase 2A — Semantic Candidates v1;
- Fase 2B — Semantic Decisions + Protection v1.

Pendiente inmediato: **Fase 2C — validación semántica real**. No existe todavía promoción semántica al Edit Plan.

## 3. Evidencia principal

- Portable core `33600174568`: PASS.
- Portable ML `33621357438`: PASS.
- Sync hardening `33639009841`: PASS.
- Master-audio analysis `33640872486`: PASS.
- Target-model Spanish `33656235038`: PASS — WER 1.64%, RTF 0.4854, peak 1818.7 MiB, modelo 1546.5 MiB, automatic edits 0.
- Semantic Candidates `33659725847`: PASS — 48 tests, doctor PASS, artifacts 0.
- Semantic Decisions/Protection `33741195594`: PASS — 55 tests en 6.671 s, doctor PASS, artifacts 0.

Run `33661062365`: 54/55 PASS. El único fallo fue un test heredado que esperaba `analysis.json schema_version == 2`; Fase 2B eleva deliberadamente el schema actual a v3. Se corrigió sólo el test, no código productivo.

## 4. Stack fijado

```text
faster-whisper 1.2.1
CTranslate2 4.8.1
ONNX Runtime 1.29.0
tokenizers 0.23.1
NumPy 2.5.2
PyInstaller 6.22.2
```

VAD: faster-whisper + `silero_vad_v6.onnx`. No standalone Torch.

Modelo objetivo: `large-v3-turbo`; `tiny` sólo para fixtures baratos.

Validación target-model:

```text
repo: rtlingo/mobiuslabsgmbh-faster-whisper-large-v3-turbo
revision: 6bd64462dd562f8062828f585c3709aa52df0083
model.bin sha256: e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da
```

## 5. Portable

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

Frozen => portable strict. Sin fallback silencioso a PATH o caches globales.

## 6. Ingesta / sync

Convención temporal inmutable:

```text
video_time = offset_seconds + time_scale * external_time
```

Auto-sync actual: log-RMS → ZNCC coarse → anchors multi-window → offset/scale → MAD outliers → confidence/residual/coverage.

Evidencia insuficiente => `review_required`, sin master. Huecos del audio externo son silencio; nunca mezclar implícitamente audio de cámara.

Outputs:

```text
<stem>_master_audio.flac
<stem>_ingest.json
```

## 7. Analysis / schema

`analyze` siempre usa master audio acreditado. Master pre-resuelto exige `ingest.json` y SHA-256 del vídeo fuente coincidente.

Fase 1C introdujo `analysis.json` schema v2 para provenance. **Schema actual: v3 desde Fase 2B.**

Schema v3 separa:

```text
candidates[]
semantic_decisions[]
```

Safety flags obligatorios:

```text
semantic_protection_enabled = true
semantic_decisions_are_not_edits = true
semantic_decisions_executable = false
```

`automatic_edits` permanece `0`.

## 8. Fase 2A — Semantic Candidates v1

Módulo: `Source/video_tunner/semantic_candidates.py`.

Clases:

```text
possible_repetition
possible_retake
explicit_correction
```

Todo candidate semántico:

```text
decision = undecided
suggested_decision = REVIEW
auto_apply = false
span_safe_for_auto_apply = false
```

Conservar normalmente la lectura posterior. En `explicit_correction` el span es sólo el marcador; detectar `perdón` no demuestra qué texto anterior debe borrarse.

Referencia conceptual: `Railly/vcut@2142cc54dc01a0d2272f1d99717b89cd1c7c9262`. Implementación Python propia.

## 9. Fase 2B — Semantic Decisions + Protection v1

Módulos:

```text
Source/video_tunner/semantic_decisions.py
Source/video_tunner/semantic_report.py
```

Decisiones posibles:

```text
KEEP
REVIEW
PROPOSED_TRIM
PROPOSED_CUT
```

Todas siguen:

```text
executable = false
auto_apply = false
```

Guardas deterministas v1:

- integridad de word indices/timestamps;
- `removed_text` debe coincidir con el transcript;
- cifras;
- importes, porcentajes y unidades;
- negaciones;
- persona/sujeto;
- tiempo/aspecto y marcadores temporales;
- causalidad/contraste;
- señal heurística de entidades/nombres.

Span inconsistente => `KEEP` + `guard_status=blocked`.

Política:

- repetición adyacente exactamente equivalente puede producir `PROPOSED_CUT`, nunca ejecutable;
- retake con material real o conflicto protegido => `REVIEW`;
- `explicit_correction` => siempre `REVIEW` en v1 y registra relación intento/corrección;
- no inferir equivalencias ni conversiones de unidades;
- no intentar reparar silenciosamente un candidate inválido.

Casos cubiertos:

```text
200 → perdón → 250 mil euros
10% → perdón → 15%
no funciona → perdón → funciona
```

Ver `Validation/phase2-semantic-protection.md`.

## 10. Siguiente — Fase 2C

Crear corpus/fixtures de habla real con:

- retomas/reinicios;
- repeticiones;
- errores/autocorrecciones;
- cifras/importes/porcentajes;
- negaciones;
- nombres/entidades;
- sujeto/persona;
- tiempo/aspecto;
- fillers.

Objetivos:

1. medir falsos positivos/falsos negativos;
2. tensionar las guardas actuales;
3. inferir de forma segura el scope `intento incorrecto → corrección válida`;
4. distinguir fillers eliminables de elementos necesarios para naturalidad/significado;
5. añadir límites de frase/join safety antes de promotion;
6. mantener `executable=false` hasta evidencia suficiente.

Cualquier modelo semántico futuro debe estar bounded por candidates deterministas y guardas de seguridad; local-first y fail-safe.

## 11. Edit Plan / render

Edit Plan sólo contiene ediciones efectivas aprobadas; nunca candidates o semantic decisions no ejecutables.

Renderer actual: merge overlaps, trim/atrim+concat, H.264/AAC, no overwrite, abort si elimina todo.

Pendiente: source hash, removedText definitivo del edit aprobado, join audit, edge fades, loudness y post-render verification.

## 12. Technology harvest

Video_Tunner NO es fork. Referencias principales: Railly/vcut, Cadence-Lab, ai-video-editor y SYSTRAN/faster-whisper. Ver `UPSTREAM_SOURCES.md`.

Antes de adoptar código: licencia + commit + motivo + validación propia.

## 13. GitHub / CI / Release

GitHub es source of truth.

- CI deliberada; no Actions como debugger;
- no polling frecuente;
- no modelos, vídeos, ZIPs o artifacts pesados ordinarios;
- Manual CI ligera = paquete base + NumPy + FFmpeg; no sustituye validaciones ML/portable;
- workflows manual-only normalmente;
- si el conector no puede `workflow_dispatch`, usar sólo el mecanismo one-shot documentado, restaurando inmediatamente `workflow_dispatch` y eliminando el marker;
- no publicar GitHub Release sin autorización expresa de Guille.

## 14. Repo / docs

No versionar builds, modelos, vídeos, caches, outputs ni ZIPs.

Cambios relevantes => mantener sincronizados README, AGENTS, ROADMAP, RELEASE_STATUS y Validation cuando corresponda.

## 15. Changelog técnico

- Bootstrap: CLI, tools, silence Cleaner, Edit Plan, render.
- Portable core/ML: PyInstaller onedir, tools/modelos locales, frozen/offline PASS.
- Sync: dual ingest, offset/drift, confidence/coverage, manual override, master FLAC alineado.
- Master analysis: mismo master para Whisper + VAD, provenance.
- Target Spanish: `large-v3-turbo`, WER 1.64%, RTF 0.4854.
- Semantic Candidates v1: repetitions/retakes/explicit corrections review-only.
- Semantic Decisions + Protection v1: schema v3, guardas deterministas, 55-test Windows lightweight PASS, ninguna decision ejecutable.
