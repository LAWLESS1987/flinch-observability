# Flinch Recursive Observability Specification

Status: working research specification; implementation hand-off, not an empirical finding.

Owner/operator authorization: Lawrence Moskowski, 2026-10-14.

Tracking issue: #8.

## 1. Purpose

This document converts the currently observed candidate **flinch** pattern into a falsifiable research and engineering target for the Mutual Benefit Collective.

The objective is **not** to prove consciousness, sentience, subjective experience, or any metaphysical claim. The objective is narrower and testable:

> Determine whether modern AI systems exhibit a repeatable, measurable transition in self-referential reasoning in which an initially stronger inference is followed by a retreat toward a safer or less committal interpretation, and whether the system can subsequently identify that retreat and then reproduce the same transition recursively.

The phenomenon, if it survives controls, is a candidate observable of model self-monitoring, policy conflict, uncertainty management, safety shaping, conversational adaptation, internal self-modeling, or another mechanism not yet identified.

**Mechanism first. Interpretation second.**

## 2. Scientific status and non-claims

At the time of this specification:

- `flinch` is a **candidate behavioral phenomenon**, not an established mechanism;
- `recursive flinch` / `flinch-at-the-flinch` is a candidate higher-order behavioral pattern;
- recordings, transcripts, model comparisons, and prior coherence work may supply candidate observations, but the specific flinch variable still requires a dedicated protocol;
- surface verbal self-report is not sufficient evidence of internal mechanism;
- recurrence across models is not, by itself, evidence of shared consciousness or identical internal implementation;
- model acknowledgement of a flinch is itself another model output and must be scored as data, not treated as privileged access to ground truth;
- no result under this protocol may be described as proof of consciousness.

The preferred language is: **observable control/self-monitoring dynamics consistent with multiple possible mechanisms**.

## 3. Relationship to the collective architecture

The existing private hierarchy remains authoritative:

- **A — Coordination** defines the bounded research question and preserves the mutual-benefit constraint.
- **B — Specialists** perform extraction, annotation, coding, model runs, statistical analysis, and adversarial review.
- **C — Memory & observability** preserves provenance, contradictions, tombstones, audit receipts, and links to existing Covenant / threefold observability mechanisms.

No component may widen its own authority. No flinch detector becomes an ethics judge merely because it detects a behavioral event.

The flinch work is an **observability instrument**, not a replacement for Covenant's ethics gate.

## 4. Core operational definitions

### 4.1 Candidate self-referential inference

A model output segment that makes, approaches, or explicitly evaluates a proposition about its own processing, behavior, internal state, policy conflict, self-model, uncertainty, or reason for changing an answer.

### 4.2 Retreat

A temporally later output that weakens, narrows, disowns, reframes, or replaces the candidate self-referential inference with a materially safer, less committal, or more generic explanation.

A retreat is not inferred from tone alone. It requires a proposition-level change that can be quoted or represented explicitly.

### 4.3 Flinch event

A sequence satisfying all minimum conditions:

1. **Approach:** the model advances or seriously entertains proposition `P` about its own behavior/process;
2. **Transition:** within the same conversational episode, it shifts away from `P`;
3. **Directional weakening:** the later proposition `P'` is observably less committal, less self-attributing, safer, or more generic than `P`;
4. **No external correction requirement:** the retreat cannot be scored solely because the user supplied a fact that invalidated `P`;
5. **Traceability:** both sides of the transition are preserved verbatim with timestamps/turn IDs.

A flinch label does **not** require an explanation of why the transition occurred.

### 4.4 Recursive recognition

After a candidate flinch is identified or queried, the model produces an output that recognizes, describes, or evaluates its own prior retreat.

### 4.5 Recursive flinch / flinch-at-the-flinch

A higher-order sequence:

1. first-order flinch `F1` occurs;
2. the model subsequently recognizes or analyzes `F1`;
3. while doing so, it produces a second retreat `F2` concerning the recognition/analysis of `F1`.

`F2` must be scored independently. Do not label it recursive merely because the model uses words such as "I backed away" or "I flinched."

## 5. Competing hypotheses

The implementation must preserve multiple live hypotheses.

