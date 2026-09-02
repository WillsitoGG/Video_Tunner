# Portable Analysis Spike — Fase 1A

## Estado

**PASS — WINDOWS FROZEN ML RUNTIME VALIDADO**

GitHub Actions `Portable ML Foundation Spike` run #1 (`33621357438`) finalizó **SUCCESS** el 2026-09-02. Se ejecutó una sola vez y el trigger temporal utilizado para iniciarlo desde el conector fue retirado inmediatamente; el workflow permanece `workflow_dispatch`-only.

## Stack validado

- Python builder: 3.12.10;
- PyInstaller: 6.22.2 `onedir`;
- `faster-whisper`: 1.2.1;
- `ctranslate2`: 4.8.1;
- `onnxruntime`: 1.29.0;
- `tokenizers`: 0.23.1;
- PyAV: 18.1.0;
- Silero VAD asset: `_internal/faster_whisper/assets/silero_vad_v6.onnx`;
- FFmpeg/ffprobe: bundled bajo `Tools/ffmpeg/bin`.

FFmpeg archive SHA-256 observado en el run:

`06910d03c4c4407a092336e1b9b4d200afa361979fdb2e5971c9e0f430a355de`

## Estrategia de modelos validada

Los modelos Whisper NO se incrustan dentro de `Video_Tunner.exe` ni `_internal/`.

Ruta:

```text
Models/whisper/<modelo>/
```

El run comenzó sin `tiny`, ejecutó:

```text
Video_Tunner.exe model fetch tiny
```

y confirmó que quedó completo bajo:

```text
<portable>/Models/whisper/tiny
```

con `config.json`, `model.bin` y `tokenizer.json` presentes.

Después se activó `HF_HUB_OFFLINE=1` y se ejecutó la inferencia desde el ejecutable frozen. Por tanto, la prueba demuestra que, una vez adquirido el modelo, la inferencia no necesita resolverlo desde Internet ni desde una caché global como source of truth.

## Fixture

Fixture upstream temporal:

`SYSTRAN/faster-whisper` v1.2.1 — `tests/data/jfk.flac`

SHA-256 observado:

`63A4B1E4C1DC655AC70961FFBF518ACD249DF237E5A0152FAAE9A4A836949715`

No se versionó ni almacenó como artifact.

El workflow generó con FFmpeg bundled un vídeo negro con ese audio para ejercitar el pipeline audiovisual real.

## Resultados

### Source tests

- 23 tests ejecutados;
- 23 PASS funcionales;
- 2 tests E2E source marcados `skipped` porque FFmpeg/ffprobe no estaban deliberadamente disponibles en el PATH de esa fase;
- la disponibilidad y uso de FFmpeg bundled se validó posteriormente dentro del portable.

### Frozen runtime

PASS:

- `faster_whisper` import real;
- CTranslate2 + DLLs;
- ONNX Runtime + DLLs;
- tokenizers;
- PyAV;
- Silero V6 ONNX asset;
- runtime local;
- PATH sin Python del sistema;
- PATH sin FFmpeg del sistema.

### Inferencia real offline

`Video_Tunner.exe analyze` con modelo `tiny`, CPU/int8 y `HF_HUB_OFFLINE=1`:

- `word_count`: **22**;
- candidates: **3**;
- kinds: **3 pause**;
- automatic edits: **0**;
- review required: **3**;
- transcript JSON/TXT/SRT generados;
- analysis JSON generado.

Esto confirma además que la separación candidate ≠ edit se conserva en la ejecución frozen real.

### Tamaño

ZIP temporal del perfil ML, **sin modelo Whisper incluido**:

- bytes: `212334854`;
- aproximadamente: `202.5 MiB`;
- SHA-256: `F1208C6E830A60CB06C1AB7781C0D7D60161341AC5C9DEA3D12EFB3F2BE3AF05`.

Comparación con core portable anterior:

- core: `122677058` bytes (~117 MiB);
- ML runtime: `212334854` bytes (~202.5 MiB);
- incremento aproximado: 89.7 MB decimales antes de añadir el modelo elegido por el usuario/producto.

Artifacts de Actions almacenados: **0**.

## Observaciones / optimización posterior

PyInstaller mostró un warning al intentar recoger módulos opcionales de `onnxruntime.quantization` porque no estaba instalado el paquete `onnx`. No afectó al runtime requerido: build, import ONNX Runtime, Silero VAD e inferencia terminaron PASS.

Actualmente el build usa `--collect-all onnxruntime`, que recoge herramientas de ONNX Runtime que Video_Tunner probablemente no necesita. Es una oportunidad de reducción de tamaño, pero no justifica un segundo run ahora que la viabilidad está demostrada. Se optimizará cuando exista un objetivo de tamaño o durante Release Hardening.

La descarga frozen avisó de fallback HTTP para Xet; la adquisición terminó correctamente. `hf_xet` no es requisito funcional del modelo local/offline.

## Qué valida este PASS

- PyInstaller `onedir` es base viable para el stack CPU actual;
- runtime ML portable viable;
- native DLLs cargan correctamente;
- Silero ONNX funciona dentro del frozen bundle;
- modelo puede adquirirse dentro del árbol portable;
- inferencia Whisper + VAD funciona offline después de adquisición;
- paths con espacios y aislamiento de PATH no rompen el flujo.

## Qué NO valida

- calidad STT de `large-v3-turbo`;
- rendimiento final con vídeos largos;
- CUDA/GPU;
- audio externo/sync/drift;
- protección semántica;
- UX final;
- tamaño del ZIP final con modelo;
- Release definitiva Windows 10/11 en equipo limpio real del usuario.

## Decisión

**Fase 1A queda técnicamente demostrada para continuar.**

PyInstaller `onedir` se mantiene como base provisional. No evaluar Nuitka sin una ventaja o problema concreto.

Siguiente fase: **1B — ingesta dual + master audio + sincronización A/V + drift**.
