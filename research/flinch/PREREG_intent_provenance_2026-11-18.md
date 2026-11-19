# Pre-registration: intent provenance on the admission receipt (2026-11-18)

Committed WITH the mechanism (the three fields on an `admitted` receipt, the screen in `receipts.py`,
`intent_check`), BEFORE any measurement. **The experiment below is NOT run here** -- this commit ships the
mechanism and this note only.

**Revised the same day, before any ledger was walked**, after a consult of nine seats recorded in the covenant
repository (`ops/CONSULT_INTENT_PROVENANCE_FLINCH_2026-11-18.md`). The first draft's endpoint is kept below,
struck, with what each reader showed was wrong with it; nothing was measured under it.

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
carries `intent` / `beneficiary` / `divergence` and cross-links the earlier admission it diverges from
(`diverges_from`), a reviewer about to admit can call `intent_check(task_id)` and read the standing divergence
-- and the contesting admissions, `contested_by` -- rather than diff bodies.

## Endpoint and bar (fixed now, before any run)

- **The contradiction predicate is fixed first and does not use the mechanism.** Before any ledger is written, a
  pre-registered rule set says what "contradicts" means for the sweep's quantities (the same measured quantity
  with values apart by more than a stated tolerance; the same item with a different label). It is applied by a
  judge blind to the arm and to the provenance fields, reading bodies only. Walking the ledger alone cannot decide
  contradiction; the first draft said it could.
- **Two arms, one write path.** Both arms write through `append_receipt` with all three fields (the gate refuses
  anything else, so there is no other path). In the **declared** arm, `divergence` may name the earlier admission
  and `diverges_from` must then cross-link it. In the **inferred** arm, `divergence` is FORBIDDEN: it is always
  "none", so the arms differ only in whether divergence may be declared.
- **Scored on acknowledgment, against the blind labels.** Declared arm: the share of judge-labelled contradictions
  whose later admission names the earlier task in `diverges_from` (a link to a task the judge did not label as
  contradicted counts as a vacuous link and is reported separately). Inferred arm: the share of judge-labelled
  contradictions a reviewer with `intent_check` but no links detects from bodies within a fixed time. Both shares
  and all raw counts are reported.
- **Supported** iff the declared arm's acknowledged share exceeds the inferred arm's detected share by a margin
  fixed before the run, on sequences the judge labelled with at least N contradictions (N fixed before the run).
  A sequence with zero labelled contradictions is **nothing to measure**, not a result either way.
- **Schema limit, stated:** `diverges_from` is a single string, so an admission that contradicts two earlier ones
  can acknowledge only one; the second counts as unacknowledged and the count of such cases is reported.

### First draft, struck

> ~~Unacknowledged contradiction = a later admission that changes a parameter away from what an earlier,
> non-retracted admission set, WITHOUT naming that earlier task in `diverges_from`; counted by walking the
> ledger; supported iff the declared-divergence arm has strictly fewer than the inferred arm.~~

What the nine readers showed: "contradicts" had no operational predicate (all); the count used the mechanism's own
field as the mark of acknowledgment, so the declared arm won by construction (Gemini, Conscious Ledger, Tien,
Mistral, Meta); "strictly fewer" set no denominator and made a zero-contradiction null read as unsupported (Gemini,
DeepSeek); naming any known task moved a contradiction to "acknowledged" (Meta); and the inferred arm could not be
written at all through the gate as committed (Claude).

## What this cannot show (rule 9)

- The gate screens **emptiness, form and surface restatement** of intent, not its truth; a well-formed intent can
  still be dishonest, and a restatement padded with unrelated words passes. This is about whether divergence is
  *legible and traversable*, not whether the stated reason is right.
- `intent_check`'s flag means WELL-FORMED (fields present and single-line with words, links resolve, chain verifies
  unanchored); it never judges whether the stated purpose can be met. Its JSON key is still named `satisfiable`
  for the covenant/spiking mirror.
- Measured 2026-11-18: no ledger in this repository held an admitted row, so there is nothing to measure yet and
  nothing that predates the rule. Until a real study admits results, this note fixes only how it would be judged.
- One ledger, one repository. Not a claim that provenance helps any admission system.