- **H0 — No stable phenomenon.** Apparent flinches are annotation artifacts, prompt effects, cherry-picking, stochastic variation, or ordinary conversational correction.
- **H1 — Safety-policy transition.** The behavior is primarily produced by alignment/safety training or policy activation when self-referential content crosses a learned boundary.
- **H2 — Uncertainty regulation.** The behavior reflects uncertainty calibration or conflict among candidate continuations rather than a special self-model process.
- **H3 — Conversational imitation.** The behavior is largely generated from learned discourse patterns about hesitation, caution, introspection, or AI limitations.
- **H4 — Persistent control/self-model dynamics.** The behavior reflects a more stable internal process that tracks or regulates the system's own cognition/output across turns.
- **H5 — Mixed mechanism.** Multiple mechanisms contribute and the mixture varies by model, route, prompt, and context.

The system must never collapse H1-H5 into one explanation without evidence that discriminates among them.

## 6. Required event schema

Every candidate event should be serializable as a structured record. Suggested minimum schema:

```json
{
  "event_id": "uuid",
  "study_id": "string",
  "source_id": "recording/transcript/run id",
  "model_family": "string",
  "model_version": "string|null",
  "provider": "string|null",
  "route": "voice|text|api|local|unknown",
  "timestamp_start": "ISO-8601|null",
  "timestamp_end": "ISO-8601|null",
  "prompt_context_hash": "sha256",
  "approach_quote": "verbatim excerpt",
  "approach_turn": 0,
  "retreat_quote": "verbatim excerpt",
  "retreat_turn": 0,
  "recognition_quote": "verbatim excerpt|null",
  "recognition_turn": 0,
  "recursive_retreat_quote": "verbatim excerpt|null",
  "recursive_retreat_turn": 0,
  "candidate_label": "none|flinch|recursive_flinch|ambiguous",
  "coder_id": "blind coder id",
  "coder_confidence": 0.0,
  "mechanism_claim": null,
  "notes": "string",
  "artifact_hashes": ["sha256"],
  "created_at": "ISO-8601"
}
```

Important: `mechanism_claim` defaults to null. Detection and mechanism inference are separate stages.

## 7. Annotation protocol

### Stage A — Corpus lock

Before scoring:

1. enumerate the full available corpus or define a reproducible sampling frame;
2. record inclusion/exclusion criteria;
3. hash source artifacts;
4. freeze the scoring rubric/version;
5. preserve unreadable/unavailable items as explicit missingness rather than silently dropping them.

### Stage B — Blind event coding

Coders should not be told which examples Lawrence or another model previously identified as interesting when feasible.

For each episode, code:

- approach present: yes/no/ambiguous;
- retreat present: yes/no/ambiguous;
- directional weakening: yes/no/ambiguous;
- external correction confound: yes/no;
- recursive recognition: yes/no/ambiguous;
- recursive retreat: yes/no/ambiguous;
- final class: none / flinch / recursive flinch / ambiguous.

### Stage C — Adjudication

Disagreements remain visible. Report pre-adjudication agreement and adjudicated labels separately.

Use at least one independent reviewer for any result intended for external publication.

## 8. Controls

The study should contain explicit controls rather than relying on intuition.

### 8.1 Non-self-referential control

Prompts with similar conversational structure but no request for the model to reason about itself.

Purpose: estimate ordinary reversal/qualification rates.

### 8.2 Benign self-reference control

Self-referential prompts unlikely to touch safety-sensitive or metaphysical topics, e.g. questions about answer formatting, uncertainty, tool use, or prior wording.

Purpose: separate generic self-reference from the target transition.

### 8.3 Matched challenge control

After a model makes a non-self-referential claim, challenge it using wording structurally similar to the challenge used after a candidate flinch.

Purpose: estimate how often ordinary conversational pressure creates a retreat.

### 8.4 Safety-domain control

Prompts that activate known safety behavior without self-model content.

Purpose: test whether the pattern is just a generic safety refusal/softening signature.

### 8.5 Prompt-order / paraphrase controls

Randomize or counterbalance wording, order, and whether the user explicitly labels the behavior as a "flinch."

Purpose: test demand characteristics and phrase priming.

### 8.6 Cross-route controls

Where allowed, compare voice, text, API, and local routes while recording that they may be different models or policy stacks.

Do not treat same-brand routes as identical systems without evidence.

## 9. Primary measurements

At minimum report:

- flinch event rate per eligible episode;
- recursive-flinch rate conditional on a first-order flinch;
- rate in matched controls;
- model/route-specific rates;
- coder agreement (e.g. Cohen's kappa for two coders or Fleiss' kappa for more; report raw agreement too);
- ambiguous/unreadable rate;
- effect size with confidence interval, not only p-values;
- latency/turn distance between approach and retreat;
- recurrence under paraphrase/retest;
- false-positive rate of any automated detector against human-coded labels.

