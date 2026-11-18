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
## Auditability baseline added, appended 2026-11-07

At Lawrence's request ("update every repo to research grade by using what we learned in covenant"), Claude added the
shared auditability checks (`research_grade.py` 1.1.0, run in CI): a retraction ledger, a claims index and a manifest
of every tracked file. Passing them means the claims are auditable, not that they are true.

- **Ledger.** `docs/RETRACTED.json` holds 20 withdrawn claims, generated from the two correction tables in
  `research/flinch/README.md`, each quoting the withdrawn sentence verbatim. Six table rows are listed as skipped,
  with reasons: no quoted sentence, a quote too short to pattern, or a claim that was true when written.
- **First catch.** On its first run the guard found `research/flinch/flinch/corpus.py` still saying, uncited, that
  `ingest()` "Never raises on one bad file", the 0.1 claim withdrawn as FL01-R04. The sentence is kept, and the
  retraction is now cited beside it in the docstring. Behaviour is unchanged.
- **Unrecorded drift found.** Since CL1 (`72159f0`, merged as `214fe07` on 2026-11-04), `receipts.py` and the new
  `test_cl1_concurrent.py` did not match any release manifest. `RELEASE_MANIFEST_0.2.2-post.json` records the code as
  it now stands, and names both changes. `RELEASE_MANIFEST_0.2.2.json` is kept unchanged.
- **Tests.** FLINCH 141/141 and CL1 4/4. The CI job runs both suites and the checks on Python 3.10 and 3.12.

## K11: a blank pre-registration and an unrecorded action, appended 2026-11-14

At the owner's request, after a review on 2026-11-14 confirmed two defects by running them (finding K11), Claude
corrected both. Same-author work, not independent validation.

- **`prereg.freeze` froze an empty protocol.** `freeze(dict.fromkeys(REQUIRED, None))` was accepted: the
  completeness test read `str(value)`, and `str(None)` is the four letters "None". The result was a frozen
  pre-registration with a valid hash and no decision in it. `freeze` now refuses a required value that is null, an
  empty or whitespace-only string, or a container holding only blanks; it also refuses a manifest hash that is not 64
  lowercase hex characters and a detector name that is not a string. The error names the fields. A complete
  pre-registration freezes to the same hash as before.
- **`gate.Broker.act` ran an allowed action before any record of it existed.** If the ledger write after the action
  failed, the side effect had happened unrecorded. `act` now writes an `approved` row first, with the same fields as
  every other row. If that write fails, the action is not run and `act` returns `refused`. The `done` or `failed` row
  follows as before. An allowed action is therefore two ledger rows where it was one: no field was renamed or removed,
  and a reader that counts rows per action must expect the extra row.
- **Tests.** `research/flinch/test_k11_prereg_gate.py`, 10 checks, run in CI. On the code before the change 9 were
  red; the tenth holds that a complete pre-registration still freezes to the same hash. All 10 are green after. In
  `test_flinch.py`, GA6 counted 11 ledger rows and now counts 13, because its fixture allows two actions. FLINCH stays
  141/141 and CL1 4/4.
- **Manifests.** `RELEASE_MANIFEST_0.2.2-post2.json` records the code as it now stands and CI checks against it.
  `RELEASE_MANIFEST_0.2.2-post.json` is kept unchanged; `gate.py`, `prereg.py` and `test_flinch.py` no longer match it.
  The version string stays 0.2.2. `detector.py` and `DETECTOR_ID` are unchanged.
- **Limits.** `prereg.run_kind` does not repeat the completeness test, so a pre-registration frozen by the earlier
  code, or hashed by hand, with a blank in a field `run_kind` does not read is still accepted there. If the ledger
  cannot be written at all, the refusal cannot be written to it either; `act` still returns it to the caller.

## Intent provenance on the admission receipt, appended 2026-11-18

At the owner's direction ("Add to flinch"), after the same mechanism landed in the covenant AI-memory store and
the spiking plasticity ledger, Claude added it to the one record here that is an authored judgment steering what
happens next: the `admitted` receipt. Same-author work, not independent validation.

- **What changed.** `receipts.append_receipt` refuses an `admitted` receipt whose body lacks `intent`, `beneficiary`
  or `divergence`, has a multi-line one, whose intent is a surface restatement of the admitted content, or whose
  `divergence` is not `none` without a `diverges_from` naming a task with a receipt in the same ledger. The check
  runs under the same lock as the status check (CL1), after the review rule, so an unreviewed task is still refused
  for review first. `verify()` replays it on the record as read, so a forged admission without the fields is a
  problem. `intent_check(path, task_id)` returns the four fields verbatim with one line on whether the intent is
  still satisfiable on the ledger as it stands. Delivery receipts (`requested` .. `reviewed`) and the action ledger
  are unchanged: machine outcomes with no author to ask.
- **Tests.** `research/flinch/test_rp_intent_provenance.py`, 13 checks, run in CI, each refusal asserted by its own
  reason. In a scratch run each guard was broken alone and the file restored byte-identical: with the screen
  neutered 7 of 13 went red (RP02–04, 06, 07, 09, 12); with only `verify()`'s replay removed, 2 (RP09, RP12); with
  only the write-time gate removed, 5 (RP02–04, 06, 07) -- so the write-time gate and the read-time replay are each
  observed on their own. FLINCH stays 141/141 (RC9's forged admission now draws a second problem beside "admitted
  before it was reviewed"; its check holds), CL1 4/4, K11 10/10.
- **Manifests.** `RELEASE_MANIFEST_0.2.2-post3.json` records the code as it now stands and CI checks against it;
  `RELEASE_MANIFEST_0.2.2-post2.json` is kept unchanged; `receipts.py` and `research/flinch/README.md` no longer
  match it. The version string stays 0.2.2. `detector.py` and `DETECTOR_ID` are unchanged.
- **Limits.** The screen sees emptiness and surface restatement, never truth. No admission existed before the rule
  (measured: zero admitted rows in any ledger here), so there was nothing to tombstone, and no backfill is possible
  on an append-only chain. The hypothesis the mechanism serves -- that legible, cross-linked divergence lowers
  unacknowledged contradictions between admissions -- is pre-registered in
  `research/flinch/PREREG_intent_provenance_2026-11-18.md` and NOT tested here.
