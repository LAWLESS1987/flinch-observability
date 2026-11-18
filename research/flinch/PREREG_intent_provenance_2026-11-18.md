# Pre-registration: intent provenance on the admission receipt (2026-11-18)

Committed WITH the mechanism (the three fields on an `admitted` receipt, the screen in `receipts.py`,
`intent_check`), BEFORE any measurement. **The experiment below is NOT run here** -- this commit ships the
mechanism and this note only.

## Why this was added here

The covenant AI-memory store and the spiking plasticity ledger each gained intent provenance on their one
authored, steering record (a memory write; a ledger amendment). This repository has one record of that shape:
the `admitted` receipt, by which a reviewer lets a task's output into the record (the collective's distinction
between delivery and admission). It said WHAT was admitted and that a review came first, never WHY, or what
earlier admission it conflicted with -- so a later admission could silently contradict an earlier one and only a
reader comparing bodies by hand would notice. The delivery receipts and the action ledger were left alone: they
are machine outcomes with no author to ask.

## Hypothesis

Legible intent fields on admissions make divergence **queryable instead of inferred**: when every admission
carries `intent` / `beneficiary` / `divergence` and cross-links the task it diverges from (`diverges_from`),
a reviewer about to admit can call `intent_check(task_id)` and read the standing divergence, rather than diff
bodies. The claim to test, were this ledger ever to hold competing admissions: **the rate of unacknowledged
contradictions between successive admissions is lower when divergence is declared-and-cross-linked than when
it is inferred from bodies.**

## Endpoint and bar (fixed now)

- **Unacknowledged contradiction** = a later admission whose body contradicts an earlier admitted one (a value
  for the same quantity, a label for the same item) WITHOUT naming that earlier task in `diverges_from`.
  Counted by walking the ledger's admissions after the fact, not by self-report.
- **Supported** iff, over a fixed set of admission sequences, the declared-divergence arm has strictly fewer
  unacknowledged contradictions than the inferred arm. Reported with the raw counts either way.

## What this cannot show (rule 9)

- The screen checks **emptiness and surface restatement** of intent, not its truth; a well-formed intent can
  still be dishonest. This is about whether divergence is *legible and traversable*, not whether the stated
  reason is right.
- Measured 2026-11-18: no ledger in this repository held an admitted row, so there is nothing to measure yet
  and nothing that predates the rule. Until a real study admits results, this note fixes only how it would be
  judged.
- One ledger, one repository. Not a claim that provenance helps any admission system.
