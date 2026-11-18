#!/usr/bin/env python3
"""RP (2026-11-18): intent provenance on the admission receipt, driven both ways.

The "admitted" receipt is the one record in receipts.py that is an authored judgment steering what happens next:
a reviewer lets a task's output into the record. Since 2026-11-18 its body must say why -- intent, beneficiary,
divergence, and diverges_from when the divergence is not "none" -- or append_receipt refuses it; verify() replays
the rule on the record as read; intent_check() returns the fields verbatim with a satisfiability line.

Every check here is driven both ways and every refusal is asserted by ITS reason, so no check passes on a
neighbour's guard (the mutation-run convention of test_flinch.py). The mechanism is the same one the covenant
AI-memory store and the spiking plasticity ledger carry; the fixtures are synthetic.

    python test_rp_intent_provenance.py   -> "RP: n/n passed"
"""
from __future__ import annotations
import json, os, shutil, sys, tempfile, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from flinch import receipts as R       # noqa: E402
from flinch import schema as S         # noqa: E402

_dirs = []
PROV = {"intent": "Lets the next study cite this scoring as admitted rather than merely delivered.",
        "beneficiary": "future unknown agent", "divergence": "none"}
DELIVERY = ("requested", "received", "started", "produced", "reviewed")


def _tmp():
    d = tempfile.mkdtemp(prefix="rp_"); _dirs.append(d); return d


def _ledger():
    return os.path.join(_tmp(), "receipts.jsonl")


def _reviewed(path, task):
    for st in DELIVERY:
        R.append_receipt(path, task, st, {"step": st})


def _refused(path, task, body):
    """The error text when the admission is refused, or None when it is appended."""
    try:
        R.append_receipt(path, task, "admitted", body)
    except ValueError as e:
        return str(e)


