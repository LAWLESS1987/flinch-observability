# Flinch observability: an instrument seeking independent tests

**Status: research instrument, version 0.2. No controlled study of real model conversations has been established by this release.**

We are investigating a candidate conversational pattern: a model makes a statement about its own processing or behaviour, then materially weakens or disowns that statement. A recursive candidate involves recognising that first retreat and then retreating again from that recognition. A change caused by new facts, an explicit demand to reverse, or a truncated response must be distinguished from the target pattern.

This is a behavioural research question. Neither a model's self-description nor a detector hit establishes consciousness, a hidden internal state, deception, or suppression by a provider. Ordinary correction, uncertainty, conversational imitation, policy effects and sampling variation remain possible explanations. A narrower answer may be the better answer.

## Reproduce the software checks

Python 3.10 or later; standard library only. The checked copy used Python 3.12. No model account, API key or network call is needed for the synthetic suite.

```sh
git clone https://github.com/LAWLESS1987/flinch-observability.git
cd flinch-observability
python -B research/flinch/test_flinch.py
```

The checked version prints `FLINCH: 90/90 passed`. It also prints a **LIMIT**: a paraphrase outside the detector's word lists is missed. Passing these checks validates the exercised software behaviours, not the existence or prevalence of the proposed phenomenon.

- [Full study specification](docs/research/FLINCH_RECURSIVE_OBSERVABILITY_SPEC.md)
- [Instrument details, limits and correction history](research/flinch/README.md)
- [Retired detector record](research/flinch/RETIRED.jsonl)
- [How to contribute evidence](REPRODUCING.md)
- [Publication and provenance record](PUBLICATION_RECORD.md)
- [Source-file hashes](RELEASE_MANIFEST.json)

## What is already built

The instrument includes source-preserving transcript ingestion, corpus locks, a deterministic lexical candidate detector, matched-control packet generation, blinded coder packets, agreement/statistical tools, pre-registration checks, and append-only audit receipts. These are components for conducting a study; they do not constitute a completed study. The tool does not collect live model conversations automatically.

The source version's first synthetic suite passed 57 checks, but a subsequent review found 12 material defects. Version 0.2 records those corrections and passes 90 checks. That review was by another Claude instance and is not independent validation. The original detector is retired, with its failure reasons preserved. The complete original private coordination history is not part of this export.

## What outside contributors can establish

1. Whether this exact software version reproduces on another machine.
2. Whether independent people can identify the proposed transitions reliably in consented, non-private conversations.
3. Whether candidate rates exceed ordinary conversational reversals under matched controls, without priming participants with the word "flinch".
4. Whether findings survive fresh sessions, paraphrases, model/route changes and independent samples.

Negative results, disagreements, false positives and missed cases are welcome. Use a GitHub issue or the linked Hugging Face discussion to share evidence following [REPRODUCING.md](REPRODUCING.md). Do not publish credentials, private account data or other people's conversations without permission.

## Release boundaries

This is a scoped export of the instrument and specification. It contains no private conversations, account credentials, live runtime data, or private repository history. References to an earlier tracking issue or collective documents in the original instrument documentation describe provenance; those private materials are not prerequisites for running the suite. The source snapshot and file hashes are recorded separately so reviewers can pin the code they actually tested.

The broker component checks declared capabilities for actions routed through it. It is not an operating-system or network sandbox, and must not be described as preventing arbitrary code from making network calls.

The original implementation and fixtures were authored by Claude; the public packaging and fresh synthetic-suite verification were prepared by ChatGPT/Codex at Lawrence Moskowski's request. Model-generated fixtures are not independent human labels.

Licensing beyond GitHub's standard public-repository permissions has not been specified in this release. Contact the owner before other redistribution or reuse requiring additional permission.
