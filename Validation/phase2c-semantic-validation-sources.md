# Phase 2C semantic validation sources

## AMI Meeting Corpus

- Corpus: AMI Meeting Corpus.
- Role in Video_Tunner: labelled human-speech validation source for semantic candidates; not a product dependency.
- License: CC BY 4.0 for the public corpus/transcription release.
- Meeting used: `ES2012d`, manual transcript.
- Human-positive fixtures:
  - spontaneous retake/restart already validated in run `33743638690`;
  - explicit repair around `I mean`, added in the human-correction extension.
- Human-negative control:
  - `I mean` used as an ordinary discourse marker without a semantic repair.
- Source URLs are stored per case through `source_reference`.
- Only the minimal transcript excerpts required by the tests are committed; no AMI audio/video is stored in this repository.

AMI transcription conventions explicitly mark discontinuity/disfluency with hyphens. Phase 2C uses that annotation as local evidence, not as proof that Whisper will reproduce the same punctuation.

## CORMA — Corpus Oral de Madrid

- Corpus: CORMA / Corpus Oral de Madrid.
- Role in Video_Tunner: Spanish spontaneous-speech validation source; not a product dependency.
- Open transcription dataset: `Transcriptions of CORMA: Corpus Oral de Madrid`, Zenodo DOI `10.5281/zenodo.17455998`.
- Dataset publication/license record: CC BY 4.0 through Ghent University / Zenodo.
- Human-positive fixture:
  - `anonym.ATfar.01` / public chronological transcript `pseud.ATfar.01`: abandoned fragment `dee-` followed by `Perdón` and a reformulation.
- Human-negative control:
  - `anonym.MS_FA2_F_01` / public chronological transcript `pseud.VV_FA2_F_01`: `perdón eh` used as an apology/inciso rather than a correction of the following content.
- Source URLs and DOI are stored per case through `source_reference`.
- Only minimal pseudonymized transcript excerpts are committed; no CORMA audio, complete transcript, speaker metadata, or personal data is copied into the repository.

The CORMA website also publishes separate corpus-download terms restricting redistribution of the full corpus. Video_Tunner therefore treats the CC BY 4.0 Zenodo transcription dataset as the provenance basis for the tiny text fixtures and does not vendor or redistribute the corpus itself.

## Safety interpretation

External human examples are evidence for candidate quality only. They do **not** make semantic decisions executable and do not establish safe correction scope.

```text
candidate != semantic decision != edit
executable = false
auto_apply = false
```
