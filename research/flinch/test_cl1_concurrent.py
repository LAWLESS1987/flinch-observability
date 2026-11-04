#!/usr/bin/env python3
"""CL1 (C / Codex #10.3, 2026-11-04): concurrent appends to a receipts/event chain lose no events and do not
fork the chain. _chain read the head and appended with no lock between; two writers chained off the same head
(a reproduction lost an event while verify() still passed on the one-row survivor). With the lock, N concurrent
appends yield N rows with unique contiguous seqs that verify(); concurrent receipts for one task stay monotonic.

    python test_cl1_concurrent.py   -> "CL1: n/n passed"
"""
from __future__ import annotations
import os, sys, tempfile, shutil, threading, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from flinch import receipts as R       # noqa: E402
from flinch import schema as S         # noqa: E402

_dirs = []
def _path():
    d = tempfile.mkdtemp(prefix="cl1_"); _dirs.append(d); return os.path.join(d, "ledger.jsonl")


def test_concurrent_events_no_loss_no_fork():
    path = _path()
    N = 24
    barrier = threading.Barrier(N)
    errs = []
    def worker(i):
        try:
            barrier.wait()
            R.append_event(path, {"i": i})
        except Exception as e:                                   # noqa: BLE001
            errs.append(repr(e))
    ts = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
    for t in ts: t.start()
    for t in ts: t.join()
    assert not errs, errs
    rows = R._rows(path)
    assert len(rows) == N, "lost events: %d of %d" % (len(rows), N)
    assert sorted(r["seq"] for r in rows) == list(range(N)), "seqs not unique/contiguous"
    res = R.verify(path)
    assert res["ok"], res["problems"]


def test_concurrent_receipts_stay_monotonic():
    path = _path()
    order = list(S.STATUSES)
    barrier = threading.Barrier(len(order))
    def worker(status):
        barrier.wait()
        try:
            R.append_receipt(path, "t1", status, {})
        except ValueError:
            pass                                                 # a backward/early status is correctly rejected
    ts = [threading.Thread(target=worker, args=(s,)) for s in order]
    for t in ts: t.start()
    for t in ts: t.join()
    assert R.verify(path)["ok"], R.verify(path)["problems"]
    idxs = [order.index(r["status"]) for r in R._rows(path) if r.get("kind") == "receipt"]
    assert idxs == sorted(idxs), "receipt statuses are not monotonic on disk: %s" % idxs


def test_single_append_and_verify():
    path = _path()
    R.append_event(path, {"x": 1})
    R.append_receipt(path, "tA", "requested", {})
    assert R.verify(path)["ok"]
    assert len(R._rows(path)) == 2


def test_lock_is_exclusive():
    # one holder blocks a second acquisition until released -- proves the lock serializes, without relying on
    # the race manifesting
    path = _path()
    open(path, "w").close()
    order = []
    rel = threading.Event()
    def holder():
        with R._lock(path):
            order.append("h-in")
            rel.wait(2)
            order.append("h-out")
    def waiter():
        with R._lock(path):
            order.append("w-in")
    h = threading.Thread(target=holder); h.start()
    while "h-in" not in order:
        pass
    w = threading.Thread(target=waiter); w.start()
    import time as _t; _t.sleep(0.2)
    assert order == ["h-in"], "waiter entered while the lock was held: %s" % order
    rel.set()
    h.join(); w.join()
    assert order == ["h-in", "h-out", "w-in"], order


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
    print("CL1: %d/%d passed" % (p, len(fns)))
    return 0 if p == len(fns) else 1


if __name__ == "__main__":
    sys.exit(_main())
