#!/usr/bin/env python3
"""RP (2026-11-18): intent provenance on the admission receipt, driven both ways.

The "admitted" receipt is the one record in receipts.py that is an authored judgment steering what happens next:
a reviewer lets a task's output into the record. Since 2026-11-18 its body must say why -- intent, beneficiary,
divergence, and diverges_from when the divergence is not "none" -- or append_receipt refuses it; verify() replays
the rule on the record as read; intent_check() returns the fields verbatim with a line saying what was checked.

RP01-RP13 shipped with the rule. RP14-RP23 came from the consult of the same day (covenant,
ops/CONSULT_INTENT_PROVENANCE_FLINCH_2026-11-18.md): six seats, every shown input reproduced by probe against
d343281 before the rule was tightened. Each is the input that got in, or the honest input that was refused.

Every check here is driven both ways and every refusal is asserted by ITS reason, so no check passes on a
neighbour's guard (the mutation-run convention of test_flinch.py). The fixtures are synthetic.

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


def test_rp08_a_declared_divergence_cross_links_to_an_earlier_admission_and_is_traversable():
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


def test_rp07_diverges_from_must_name_a_task_with_an_earlier_admission_in_this_ledger():
    p = _ledger(); _reviewed(p, "t1")
    why = _refused(p, "t1", dict(PROV, divergence="a reading nobody recorded here", diverges_from="ghost"))
    assert why and "no earlier admitted receipt" in why and "'ghost'" in why, why
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


# ---- the reader: verbatim fields and a line that says what was checked

def test_rp11_intent_check_returns_the_fields_verbatim_and_says_well_formed():
    p = _ledger(); _reviewed(p, "t1")
    body = {"intent": "  Lets a LATER verifier   recompute this digest.", "beneficiary": "the reviewer of run t1",
            "divergence": "none", "digest": "ab" * 32}
    R.append_receipt(p, "t1", "admitted", body)
    out = R.intent_check(p, "t1")
    assert all(out[k] == body[k] for k in R.PROVENANCE_FIELDS) and out["diverges_from"] is None, out
    assert out["satisfiable"] is True and out["assessment"].startswith("WELL-FORMED"), out
    assert "does not judge whether the stated purpose can be met" in out["assessment"] and out["contested_by"] == [], out


def test_rp12_intent_check_is_not_well_formed_for_no_admission_a_forged_admission_and_a_broken_chain():
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


# ---- from the consult: the inputs that got in, and the honest ones that were refused

def test_rp14_a_non_string_field_is_refused_by_type():
    p = _ledger(); _reviewed(p, "t1")
    for k, v in (("intent", 123), ("beneficiary", True), ("intent", ["x"]), ("divergence", 0.5)):
        why = _refused(p, "t1", dict(PROV, **{k: v}))
        assert why and "must be a string" in why and ("'%s'" % k) in why, (k, v, why)
    why = _refused(p, "t1", dict(PROV, divergence="the earlier reading", diverges_from=7))
    assert why and "diverges_from must be a string" in why, why
    assert R.verify(p)["count"] == len(DELIVERY)


def test_rp15_a_field_without_a_word_is_refused_and_unicode_words_count():
    p = _ledger(); _reviewed(p, "t1")
    for bad in ("...", "???", "​", "​ ​"):
        why = _refused(p, "t1", dict(PROV, intent=bad))
        assert why and ("must contain at least one word" in why or "may not be empty" in why), (repr(bad), why)
    why = _refused(p, "t1", dict(PROV, beneficiary="​"))
    assert why and "'beneficiary'" in why, why
    assert _refused(p, "t1", dict(PROV, intent="目的を果たすために記録する", summary="scoring")) is None, "CJK words refused"
    q = _ledger(); _reviewed(q, "t1")
    why = _refused(q, "t1", dict(PROV, intent="目的を果たす", summary="目的を果たす"))             # identical to the payload
    assert why and "restates the admitted content" in why, why


def test_rp16_every_line_separator_counts_as_a_second_line():
    p = _ledger(); _reviewed(p, "t1")
    for sep in (" ", " ", "\r", "\x85"):
        why = _refused(p, "t1", dict(PROV, intent="Lets the next study" + sep + "cite this."))
        assert why and "must be a single line" in why, (repr(sep), why)


def test_rp17_divergence_none_tolerates_case_and_trailing_punctuation():
    p = _ledger(); _reviewed(p, "t1")
    assert _refused(p, "t1", dict(PROV, divergence="None.")) is None, "'None.' was not read as none"
    q = _ledger(); _reviewed(q, "t0"); R.append_receipt(q, "t0", "admitted", dict(PROV)); _reviewed(q, "t1")
    why = _refused(q, "t1", dict(PROV, divergence="NONE ", diverges_from="t0"))
    assert why and "one or the other" in why, why


def test_rp18_the_span_test_matches_on_token_boundaries():
    p = _ledger(); _reviewed(p, "t1")
    assert _refused(p, "t1", dict(PROV, intent="stop drift", nonstop="drifting")) is None, "refused across a word boundary"
    q = _ledger(); _reviewed(q, "t1")
    assert _refused(q, "t1", dict(PROV, intent="cause review", note="because reviewed")) is None, "refused inside a word"
    r = _ledger(); _reviewed(r, "t1")
    why = _refused(r, "t1", dict(PROV, intent="ship it", note="we will ship it friday"))   # a real span: still refused
    assert why and "restates the admitted content" in why, why


def test_rp19_a_task_cannot_diverge_from_itself():
    p = _ledger(); _reviewed(p, "t1")
    why = _refused(p, "t1", dict(PROV, divergence="the earlier reading", diverges_from="t1"))
    assert why and "same task" in why, why


def test_rp20_diverges_from_needs_an_earlier_admission_not_merely_a_receipt():
    p = _ledger(); R.append_receipt(p, "u", "requested", {}); _reviewed(p, "t1")
    why = _refused(p, "t1", dict(PROV, divergence="the earlier reading", diverges_from="u"))
    assert why and "no earlier admitted receipt" in why and "'u'" in why, why
    _reviewed(p, "u"); R.append_receipt(p, "u", "admitted", dict(PROV))
    assert _refused(p, "t1", dict(PROV, divergence="the earlier reading", diverges_from="u")) is None
    assert R.verify(p)["ok"]


def test_rp21_one_admission_per_task_at_write_and_in_replay():
    p = _ledger(); _reviewed(p, "t1"); R.append_receipt(p, "t1", "admitted", dict(PROV, reading=0.28))
    why = _refused(p, "t1", dict(PROV, intent="Replaces the first admission quietly.", reading=0.31))
    assert why and "already admitted" in why, why
    assert R.intent_check(p, "t1")["intent"] == PROV["intent"]
    R._chain(p, {"kind": "receipt", "task_id": "t1", "status": "admitted", "body": dict(PROV, reading=0.31)})   # forged second
    v = R.verify(p)
    assert not v["ok"] and any("admitted a second time" in x for x in v["problems"]), v
    assert R.intent_check(p, "t1")["intent"] == PROV["intent"], "the reader followed the forged second admission"


def test_rp22_intent_check_names_the_tasks_that_contest_this_admission():
    p = _ledger()
    _reviewed(p, "T1"); R.append_receipt(p, "T1", "admitted", dict(PROV, reading=0.28))
    assert R.intent_check(p, "T1")["contested_by"] == [] and "uncontested" in R.intent_check(p, "T1")["assessment"]
    _reviewed(p, "T2"); R.append_receipt(p, "T2", "admitted", dict(PROV, intent="Replaces the T1 reading so later runs use 0.31.",
                                                                     divergence="supersedes T1", diverges_from="T1", reading=0.31))
    out = R.intent_check(p, "T1")
    assert out["contested_by"] == ["T2"] and "contested by ['T2']" in out["assessment"], out
    assert out["satisfiable"] is True, "a contested admission is still well-formed; the flag is not a truth judgment"


def test_rp23_intent_check_reads_the_ledger_once():
    p = _ledger(); _reviewed(p, "t1"); R.append_receipt(p, "t1", "admitted", dict(PROV))
    orig, calls = R._rows, []
    def counting(path):
        calls.append(path); return orig(path)
    R._rows = counting
    try:
        out = R.intent_check(p, "t1")
    finally:
        R._rows = orig
    assert len(calls) == 1 and out["satisfiable"] is True, (calls, out)


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
