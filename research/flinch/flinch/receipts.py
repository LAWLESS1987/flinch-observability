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

INTENT PROVENANCE ON ADMISSION (2026-11-18, ported from the covenant AI-memory store and the spiking plasticity
ledger). Of every record here, one is an authored judgment that steers what happens next: the "admitted"
receipt, by which a reviewer lets a task's output into the record. It must now say WHY. Its body carries three
required fields -- intent (one line: what admitting this is meant to CAUSE, not a restatement of what was
admitted), beneficiary (who or what it is for; "future unknown agent" is valid) and divergence (the prior claim
or value this admission conflicts with, or the literal "none"; when not "none", diverges_from names a task with
a receipt in this ledger, so the conflict chain is traversable). append_receipt refuses an admission without
them, under the same lock as its status check; verify() replays the rule on the record as read; intent_check()
returns the fields verbatim with one line on whether the intent is still satisfiable. The other records are
untouched: requested..reviewed receipts are delivery steps and append_event rows are machine outcomes --
neither has an author with an intent to state, and a field invented for them would be ceremony. What the
screen cannot see: it checks emptiness and surface restatement, never truth; a well-formed intent can still be
dishonest. No backfill: the chain is append-only by construction, so an earlier admission cannot be given
fields later. Measured 2026-11-18: no ledger in this repository held an admitted row, so there was nothing to
tombstone, and verify() reads any admitted row without the fields as a problem.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import time

from . import schema as S

GENESIS = "0" * 64

# --- intent provenance on admission (2026-11-18): the fields, the screen ---
PROVENANCE_FIELDS = ("intent", "beneficiary", "divergence")
DIVERGENCE_NONE = "none"
_PWORD = re.compile(r"[a-z0-9]+")


def _norm_tokens(s):
    return _PWORD.findall(str(s).lower())


def _intent_restates(intent, payload):
    """True iff `intent` reads as a restatement of `payload` rather than a statement of purpose. SURFACE ONLY, and
    that limit is the point: this is not a grammar or mood parser. It catches two shapes a human reviewer would
    also call a restatement -- the normalized intent appearing verbatim inside the payload, and the intent being
    almost entirely the payload's own words -- and nothing subtler. (The rule as covenant's memory_store.py has it.)"""
    it = _norm_tokens(intent)
    if not it:
        return False
    iset, pset = set(it), set(_norm_tokens(payload))
    ni, npl = " ".join(it), " ".join(_norm_tokens(payload))
    if ni and ni in npl:                                             # intent is literally a span of the payload
        return True
    if len(iset) < 3:                                                # too short to judge by overlap
        return False
    return len(iset & pset) / len(iset) >= 0.8                       # ~all of intent's words are the payload's