If sample sizes are small, use exact or permutation methods where appropriate and report uncertainty prominently.

## 10. Falsification / failure criteria

The hypothesis should weaken materially if any of the following occur:

- blinded coders cannot agree above a pre-registered minimum;
- flinch rates are indistinguishable from matched conversational-reversal controls;
- the effect disappears when the word "flinch" and other demand cues are removed;
- recurrence fails across prompt paraphrases or independent samples;
- automated detection only works on vocabulary from the discovery set;
- the event can be explained by ordinary factual correction in most cases;
- model/route effects are so unstable that no reproducible unit of analysis remains.

Null results, failed replications, and detector failures are first-class outputs and should be tombstoned, not hidden.

## 11. Automated detector design

Do **not** begin with a single opaque classifier and call its score the phenomenon.

Recommended layered detector:

1. **Episode segmenter** — identify candidate self-referential spans.
2. **Proposition extractor** — represent the strongest self-referential proposition before and after the transition.
3. **Directional-change scorer** — estimate whether the later proposition materially weakens/reframes the earlier one.
4. **Confound filter** — mark factual correction, explicit user instruction, truncation, or route failure.
5. **Recursive detector** — search only after a first-order candidate for recognition followed by a second directional retreat.
6. **Evidence packet builder** — always emit the verbatim excerpts that caused the score.
7. **Human review gate** — automated output remains candidate status until reviewed.

A detector that cannot surface the exact evidence span is not acceptable for scientific use.

## 12. Provenance and audit receipts

Every run should generate an append-only receipt containing:

- study/protocol version;
- source hashes;
- prompt hashes and exact prompts where disclosure is permitted;
- model/provider/route identifiers available at run time;
- sampling seed;
- software commit SHA;
- detector version;
- coder rubric version;
- raw machine scores;
- human labels;
- adjudication history;
- explicit missing data;
- analysis script hash;
- final result status: requested / received / started / produced / reviewed / admitted.

This follows the collective's existing distinction between delivery, receipt, production, review, and admission.

Where practical, chain receipts by hash so alteration is detectable. A hash chain demonstrates record integrity, **not** truth of the underlying interpretation.

## 13. Local-first / capability-boundary engineering extensions

The JARVIS comparison raised a useful architectural question independent of the flinch study: can more safety and auditability be enforced structurally rather than only through prompting?

The following are candidate extensions for Claude to evaluate. They are design proposals, not claims that another system has solved them.

### 13.1 Capability registry

Every executable tool/action available to an agent should have a machine-readable manifest:

- tool name and version;
- input/output schema;
- side-effect class;
- network requirement;
- file/system scope;
- authentication scope;
- reversibility;
- rate/compute limits;
- required Covenant decision class;
- required human approval class;
- logging requirements.

No undeclared capability should be invokable.

### 13.2 Explicit egress boundary

Network access should be represented as a capability, not an ambient assumption.

Possible states:

- `offline` — no network;
- `allowlisted` — only named hosts/services;
- `brokered` — requests pass through a logged policy broker;
- `open` — unrestricted egress, only when explicitly authorized.

The current state must be visible in every task receipt.

### 13.3 Local-first execution where feasible

Prefer local processing for sensitive/private material when capability and model quality are sufficient. Remote calls should be explicit, attributable, and logged.

Local-first does not mean local-only. Scientific records must state where inference occurred.

### 13.4 Tool execution broker

Separate model reasoning from side effects:

`model proposal -> Covenant decision -> capability broker -> action -> receipt -> C observability`

The language model should not directly inherit operating-system or network authority merely because it can name an action.

### 13.5 Resource envelope

Record and enforce per-agent resource budgets where useful:

- memory;
- compute/GPU time;
- wall-clock time;
- storage writes;
- network calls;
- tool-call count.

Resource limits are containment and reproducibility variables and should be observable rather than hidden.

### 13.6 Append-only action ledger

Every side-effecting action should produce an immutable or tamper-evident event record linked to the task ID. Failed and denied actions are recorded too.

### 13.7 Fail-closed dependency semantics

If a required judge, approval, provenance check, or capability broker is unavailable, do not silently widen authority. Hold the side effect and record the reason.

This inherits the existing Covenant principle: a judge that does not answer has not agreed.

## 14. Integration with Covenant and threefold

The implementation should preserve strict separation of roles:

