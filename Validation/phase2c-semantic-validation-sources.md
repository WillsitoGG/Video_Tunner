# Phase 2C semantic validation sources

## AMI Meeting Corpus

- Corpus: AMI Meeting Corpus
- Role in Video_Tunner: labelled human-speech validation source for semantic candidates; not a product dependency.
- License: CC BY 4.0 for publicly released corpus/transcription data.
- Positive fixture currently used: meeting `ES2012d`, manual transcript, real retake/restart.
- Source recorded in `tests/fixtures/semantic_corpus_v1.json` through `source_reference`.
- The fixture stores only the minimal transcript excerpt needed for the test; no AMI audio/video is committed to this repository.
- A separate human autocorrection containing `I mean` has been identified for a future corpus expansion but is not yet part of the validated fixture set.

Purpose: preserve provenance and make it explicit that human-positive validation data is externally sourced and licensed, while keeping the repository lightweight.
