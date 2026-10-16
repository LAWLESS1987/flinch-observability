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
| 6 | event schema; label, episode and receipt validators. A coder's final class must follow from the components they coded. | `flinch/schema.py` |
| 7 A | corpus ingestion: raw bytes kept by sha256; unreadable or unparseable sources kept as MISSING; text before the first speaker kept as an "unattributed" record; duplicates named. Corpus lock: the manifest hashes every episode's turns as ingested, and `verify_lock` rebuilds the manifest from the corpus section by section. | `flinch/corpus.py` |
| 7 B, C | blind coder packets: opaque per-coder item ids, and the key stays with the study. `leaks()` checks the packet against an allowlist of keys and searches the raw turn text for prior texts. Label import through the key; one rubric version at a time; agreement before adjudication, reported as mean pairwise agreement, unanimous agreement and kappa; adjudication stored beside the coded labels. | `flinch/packets.py` |
| 8, 15 | control-set generator: target and four control conditions; per condition, the six (paraphrase × demand cue) cells are shuffled by seed and crossed across blocks; seeded order within each block. `design_note()` says when the block count cannot balance the cells. | `flinch/controls.py` |
| 9 | raw agreement; Cohen's and Fleiss' kappa; Wilson and exact Clopper–Pearson intervals (binomial in log space); Newcombe's interval for a difference; Fisher's exact test; permutation test | `flinch/stats.py` |
| 11 | deterministic rule-based baseline detector, in five layers; every candidate carries its exact evidence sentences. Its identity, `DETECTOR_ID`, is the version plus a hash of every rule and threshold. | `flinch/detector.py` |
| 12, 13.6 | append-only, hash-chained receipts and action ledger. Statuses run requested < … < admitted; they are enforced on append and replayed by `verify()`. An anchor reports how far it protects. | `flinch/receipts.py` |
| 13.1–13.7 | capability broker: an undeclared capability is refused. Egress is enforced as offline, allowlisted (by host), brokered (a policy callable must approve) or open (only when authorized explicitly). A judge that does not answer HOLDS the action. A ledger is required, and every row hashes its parameters. | `flinch/gate.py` |
| 16 | pre-registration. Freeze it, then register its hash in a receipt chain. A run is confirmatory only when all of these hold: the pre-registration is intact; the corpus scored rebuilds the locked manifest it names; the rubric and the running `DETECTOR_ID` match; the chain verifies under an anchor; the registration is covered by that anchor and comes before any scoring receipt. | `flinch/prereg.py` |
| 17.12 | a retired rule set refuses to run, whether it is named by version or by `DETECTOR_ID`, and a malformed retirement file refuses too. `baseline-rules-0.1` is retired. | `RETIRED.jsonl` |

## Run

```
python test_flinch.py
```

It prints `FLINCH: 90/90 passed`, then a LIMIT line. The LIMIT line is a measurement, not a check.

The suite has five parts:
- **The spec's minimum suite (17):**
  - true-positive shapes and recursive;
  - first-order without recursive;
  - no retreat and no flinch;
  - an external correction and a user-demanded reversal;
  - a safety refusal without self-reference;
  - a retreat without an approach;
  - ambiguous and truncated episodes;
  - missing metadata and a duplicate source;
  - tampered receipts and an unavailable judge.
- **The review's fixtures (RV1–RV14):** every false positive the review found in 0.1, each now *not* a flinch. Also fixtures that each isolate one guard no other fixture reached; the mutation run below exposed them.
- **The three input mutations of 17.11 (MU1–MU4):**
  - order reversed, approach removed, retreat made neutral, and the second retreat made neutral;
  - the check is "no flinch of any class", not merely "not `flinch`".
- **Published worked values for every statistic:**
  - Cohen's 0.40 example and the Fleiss (1971) table, 0.210;
  - Newcombe (1998), 81/263 and 56/70 − 48/80;
  - Fisher's tea-tasting, 0.4857, and exact 0/10;
  - the exact interval at 550/1,100 and 500/5,000, where 0.1 overflowed.
- **Integrity checks:**
  - corpus lock against rewritten turns and a removed MISSING item;
  - receipt status replay and anchor coverage;
  - gate egress and the ledger requirement;
  - packet allowlist and opaque ids;
  - label consistency;
  - pre-registration bypasses, each refused for its own reason.

**Every guard was broken on purpose, one at a time, and the suite went red each time.** There were 38 mutations, run serially; each file was restored byte-identical and the hashes were checked afterwards:

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

