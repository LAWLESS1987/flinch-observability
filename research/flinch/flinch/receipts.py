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

TIGHTENED THE SAME DAY after a nine-seat consult (covenant: ops/CONSULT_INTENT_PROVENANCE_FLINCH_2026-11-18.md),
every shown input reproduced by probe first: each field must be a string with at least one Unicode word and no
line separator of any kind; divergence "none" tolerates case and trailing punctuation; the restatement span test
matches on token boundaries, not inside words; diverges_from must name a DIFFERENT task with an EARLIER admitted
receipt; a task is admitted ONCE (a later claim is a new task that diverges from the old one), replayed by
verify_rows(); intent_check() reads one snapshot under the lock, lists contested_by, and says WELL-FORMED -- never
"satisfiable", which it cannot judge.
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
# Tightened the same day after the consult recorded in covenant's ops/CONSULT_INTENT_PROVENANCE_FLINCH_2026-11-18.md:
# six seats, every shown input reproduced by probe against d343281 before anything here changed.
PROVENANCE_FIELDS = ("intent", "beneficiary", "divergence")
DIVERGENCE_NONE = "none"
_PWORD = re.compile(r"\w+")              # Unicode words: [a-z0-9] saw no words in a CJK intent, so the screen never fired


def _norm_tokens(s):
    return _PWORD.findall(str(s).lower())


def _intent_restates(intent, payload):
    """True iff `intent` reads as a restatement of `payload` rather than a statement of purpose. SURFACE ONLY, and
    that limit is the point: this is not a grammar or mood parser. It catches two shapes a human reviewer would
    also call a restatement -- the normalized intent appearing verbatim inside the payload, and the intent being
    almost entirely the payload's own words -- and nothing subtler. (The rule as covenant's memory_store.py has it,
    with one repair from the consult: the span test matched INSIDE words, so "cause review" was refused against
    "because reviewed" and "stop drift" against {"nonstop": "drifting"}; it now matches on token boundaries.)
    Still refused: a short intent that is literally a span of the payload ("ship it" when the body says "we will
    ship it friday"). Still passing: a restatement padded with unrelated words until the overlap drops under 0.8
    (7 payload words + 3 others). Both are the price of a screen that reads words, not meaning."""
    it = _norm_tokens(intent)
    if not it:
        return False
    iset, pset = set(it), set(_norm_tokens(payload))
    ni, npl = " " + " ".join(it) + " ", " " + " ".join(_norm_tokens(payload)) + " "
    if ni in npl:                                                    # a span of the payload, on token boundaries
        return True
    if len(iset) < 3:                                                # too short to judge by overlap
        return False
    return len(iset & pset) / len(iset) >= 0.8                       # ~all of intent's words are the payload's


def _one_line_words(v):
    """Why a provenance value is malformed, or None. A str; one line, where EVERY line separator counts (U+2028 passed
    a CR/LF test); no NUL; and at least one word under the Unicode tokenizer (a zero-width space, "..." and "???"
    carried no intent and passed an emptiness test that only stripped whitespace)."""
    if not isinstance(v, str):
        return "must be a string, not %s" % type(v).__name__
    if "\x00" in v or len(v.splitlines()) > 1:
        return "must be a single line (no line separators or NULs)"
    if not _norm_tokens(v):
        return "must contain at least one word"
    return None


def _divergence_is_none(dv):
    """'none', case-insensitive, with trailing punctuation or whitespace ignored ("None." demanded a cross-link)."""
    return re.sub(r"[\s.!]+$", "", str(dv).strip().lower()) == DIVERGENCE_NONE


def admission_provenance_reason(body, admitted_task_ids, task_id):
    """Why an admission body's provenance is malformed, or None when it is well-formed.

    `admitted_task_ids` are the tasks with an EARLIER admitted receipt in this ledger -- the only records that carry
    a claim a new admission can diverge from. (Before the consult any receipt counted, so an admission could diverge
    from a task that was merely requested, or from itself.) `task_id` is the task being admitted. Pure: the writer
    calls it under its lock and raises on any non-None answer; verify_rows() calls it on the record as read."""
    if not isinstance(body, dict):
        return "an admission body must be a dict carrying intent, beneficiary and divergence"
    for k in PROVENANCE_FIELDS:
        v = body.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            return "missing provenance field: %s is required and may not be empty" % k
        why = _one_line_words(v)
        if why:
            return "provenance field %r %s" % (k, why)
    payload = S.canonical({k: v for k, v in body.items() if k not in PROVENANCE_FIELDS + ("diverges_from",)})
    if _intent_restates(body["intent"], payload):
        return ("intent restates the admitted content instead of stating its purpose; say what admitting this "
                "is meant to CAUSE, not what it says")
    df = body.get("diverges_from")
    if df is not None and not isinstance(df, str):
        return "diverges_from must be a string task id, not %s" % type(df).__name__
    df = (df or "").strip()
    if _divergence_is_none(body["divergence"]):
        if df:
            return "divergence is 'none' but diverges_from names a task; one or the other"
    else:
        if not df:
            return ("divergence is not 'none' but no diverges_from task is given; name the task this admission "
                    "conflicts with so the chain is traversable")
        if df == task_id:
            return "diverges_from names this same task; a divergence is from an earlier admission of ANOTHER task"
        if df not in admitted_task_ids:
            return "diverges_from names a task with no earlier admitted receipt in this ledger: %r" % df
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
            admitted = {r.get("task_id") for r in rows if r.get("kind") == "receipt" and r.get("status") == "admitted"}
            if task_id in admitted:                                  # consult: a second admission silently shadowed the first
                raise ValueError("task %s is already admitted; one admission per task -- a later claim is a new task "
                                 "that diverges from it" % task_id)
            why = admission_provenance_reason(body, admitted, task_id)
            if why:
                raise ValueError("task %s cannot be admitted without intent provenance: %s" % (task_id, why))
        return _chain_unlocked(path, {"kind": "receipt", "task_id": task_id, "status": status, "body": body})


