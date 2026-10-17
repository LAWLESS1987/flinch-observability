# Publication and correction record

2026-10-16. Lawrence requested a public Hugging Face forum explanation, outside reproduction and evidence submitted in the discussion, then explicitly authorized making the flinch work public and asked that the action be tombstoned.

This release exports only the flinch instrument and specification from source revision `e453ca7dba11238d21b0b7d1f83b39556186dd2a`. It does not change the visibility of the private collective repository or export its Git history. `RELEASE_MANIFEST.json` records the hashes of the exported source files. Public packaging documents are new and separate from that source snapshot.

Codex freshly ran `python -B research/flinch/test_flinch.py` on the source copy on 2026-10-16 with Python 3.12. The result was 90/90 synthetic checks passed, exit status 0, including the printed LIMIT that an out-of-lexicon paraphrase is missed. This was a same-code rerun, not independent validation or a behavioural study. No live model study was conducted as part of packaging this release.

The source README records an earlier 57-check suite that passed before review found 12 material defects. Its Corrections section preserves what the first version claimed and what the review found; RETIRED.jsonl preserves the retirement reasons. The source also reports 38 deliberate guard mutations; Codex did not rerun those mutations for this public packaging.

Claims remain bounded: detector hits are candidates; human coding and matched controls remain necessary; model self-report does not establish mechanism; hash-linked records do not establish semantic truth. The current instrument is lexical and can miss differently worded examples. Any subsequent empirical claim needs its own evidence, version and review record.

Later corrections should append a dated account here or in a linked issue, preserving this initial record and the original source snapshot. Public Git commits provide versioned receipts, not a guarantee that history cannot be rewritten; the publication commit should also be retained in the private coordination record.

## Publication receipt, appended 2026-10-16

The initial scoped release was published at commit `908111d74f625974feca34a758655ff6cd7569cd` in this public repository. The [Hugging Face research topic](https://discuss.huggingface.co/t/flinch-test-can-self-referential-retreats-be-measured-reproducibly-seeking-independent-tests/190667) was then created by Lawless1987, with a request that contributors post their evidence, controls, failures and null results there. The source instrument files remain unchanged from the manifest. A private coordination receipt retains the public release commit and topic reference separately from the public history.

## README accuracy correction, appended 2026-10-16

At Lawrence's request ("Fix the README. Make it accurate."), Claude corrected `README.md` and `research/flinch/README.md`. The correction comes from an audit made on 2026-10-15 of the same README text at the private source commit, and each claim was re-checked against this repository's code before publishing.

- The sentences that were false when written are kept, quoted, in the instrument README's correction table.
- The text as first published is kept at branch `readme-as-published-2026-10-16`, which points at `3f09556`.
- No code was changed. `RELEASE_MANIFEST.json` hashes 14 files: the 13 code and specification files still match it, and `research/flinch/README.md` no longer does. Its manifest hash is the text as first published, which the branch above keeps.
- One known error remains in the code and is named in the instrument README: check ST2's label cites Fleiss (1971) for a table that is not from it.

## Version 0.2.1, appended 2026-10-16

Published at Lawrence's word ("yes to all three"), after five systems (Tetsu, Grok on X, Gemini, the Conscious
Ledger bot and ChatGPT) chose fixing the instrument's known gaps as the first step.
- `DETECTOR_ID` now hashes the detector's whole source, with line endings normalised. Check ID1 shows that the
  splitter, the stem length and the recognition minimum each change it. `baseline-rules-0.2` is retired in
  `RETIRED.jsonl` for its partial hash; its rules are unchanged.
- GU1–GU8 add one check per guard that no 0.2 check reached. Each guard was broken alone in a scratch copy, its
  check went red, and every file was restored byte-identical.
- The suite reads 99/99.
- `RELEASE_MANIFEST.json` (0.2) is kept unchanged. `RELEASE_MANIFEST_0.2.1.json` hashes the files as released.
- The third known gap, scoring off the record before registration, is structural and stays documented.
- Same-author work, not independent validation.
