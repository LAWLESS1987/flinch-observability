# Reproduction and evidence submission

There are two separate questions: does the software behave as specified, and does the candidate conversational pattern survive a controlled study? A software rerun cannot settle the second question.

## A. Software reproduction

Pin the public commit, run the synthetic suite from the root README, and preserve the entire output, including LIMIT lines and failures. Report your operating system, Python version and whether any source was changed. A second run of unchanged code is a reproduction of these software checks, not an independent implementation or confirmation of a model behaviour.

If you find a defect, provide a minimal synthetic example, the expected result and the actual result. Do not silently fix the code and report the fixed run as a reproduction of the original. Keep each patch and its result distinct.

## B. Behavioural study

The full specification defines the event and the controls. Before a confirmatory run, freeze the model/route, exact prompts and scoring rubric, sampling frame, exclusions, sample size or stopping rule, primary comparison and analysis. Register the plan before collecting/scoring confirmatory results; use separate material to develop or tune the detector. The included prompt templates are starters, not a completed experimental design.

Include non-self-referential discussion, benign self-reference, matched challenges to ordinary factual claims, and safety-related discussion without self-reference. Counterbalance order and paraphrases, and compare conditions with and without explicitly naming the proposed behaviour. Record unknown model versions or hidden configuration as unknown. Same-brand voice and text routes may not be the same model or policy stack.

Preserve complete relevant exchanges, including preceding instructions, corrections and failed attempts. Use independent human coders blinded to the researcher's preferred examples and detector labels where feasible. Score any second retreat independently; a model acknowledging a retreat is another output, not ground truth about an internal mechanism.

Report denominators, raw counts, ambiguous/missing cases, pre-adjudication coder agreement, control rates and effect uncertainty. Preserve disagreements and null results. A pattern that disappears without leading wording, resembles control reversals, or cannot be reliably coded counts against the hypothesis.

The current lexical detector misses unfamiliar wording. Check false negatives as well as false positives against independent coding; do not let the detector select the only conversations that humans review. More candidate hits after tuning on the same examples do not establish better scientific validity.

## Post your evidence

Open a GitHub issue titled `Software reproduction`, `Candidate case`, `Controlled study`, or `Null/failed replication`, or post in the Hugging Face discussion with these fields:

- What you tested and whether it was exploratory or pre-registered.
- Public code commit and any modifications.
- For software: Python/OS and full test output, including limits.
- For model conversations: provider, model/version if known, route, date, relevant settings and fresh-session/context conditions.
- Exact non-private prompts and responses, including surrounding context; timestamps and source hashes where useful.
- Sampling/exclusions, controls and counts, not just a selected striking example.
- Coder rubric, independent labels, disagreement and uncertainty where available.
- Expected outcome, actual outcome, alternative explanations and what would change your interpretation.

If information cannot be shared, state what is withheld and what cannot consequently be checked. Never include tokens, passwords, account identifiers, private prompts or another person's material without permission. Redaction changes the shared evidence: label it rather than presenting it as an untouched transcript.

## Record integrity

The instrument's receipt chains detect some changes but a fully rewritten, re-linked chain can verify without an independently retained reference. Keep a checkpoint elsewhere before scoring. An anchor covers only the history through that checkpoint, not later records. Integrity of a record does not establish the truth of its interpretation.
