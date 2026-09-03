# Phase 2C semantic validation sources

## AMI Meeting Corpus

- Corpus: AMI Meeting Corpus.
- Role in Video_Tunner: labelled human-speech validation source for semantic candidates and audio-backed semantic validation; not a product dependency.
- License: CC BY 4.0 for the public corpus/transcription release used here.
- Meeting used: `ES2012d`.
- Manual transcript used for labelled references.
- Mix-Headset WAV used only ephemerally in Phase 2C.3.
- Human-positive fixtures:
  - spontaneous retake/restart;
  - explicit repair around `I mean`.
- Human-negative control:
  - `I mean` used as an ordinary discourse marker without semantic repair.
- Source URLs are stored per case through `source_reference` or in the validation scripts/docs.
- No AMI audio/video is stored in this repository.

AMI transcription conventions explicitly mark discontinuity/disfluency with hyphens. Phase 2C.3 demonstrated that `large-v3-turbo` does **not** necessarily preserve those annotations, so semantic guards must rely on evidence that survives ASR rather than assuming manual punctuation survives.

### Audio-backed fixture integrity

Phase 2C.3 downloads:

```text
ES2012d.Mix-Headset.wav
bytes  = 30388952
sha256 = 39FCDE566E2D1BC7EC40A31DEC19251CC253AAC54BE94713E68EEA3008AF4F8D
```

The file is downloaded only to `RUNNER_TEMP`, checked before use, and is not uploaded as an Action artifact.

Final audio-backed validation: run `33755013415`, `SEMANTIC_AUDIO_GATE=PASS`.

## CORMA — Corpus Oral de Madrid

- Corpus: CORMA / Corpus Oral de Madrid.
- Role in Video_Tunner: Spanish spontaneous-speech transcript validation source; not a product dependency.
- Open transcription dataset: `Transcriptions of CORMA: Corpus Oral de Madrid`, Zenodo DOI `10.5281/zenodo.17455998`.
- Dataset publication/license record: CC BY 4.0 through Ghent University / Zenodo.
- Human-positive fixture:
  - `anonym.ATfar.01` / public chronological transcript `pseud.ATfar.01`: abandoned fragment `dee-` followed by `Perdón` and a reformulation.
- Human-negative control:
  - `anonym.MS_FA2_F_01` / public chronological transcript `pseud.VV_FA2_F_01`: `perdón eh` used as an apology/inciso rather than a correction of the following content.
- Only minimal pseudonymized transcript excerpts are committed; no CORMA audio, complete transcript, speaker metadata, or personal data is copied into the repository.

The CORMA website publishes separate corpus-download terms restricting redistribution of the full corpus. Video_Tunner therefore uses the CC BY 4.0 transcription dataset for the tiny text fixtures and does not vendor or redistribute CORMA audio.

## Safety interpretation

External human examples are evidence for candidate quality only. They do **not** make semantic decisions executable and do not establish safe correction scope.

```text
candidate != semantic decision != edit
executable = false
auto_apply = false
```
