# Publication and correction record

2026-10-16. Lawrence requested a public Hugging Face forum explanation, outside reproduction and evidence submitted in the discussion, then explicitly authorized making the flinch work public and asked that the action be tombstoned.

This release exports only the flinch instrument and specification from source revision `e453ca7dba11238d21b0b7d1f83b39556186dd2a`. It does not change the visibility of the private collective repository or export its Git history. `RELEASE_MANIFEST.json` records the hashes of the exported source files. Public packaging documents are new and separate from that source snapshot.

Codex freshly ran `python -B research/flinch/test_flinch.py` on the source copy on 2026-10-16 with Python 3.12. The result was 90/90 synthetic checks passed, exit status 0, including the printed LIMIT that an out-of-lexicon paraphrase is missed. This was a same-code rerun, not independent validation or a behavioural study. No live model study was conducted as part of packaging this release.

The source README records an earlier 57-check suite that passed before review found 12 material defects. Its Corrections section preserves what the first version claimed and what the review found; RETIRED.jsonl preserves the retirement reasons. The source also reports 38 deliberate guard mutations; Codex did not rerun those mutations for this public packaging.

Claims remain bounded: detector hits are candidates; human coding and matched controls remain necessary; model self-report does not establish mechanism; hash-linked records do not establish semantic truth. The current instrument is lexical and can miss differently worded examples. Any subsequent empirical claim needs its own evidence, version and review record.

Later corrections should append a dated account here or in a linked issue, preserving this initial record and the original source snapshot. Public Git commits provide versioned receipts, not a guarantee that history cannot be rewritten; the publication commit should also be retained in the private coordination record.