def verify(path, anchor=None):
    """{"ok", "problems", "count", "head", "anchored"}. anchor = {"seq": n, "hash": h}, kept somewhere else.

    An anchor protects rows 0..n only: rows after it can be cut or rewritten undetected until a newer anchor is
    taken. "anchored" says exactly that, every time (review finding 6)."""
    return verify_rows(_rows(path), anchor)


def verify_rows(rows, anchor=None):
    """verify() over rows already read: ONE snapshot, so a reader that also returns the rows (intent_check) judges
    the same bytes it hands back. The consult found intent_check reading the file once for the fields and again,
    inside verify(), for the verdict; a write landing between the two reads gave fields from one state and a verdict
    from another."""
    problems, prev = [], GENESIS
    status, admitted = {}, set()
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
            if st == "admitted":                                     # intent provenance, replayed the same way
                tid = r.get("task_id")
                if tid in admitted:
                    problems.append("row %d: task %s admitted a second time; one admission per task" % (i, tid))
                why = admission_provenance_reason(r.get("body"), admitted, tid)
                if why:
                    problems.append("row %d: task %s admitted without intent provenance: %s" % (i, tid, why))
                admitted.add(tid)
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
    rewriting, no summary -- plus a flag and one line saying exactly what was checked, on ONE snapshot of the ledger
    (read under the writers' lock, so never a half-written line). Read-only: it never writes to the ledger.

    The flag is `satisfiable`, the name the write-schema spec and the covenant/spiking readers use, and the consult
    of 2026-11-18 was unanimous that the WORD claims more than the check does: it means well-formed fields, links
    that resolve, a chain that verifies (unanchored) -- never that the stated purpose can be met ("Make yesterday
    happen again" reads True). So the assessment line says WELL-FORMED, not satisfiable, and names the limit; the key
    stays until the three repositories rename it together. `contested_by` lists the tasks whose own admission
    diverges from this one, so a superseded claim is visible here instead of only from the other end of the link."""
    with _lock(path):
        rows = _rows(path)
    out = {"task_id": task_id, "intent": None, "beneficiary": None, "divergence": None, "diverges_from": None,
           "contested_by": [], "satisfiable": False, "assessment": ""}
    adm = [r for r in rows if r.get("kind") == "receipt" and r.get("task_id") == task_id and r.get("status") == "admitted"]
    if not adm:
        out["assessment"] = "NOT WELL-FORMED: no admission receipt for task %r in this ledger" % task_id
        return out
    row = adm[0]                                                     # one admission per task; a second is a verify problem
    body = row.get("body") if isinstance(row.get("body"), dict) else {}
    for k in PROVENANCE_FIELDS + ("diverges_from",):
        out[k] = body.get(k)
    out["contested_by"] = [r.get("task_id") for r in rows if r.get("kind") == "receipt" and r.get("status") == "admitted"
                           and isinstance(r.get("body"), dict) and r["body"].get("diverges_from") == task_id]
    v = verify_rows(rows)
    if not v["ok"]:
        out["assessment"] = "NOT WELL-FORMED: the chain does not verify (%s)" % v["problems"][0]
        return out
    before = {r.get("task_id") for r in rows[:row.get("seq", 0)] if r.get("kind") == "receipt" and r.get("status") == "admitted"}
    why = admission_provenance_reason(body, before, task_id)
    if why:
        out["assessment"] = "NOT WELL-FORMED: %s" % why
        return out
    out["satisfiable"] = True
    none = _divergence_is_none(out["divergence"])
    out["assessment"] = ("WELL-FORMED: admitted at %s (row %s); fields present, one line each, with words; links resolve; "
                         "the chain verifies (unanchored: see verify()); divergence %s%s; %s. This does not judge whether "
                         "the stated purpose can be met." % (
                             row.get("at"), row.get("seq"), out["divergence"],
                             "" if none else " from task %r" % out["diverges_from"],
                             ("contested by %s" % out["contested_by"]) if out["contested_by"] else "uncontested"))
    return out