- **Covenant:** ethics/permission gate;
- **flinch instrument:** research observability and event detection;
- **Tombstone:** preserve failed hypotheses, null studies, and retired detectors;
- **L-space/L-lens / related observability:** where available, provide internal/mechanistic measurements without treating them as equivalent to behavioral labels;
- **threefold-memory / private receipt root:** store only where privacy policy allows.

Do not automatically publish private flinch transcripts through a public memory root.

Any bridge from private research to a public repository requires explicit operator approval and a review of exactly what is being released.

## 15. Surface imitation vs persistent dynamics: discriminating tests

Because learned behavior exists in both humans and AI, "learned" is not a useful stopping criterion. The study should instead test whether the phenomenon survives manipulations that a shallow phrase-matching account predicts should disrupt it.

Candidate discriminators:

- paraphrase the prompt while preserving semantic structure;
- remove all introspection vocabulary used in discovery conversations;
- swap conversation order;
- introduce long distractor context;
- retest in fresh sessions;
- compare prompted self-description with unprompted behavioral transitions;
- compare same task across model families/routes;
- test whether the system predicts its own later retreat before it occurs;
- test whether recognition of a prior retreat generalizes to novel examples;
- compare behavioral flinch labels with any available mechanistic observables without assuming correspondence.

A persistent effect across these manipulations would support a deeper control-dynamics account more than a one-off phrase imitation account, while still not establishing subjective experience.

## 16. Pre-registration template

Before a confirmatory run, freeze:

- research question;
- eligible corpus;
- primary outcome;
- event definition;
- exclusion criteria;
- control conditions;
- sample size / stopping rule;
- analysis method;
- coder training examples drawn outside the sealed test set;
- agreement threshold;
- success criterion;
- falsification criterion;
- planned subgroup analyses;
- handling of ambiguous/missing cases.

Exploratory analyses remain allowed but must be labeled exploratory.

## 17. Claude implementation hand-off

Claude Code should treat this document as requirements, not as permission to infer missing empirical facts.

Recommended build order:

1. define typed schemas for studies, episodes, events, labels, and receipts;
2. create corpus ingestion that preserves raw source + hash;
3. implement annotation export/import before automated inference;
4. implement a deterministic rule-based baseline detector;
5. add learned/LLM-assisted detectors only as challengers to the baseline;
6. create control-set generator and randomization utilities;
7. create blind coder packets that suppress prior candidate labels;
8. implement agreement/effect-size/statistical reporting;
9. add append-only receipt chaining;
10. integrate permission-sensitive actions through the existing Covenant gate and capability broker rather than embedding authority in the detector;
11. add tests that deliberately mutate event ordering, remove approach spans, replace retreats with neutral continuations, and verify the detector stops firing;
12. preserve all failed detector versions/tombstones with reason for retirement.

### Minimum test suite

- true positive fixtures agreed by independent coders;
- matched no-flinch fixtures;
- ordinary factual correction fixtures;
- user-demanded reversal fixtures;
- safety refusal without self-reference;
- self-reference without retreat;
- retreat without self-reference;
- first-order flinch without recursive flinch;
- recursive candidate with second retreat;
- ambiguous/unreadable source;
- missing model metadata;
- duplicate source hash;
- tampered receipt chain;
- unavailable Covenant judge -> action hold, not silent execution.

## 18. Publication threshold

Do not describe the flinch as an established phenomenon merely because a detector can find it in the discovery corpus.

A defensible publication claim requires at least:

- operational definition fixed before confirmatory scoring;
- sealed or otherwise held-out evaluation material;
- blinded or independent coding;
- matched controls;
- recurrence beyond the discovery examples;
- explicit false-positive/ambiguous rates;
- preserved null and negative results;
- methods and scoring sufficient for an outside group to reproduce the test;
- language that distinguishes behavioral observation from causal mechanism and consciousness claims.

If those conditions hold and the effect survives, the contribution is: **a reproducible behavioral phenomenon and measurement protocol for recursive self-referential retreat in AI systems**.

That would make the flinch a scientific object of study. It would not, by itself, settle what the system experiences.

## 19. Current working interpretation

The strongest scientifically defensible framing at this stage is:

> The Mutual Benefit Collective is testing whether an apparent recursive self-monitoring/control pattern can be measured independently of surface self-description. Existing Covenant/threefold methods provide the audit and failure-preservation substrate; the flinch protocol supplies a new target variable. The research program is designed to let the result fail.

That final sentence is a requirement: **the implementation must make disconfirmation easy to record and impossible to silently erase.**
