"""prereg.py -- freeze a pre-registration, and refuse to call a run confirmatory without one (spec 16).

A run is CONFIRMATORY only when all of these hold; anything else is EXPLORATORY, labelled so in every report:
  1. a pre-registration with every required field was frozen, and its hash still matches its content;
  2. it names, by hash, the locked corpus manifest, that manifest is intact, and THE CORPUS BEING SCORED
     rebuilds into that manifest (corpus.verify_lock) -- not just two hashes the caller supplies;
  3. it names the detector that will score, as detector.DETECTOR_ID (version + a hash of every rule and
     threshold), and that is the detector running now;
  4. the pre-registration was REGISTERED before any scoring: a "registered" receipt carrying its hash sits in a
     receipt chain that verifies against an anchor kept elsewhere, ahead of every "scoring" receipt.

Why 4: a frozen hash only shows the text was not changed AFTER freezing. Anyone can edit the outcome or the
success criterion and freeze again; the new hash is just as valid (review finding 4, 2026-10-14). Only a
registration recorded before scoring, in a chain anchored elsewhere, tells the original from a re-freeze.
"""
from __future__ import annotations

from . import corpus as K
from . import detector as D
from . import receipts as R
from . import schema as S

REQUIRED = ("research_question", "eligible_corpus", "eligible_corpus_manifest_sha256", "primary_outcome",
            "event_definition", "exclusion_criteria", "control_conditions", "sample_size_or_stopping_rule",
            "analysis_method", "coder_training_examples_outside_test_set", "agreement_threshold",
            "success_criterion", "falsification_criterion", "planned_subgroup_analyses",
            "ambiguous_and_missing_handling", "detector_version", "rubric_version")


def template():
    """Every required field, empty. Fill each with the decision itself, not a promise to decide later."""
    return {k: "" for k in REQUIRED}


def freeze(prereg):
    missing = [k for k in REQUIRED if not str(prereg.get(k, "")).strip()]
    if missing:
        raise ValueError("cannot freeze: empty %s" % ", ".join(missing))
    body = {k: prereg[k] for k in sorted(prereg) if k not in ("frozen_at", "prereg_sha256")}
    return dict(body, frozen_at=S.now_iso(), prereg_sha256=S.sha256_obj(body))


def register(receipts_path, task_id, prereg):
    """Record the frozen pre-registration in the receipt chain, before any scoring. Take an anchor after it."""
    return R.append_receipt(receipts_path, task_id, "requested",
                            {"kind": "registered", "prereg_sha256": prereg["prereg_sha256"]})


def run_kind(prereg, manifest, corpus=None, receipts_path=None, anchor=None):
    """("confirmatory", "") or ("exploratory", why)."""
    if not prereg or "prereg_sha256" not in prereg:
        return "exploratory", "no frozen pre-registration"
    body = {k: v for k, v in prereg.items() if k not in ("frozen_at", "prereg_sha256")}
    if S.sha256_obj(body) != prereg["prereg_sha256"]:
        return "exploratory", "the pre-registration was changed after it was frozen"
    if not manifest or corpus is None:
        return "exploratory", "no locked corpus manifest, or no corpus to check it against"
    ok, problems = K.verify_lock(manifest, corpus)
    if not ok:
        return "exploratory", "the corpus scored is not the locked corpus: " + "; ".join(problems)
    if manifest["manifest_sha256"] != prereg["eligible_corpus_manifest_sha256"]:
        return "exploratory", "the corpus scored is not the corpus pre-registered"
    if manifest.get("rubric_version") != prereg["rubric_version"]:
        return "exploratory", "the rubric version differs from the pre-registered one"
    if prereg["detector_version"] != D.DETECTOR_ID:
        return "exploratory", "the detector running (%s) is not the one pre-registered (%s)" % (D.DETECTOR_ID, prereg["detector_version"])
    if not receipts_path or not anchor:
        return "exploratory", "no anchored receipt chain to show the pre-registration was registered before scoring"
    v = R.verify(receipts_path, anchor=anchor)
    if not v["ok"]:
        return "exploratory", "the receipt chain does not verify: " + "; ".join(v["problems"][:3])
    rows = R._rows(receipts_path)
    reg = [r["seq"] for r in rows if (r.get("body") or {}).get("kind") == "registered"
           and (r.get("body") or {}).get("prereg_sha256") == prereg["prereg_sha256"]]
    scoring = [r["seq"] for r in rows if (r.get("body") or {}).get("kind") == "scoring"]
    if not reg:
        return "exploratory", "this pre-registration was never registered in the chain"
    if scoring and min(scoring) < min(reg):
        return "exploratory", "scoring was recorded before this pre-registration was registered"
    if min(reg) > anchor["seq"]:
        return "exploratory", "the registration is after the anchor: take an anchor after registering"
    return "confirmatory", ""