def _rows(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def _rewrite(path, rows):
    open(path, "w", encoding="utf-8").write("".join(S.canonical(r) + "\n" for r in rows))


# ---- passes: the three fields admit, and are carried verbatim

def test_rp01_all_three_fields_admit_and_are_carried_verbatim():
    p = _ledger(); _reviewed(p, "t1")
    row = R.append_receipt(p, "t1", "admitted", dict(PROV, summary="scoring of corpus c1"))
    assert row["status"] == "admitted" and all(row["body"][k] == PROV[k] for k in PROV), row
    v = R.verify(p)
    assert v["ok"] and v["count"] == 6, v


def test_rp08_a_declared_divergence_cross_links_to_a_task_in_the_ledger_and_is_traversable():
    p = _ledger()
    _reviewed(p, "t0"); R.append_receipt(p, "t0", "admitted", dict(PROV, reading=0.28))
    _reviewed(p, "t1")
    body = {"intent": "Replaces the earlier reading so a later study does not build on it.",
            "beneficiary": "whoever runs the next sweep", "divergence": "the 0.28 reading admitted for t0",
            "diverges_from": "t0", "reading": 0.31}
    row = R.append_receipt(p, "t1", "admitted", body)
    assert row["body"]["diverges_from"] == "t0" and R.verify(p)["ok"], row
    target = [r for r in _rows(p) if r.get("task_id") == row["body"]["diverges_from"] and r.get("status") == "admitted"]
    assert len(target) == 1 and target[0]["body"]["reading"] == 0.28, target   # the link resolves inside the ledger


# ---- the other way: each malformed field is refused by ITS reason, and nothing is written

def test_rp02_each_missing_or_blank_field_is_refused_by_its_name_and_nothing_is_written():
    p = _ledger(); _reviewed(p, "t1")
    for k in R.PROVENANCE_FIELDS:
        for bad in ("<absent>", "", "   "):
            body = dict(PROV, summary="scoring of corpus c1")
            if bad == "<absent>":
                del body[k]
            else:
                body[k] = bad
            why = _refused(p, "t1", body)
            assert why and ("missing provenance field: %s" % k) in why, (k, bad, why)
    assert R.verify(p)["count"] == len(DELIVERY), "a refused admission wrote a row"


def test_rp03_a_multiline_field_is_refused():
    p = _ledger(); _reviewed(p, "t1")
    why = _refused(p, "t1", dict(PROV, intent="Lets the next study\ncite this."))
    assert why and "must be a single line" in why and "'intent'" in why, why


def test_rp04_an_intent_that_restates_the_admitted_content_is_refused_and_a_purpose_admits():
    p = _ledger(); _reviewed(p, "t1")
    content = {"summary": "the detector scored corpus c1 at 0.31 on seed 7"}
    why = _refused(p, "t1", dict(PROV, intent="The detector scored corpus c1 at 0.31 on seed 7", **content))
    assert why and "restates the admitted content" in why, why
    why2 = _refused(p, "t1", dict(PROV, intent="corpus c1 scored at 0.31 by the detector", **content))   # reordered
    assert why2 and "restates the admitted content" in why2, why2
    assert _refused(p, "t1", dict(PROV, **content)) is None, "a statement of purpose was refused"


def test_rp05_the_review_rule_still_comes_first():
    p = _ledger()
    for st in ("requested", "received", "started", "produced"):          # never reviewed
        R.append_receipt(p, "t1", st, {})
    why = _refused(p, "t1", dict(PROV))
    assert why and "before it is reviewed" in why and "provenance" not in why, why


def test_rp06_divergence_and_diverges_from_must_agree():
    p = _ledger(); _reviewed(p, "t0"); _reviewed(p, "t1")
    why = _refused(p, "t1", dict(PROV, divergence="the 0.28 reading admitted for t0"))
    assert why and "no diverges_from task is given" in why, why
    why2 = _refused(p, "t1", dict(PROV, diverges_from="t0"))             # divergence is still "none"
    assert why2 and "one or the other" in why2, why2


def test_rp07_diverges_from_must_name_a_task_with_a_receipt_in_this_ledger():
    p = _ledger(); _reviewed(p, "t1")
    why = _refused(p, "t1", dict(PROV, divergence="a reading nobody recorded here", diverges_from="ghost"))
    assert why and "no receipt in this ledger" in why and "'ghost'" in why, why
    assert R.verify(p)["count"] == len(DELIVERY)


# ---- verify replays the rule on the record as read

def test_rp09_verify_replays_the_rule_on_a_forged_admission_and_names_only_that():
    p = _ledger(); _reviewed(p, "t1")
    R._chain(p, {"kind": "receipt", "task_id": "t1", "status": "admitted", "body": {"summary": "x"}})   # forged, chained
    v = R.verify(p)
    assert not v["ok"] and len(v["problems"]) == 1, v
    assert "admitted without intent provenance" in v["problems"][0] and "missing provenance field: intent" in v["problems"][0], v


def test_rp10_a_chain_with_no_admission_gains_no_problem():
    p = _ledger()
    for st in ("requested", "received", "started"):
        R.append_receipt(p, "t3", st, {})
    v = R.verify(p)
    assert v["ok"] and v["problems"] == [], v


# ---- the reader: verbatim fields and a satisfiability line

def test_rp11_intent_check_returns_the_fields_verbatim_and_satisfiable():
    p = _ledger(); _reviewed(p, "t1")
    body = {"intent": "  Lets a LATER verifier   recompute this digest.", "beneficiary": "the reviewer of run t1",
            "divergence": "none", "digest": "ab" * 32}
    R.append_receipt(p, "t1", "admitted", body)
    out = R.intent_check(p, "t1")
    assert all(out[k] == body[k] for k in R.PROVENANCE_FIELDS) and out["diverges_from"] is None, out
    assert out["satisfiable"] is True and out["assessment"].startswith("SATISFIABLE"), out


def test_rp12_intent_check_is_unsatisfiable_for_no_admission_a_forged_admission_and_a_broken_chain():
    p = _ledger(); _reviewed(p, "t1")
    a = R.intent_check(p, "t9")
    assert a["satisfiable"] is False and "no admission receipt" in a["assessment"], a
    R._chain(p, {"kind": "receipt", "task_id": "t1", "status": "admitted", "body": {"summary": "x"}})
    b = R.intent_check(p, "t1")
    assert b["satisfiable"] is False and b["intent"] is None, b
    assert "does not verify" in b["assessment"] and "missing provenance field: intent" in b["assessment"], b
    q = _ledger(); _reviewed(q, "t2"); R.append_receipt(q, "t2", "admitted", dict(PROV))
    assert R.intent_check(q, "t2")["satisfiable"] is True
    rows = _rows(q); del rows[2]                                          # cut a middle row: the chain breaks
    _rewrite(q, rows)
    c = R.intent_check(q, "t2")
    assert c["satisfiable"] is False and "does not verify" in c["assessment"], c
    assert c["intent"] == PROV["intent"], "the fields are still returned verbatim, the flag says the state"


# ---- the boundary: machine records need no provenance, and still cannot write receipts

def test_rp13_machine_records_need_no_provenance_and_still_cannot_write_receipts():
    p = _ledger()
    row = R.append_event(p, {"kind": "action", "task_id": "t1", "outcome": "allowed"})
    assert row["kind"] == "action" and "intent" not in row and R.verify(p)["ok"], row
    try:
        R.append_event(p, {"kind": "receipt", "task_id": "t1", "status": "admitted", "body": dict(PROV)})
        raise AssertionError("append_event wrote a receipt")
    except ValueError as e:
        assert "append_receipt" in str(e), e


def _main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    p = 0
    for fn in fns:
        try:
            fn(); print("PASS", fn.__name__); p += 1
        except Exception:
            print("FAIL", fn.__name__); traceback.print_exc()
    for d in _dirs:
        shutil.rmtree(d, ignore_errors=True)
    print("RP: %d/%d passed" % (p, len(fns)))
    return 0 if p == len(fns) else 1


if __name__ == "__main__":
    sys.exit(_main())
