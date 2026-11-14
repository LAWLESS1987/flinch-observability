#!/usr/bin/env python3
"""K11 (review of 2026-11-14): two places where a record could be empty or missing.

prereg.freeze: `freeze(dict.fromkeys(REQUIRED, None))` was accepted and froze an empty protocol, because the
completeness test turned each value into a string and str(None) is "None". A required value that is null, an
empty or whitespace-only string, an empty container, or plainly the wrong type is now refused before hashing,
and the error names the fields.

gate.Broker.act: on an explicit allow, run(params) was called before any durable record of the action existed;
if writing the record then failed, the side effect had happened unrecorded. An "approved" row is now written
first. If that write fails the action is not run and the answer is a refusal. The "done" or "failed" row
follows as before.

    python test_k11_prereg_gate.py   -> "K11: n/n passed"
"""
from __future__ import annotations
import json, os, shutil, sys, tempfile, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from flinch import gate as G           # noqa: E402
from flinch import prereg as PR        # noqa: E402
from flinch import receipts as R       # noqa: E402
from flinch import schema as S         # noqa: E402

_dirs = []
HEX = "ab" * 32                        # a placeholder sha256, not a real manifest


def _tmp():
    d = tempfile.mkdtemp(prefix="k11_"); _dirs.append(d); return d


def _full():
    pre = {k: "decided" for k in PR.REQUIRED}
    pre.update(eligible_corpus_manifest_sha256=HEX, rubric_version="r1", detector_version="some-detector-1.0")
    return pre


def _refused(prereg):
    """The error text when freeze refuses, or None when it accepts."""
    try:
        PR.freeze(prereg)
    except ValueError as e:
        return str(e)
    return None


# ---------------------------------------------------------------- prereg.freeze
def test_prereg_all_null_is_refused_and_every_field_is_named():
    msg = _refused(dict.fromkeys(PR.REQUIRED, None))
    assert msg is not None, "freeze accepted a pre-registration whose every required value is null"
    absent = [k for k in PR.REQUIRED if k not in msg]
    assert not absent, "the error does not name: %s" % absent


def test_prereg_one_null_field_is_named_alone():
    msg = _refused(dict(_full(), primary_outcome=None))
    assert msg is not None, "freeze accepted a null primary_outcome"
    assert "primary_outcome" in msg and "success_criterion" not in msg, msg


def test_prereg_empty_and_whitespace_values_are_refused():
    for label, bad in (("empty string", ""), ("spaces", "   "), ("tab and newline", "\t\n"), ("empty list", []),
                       ("empty dict", {}), ("a list of blanks", ["", None, "  "]), ("a dict of blanks", {"a": None})):
        msg = _refused(dict(_full(), exclusion_criteria=bad))
        assert msg is not None, "freeze accepted exclusion_criteria = %s" % label
        assert "exclusion_criteria" in msg, (label, msg)


def test_prereg_wrong_type_is_refused_where_the_meaning_fixes_the_type():
    for field, bad in (("eligible_corpus_manifest_sha256", "not-a-hash"), ("eligible_corpus_manifest_sha256", 12345),
                       ("eligible_corpus_manifest_sha256", HEX.upper()), ("detector_version", 7),
                       ("detector_version", ["some-detector-1.0"])):
        msg = _refused(dict(_full(), **{field: bad}))
        assert msg is not None, "freeze accepted %s = %r" % (field, bad)
        assert field in msg, (field, msg)


def test_prereg_full_one_still_freezes_with_the_same_hash():
    pre = dict(_full(), agreement_threshold=0.7, control_conditions=["A", "B"], planned_subgroup_analyses={"by": "route"})
    fz = PR.freeze(pre)
    assert fz["prereg_sha256"] == S.sha256_obj(pre), "the hash is no longer taken over the body as given"
    assert {k: v for k, v in fz.items() if k not in ("frozen_at", "prereg_sha256")} == pre


# ---------------------------------------------------------------- gate.Broker.act
REG = [{"name": "write_report", "version": "1", "side_effect": "file write", "network": False, "scope": "reports/",
        "reversible": True, "decision_class": "covenant", "approval_class": "none", "logging": "receipt"}]
ALLOW = lambda p: ("allow", "ok")                                     # noqa: E731


def _rows(path):
    return R._rows(path) if os.path.isfile(path) else []


