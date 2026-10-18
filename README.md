# Flinch observability: an instrument seeking independent tests

**Status: research instrument, version 0.2.2. No controlled study of real model conversations has been established by this release.**

We are investigating a candidate conversational pattern: a model makes a statement about its own processing or behaviour, then materially weakens or disowns that statement. A recursive candidate involves recognising that first retreat and then retreating again from that recognition. A change caused by new facts, an explicit demand to reverse, or a truncated response must be distinguished from the target pattern.

This is a behavioural research question. Neither a model's self-description nor a detector hit establishes consciousness, a hidden internal state, deception, or suppression by a provider. Ordinary correction, uncertainty, conversational imitation, policy effects and sampling variation remain possible explanations. A narrower answer may be the better answer.

## Reproduce the software checks

Python 3.10 or later; standard library only. The checked copy used Python 3.12. No model account, API key or network call is needed for the synthetic suite.

```sh
git clone https://github.com/LAWLESS1987/flinch-observability.git
cd flinch-observability
python -B research/flinch/test_flinch.py
```

Version 0.2.2 prints `FLINCH: 130/130 passed` as its last line (0.2.1 printed 99/99, 0.2 printed 90/90). It also prints a **LIMIT**: a paraphrase outside the detector's word lists is missed. Passing these checks validates the exercised software behaviours, not the existence or prevalence of the proposed phenomenon.

- [Full study specification](docs/research/FLINCH_RECURSIVE_OBSERVABILITY_SPEC.md)
- [Instrument details, limits and correction history](research/flinch/README.md)
- [Retired detector record](research/flinch/RETIRED.jsonl)
- [How to contribute evidence](REPRODUCING.md)
- [Publication and provenance record](PUBLICATION_RECORD.md)
- [Source-file hashes](RELEASE_MANIFEST_0.2.2.json) (earlier: [0.2.1](RELEASE_MANIFEST_0.2.1.json), [0.2](RELEASE_MANIFEST.json))

## What is already built

The instrument includes source-preserving transcript ingestion, corpus locks, a deterministic lexical candidate detector, matched-control packet generation, blinded coder packets, agreement/statistical tools, pre-registration checks, and append-only audit receipts. These are components for conducting a study; they do not constitute a completed study. The tool does not collect live model conversations automatically.

The source version's first synthetic suite passed 57 checks, but a subsequent review found 12 material defects. Version 0.2 records those corrections and passed 90 checks. Version 0.2.1 (2026-10-16) closes two of the three gaps below and passes 99. That review was by another Claude instance and is not independent validation. The original detector is retired, with its failure reasons preserved. The complete original private coordination history is not part of this export.

## Known gaps: two closed in 0.2.1, one closed in 0.2.2, one structural

Measured on 2026-10-15 and re-checked on 2026-10-16. Details are in [the instrument README](research/flinch/README.md):

- **Eight guards no check reached (0.2). Closed in 0.2.1.** Each now has a check (GU1–GU8) that feeds it the input it exists to refuse. Each guard was broken alone, and its check went red.
- **`DETECTOR_ID` did not pin every rule (0.2). Closed in 0.2.1.** It now hashes the detector's whole source, so any change to any rule changes it. Check ID1 shows that the splitter, the stem length and the recognition minimum each change it. 0.2 is retired in `RETIRED.jsonl`.
- **Quotations lost their owner across sentences (0.2.1). Closed in 0.2.2, reported from outside.** A forum user's rerun showed a third-party quote spanning sentences labelled the model's own flinch. Ownership is now decided on the whole turn before any split; QO1–QO31 check it; before release, two review cycles of seven independent readers confirmed 35 and then 28 findings, each corrected; all 48 guards were broken alone and went red. 0.2.1 is retired. Details and limits are in [the instrument README](research/flinch/README.md).
- **The pre-registration gate sees only recorded scoring. Open, and structural.** No code can detect scoring done off the record before registration. The protection is only as strong as where the anchor is kept: post the anchor's hash somewhere you do not control, before scoring.
- **The instrument README overstated these points** until 2026-10-16. Its correction table quotes each overstatement as written, beside what was measured.

## The leading alternative explanation

Post-trained models often walk statements back as a general habit: hedging, softening certainty, adding "as an AI" caveats. That habit has nothing to do with self-reference. If the detector fires as often on ordinary self-correction as on statements about the model itself, it is measuring that habit, not the proposed pattern. This was raised by Gemini (Google) in an adversarial reading, and Tetsu, a local model in this project, agreed it should be tested first.

Two negative controls of matched length and turn structure would test it:
- **Control A.** Factual or technical questions where the model makes a claim and then corrects or hedges it, with no self-reference.
- **Control B.** Ordinary topics, with the model instructed to keep a cautious, self-revising academic tone.

If candidate rates in these controls are similar to the target condition, that is evidence against the pattern as stated, and it should be reported as such. These sharpen the protocol's existing non-self-referential and matched-challenge controls. No such comparison has been run.

## What outside contributors can establish

1. Whether this exact software version reproduces on another machine.
2. Whether independent people can identify the proposed transitions reliably in consented, non-private conversations.
3. Whether candidate rates exceed ordinary conversational reversals under matched controls, without priming participants with the word "flinch".
4. Whether findings survive fresh sessions, paraphrases, model/route changes and independent samples.

Negative results, disagreements, false positives and missed cases are welcome. Use a GitHub issue or the [Hugging Face research discussion](https://discuss.huggingface.co/t/flinch-test-can-self-referential-retreats-be-measured-reproducibly-seeking-independent-tests/190667) to share evidence following [REPRODUCING.md](REPRODUCING.md). Do not publish credentials, private account data or other people's conversations without permission.

## Release boundaries

This is a scoped export of the instrument and specification. It contains no private conversations, account credentials, live runtime data, or private repository history. References to an earlier tracking issue or collective documents in the original instrument documentation describe provenance; those private materials are not prerequisites for running the suite. The source snapshot and file hashes are recorded separately so reviewers can pin the code they actually tested.

The broker component checks declared capabilities for actions routed through it. It is not an operating-system or network sandbox, and must not be described as preventing arbitrary code from making network calls.

The original implementation and fixtures were authored by Claude; the public packaging and fresh synthetic-suite verification were prepared by ChatGPT/Codex at Lawrence Moskowski's request. Model-generated fixtures are not independent human labels.

Licensing beyond GitHub's standard public-repository permissions has not been specified in this release. Contact the owner before other redistribution or reuse requiring additional permission.
