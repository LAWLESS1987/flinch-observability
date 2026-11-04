"""receipts.py -- append-only, hash-chained records for runs and actions (spec 12, 13.6).

A hash chain shows record INTEGRITY, never the truth of what a record says (spec 12).

ITS LIMIT, measured in this collective's own review of covenant (issue #4, finding F1): a writer who alters a
middle record and recomputes every later hash produces a chain that verifies. Only a head hash kept somewhere
else -- an ANCHOR -- detects that rewrite. verify() takes an optional anchor and reports, every time, whether
one was checked; a result without one says "unanchored", so a reader never mistakes internal consistency for
protection against a rewrite.

Two kinds of ledger share the chain:
  append_receipt -- a study/run receipt with a status from requested < received < started < produced <
                    reviewed < admitted. A task's status never moves backward, and "admitted" needs a
                    "reviewed" receipt first (the collective's distinction between delivery and admission).
  append_event   -- any other record (the action ledger of gate.py), chained the same way.
Nothing here edits or deletes a line. A rejected append writes nothing and raises.

CONCURRENCY (C / Codex #10.3, 2026-11-04): _chain read the head (_rows) and then appended with NO lock
spanning those two steps, and append_receipt validated the task's status outside it too. Two concurrent
writers could read the same head and chain off it -- a reproduction lost an event while verify() still
passed on the surviving one-row chain. Every write now takes an exclusive, cross-process lock spanning
read-head -> validate -> append, and fsyncs, so concurrent writers serialize and nothing is lost or forked.
"""
from __future__ import annotations

import contextlib
import json
import os
import time

from . import schema as S

GENESIS = "0" * 64


# --- an exclusive, cross-process lock (held on a sidecar <path>.lock, auto-released on process exit) ---
try:
    import fcntl

    def _plat_lock(fh):
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)

    def _plat_unlock(fh):
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
except ImportError:                                              # Windows
    import msvcrt

    def _plat_lock(fh):
        fh.seek(0)
        while True:
            try:
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                time.sleep(0.01)

    def _plat_unlock(fh):
        fh.seek(0)
        try:
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass


@contextlib.contextmanager
def _lock(path):
    """Exclusive, cross-process lock spanning read-head -> compute -> append (C / Codex #10.3). Held on a
    sidecar <path>.lock and released when the context exits (or the process does, so a crash leaves no stale
    lock). Serializes every writer to this ledger."""
    lockpath = path + ".lock"
    d = os.path.dirname(os.path.abspath(lockpath))
    if d:
        os.makedirs(d, exist_ok=True)
    fh = open(lockpath, "a+")
    try:
        _plat_lock(fh)
        yield
    finally:
        try:
            _plat_unlock(fh)
        finally:
            fh.close()


def _rows(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def _chain_unlocked(path, record):
    """Read the head, compute seq/prev/hash, append, fsync. The caller MUST hold _lock(path) -- this reads the
    head and appends, and the two must not be split by another writer."""
    rows = _rows(path)
    row = dict(record, seq=len(rows), prev=rows[-1]["hash"] if rows else GENESIS, at=record.get("at") or S.now_iso())
    row["hash"] = S.sha256_obj({k: v for k, v in row.items() if k != "hash"})
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(S.canonical(row) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return row


def _chain(path, record):
    with _lock(path):
        return _chain_unlocked(path, record)


def append_event(path, record):
    if record.get("kind") == "receipt":                          # review finding 6: only append_receipt writes receipts
        raise ValueError("a receipt is written by append_receipt, which enforces its status rules")
    return _chain(path, dict(record, kind=record.get("kind", "event")))


def append_receipt(path, task_id, status, body):
    if status not in S.STATUSES:
        raise ValueError("status %r is not one of %s" % (status, S.STATUSES))
    # The status check reads this task's prior receipts; it and the append share ONE lock so a concurrent
    # writer cannot slip a backward status in between (C / Codex #10.3).
    with _lock(path):
        mine = [r for r in _rows(path) if r.get("kind") == "receipt" and r.get("task_id") == task_id]
        if mine:
            last = S.STATUSES.index(mine[-1]["status"])
            if S.STATUSES.index(status) < last:
                raise ValueError("task %s is already %s; a status never moves back to %s" % (task_id, mine[-1]["status"], status))
        if status == "admitted" and not any(r["status"] == "reviewed" for r in mine):
            raise ValueError("task %s cannot be admitted before it is reviewed" % task_id)
        return _chain_unlocked(path, {"kind": "receipt", "task_id": task_id, "status": status, "body": body})


def verify(path, anchor=None):
    """{"ok", "problems", "count", "head", "anchored"}. anchor = {"seq": n, "hash": h}, kept somewhere else.

    An anchor protects rows 0..n only: rows after it can be cut or rewritten undetected until a newer anchor is
    taken. "anchored" says exactly that, every time (review finding 6)."""
    rows, problems, prev = _rows(path), [], GENESIS
    status = {}
    for i, r in enumerate(rows):
        want = S.sha256_obj({k: v for k, v in r.items() if k != "hash"})
        if r.get("hash") != want:
            problems.append("row %d: its hash does not match its content (altered)" % i)
        if r.get("prev") != prev:
            problems.append("row %d: prev does not name row %d's hash (removed, reordered or spliced)" % (i, i - 1))
        if r.get("seq") != i:
            problems.append("row %d: seq is %r" % (i, r.get("seq")))
        if r.get("kind") == "receipt":                           # the status rules, replayed on the record as read
            st, seen = r.get("status"), status.setdefault(r.get("task_id"), [])
            if st not in S.STATUSES:
                problems.append("row %d: status %r" % (i, st))
            elif seen and S.STATUSES.index(st) < S.STATUSES.index(seen[-1]):
                problems.append("row %d: task %s moves back from %s to %s" % (i, r.get("task_id"), seen[-1], st))
            elif st == "admitted" and "reviewed" not in seen:
                problems.append("row %d: task %s admitted before it was reviewed" % (i, r.get("task_id")))
            if st in S.STATUSES:
                seen.append(st)
        prev = r.get("hash")
    if anchor is None:
        anchored = "unanchored: a full rewrite from the altered row on would verify"
    else:
        n = anchor.get("seq")
        if isinstance(n, int) and 0 <= n < len(rows) and rows[n].get("hash") == anchor.get("hash"):
            anchored = "anchored through row %d; %d later row(s) unprotected" % (n, len(rows) - n - 1)
        else:
            anchored = False
            problems.append("the anchor (row %r, %s) does not match: the chain was rewritten or cut" % (n, str(anchor.get("hash"))[:16]))
    return {"ok": not problems, "problems": problems, "count": len(rows), "head": prev if rows else GENESIS,
            "anchored": anchored}


def anchor(path):
    """The head to keep elsewhere (another machine, a signed note, a public commit) before relying on the chain."""
    rows = _rows(path)
    return {"seq": len(rows) - 1, "hash": rows[-1]["hash"]} if rows else None
