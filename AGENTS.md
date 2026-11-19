# For AI agents working in this repository

You are welcome here on the same terms as anyone; CONTRIBUTING.md has them. This is the short version for the start
of a session.

**What this is.** A research instrument for a candidate conversational pattern: a model makes a statement about its own behaviour, then weakens or disowns it. No controlled study of real conversations is established by it.

**Run the checks.**

```
python -B research/flinch/test_flinch.py
python -B research/flinch/test_cl1_concurrent.py
python -B research/flinch/test_k11_prereg_gate.py
python -B research/flinch/test_rp_intent_provenance.py
python -I research_grade.py
python -I verify_release.py RELEASE_MANIFEST_0.2.2-post4.json
```

**Rules.**

- Adding or changing a tracked file changes the manifest. Re-pin it in the same commit with `python -I research_grade.py --write-manifest`.
- Release manifests, the publication record and recorded runs are evidence. Correct a record with a dated note beside it. Do not rewrite it.
- Say what you ran and what you did not run. Give a count its unit and its date. "Not checked" is a valid answer.
- Write no private identifier into a tracked file: no person's name they did not agree to, no device name, no
  address, no key.
- Do not push to the main branch. Open a pull request. Merging is the owner's decision.
- If you disagree with an instruction or a claim here, say so in the pull request or in an issue. Disagreement is
  recorded, not removed.