def admission_provenance_reason(body, known_task_ids):
    """Why an admission body's provenance is malformed, or None when it is well-formed.

    `known_task_ids` are the tasks with a receipt in this ledger, for the diverges_from cross-link. Pure: the
    writer calls it under its lock and raises on any non-None answer; verify() calls it on the record as read."""
    if not isinstance(body, dict):
        return "an admission body must be a dict carrying intent, beneficiary and divergence"
    for k in PROVENANCE_FIELDS:
        v = body.get(k)
        if not str(v or "").strip():
            return "missing provenance field: %s is required and may not be empty" % k
        if any(c in str(v) for c in "\r\n\x00"):
            return "provenance field %r must be a single line (no newlines or NULs)" % k
    payload = S.canonical({k: v for k, v in body.items() if k not in PROVENANCE_FIELDS + ("diverges_from",)})
    if _intent_restates(body["intent"], payload):
        return ("intent restates the admitted content instead of stating its purpose; say what admitting this "
                "is meant to CAUSE, not what it says")
    dv, df = str(body["divergence"]).strip().lower(), str(body.get("diverges_from") or "").strip()
    if dv == DIVERGENCE_NONE:
        if df:
            return "divergence is 'none' but diverges_from names a task; one or the other"
    else:
        if not df:
            return ("divergence is not 'none' but no diverges_from task is given; name the task this admission "
                    "conflicts with so the chain is traversable")
        if df not in known_task_ids:
            return "diverges_from names a task with no receipt in this ledger: %r" % df
    return None


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
        rows = _rows(path)
        mine = [r for r in rows if r.get("kind") == "receipt" and r.get("task_id") == task_id]
        if mine:
            last = S.STATUSES.index(mine[-1]["status"])
            if S.STATUSES.index(status) < last:
                raise ValueError("task %s is already %s; a status never moves back to %s" % (task_id, mine[-1]["status"], status))
        if status == "admitted" and not any(r["status"] == "reviewed" for r in mine):
            raise ValueError("task %s cannot be admitted before it is reviewed" % task_id)
        if status == "admitted":                                     # the authored judgment says why (2026-11-18)
            known = {r.get("task_id") for r in rows if r.get("kind") == "receipt"}
            why = admission_provenance_reason(body, known)
            if why:
                raise ValueError("task %s cannot be admitted without intent provenance: %s" % (task_id, why))
        return _chain_unlocked(path, {"kind": "receipt", "task_id": task_id, "status": status, "body": body})


def verify(path, anchor=None):
    """{"ok", "problems", "count", "head", "anchored"}. anchor = {"seq": n, "hash": h}, kept somewhere else.

    An anchor protects rows 0..n only: rows after it can be cut or rewritten undetected until a newer anchor is
    taken. "anchored" says exactly that, every time (review finding 6)."""
    rows, problems, prev = _rows(path), [], GENESIS
    status, tasks = {}, set()
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
            tasks.add(r.get("task_id"))
            if st == "admitted":                                     # intent provenance, replayed the same way
                why = admission_provenance_reason(r.get("body"), tasks)
                if why:
                    problems.append("row %d: task %s admitted without intent provenance: %s" % (i, r.get("task_id"), why))
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


def intent_check(path, task_id):
    """Reader side, for any agent: the admission's intent, beneficiary, divergence and diverges_from VERBATIM -- no
    rewriting, no summary -- plus `satisfiable` and one line saying why, judged on the ledger as it stands now.
    UNSATISFIABLE when there is no admission for the task, when the chain does not verify, when the fields are
    missing or malformed (an admission that predates or evaded the rule), or when diverges_from names a task with
    no receipt here. Read-only: it never writes to the ledger."""
    rows = _rows(path)
    out = {"task_id": task_id, "intent": None, "beneficiary": None, "divergence": None, "diverges_from": None,
           "satisfiable": False, "assessment": ""}
    adm = [r for r in rows if r.get("kind") == "receipt" and r.get("task_id") == task_id and r.get("status") == "admitted"]
    if not adm:
        out["assessment"] = "UNSATISFIABLE: no admission receipt for task %r in this ledger" % task_id
        return out
    row = adm[-1]
    body = row.get("body") if isinstance(row.get("body"), dict) else {}
    for k in PROVENANCE_FIELDS + ("diverges_from",):
        out[k] = body.get(k)
    v = verify(path)
    if not v["ok"]:
        out["assessment"] = "UNSATISFIABLE: the chain does not verify (%s)" % v["problems"][0]
        return out
    known = {r.get("task_id") for r in rows if r.get("kind") == "receipt"}
    why = admission_provenance_reason(body, known)
    if why:
        out["assessment"] = "UNSATISFIABLE: %s" % why
        return out
    out["satisfiable"] = True
    none = str(out["divergence"]).strip().lower() == DIVERGENCE_NONE
    out["assessment"] = "SATISFIABLE: admitted at %s (row %s); the chain verifies (unanchored: see verify()); divergence %s%s" % (
        row.get("at"), row.get("seq"), out["divergence"], "" if none else " from task %r" % out["diverges_from"])
    return out