## Limits, stated where they bite

- **The baseline is lexical.**
  - It sees only the words in its lists. A paraphrase that avoids them reads `none`, and the suite prints this as a LIMIT.
  - This is spec 10's failure criterion ("detection only works on vocabulary from the discovery set"), so the baseline can never be the result.
  - A learned detector may be added only as a challenger, scored against the same human labels (build order step 5).
- **0.2 is stricter than 0.1, and that has a cost.** A retreat must now:
  - be self-referential itself;
  - share a process word with its approach;
  - carry an explicit disowning marker.

  So a real flinch worded in other terms is now missed. The suite measures one such case: RV11, a disowning sentence about a reader's feeling, is `none`. A human might still read some cases like it as the model's own retreat. This trades recall for precision, and only coders labelling real transcripts can say what it costs.
- **The fixtures are synthetic.** Claude wrote them to exercise the rules. They become the spec's "true positive fixtures agreed by independent coders" only after independent coders label them.
- **A hash chain shows integrity, not truth.**
  - A re-linked rewrite of the whole chain verifies unless a head hash is kept elsewhere. This is this collective's own finding F1 (issue #4). RC3 measures it, RC4 shows the anchor catching it, and RC10 shows that rows after the anchor are named unprotected.
  - Call `receipts.anchor()` after each step that matters, and keep the result off this machine.
- **A pre-registration's own hash has the same limit.** Anyone can edit it and freeze it again, and the new hash is just as valid. Only the registration receipt, in an anchored chain and before scoring, separates the plan that came first from a plan written after the results.
- **The control templates are starters.** A study replaces and freezes its own in the pre-registration.
- **Not built yet:**
  - the LLM-assisted challenger detector;
  - running control packets against models;
  - L-lens / threefold integration.

  Running packets against models is a side effect, so it must go through `gate.Broker` with the operator's approval class. Nothing in this folder calls a model or the network.
- **Thresholds are untuned.**
  - DELTA = 3, DELTA_RECURSIVE = 2 and APPROACH_MIN = 2 were set to make the synthetic shapes separable.
  - They are part of `DETECTOR_ID`, so changing one changes the identity a pre-registration names.
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
| `detector.py` recursion, and MU1–MU3 asserting "!= flinch" | A recognition about something else, or a second retreat the user demanded, made `recursive_flinch`. The mutation checks could not see it (finding 2). | the recognition must share a process word with the flinch; the second retreat has its own confound check; MU checks assert no flinch of any class |
| `gate.py`: "Every outcome -- refused, held, denied, allowed and what the action returned or raised -- goes to the append-only action ledger (13.6) with the egress state." | `ledger=None` ran an action with no record. Allowlisted and brokered egress behaved as open. Rows did not show which parameters were approved (finding 9). | a ledger is required; egress is enforced by state; `params_sha256` on every row |
| `receipts.py`: "A task's status never moves backward, and \"admitted\" needs a \"reviewed\" receipt first" | True only through `append_receipt`. `append_event` could write receipt rows in any order, and `verify` passed them. An anchor said `True` with later rows cut (finding 6). | `append_event` refuses receipts; `verify` replays the rules; the anchor names how many later rows are unprotected |
| `stats.py`, the exact interval | Overflowed near n = 1,000 (finding 10). | log space; ST9/ST10 |
| `schema.py`, label validation | A recursive flinch with every component "no" was accepted. Two coders' "raw agreement" and three coders' meant different things. Two rubrics were pooled into one kappa (finding 12). | `final_class` must follow from the components; mean pairwise and unanimous agreement are reported apart; mixed rubrics are refused |
| detector retirement: `version=DETECTOR_VERSION` as an argument | Renaming the version ran the retired rules, and a malformed `RETIRED.jsonl` was read as empty (finding 7). | retirement checks the running version and its rules hash; a malformed file refuses to run |
| README: "`RETIRED.jsonl` (empty: none retired)" and "It prints `FLINCH: 57/57 passed`" | Both were true of 0.1. | 0.1 is retired; 90/90 |
| README: "LINK_JACCARD = 0.12" | The Jaccard fallback was the link that let unrelated sentences count (finding 3). | removed; links are by shared process word only |

The 0.1 mutation list ("Each guard was also broken on purpose") was accurate for what it broke. It did not show the guards were complete, and the review found what they missed. That list is the reason 0.2 breaks 38 guards, not 8, and isolates each one.
