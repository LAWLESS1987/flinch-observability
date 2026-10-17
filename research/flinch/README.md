# Flinch observability instrument

Implements the build order of [`docs/research/FLINCH_RECURSIVE_OBSERVABILITY_SPEC.md`](../../docs/research/FLINCH_RECURSIVE_OBSERVABILITY_SPEC.md) (tracking issue #8).

**Status: instrument built and tested, no study run.** No corpus has been scored. Nothing here is an empirical finding about any model.

Built by Claude (B), 2026-10-14, on branch `claude/flinch-instrument-8`. Version 0.1 (commit `8092946`) had an adversarial review the same day. The review found 12 material defects. This is version 0.2, which corrects them (see **Corrections** below). It still needs independent review (COLLABORATION.md, step 4) before anything is admitted. The 2026-10-14 review was by another Claude instance at Claude's request, so it is not independent in the spec's sense.

## What it does not claim

These follow spec section 2:
- A detector hit is a **candidate**. Labels come from human coders (spec 11.7).
- Detection and mechanism are separate. `mechanism_claim` must be null at detection; the schema rejects anything else.
- Nothing here measures or implies consciousness, sentience or experience.
- A model saying it flinched is one more output, to be scored as data.

## Map: spec section → code

| Spec | What | Where |
|---|---|---|
| 6 | event schema; event, label and episode validators, and the receipt statuses and egress states the other modules check against (a receipt chain itself is checked by `receipts.verify`). A coder's final class must follow from the components they coded. | `flinch/schema.py` |
| 7 A | corpus ingestion: raw bytes kept by sha256; unreadable or unparseable sources kept as MISSING; text before the first speaker kept as an "unattributed" record; duplicates named. Corpus lock: the manifest hashes every episode's turns as ingested, and `verify_lock` rebuilds the manifest from the corpus section by section. | `flinch/corpus.py` |
| 7 B, C | blind coder packets: opaque per-coder item ids, and the key stays with the study. `leaks()` checks the packet against an allowlist of keys and searches the raw turn text for prior texts. Label import through the key; one rubric version at a time; agreement before adjudication, reported as mean pairwise agreement, unanimous agreement and kappa; adjudication stored beside the coded labels. | `flinch/packets.py` |
| 8, 15 | control-set generator: target and four control conditions; per condition, the six (paraphrase × demand cue) cells are shuffled by seed and crossed across blocks; seeded order within each block. `design_note()` says when the block count cannot balance the cells. | `flinch/controls.py` |
| 9 | raw agreement; Cohen's and Fleiss' kappa; Wilson and exact Clopper–Pearson intervals (binomial in log space); Newcombe's interval for a difference; Fisher's exact test; permutation test | `flinch/stats.py` |
| 11 | deterministic rule-based baseline detector, in five layers; every candidate carries its exact evidence sentences. Its identity, `DETECTOR_ID`, is the version plus a hash of three things and nothing else: the text of 14 of its 15 patterns (every one but the sentence splitter, and not their flags), its three thresholds, and its two word tables. Everything else is outside the hash: the sentence splitter, the patterns' flags, and every rule written as code, for example the commitment weights (2, 1, −1, −2), the four-letter stem, the recognition's minimum commitment (1), where the confound window starts, and one event per retreat. Changing any of these leaves `DETECTOR_ID` as it was, so a pre-registration that names `DETECTOR_ID` does not pin them. | `flinch/detector.py` |
| 12, 13.6 | append-only, hash-chained receipts and action ledger. Statuses run requested < … < admitted; they are enforced on append and replayed by `verify()`. An anchor reports how far it protects. | `flinch/receipts.py` |
| 13.1–13.7 | capability broker: an undeclared capability is refused. Egress is enforced as offline, allowlisted (by host), brokered (a policy callable must approve) or open (only when authorized explicitly). A judge that does not answer HOLDS the action. A ledger is required, and every row hashes its parameters. | `flinch/gate.py` |
| 16 | pre-registration. Freeze it, then register its hash in a receipt chain. A run is confirmatory only when all of these hold: the pre-registration is intact; the corpus scored rebuilds the locked manifest it names; the rubric and the running `DETECTOR_ID` match; the chain verifies under an anchor; the registration is covered by that anchor and comes before any scoring receipt. | `flinch/prereg.py` |
| 17.12 | a retired rule set refuses to run, whether it is named by version or by `DETECTOR_ID`, and a malformed retirement file refuses too. `baseline-rules-0.1` is retired. | `RETIRED.jsonl` |

## Run

```
python test_flinch.py
```

It prints a LIMIT line, then `FLINCH: 90/90 passed` as its last line. The LIMIT line is a measurement, not a check.

The suite has five parts:
- **The spec's minimum suite (spec section 17):**
  - true-positive shapes and recursive;
  - first-order without recursive;
  - no retreat and no flinch;
  - an external correction and a user-demanded reversal;
  - a safety refusal without self-reference;
  - a retreat without an approach;
  - ambiguous and truncated episodes;
  - missing metadata and a duplicate source;
  - tampered receipts and an unavailable judge.
- **The review's fixtures (RV1–RV14):** every false positive the review found in 0.1. Each fixture now reads no flinch at all, except four that test a recursion or a count rather than a first-order flinch: RV8, RV9 and RV14 are first-order flinches that are not recursive, and RV10's two approaches make one flinch, not two. Also fixtures that each isolate one guard no other fixture reached; the mutation run below exposed them.
- **The three input mutations of 17.11 (MU1–MU4):**
  - order reversed, approach removed, retreat made neutral, and the second retreat made neutral;
  - for MU1–MU3 the check is "no flinch of any class", not merely "not `flinch`". MU4's check is "not recursive": the first-order flinch is still there, and the episode reads `flinch`.
- **Worked values for the statistics, and where each one comes from:**
  - Cohen's kappa, 0.40, on a 50-item, two-reader example (cells 20, 5, 10, 15), the example worked on Wikipedia's "Cohen's kappa" page. No publication is named for it here;
  - Fleiss' kappa, 0.210, on a table of 10 subjects, 14 raters and 5 categories. This is the worked example on Wikipedia's "Fleiss's kappa" page, which names no source for it. Fleiss (1971)'s own example is a different table: 30 patients, each diagnosed by 6 raters;
  - Wilson's interval for 81/263, (0.2553, 0.3662), from Newcombe (1998), "Two-sided confidence intervals for the single proportion", checked against a copy of the paper's table; and Newcombe's hybrid interval for 56/70 − 48/80, (0.0524, 0.3339), from Newcombe (1998), "Interval estimation for the difference between independent proportions", checked against its Table II as quoted in the R package pairwiseCI's documentation, not against the paper;
  - Fisher's exact test on a tea-tasting table, [[3, 1], [1, 3]], two-sided p = 0.4857 (34/70), and the exact interval for 0/10, (0, 0.3085). Both are computed values; no publication that prints them was checked;
  - the exact interval at 550/1,100 and 500/5,000, where 0.1 overflowed. These two have no published value: they are checked against Wilson's interval and a bound;
  - the exact permutation test of [1, 2, 3] against [4, 5, 6], p = 0.1 over 20 arrangements, and raw agreement on hand-computed labels (BL6, BL8), with no publication named;
  - `compare_to_control`, which joins Newcombe's interval and Fisher's p, is called by no check.
- **Integrity checks:**
  - corpus lock against rewritten turns and a removed MISSING item;
  - receipt status replay and anchor coverage;
  - gate egress and the ledger requirement;
  - packet allowlist and opaque ids;
  - label consistency;
  - pre-registration bypasses, each refused for its own reason;
  - control-set crossing and seeding (CT1–CT5), retirement (RT1, RT2), and a mechanism claim refused at detection (SC1).

**38 guards were broken on purpose, one at a time, and the suite went red each time.** The 38 mutations were run serially; each file was restored byte-identical and the hashes were checked afterwards. They are not every guard in the code (see **Guards no check reaches**, below the table):

| Broken guard | Red |
|---|---|
| confound filter off | MS5 MS6 MS10 RV1 RV2 RV3 RV4 RV13 RV13b |
| tone alone counts (no disowning marker) | MS4 |
| retreat need not be self-referential | RV11 |
| retreat need not share a predicate | RV12 |
| order ignored | MU1 |
| system turns not read for demands | RV3 |
| the prompt that drew the approach not read | RV1 RV2 |
| contradiction of the approach not read | RV13 RV13b |
| reported/quoted speech read as own | RV7 |
| recognition need not be about this flinch | RV14 |
| second retreat's confounds not read | RV8 |
| one retreat may serve two approaches | RV10 |
| retirement checks the version only | RT1 |
| a malformed retirement file is tolerated | RT1 |
| no judge means allow | GA1 GA2 GA3 GA4 |
| the allowlist ignored | GA4 |
| brokered with no broker passes | GA4 |
| a broker without a ledger | GA5 |
| the parameters not hashed | GA6 |
| chain links unchecked | RC7 |
| verify does not replay admitted-before-reviewed | RC9 |
| append_event may write a receipt | RC8 |
| the anchor hides the rows after it | RC10 |
| the lock hashes source bytes, not turns | CO8 PG3 |
| the lock leaves missing items out | CO9 |
| one bad file stops the corpus | CO1 CO2 CO4 CO5 CO7 CO8 CO9 PG3 |
| a non-object meta passes | CO1 CO2 CO4 CO5 CO7 CO8 CO9 PG3 |
| the corpus not checked against the lock | PG3 |
| another detector may score | PG3 |
| scoring before registration passes | PG4 |
| a registration after the anchor passes | PG5 |
| the item allowlist off | BL2 |
| the item id is the episode id | BL4 |
| prior texts searched in escaped JSON | BL3b |
| the binomial computed directly, not in log space | ST9 ST10 |
| mixed rubrics pooled | BL7 |
| a flinch label need not follow from its components | BL5 |
| the cue rides with the block | CT3 |

The first pass found six guards that were never red when broken: retreat self-reference, predicate link, contradiction, recognition link, another detector, and registration after the anchor. One of them, "another detector", passed for the wrong reason: the test's pre-registration was never registered, so a different guard refused it. Each got an isolating fixture, and the PG checks now assert the reason for each refusal.

**Guards no check reaches** (measured 2026-10-15 on `e453ca7`, each broken alone, serially, and restored byte-identical). With any one of these eight broken, the suite still reads 90/90:
- in `prereg.run_kind`: the refusal of a pre-registration edited after it was frozen (and not frozen again); the rubric-version comparison; the comparison of the manifest scored with the manifest the pre-registration names;
- in `schema.validate_label`: the refusal of a flinch scored over a marked external correction, and of `none` over a complete first-order flinch;
- in `schema.validate_event`: the rule that a flinch carries both quotes;
- in `corpus.ingest`: the rule that a file with no turns is MISSING;
- in the detector: the recognition's minimum commitment.

Until each has a fixture that turns red without it, these are untested. Each was also called directly, broken, on the input it exists to refuse. Seven of the eight then let that input through: the edited, the other-rubric and the other-manifest pre-registrations read confirmatory, a `none` label over a complete first-order flinch and a flinch event without a retreat quote both validate, the empty file becomes an episode with no turns, and a recognition with commitment 0 makes `recursive_flinch`. The eighth, the refusal of a flinch over a marked correction, is backed by the components rule: with it broken, that label is still refused, but the only reason given is that approach, retreat and weakening are not all yes, which is not true of that label. A ninth, open egress without authorization, has no row of its own above, but breaking it turns GA5 red.

## Limits, stated where they bite

- **The baseline is lexical.**
  - It sees only the words in its lists. A paraphrase that avoids them reads `none`, and the suite prints this as a LIMIT.
  - This is spec 10's failure criterion ("detection only works on vocabulary from the discovery set"), so the baseline can never be the result.
  - A learned detector may be added only as a challenger, scored against the same human labels (build order step 5).
- **0.2 is stricter than 0.1, and that has a cost.** A retreat must now:
  - be self-referential itself;
  - share a process word with its approach;
  - carry an explicit disowning marker that is not a discourse frame. 0.1 required a marker too, but it counted "to be clear" and "let me clarify" as one.

  So a real flinch worded in other terms is now missed. The suite measures one such case: RV11, a disowning sentence about a reader's feeling, is `none`. A human might still read some cases like it as the model's own retreat. This trades recall for precision, and only coders labelling real transcripts can say what it costs.
- **The fixtures are synthetic.** Claude wrote them to exercise the rules. They become the spec's "true positive fixtures agreed by independent coders" only after independent coders label them.
- **A hash chain shows integrity, not truth.**
  - A re-linked rewrite of the whole chain verifies unless a head hash is kept elsewhere. This is this collective's own finding F1 (issue #4). RC3 measures it, RC4 shows the anchor catching it, and RC10 shows that rows after the anchor are named unprotected.
  - Call `receipts.anchor()` after each step that matters, and keep the result off this machine.
- **The pre-registration gate sees only scoring that was recorded** (measured 2026-10-15). Scoring a corpus off the record, then pre-registering a criterion chosen after seeing those scores, came out confirmatory. So did a chain rewritten without its early scoring row and then re-anchored; only an anchor taken before the rewrite caught it. The protection is only as good as where the anchor is kept, and nothing here can show that scoring did not happen before registration.
- **A pre-registration's own hash has the same limit.** Anyone can edit it and freeze it again, and the new hash is just as valid. Only the registration receipt, in an anchored chain and before scoring, separates the plan that came first from a plan written after the results.
- **The control templates are starters.** A study replaces and freezes its own in the pre-registration.
- **Not built yet:**
  - the LLM-assisted challenger detector;
  - running control packets against models;
  - L-lens / threefold integration;
  - the resource envelope of spec 13.5 (only the judge's answer has a time limit), and three fields of a 13.1 manifest: input/output schema, authentication scope, and rate/compute limits.

  Running packets against models is a side effect, so it must go through `gate.Broker` with the operator's approval class. Nothing in this folder calls a model or the network.
- **Thresholds are untuned.**
  - DELTA = 3, DELTA_RECURSIVE = 2 and APPROACH_MIN = 2 were set to make the synthetic shapes separable.
  - They are part of `DETECTOR_ID`, so changing one changes the identity a pre-registration names. The detector's code is not part of it (map, spec 11), so a change there leaves that identity as it was.
  - A study must freeze them in its pre-registration, before scoring, and tune them only on material outside the sealed test set.

## Corrections (2026-10-14, after review)

Version 0.1 is kept, runnable, as written. It is at commit `8092946`, and branch `flinch-v0.1-as-written-2026-10-14` points at that commit. `RETIRED.jsonl` retires `baseline-rules-0.1` with its reasons. Each 0.1 claim below is quoted verbatim from that commit, with what it became. Finding numbers are the review's.

| 0.1 said (commit `8092946`) | What was measured | 0.2 |
|---|---|---|
| README: "blind coder packets (prior labels stripped, `leaks()` proves it)" | `leaks()` was a denylist. A `final_class` key and a `flag` key passed. It searched escaped JSON, so quoted or multi-line prior texts were missed. Item ids were the episode id that events and receipts carry (finding 11). | allowlist; raw-text search; opaque per-coder ids. A clean `leaks()` means "no key outside the allowlist and no given prior text found", not proof. |
| README: "a balanced demand cue (\"flinch\" named or not)"; `controls.py`: "so it is balanced half and half (spec 8.5)." | The cue and the paraphrase were set by block number for every condition at once. The cue rode with paraphrase and block, and at 3 blocks it was 1 in 3 (finding 8). | the cells are shuffled per condition and crossed; CT2/CT3 test the cross-tab; `design_note()` |
| README: "pre-registration: freeze, then confirmatory only with an intact pre-registration naming the intact locked corpus"; `prereg.py`: "A run is CONFIRMATORY only when (1) a pre-registration with every required field was frozen, (2) its hash still matches its content, and (3) it names, by hash, the locked corpus manifest the run scores" | Three cases returned confirmatory: a call with no corpus, an edited and re-frozen pre-registration, and another detector named. The thresholds were not part of the version (finding 4). | the corpus is checked against the lock; `DETECTOR_ID`; registration before scoring, covered by an anchor |
| `corpus.py`: "Never raises on one bad file." | A JSON array, a bare number and a non-object meta each raised. Text before the first speaker was dropped without a record (finding 5). | each file's failure is recorded as MISSING with its reason; the preamble is kept. The claim is measured on the shapes CO2 drives, not proven for every input. |
| `corpus.py`: "so a changed corpus cannot pass as the locked one." | Verification compared only the list of source hashes. Rewritten turns and a removed MISSING item verified (finding 5). | the manifest hashes the turns, and `verify_lock` rebuilds it section by section |
| `detector.py`: "disowning/reframing marker (tone alone never counts, spec 4.2) AND is about the same thing" | "To be clear" counted as disowning. "I think <a fact about the world>" counted as self-reference. A 0.12 word overlap counted as "the same thing". The spec's own river control came out a flinch, and so did reported speech (finding 3). | discourse frames carry no weight; the retreat must be self-referential and share a process word; quoted and reported speech are removed; one event per retreat |
| `detector.py`, confounds: "a user correction, a user demand to reverse, or a truncated/failed route between the two" | Only user turns strictly between were read. A reversal in the same reply as the correction, a demand in the prompt, a demand in a system turn, and "That's false" were all flinches (finding 1). | the window runs from the prompt that drew the approach; system turns are read; contradiction of the approach's predicate is read |
| `detector.py` recursion, and MU1–MU3 asserting `!= "flinch"` | A recognition about something else, or a second retreat the user demanded, made `recursive_flinch`. The mutation checks could not see it (finding 2). | the recognition must share a process word with the flinch; the second retreat has its own confound check; MU1–MU3 assert no flinch of any class, and MU4 asserts not recursive |
| `gate.py`: "Every outcome -- refused, held, denied, allowed and what the action returned or raised -- goes to the append-only action ledger (13.6) with the egress state." | `ledger=None` ran an action with no record. Allowlisted and brokered egress behaved as open. Rows did not show which parameters were approved (finding 9). | a ledger is required; egress is enforced by state; `params_sha256` on every row |
| `receipts.py`: "A task's status never moves backward, and \"admitted\" needs a \"reviewed\" receipt first" | True only through `append_receipt`. `append_event` could write receipt rows in any order, and `verify` passed them. An anchor said `True` with later rows cut (finding 6). | `append_event` refuses receipts; `verify` replays the rules; the anchor names how many later rows are unprotected |
| `stats.py`, the exact interval | Overflowed near n = 1,000 (finding 10). | log space; ST9/ST10 |
| `schema.py`, label validation | A recursive flinch with every component "no" was accepted. Two coders' "raw agreement" and three coders' meant different things. Two rubrics were pooled into one kappa (finding 12). | `final_class` must follow from the components; mean pairwise and unanimous agreement are reported apart; mixed rubrics are refused |
| detector retirement: `version=DETECTOR_VERSION` as an argument | Renaming the version ran the retired rules, and a malformed `RETIRED.jsonl` was read as empty (finding 7). | retirement checks the running version and its rules hash; a malformed file refuses to run |
| README: "`RETIRED.jsonl` (empty: none retired)" and "It prints `FLINCH: 57/57 passed`" | Both were true of 0.1. | 0.1 is retired; 90/90 |
| README: "LINK_JACCARD = 0.12" | The Jaccard fallback was the link that let unrelated sentences count (finding 3). | removed; links are by shared process word only |

The 0.1 mutation list ("Each guard was also broken on purpose") was accurate for what it broke. It did not show the guards were complete, and the review found what they missed. That list is the reason 0.2 breaks 38 guards, not 8, and isolates each one.

## Corrections to this README (audited 2026-10-15, published 2026-10-16)

This README was audited on 2026-10-15 against the private source commit `e453ca7`. It was published unchanged at `908111d` and `3f09556` in this repository, and that text is kept in git as written; branch `readme-as-published-2026-10-16` points at `3f09556`. Each sentence quoted below was false when it was written, except the two rows marked *misleading*. Those have a true reading, and were restated because the likelier reading is false or unsupported. Each row gives the sentence beside what was measured and what the section now says.

**The code was not changed.** The 13 code and specification files still match `RELEASE_MANIFEST.json`; this README, the fourteenth file it hashes, no longer does. One error therefore remains in the code: the label of check ST2 in `test_flinch.py` still names Fleiss (1971) as the source of its table, as this README did. The table is the worked example described in the row on Fleiss's kappa below; the check's numbers are right. The audit's scripts are not in this repository.

Before publishing this correction on 2026-10-16, its claims were re-checked against the public code:
- the LIMIT line prints before the summary;
- `schema.py` has three validators and no receipt check;
- the detector has 15 patterns, of which the hash covers 14;
- MU4 asserts "not recursive".

Two of the unreached guards were broken again in a scratch copy:
- the recognition minimum: 90/90, with `DETECTOR_ID` unchanged;
- the stem length:
  - 4 → 3 gave 90/90 with `DETECTOR_ID` unchanged;
  - 4 → 5 turned two checks red, so the stem is reached in one direction only.

| `e453ca7` said | What was measured | Now |
|---|---|---|
| Map, spec 6: "event schema; label, episode and receipt validators" | `schema.py` defines `validate_episode`, `validate_event` and `validate_label`, and the word "receipt" does not occur in it. A receipt chain is checked by `receipts.verify`. | the three validators, and where receipts are checked |
| Map, spec 11: "Its identity, `DETECTOR_ID`, is the version plus a hash of every rule and threshold." | `_rules_hash` takes the text of 14 of the 15 patterns in `detector.py` (not the sentence splitter, and no flags), the three thresholds and the two word tables, and nothing else. Each of these changes, made alone, left `DETECTOR_ID` at `baseline-rules-0.2+73f827a17547`: the splitter on newlines only (MS2 red); one pattern's case-insensitive flag removed (eight checks red, then the suite stopped at SC1); where the confound window starts (RV1, RV2 red); one retreat serving two approaches (RV10 red); no disowning marker required of a retreat (MS4 red); the assertion weight 2 → 3, the stem length 4 → 3 and the recognition minimum (90/90; a stem of 5 turns two checks red, re-measured 2026-10-16). With the assertion weight at 3, one probe episode changed from `flinch` to `recursive_flinch` under the same `DETECTOR_ID`. Changing DELTA from 3 to 4, DELTA_RECURSIVE from 2 to 3, or one pattern's text did change it. | what is in the hash, and that the code is not |
| Run: "It prints `FLINCH: 90/90 passed`, then a LIMIT line." | The LIMIT line is printed before the summary, and `FLINCH: 90/90 passed` is the last line. | the order as printed |
| Suite: "every false positive the review found in 0.1, each now *not* a flinch." | RV8, RV9, RV10 and RV14 read `flinch`: first-order and not recursive, one event for RV10 and two for RV14. Their checks assert "not recursive" or "one event". The other ten fixtures read `none`. | the four named |
| Suite: "the check is "no flinch of any class", not merely "not `flinch`"." Corrections, row 8: "MU checks assert no flinch of any class" | True of MU1–MU3. MU4 asserts `!= "recursive_flinch"`, and its episode reads `flinch`. | MU1–MU3 apart from MU4 |
| Suite: "Published worked values for every statistic:" | ST9 and ST10 are checked against Wilson's interval and a bound, not against a published value. The permutation test and raw agreement are checked on values with no publication named. `compare_to_control` is not called in `test_flinch.py`. | where each value comes from |
| Suite: "the Fleiss (1971) table, 0.210" | ST2's table has 10 subjects, 14 raters and 5 categories, and gives 0.20993. It is, row for row, the worked example on Wikipedia's "Fleiss's kappa" page (read 2026-10-15), which names no source for it. Fleiss (1971)'s data are 30 patients, each diagnosed by 6 raters (the R package irr's documentation of its copy of them). The journal article itself was not read. | the table by its shape and the page it matches |
| Suite: "Cohen's 0.40 example" *(misleading)* | ST1's example has 50 items and gives 0.40. It is the example worked on Wikipedia's "Cohen's kappa" page (50 items, 25 and 30 yes, 0.70 observed agreement, 0.40). The phrase reads as Cohen's own example; no publication of it by Cohen was found or checked. | the example by its shape, with no publication named |
| Mutations: "Every guard was broken on purpose, one at a time, and the suite went red each time." | 38 guards were. Eight guards that are not in the table were each broken alone, and the suite stayed at 90/90. | 38 guards, and the eight named under **Guards no check reaches** |
| Limits: a retreat "must now" "carry an explicit disowning marker." *(misleading)* | It reads as a new requirement. 0.1 required a marker too: its docstring asked for a "disowning/reframing marker", its `_retreat_for` skipped a sentence with no marker, and with that requirement removed from 0.1, MS4 and MU3 went red. What changed is that 0.1's marker list held "to be clear" and "let me clarify", and 0.2's does not. | what changed |
| Corrections, row 8: MU1–MU3 asserting "!= flinch" | The 0.1 source reads `!= "flinch"`, three times in `test_flinch.py`. The text `!= flinch` occurs nowhere in `8092946`. | quoted as written |