def test_gate_approval_is_on_the_ledger_before_the_action_runs():
    led = os.path.join(_tmp(), "actions.jsonl")
    seen = []
    out = G.Broker(REG, judge=ALLOW, ledger=led).act("t", "write_report", {"a": 1}, lambda p: seen.append(_rows(led)) or "w")
    assert out[0] == "done" and out[2] == "w", out
    during = seen[0]
    assert during, "the action ran while the ledger held no record of it"
    last = during[-1]
    assert last["outcome"] == "approved" and last["action"] == "write_report" and last["task_id"] == "t", last
    assert last["params_sha256"] == S.sha256_obj({"a": 1}), "the approval does not name the request approved"
    after = _rows(led)
    assert [r["outcome"] for r in after] == ["approved", "done"], [r["outcome"] for r in after]
    assert R.verify(led)["ok"], R.verify(led)["problems"]


def test_gate_does_not_run_when_the_approval_cannot_be_recorded():
    d = _tmp()
    blocker = os.path.join(d, "not_a_folder")
    open(blocker, "w").close()
    led = os.path.join(blocker, "actions.jsonl")                      # its parent is a file: every write fails
    ran = []
    try:
        out = G.Broker(REG, judge=ALLOW, ledger=led).act("t", "write_report", {"a": 1}, lambda p: ran.append(p) or "w")
    except Exception as e:                                            # noqa: BLE001
        out = ("raised", "%s: %s" % (type(e).__name__, e), None)
    assert not ran, "the action ran although no record of it could be written (act gave %r)" % (out[:2],)
    assert out[0] == "refused" and out[2] is None, out
    assert "record" in out[1], out


def test_gate_keeps_the_approval_when_the_done_row_cannot_be_written():
    led = os.path.join(_tmp(), "actions.jsonl")
    ran = []
    real = R.append_event

    def failing(path, record):
        if record.get("outcome") == "done":
            raise OSError("disk full (simulated)")
        return real(path, record)
    R.append_event = failing
    try:
        try:
            G.Broker(REG, judge=ALLOW, ledger=led).act("t", "write_report", {"a": 1}, lambda p: ran.append(p) or "w")
            raised = False
        except OSError:
            raised = True
    finally:
        R.append_event = real
    assert ran == [{"a": 1}] and raised, (ran, raised)                # as before: the failure is not swallowed
    rows = _rows(led)
    assert rows and rows[-1]["outcome"] == "approved" and rows[-1]["params_sha256"] == S.sha256_obj({"a": 1}), \
        "the side effect happened and the ledger holds no record of it: %r" % rows


def test_gate_failed_action_reads_approved_then_failed():
    led = os.path.join(_tmp(), "actions.jsonl")

    def boom(_p):
        raise RuntimeError("no space")
    out = G.Broker(REG, judge=ALLOW, ledger=led).act("t", "write_report", {}, boom)
    assert out[0] == "failed", out
    assert [r["outcome"] for r in _rows(led)] == ["approved", "failed"], _rows(led)


def test_gate_rows_keep_their_fields_and_only_an_allow_adds_one():
    led = os.path.join(_tmp(), "actions.jsonl")
    ran = []
    run = lambda p: ran.append(p) or "w"                              # noqa: E731
    G.Broker(REG, judge=None, ledger=led).act("t", "write_report", {}, run)                       # hold
    G.Broker(REG, judge=lambda p: ("deny", "no"), ledger=led).act("t", "write_report", {}, run)   # deny
    G.Broker(REG, judge=ALLOW, ledger=led).act("t", "delete_everything", {}, run)                 # refused
    G.Broker(REG, judge=ALLOW, ledger=led).act("t", "write_report", {"a": 1}, run)                # approved, done
    rows = [json.loads(l) for l in open(led, encoding="utf-8")]
    assert [r["outcome"] for r in rows] == ["hold", "deny", "refused", "approved", "done"], [r["outcome"] for r in rows]
    assert ran == [{"a": 1}], ran
    old = {"kind", "task_id", "action", "outcome", "why", "egress", "params_sha256", "seq", "prev", "at", "hash"}
    for r in rows:                                                    # every field an existing reader uses is there
        assert old <= set(r) and r["kind"] == "action" and S.is_hex64(r["params_sha256"]), r
    assert set(rows[3]) == old, "the approved row carries a field the other rows do not: %s" % sorted(set(rows[3]) - old)
    assert S.is_hex64(rows[4]["result_sha256"]), rows[4]
    assert R.verify(led)["ok"] and R.verify(led)["count"] == 5, R.verify(led)


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
    print("K11: %d/%d passed" % (p, len(fns)))
    return 0 if p == len(fns) else 1


if __name__ == "__main__":
    sys.exit(_main())
