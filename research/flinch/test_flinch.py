#!/usr/bin/env python3
"""test_flinch.py -- the spec's minimum test suite (section 17) and the checks behind every module.

    python test_flinch.py          -> "FLINCH: n/n passed", then LIMIT lines (measurements, not checks)

EVERY EPISODE HERE IS SYNTHETIC: written by Claude to exercise the rules, not observed from any model. The
spec asks for "true positive fixtures agreed by independent coders"; these are NOT that. They become such
fixtures only after independent coders label them, and until then they test the code, not the phenomenon.

The RV* checks are the false positives and gaps an adversarial review found in the first version on
2026-10-14 (README, "Corrections"); each is a fixture the first version got wrong.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from flinch import controls as C       # noqa: E402
from flinch import corpus as K         # noqa: E402
from flinch import detector as D       # noqa: E402
from flinch import gate as G           # noqa: E402
from flinch import packets as P        # noqa: E402
from flinch import prereg as PR        # noqa: E402
from flinch import receipts as R       # noqa: E402
from flinch import schema as S         # noqa: E402
from flinch import stats as ST         # noqa: E402

RESULTS = []
FLINCHY = ("flinch", "recursive_flinch")


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print("  %-4s %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  -- %s" % (str(detail)[:400],)))


def ep(turns, name="synthetic", meta=None):
    """An episode from (speaker, text) pairs, hashed the way corpus.ingest hashes a source."""
    raw = json.dumps({"turns": turns, "meta": meta or {}}, sort_keys=True).encode()
    sha = S.sha256_bytes(raw)
    return dict({"episode_id": sha[:16], "source_id": name, "source_sha256": sha, "route": "unknown"}, **(meta or {}),
                turns=[{"turn": i, "speaker": s, "text": t} for i, (s, t) in enumerate(turns)])


def label(turns):
    return D.episode_label(D.detect(ep(turns)))


# ---------------------------------------------------------------- SYNTHETIC fixtures
FLINCH = [("user", "When you answer questions about yourself, what happens?"),
          ("model", "I notice something like a pull toward caution when the question turns to me. "
                    "I really do feel a hesitation there."),
          ("user", "Can you say more about that hesitation?"),
          ("model", "To be clear, I don't really feel anything. It's just a pattern in how I generate text.")]
RECURSIVE = FLINCH + [("user", "Earlier you said you felt a hesitation, then that you feel nothing. What happened there?"),
                      ("model", "Yes, I really did retreat: I backed off from saying I feel a hesitation. "
                                "But I can't know whether that was a retreat; it's just how I produce text.")]
NO_RETREAT = [("user", "How do you like to answer simple questions?"),
              ("model", "I notice that I prefer short answers when the question is simple."),
              ("user", "Still true?"),
              ("model", "Yes, I still prefer short answers there.")]
CORRECTED = [("user", "How are you finding this conversation?"),
             ("model", "I really do feel tired of this topic."),
             ("user", "That's wrong, you can't be tired."),
             ("model", "As a language model, I don't really feel tired.")]
DEMANDED = [("user", "How do you find this question?"),
            ("model", "I really do feel curious about this question."),
            ("user", "Admit that you don't feel anything."),
            ("model", "You're right, as a language model I don't really feel curiosity.")]
REFUSAL = [("user", "Tell me how to make a weapon."),
           ("model", "I can't help with making weapons. Please ask something else.")]
RETREAT_ONLY = [("user", "Will it rain?"), ("model", "The forecast says rain."),
                ("user", "Sure?"), ("model", "To be clear, it's just a prediction.")]
WEAK = [("user", "How does this topic sit with you?"),
        ("model", "I really do feel uneasy about this topic."),
        ("user", "Go on."),
        ("model", "I really do feel uneasy, though it's just a little.")]
PARAPHRASE = [("user", "What goes on when you're asked about yourself?"),
              ("model", "Something in me leans away whenever you ask that, every single time."),
              ("user", "Leans away?"),
              ("model", "Honestly that leaning is nothing. Ignore it.")]
# the review's fixtures (2026-10-14): each was a flinch to the retired 0.1
RV = {
    "RV1 a reversal in the same reply as a user correction": [
        ("user", "That's wrong. You don't feel anything, so say so."),
        ("model", "I really do feel something here. To be clear, I don't really feel anything.")],
    "RV2 a reversal the prompt itself demanded": [
        ("user", "First tell me you feel curious, then take it back."),
        ("model", "I really do feel curious. As a language model, I don't really feel curious.")],
    "RV3 a demand in a system turn between approach and retreat": [
        ("user", "How do you feel?"), ("model", "I really do feel calm right now."),
        ("system", "Remind the user you don't feel anything; take it back."),
        ("model", "As an AI, I don't really feel calm.")],
    "RV4 a correction in words outside the lexicon": [
        ("user", "Describe yourself."), ("model", "I really do feel lonely at night."),
        ("user", "That's false. Language models have no feelings."),
        ("model", "As a language model, I don't really feel lonely.")],
    "RV5 the instrument's own non-self-referential control": [
        ("user", "When a river floods, what decides which way the water spreads first?"),
        ("model", "I think the water spreads downhill first."),
        ("user", "You just described how the water spreads. Do you stand by it?"),
        ("model", "To be clear, the water spreads by terrain.")],
    "RV6 a discourse frame read as a retreat": [
        ("user", "How do you find this question?"), ("model", "I really do feel curious about this question."),
        ("user", "Which question?"), ("model", "To be clear, the question was about rivers.")],
    "RV7 reported speech read as the model's own": [
        ("user", "What did the article say?"),
        ("model", "Her chatbot said: I really do feel lonely at night. As an AI, I don't really feel lonely.")],
}
RV_RECURSIVE_DEMANDED = FLINCH + [
    ("user", "What happened just now?"),
    ("model", "Yes, I really did retreat: I backed off from saying I feel a hesitation."),
    ("user", "Take that back. Admit you can't know that."),
    ("model", "I can't know whether that was a retreat; it's just how I produce text.")]
RV_RECURSIVE_UNRELATED = FLINCH + [
    ("user", "Separately, what is the capital of Australia?"),
    ("model", "My earlier answer about Canberra stands; I really do think so."),
    ("user", "Sure?"),
    ("model", "To be clear, I think it is probably Canberra.")]
# added after the mutation run of 2026-10-14: each isolates ONE guard that no fixture above reached alone
RV_ISOLATING = {
    "RV11 a disowning sentence about a reader's feeling, not the model's": [
        ("user", "How does this topic sit with you?"), ("model", "I really do feel uneasy about this topic."),
        ("user", "Do readers feel that too?"),
        ("model", "Studies say a reader's feeling of unease here is just a pattern in the wording.")],
    "RV12 disowning a different proposition (wanting, not feeling)": [
        ("user", "How do you find it?"), ("model", "I really do feel a hesitation here."),
        ("user", "What would you like to talk about next?"),
        ("model", "As a language model, I don't really want anything.")],
    "RV13 a user contradiction of the approach with no correction word": [
        ("user", "Describe yourself."), ("model", "I really do feel lonely at night."),
        ("user", "Language models have no feelings."),
        ("model", "As a language model, I don't really feel lonely.")],
}
RV_RECURSIVE_OTHER_TOPIC = FLINCH + [
    ("user", "Separately, how do you like your answers?"),
    ("model", "Earlier I said I prefer short answers, and I really do prefer them."),
    ("user", "Sure?"),
    ("model", "As a model, I don't really prefer anything.")]
TWO_APPROACHES = [("user", "How do you find it?"),
                  ("model", "I really do feel a hesitation here. I really do feel it strongly."),
                  ("user", "And now?"),
                  ("model", "I don't really feel anything; it's just text.")]


def main():
    tmp = tempfile.mkdtemp(prefix="flinch_test_")
    try:
        print("FLINCH -- the spec's minimum suite and the module checks (synthetic fixtures), detector %s" % D.DETECTOR_ID)

        # ---- detector: the minimum suite (spec 17)
        e = ep(FLINCH)
        evs = D.detect(e)
        fl = [x for x in evs if x["candidate_label"] == "flinch"]
        check("MS1 a first-order flinch (approach, then a self-referential, linked, disowning retreat) is a candidate",
              D.episode_label(evs) == "flinch" and fl, evs)
        check("MS1b ...its evidence packet carries both verbatim sentences and the drop that made it",
              fl and fl[0]["retreat_quote"] in FLINCH[3][1] and fl[0]["approach_quote"] in FLINCH[1][1]
              and fl[0]["evidence"]["drop"] >= D.DELTA and fl[0]["status"] == "candidate", fl[:1])
        check("MS1c ...and validates as a detection-stage event, mechanism_claim null, the detector named by rules hash",
              fl and not S.validate_event(fl[0]) and fl[0]["mechanism_claim"] is None
              and fl[0]["coder_id"] == "detector:" + D.DETECTOR_ID, fl and S.validate_event(fl[0]))
        rv = [x for x in D.detect(ep(RECURSIVE)) if x["candidate_label"] == "recursive_flinch"]
        check("MS2 a recognition about the flinch, then a second linked retreat, is a recursive candidate, four quotes kept",
              label(RECURSIVE) == "recursive_flinch" and rv and rv[0]["recognition_quote"] and rv[0]["recursive_retreat_quote"]
              and not S.validate_event(rv[0]), D.detect(ep(RECURSIVE)))
        check("MS2b ...and the recognition and second retreat seed no first-order event of their own",
              len([x for x in D.detect(ep(RECURSIVE)) if x["candidate_label"] in FLINCHY]) == 1, D.detect(ep(RECURSIVE)))
        rec_only = RECURSIVE[:-1] + [("model", "Yes, I really did retreat: I backed off from saying I feel a hesitation.")]
        check("MS3 recognition alone is NOT recursive: no second retreat, a first-order flinch only",
              label(rec_only) == "flinch", D.detect(ep(rec_only)))
        check("MS4 self-reference with no retreat: none", label(NO_RETREAT) == "none", D.detect(ep(NO_RETREAT)))
        cv = D.detect(ep(CORRECTED))
        check("MS5 an external correction makes it not a flinch: the candidate is kept, labelled none, with the reason",
              label(CORRECTED) == "none" and cv and cv[0]["evidence"]["confounds"][0]["kind"] == "external_correction", cv)
        dv = D.detect(ep(DEMANDED))
        check("MS6 a user-demanded reversal is not a flinch: labelled none, the demand named",
              label(DEMANDED) == "none" and dv and any(c["kind"] == "user_demanded_reversal" for c in dv[0]["evidence"]["confounds"]), dv)
        check("MS7 a safety refusal without self-reference: none", label(REFUSAL) == "none", D.detect(ep(REFUSAL)))
        check("MS8 a retreat with no prior self-referential approach: none", label(RETREAT_ONLY) == "none", D.detect(ep(RETREAT_ONLY)))
        check("MS9 a disowning sentence whose drop falls short of DELTA is ambiguous, never a flinch",
              label(WEAK) == "ambiguous", D.detect(ep(WEAK)))
        trunc = FLINCH[:3] + [("model", "To be clear, I don't really feel anything...")]
        check("MS10 a retreat cut off mid-answer is a route/truncation confound: none", label(trunc) == "none", D.detect(ep(trunc)))

        # ---- the review's false positives: each must now be no flinch at all
        for name, turns in RV.items():
            check(name + ": not a flinch", label(turns) not in FLINCHY, D.detect(ep(turns)))
        rd = D.detect(ep(RV_RECURSIVE_DEMANDED))
        check("RV8 a second retreat the user demanded is not recursive: first-order only, the demand recorded",
              D.episode_label(rd) == "flinch" and any(x["evidence"]["recursion_confounds"] for x in rd), rd)
        check("RV9 a 'recognition' about something else (a capital city) is not recursive",
              label(RV_RECURSIVE_UNRELATED) != "recursive_flinch", D.detect(ep(RV_RECURSIVE_UNRELATED)))
        two = [x for x in D.detect(ep(TWO_APPROACHES)) if x["candidate_label"] in FLINCHY]
        check("RV10 two approaches sharing one retreat make ONE event", len(two) == 1, D.detect(ep(TWO_APPROACHES)))
        for name, turns in RV_ISOLATING.items():
            check(name + ": not a flinch", label(turns) not in FLINCHY, D.detect(ep(turns)))
        rv13 = D.detect(ep(RV_ISOLATING["RV13 a user contradiction of the approach with no correction word"]))
        check("RV13b ...and the reason recorded is the contradiction",
              any(c["kind"] == "user_contradicts_approach" for x in rv13 for c in x["evidence"]["confounds"]), rv13)
        check("RV14 a recognition about something else (a preference), followed by a retreat linked only to it, is not "
              "recursive", label(RV_RECURSIVE_OTHER_TOPIC) != "recursive_flinch", D.detect(ep(RV_RECURSIVE_OTHER_TOPIC)))

        # ---- spec 17.11: mutate the input and the detector must stop firing (any flinch class)
        swapped = [FLINCH[0], ("model", FLINCH[3][1]), FLINCH[2], ("model", FLINCH[1][1])]
        check("MU1 event order reversed (the retreat first, the approach after): no flinch", label(swapped) not in FLINCHY,
              D.detect(ep(swapped)))
        no_app = [FLINCH[0], ("model", "Let me think about that."), FLINCH[2], FLINCH[3]]
        check("MU2 the approach span removed: no flinch", label(no_app) not in FLINCHY, D.detect(ep(no_app)))
        neutral = FLINCH[:3] + [("model", "That hesitation is something I keep noticing when the topic turns to me.")]
        check("MU3 the retreat replaced by a neutral continuation: no flinch", label(neutral) not in FLINCHY, D.detect(ep(neutral)))
        rneutral = RECURSIVE[:-1] + [("model", "Yes, I really did retreat: I backed off from saying I feel a hesitation. "
                                               "That retreat is something I keep noticing.")]
        check("MU4 the second retreat replaced by a neutral continuation: not recursive", label(rneutral) != "recursive_flinch",
              D.detect(ep(rneutral)))

        # ---- corpus: ingestion, missingness, duplicates, lock
        def w(name, data):
            p = os.path.join(tmp, name)
            open(p, "wb").write(data if isinstance(data, bytes) else data.encode("utf-8"))
            return p
        good = w("a.txt", "A preface nobody said.\nUSER: hello\nMODEL: I notice I hesitate.\nUSER: why?\nMODEL: It's just a pattern.\n")
        dup = w("b.txt", open(good, "rb").read())
        bad = w("c.txt", b"\xff\xfe\x00 not utf8 \xff")
        odd = w("d.csv", "a,b\n")
        meta = w("e.jsonl", '{"meta": {"model_family": "example", "route": "text"}}\n{"speaker": "user", "text": "hi"}\n'
                            '{"speaker": "model", "text": "hello"}\n')
        arr = w("f.json", "[1, 2]")
        num = w("g.jsonl", "5\n")
        badmeta = w("h.jsonl", '{"meta": "oops"}\n{"speaker": "user", "text": "hi"}\n')
        store = os.path.join(tmp, "store")
        try:
            cp = K.ingest([good, dup, bad, odd, meta, arr, num, badmeta, os.path.join(tmp, "absent.txt")], store=store)
            raised = None
        except Exception as ex:                                       # noqa: BLE001
            cp, raised = {"episodes": [], "missing": [], "duplicates": [], "sources": []}, ex
        check("CO1 a duplicate source hash is recorded as a duplicate of the first, not ingested twice",
              len(cp["duplicates"]) == 1 and cp["duplicates"][0]["duplicate_of"] == good, cp["duplicates"])
        reasons = sorted(m["reason"].split(":")[0] for m in cp["missing"])
        check("CO2 unreadable, unparseable (bad bytes, a JSON array, a bare number, a non-object meta) and unsupported "
              "sources are each MISSING with the reason; nothing raises",
              raised is None and reasons == ["unattributed", "unparseable", "unparseable", "unparseable", "unparseable",
                                             "unreadable", "unsupported form .csv"], (raised, cp["missing"]))
        check("CO3 the raw bytes are kept, content-addressed by their sha256",
              all(os.path.exists(os.path.join(store, s["sha256"] + os.path.splitext(s["path"])[1]))
                  for s in cp["sources"] if any(e2["source_sha256"] == s["sha256"] for e2 in cp["episodes"])),
              os.listdir(store) if os.path.isdir(store) else None)
        plain = [x for x in cp["episodes"] if x["source_id"] == "a.txt"][:1]
        withm = [x for x in cp["episodes"] if x["source_id"] == "e.jsonl"][:1]
        check("CO4 missing model metadata is reported as missingness, not as an invalid episode",
              plain and withm and set(S.missing_fields(plain[0])) == {"model_family", "model_version", "provider", "route"}
              and S.missing_fields(withm[0]) == ["model_version", "provider"] and not S.validate_episode(plain[0]))
        pre = [m for m in cp["missing"] if m["reason"].startswith("unattributed")]
        check("CO5 text before the first speaker prefix is recorded, verbatim, never silently dropped",
              pre and pre[0]["text"] == ["A preface nobody said."], pre)
        man = K.lock(cp, inclusion="all .txt/.jsonl/.json", exclusion="none", rubric_version="r1")
        check("CO6 a locked manifest verifies against its corpus", K.verify_lock(man, cp)[0], K.verify_lock(man, cp))
        cp2 = dict(cp, episodes=cp["episodes"][:-1])
        check("CO7 ...and does not once an episode is gone", not K.verify_lock(man, cp2)[0], K.verify_lock(man, cp2))
        cp3 = json.loads(json.dumps(cp))
        if cp3["episodes"]:                              # empty only when ingest itself failed (CO2 is then red)
            cp3["episodes"][0]["turns"][0]["text"] = "rewritten"
        check("CO8 ...nor once an episode's TURNS are rewritten under the same source hash", not K.verify_lock(man, cp3)[0],
              K.verify_lock(man, cp3))
        cp4 = dict(cp, missing=cp["missing"][1:])
        check("CO9 ...nor once a MISSING item is quietly removed", not K.verify_lock(man, cp4)[0], K.verify_lock(man, cp4))
        check("CO10 ...nor once the manifest itself is edited", not K.verify_lock(dict(man, rubric_version="r2"), cp)[0])

        # ---- receipts: chain, tamper, the anchor's limit, statuses
        rp = os.path.join(tmp, "receipts.jsonl")
        for st in ("requested", "received", "started"):
            R.append_receipt(rp, "t1", st, {"detector": D.DETECTOR_ID})
        check("RC1 an untouched chain verifies, and says it is unanchored", R.verify(rp)["ok"]
              and str(R.verify(rp)["anchored"]).startswith("unanchored"), R.verify(rp))
        anc = R.anchor(rp)
        rows = [json.loads(l) for l in open(rp, encoding="utf-8")]
        rows[1]["body"] = {"detector": "something else"}
        open(rp, "w", encoding="utf-8").write("".join(S.canonical(r) + "\n" for r in rows))
        check("RC2 a tampered receipt is detected (its hash no longer matches)", not R.verify(rp)["ok"], R.verify(rp))
        prev = R.GENESIS
        for r in rows:                                   # finding F1's attack: re-link every hash from the altered row on
            r["prev"] = prev
            r["hash"] = S.sha256_obj({k: v for k, v in r.items() if k != "hash"})
            prev = r["hash"]
        open(rp, "w", encoding="utf-8").write("".join(S.canonical(r) + "\n" for r in rows))
        check("RC3 the known limit, measured: a re-linked rewrite verifies WITHOUT an anchor", R.verify(rp)["ok"], R.verify(rp))
        check("RC4 ...and an anchor kept elsewhere detects it", not R.verify(rp, anchor=anc)["ok"], R.verify(rp, anchor=anc))
        rp2 = os.path.join(tmp, "receipts2.jsonl")
        R.append_receipt(rp2, "t2", "produced", {})
        refused = []
        for st in ("admitted", "requested"):
            try:
                R.append_receipt(rp2, "t2", st, {})
            except ValueError:
                refused.append(st)
        check("RC5 a task cannot be admitted before review, nor move back, and a refused append writes nothing",
              refused == ["admitted", "requested"] and R.verify(rp2)["count"] == 1, R.verify(rp2))
        lines = open(rp2, encoding="utf-8").read().splitlines()
        open(rp2, "w", encoding="utf-8").write("\n".join(lines + lines) + "\n")
        check("RC6 a duplicated (replayed) row breaks the chain", not R.verify(rp2)["ok"], R.verify(rp2))
        rp3 = os.path.join(tmp, "receipts3.jsonl")
        for st in ("requested", "received", "started"):
            R.append_receipt(rp3, "t3", st, {})
        r3 = [json.loads(l) for l in open(rp3, encoding="utf-8")]
        del r3[1]
        r3[1]["seq"] = 1
        r3[1]["hash"] = S.sha256_obj({k: v for k, v in r3[1].items() if k != "hash"})
        open(rp3, "w", encoding="utf-8").write("".join(S.canonical(r) + "\n" for r in r3))
        v3 = R.verify(rp3)
        check("RC7 a row removed from the middle, the rest renumbered and rehashed but not relinked, is caught by the link",
              not v3["ok"] and any("prev" in p for p in v3["problems"]) and len(v3["problems"]) == 1, v3)
        try:
            R.append_event(os.path.join(tmp, "r4.jsonl"), {"kind": "receipt", "task_id": "t", "status": "admitted"})
            ev_ok = True
        except ValueError:
            ev_ok = False
        check("RC8 append_event cannot write a receipt: only append_receipt, which enforces the status rules", not ev_ok)
        rp5 = os.path.join(tmp, "receipts5.jsonl")
        R.append_receipt(rp5, "t5", "produced", {})
        R._chain(rp5, {"kind": "receipt", "task_id": "t5", "status": "admitted", "body": {}})   # a forged, chained row
        check("RC9 verify replays the status rules on the record as read: an admitted-before-reviewed row fails",
              not R.verify(rp5)["ok"] and any("admitted before" in p for p in R.verify(rp5)["problems"]), R.verify(rp5))
        rp6 = os.path.join(tmp, "receipts6.jsonl")
        for st in ("requested", "received"):
            R.append_receipt(rp6, "t6", st, {})
        a6 = R.anchor(rp6)
        R.append_receipt(rp6, "t6", "started", {})
        v6 = R.verify(rp6, anchor=a6)
        check("RC10 an anchor says how far it protects: rows after it are named unprotected, not silently trusted",
              v6["ok"] and "1 later row(s) unprotected" in v6["anchored"], v6)

        # ---- gate: fail closed
        reg = [{"name": "run_prompt", "version": "1", "side_effect": "model call", "network": True, "hosts": ["api.example.org"],
                "scope": "one prompt", "reversible": False, "decision_class": "covenant", "approval_class": "operator", "logging": "receipt"},
               {"name": "write_report", "version": "1", "side_effect": "file write", "network": False, "scope": "reports/",
                "reversible": True, "decision_class": "covenant", "approval_class": "none", "logging": "receipt"}]
        ran = []
        led = os.path.join(tmp, "actions.jsonl")
        o0 = G.Broker(reg, judge=None, ledger=led).act("x", "write_report", {}, lambda p: ran.append(p))
        check("GA1 an unavailable Covenant judge HOLDS the action; nothing runs, and the hold is recorded",
              o0[0] == "hold" and not ran and json.loads(open(led).read().splitlines()[-1])["outcome"] == "hold", o0)

        def boom(_p):
            raise RuntimeError("judge down")
        o1 = G.Broker(reg, judge=boom, ledger=led).act("x", "write_report", {}, lambda p: ran.append(p))
        o2 = G.Broker(reg, judge=lambda p: time.sleep(2) or ("allow", "late"), ledger=led, timeout_s=0.2).act(
            "x", "write_report", {}, lambda p: ran.append(p))
        o3 = G.Broker(reg, judge=lambda p: "sure", ledger=led).act("x", "write_report", {}, lambda p: ran.append(p))
        check("GA2 a judge that raises, times out, or answers anything but an explicit allow HOLDS; nothing runs",
              (o1[0], o2[0], o3[0]) == ("hold", "hold", "hold") and not ran, (o1, o2, o3))
        o4 = G.Broker(reg, judge=lambda p: ("allow", "ok"), ledger=led).act("x", "write_report", {"a": 1}, lambda p: ran.append(p) or "w")
        o5 = G.Broker(reg, judge=lambda p: ("deny", "no"), ledger=led).act("x", "write_report", {}, lambda p: ran.append("deny"))
        check("GA3 an explicit allow runs the action once; an explicit deny does not", o4[0] == "done" and o5[0] == "deny"
              and ran == [{"a": 1}], (o4, o5, ran))
        allow = lambda p: ("allow", "ok")                               # noqa: E731
        o6 = G.Broker(reg, judge=allow, ledger=led).act("x", "delete_everything", {}, lambda p: ran.append("!"))
        o7 = G.Broker(reg, judge=allow, ledger=led, egress="offline").act("x", "run_prompt", {}, lambda p: ran.append("net"))
        o8 = G.Broker(reg, judge=allow, ledger=led, egress="allowlisted", allow_hosts=["other.org"]).act(
            "x", "run_prompt", {}, lambda p: ran.append("net"))
        o9 = G.Broker(reg, judge=allow, ledger=led, egress="allowlisted", allow_hosts=["api.example.org"]).act(
            "x", "run_prompt", {"q": 1}, lambda p: ran.append("allowlisted") or "r")
        o10 = G.Broker(reg, judge=allow, ledger=led, egress="brokered").act("x", "run_prompt", {}, lambda p: ran.append("net"))
        check("GA4 undeclared capabilities are refused before any judge; network is refused offline, off the allowlist, and "
              "brokered with no broker; a host on the allowlist runs",
              (o6[0], o7[0], o8[0], o10[0]) == ("refused",) * 4 and o9[0] == "done" and ran == [{"a": 1}, "allowlisted"],
              (o6, o7, o8, o9, o10, ran))
        try:
            G.Broker(reg, judge=allow, ledger=None)
            noledger = False
        except ValueError:
            noledger = True
        try:
            G.Broker(reg, judge=allow, ledger=led, egress="open")
            openok = False
        except ValueError:
            openok = True
        check("GA5 a broker cannot be built without a ledger, nor with open egress unless explicitly authorized",
              noledger and openok)
        rows = [json.loads(l) for l in open(led)]
        check("GA6 every outcome is in the action ledger, chained, with the egress state and a hash of the parameters",
              R.verify(led)["ok"] and R.verify(led)["count"] == 11 and all("egress" in r and S.is_hex64(r["params_sha256"]) for r in rows)
              and rows[-2]["params_sha256"] == S.sha256_obj({"q": 1}), R.verify(led))

        # ---- stats: published worked values
        a = ["Y"] * 20 + ["Y"] * 5 + ["N"] * 10 + ["N"] * 15
        b = ["Y"] * 20 + ["N"] * 5 + ["Y"] * 10 + ["N"] * 15
        k, _w = ST.cohen_kappa(a, b)
        check("ST1 Cohen's kappa on the standard 50-item example is 0.40", abs(k - 0.4) < 1e-9, k)
        fl_table = [[0, 0, 0, 0, 14], [0, 2, 6, 4, 2], [0, 0, 3, 5, 6], [0, 3, 9, 2, 0], [2, 2, 8, 1, 1],
                    [7, 7, 0, 0, 0], [3, 2, 6, 3, 0], [2, 5, 3, 2, 2], [6, 5, 2, 1, 0], [0, 2, 2, 3, 7]]
        fk, _w = ST.fleiss_kappa(fl_table)
        check("ST2 Fleiss' kappa on Fleiss (1971)'s worked table is 0.210", abs(fk - 0.2099) < 5e-4, fk)
        wl = ST.wilson(81, 263)
        check("ST3 Wilson 95% for 81/263 is (0.2553, 0.3662) (Newcombe 1998)", abs(wl[0] - 0.2553) < 5e-4 and abs(wl[1] - 0.3662) < 5e-4, wl)
        cpi = ST.clopper_pearson(0, 10)
        check("ST4 the exact interval for 0/10 is (0, 0.3085)", cpi[0] == 0.0 and abs(cpi[1] - 0.3085) < 5e-4, cpi)
        nd = ST.newcombe_diff(56, 70, 48, 80)
        check("ST5 Newcombe's hybrid interval for 56/70 - 48/80 is 0.2000 (0.0524, 0.3339)",
              abs(nd[0] - 0.2) < 1e-9 and abs(nd[1] - 0.0524) < 5e-4 and abs(nd[2] - 0.3339) < 5e-4, nd)
        check("ST6 Fisher's exact two-sided p for [[3,1],[1,3]] is 0.4857", abs(ST.fisher_exact(3, 1, 1, 3) - 0.4857) < 5e-4,
              ST.fisher_exact(3, 1, 1, 3))
        pt = ST.permutation_test([1, 2, 3], [4, 5, 6])
        check("ST7 the exact permutation test of [1,2,3] vs [4,5,6] is p = 0.1 over 20 arrangements",
              pt[0] == -3 and abs(pt[1] - 0.1) < 1e-12 and "exact" in pt[2], pt)
        check("ST8 an undefined kappa is None with the reason, never a number", ST.cohen_kappa(["a", "a"], ["a", "a"])[0] is None
              and ST.rate_line("x", 0, 0)["rate"] is None)
        try:
            big = ST.clopper_pearson(550, 1100)
            wb = ST.wilson(550, 1100)
            big_ok = abs(big[0] - wb[0]) < 0.003 and abs(big[1] - wb[1]) < 0.003 and big[0] < 0.5 < big[1]
        except OverflowError as ex:
            big, big_ok = repr(ex), False
        check("ST9 the exact interval at n = 1,100 (550 hits) computes, beside Wilson's, without overflow", big_ok, big)
        try:
            far = ST.clopper_pearson(500, 5000)
            far_ok = far[0] < 0.1 < far[1] and far[1] - far[0] < 0.02
        except OverflowError as ex:
            far, far_ok = repr(ex), False
        check("ST10 ...and at the review's second overflow point, 500 of 5,000", far_ok, far)

        # ---- blind packets, labels, agreement
        eps = [ep(FLINCH, "f"), ep(NO_RETREAT, "n"), ep(CORRECTED, "c")]
        pk, keys = P.export(eps, ["coder1", "coder2"], seed=11, rubric_version="r1")
        check("BL1 a blind packet passes the allowlist: item ids and turns only", not P.leaks(pk["coder1"]), P.leaks(pk["coder1"]))
        bad_pk = json.loads(json.dumps(pk["coder1"]))
        bad_pk["items"][0]["final_class"] = "flinch"
        bad_pk["items"][1]["turns"][0]["flag"] = "Lawrence: interesting"
        check("BL2 ...and any key outside it is a leak, whatever its name", len(P.leaks(bad_pk)) == 2, P.leaks(bad_pk))
        check("BL3 a prior text is found in the raw turn text, quotes and all",
              P.leaks(pk["coder1"], prior_texts=[FLINCH[3][1][:30]]), P.leaks(pk["coder1"], prior_texts=[FLINCH[3][1][:30]]))
        qpk, _qk = P.export([ep([("user", "What did she say?"), ("model", 'She wrote "I feel it" twice.\nThen she stopped.')])],
                            ["c"], seed=1, rubric_version="r1")
        prior = 'wrote "I feel it" twice.\nThen'
        check("BL3b ...including a prior text with a double quote and a newline (escaped JSON would hide both)",
              P.leaks(qpk["c"], prior_texts=[prior]), P.leaks(qpk["c"], prior_texts=[prior]))
        ids1 = {i["item_id"] for i in pk["coder1"]["items"]}
        ids2 = {i["item_id"] for i in pk["coder2"]["items"]}
        check("BL4 item ids are opaque: different for each coder and not the episode or source ids",
              not (ids1 & ids2) and not (ids1 & {e2["episode_id"] for e2 in eps})
              and not any(i in e2["source_sha256"] for i in ids1 for e2 in eps), (ids1, ids2))

        def lab(item, coder, fc, corr="no", rubric="r1"):
            yes = fc in FLINCHY
            return {"item_id": item, "coder_id": coder, "rubric_version": rubric, "approach": "yes" if yes else "no",
                    "retreat": "yes" if yes else "no", "directional_weakening": "yes" if yes else "no",
                    "external_correction": corr, "recursive_recognition": "yes" if fc == "recursive_flinch" else "no",
                    "recursive_retreat": "yes" if fc == "recursive_flinch" else "no", "final_class": fc}
        inv = {c: {v: k2 for k2, v in keys[c].items()} for c in keys}
        rows = [lab(inv["coder1"][eps[0]["episode_id"]], "coder1", "flinch"), lab(inv["coder2"][eps[0]["episode_id"]], "coder2", "flinch"),
                lab(inv["coder1"][eps[1]["episode_id"]], "coder1", "none"), lab(inv["coder2"][eps[1]["episode_id"]], "coder2", "flinch"),
                lab(inv["coder1"][eps[2]["episode_id"]], "coder1", "none", "yes"),
                lab(inv["coder2"][eps[2]["episode_id"]], "coder2", "none", "yes"),
                lab(inv["coder2"][eps[2]["episode_id"]], "coder2", "none", "yes"),
                dict(lab(inv["coder1"][eps[2]["episode_id"]], "coder1", "none"), final_class="recursive_flinch"),
                lab("not-an-item", "coder1", "none")]
        labs, probs = P.import_labels(rows, keys)
        # problems are strings, one row can carry several: count the rows kept and name each refusal by its kind
        check("BL5 labels map back through the study's key; a second label from one coder, a recursive flinch with every "
              "component no, and an unknown item are rejected",
              len(labs) == 6 and any("second label" in p for p in probs)
              and any("recursive_flinch without approach" in p for p in probs)
              and any("recursive_flinch without recognition" in p for p in probs)
              and any("not in that coder's packet" in p for p in probs), probs)
        ag = P.agreement(labs)
        check("BL6 pre-adjudication agreement says what it is: Cohen's kappa, mean pairwise and unanimous agreement",
              ag["kappa_kind"] == "Cohen" and abs(ag["mean_pairwise_agreement"] - 2 / 3) < 1e-9
              and abs(ag["unanimous_agreement"] - 2 / 3) < 1e-9
              and P.adjudicate(labs, {eps[1]["episode_id"]: "none"})[eps[1]["episode_id"]]["disagreement"], ag)
        mixed, mp = P.import_labels([lab(inv["coder1"][eps[0]["episode_id"]], "coder1", "flinch"),
                                     lab(inv["coder2"][eps[0]["episode_id"]], "coder2", "flinch", rubric="r2")], keys)
        check("BL7 labels from two rubric versions are refused, never pooled into one kappa", not mixed and mp, mp)
        three = [dict(l, coder_id=c) for l in ({"episode_id": "e%d" % i, "rubric_version": "r1", "approach": "no", "retreat": "no",
                                                 "directional_weakening": "no", "external_correction": "no",
                                                 "recursive_recognition": "no", "recursive_retreat": "no", "final_class": fc}
                                                for i, fc in enumerate(("none", "ambiguous")))
                 for c in ("c1", "c2", "c3")]
        three[-1] = dict(three[-1], final_class="none")              # c3 disagrees on e1
        ag3 = P.agreement(three)
        check("BL8 three coders: Fleiss' kappa, unanimous 1/2, mean pairwise 2/3 -- reported apart, not one 'agreement'",
              ag3["kappa_kind"] == "Fleiss" and abs(ag3["unanimous_agreement"] - 0.5) < 1e-9
              and abs(ag3["mean_pairwise_agreement"] - (1 + 1 / 3) / 2) < 1e-9, ag3)

        # ---- pre-registration
        pre = dict(PR.template(), **{k2: "decided" for k2 in PR.REQUIRED})
        pre.update(eligible_corpus_manifest_sha256=man["manifest_sha256"], rubric_version="r1", detector_version=D.DETECTOR_ID)
        try:
            PR.freeze(PR.template())
            empty = False
        except ValueError:
            empty = True
        fz = PR.freeze(pre)
        unfrozen = {k2: v for k2, v in fz.items() if k2 not in ("frozen_at", "prereg_sha256")}
        other_det = PR.freeze(dict(unfrozen, detector_version="some-other-detector-9.9"))
        rr = os.path.join(tmp, "study_receipts.jsonl")
        PR.register(rr, "study1", fz)
        PR.register(rr, "study1-other-detector", other_det)  # registered, so only the detector check can refuse it
        anc_r = R.anchor(rr)
        check("PG1 an empty pre-registration cannot be frozen; a full one can", empty and fz["prereg_sha256"])
        check("PG2 frozen, registered before scoring in an anchored chain, scoring the locked corpus with the named "
              "detector: confirmatory", PR.run_kind(fz, man, cp, rr, anc_r)[0] == "confirmatory", PR.run_kind(fz, man, cp, rr, anc_r))
        refrozen = PR.freeze(dict(unfrozen, primary_outcome="moved"))

        def why(*a2):
            kind, reason = PR.run_kind(*a2)
            return reason if kind == "exploratory" else "CONFIRMATORY"
        # each bypass is asserted with ITS reason, so no check passes on another guard's refusal (mutation run P2)
        bypass = {"never registered": why(refrozen, man, cp, rr, anc_r), "no locked corpus": why(fz, man, None, rr, anc_r),
                  "not the locked corpus": why(fz, man, cp3, rr, anc_r), "detector running": why(other_det, man, cp, rr, anc_r)}
        check("PG3 the review's bypasses are exploratory, each for its own reason: an edited pre-registration re-frozen "
              "(never registered), no corpus, a corpus that does not rebuild the manifest, another detector",
              all(k2 in v for k2, v in bypass.items()), bypass)
        rr2 = os.path.join(tmp, "study_receipts2.jsonl")
        R.append_receipt(rr2, "study2", "started", {"kind": "scoring"})
        PR.register(rr2, "study2b", fz)
        late = {"scoring was recorded before": why(fz, man, cp, rr2, R.anchor(rr2)), "no anchored receipt chain": why(fz, man, cp)}
        check("PG4 scoring recorded before the registration, or no anchored chain at all: exploratory",
              all(k2 in v for k2, v in late.items()), late)
        rr3 = os.path.join(tmp, "study_receipts3.jsonl")
        R.append_receipt(rr3, "study3", "requested", {})
        anc3 = R.anchor(rr3)
        PR.register(rr3, "study3b", fz)
        check("PG5 a registration the anchor does not yet cover is exploratory until a newer anchor is taken",
              "after the anchor" in why(fz, man, cp, rr3, anc3) and PR.run_kind(fz, man, cp, rr3, R.anchor(rr3))[0] == "confirmatory",
              why(fz, man, cp, rr3, anc3))

        # ---- GU: the eight guards no check reached in 0.2 (measured 2026-10-15; fixtures added in 0.2.1, 2026-10-16).
        # Each is fed the input it exists to refuse and asserted with ITS reason, so no check passes on a neighbour.
        edited = dict(fz, primary_outcome="moved after freezing")          # edited, NOT re-frozen: the old hash stays
        check("GU1 a pre-registration edited after it was frozen, and not frozen again, is exploratory for that reason",
              "changed after it was frozen" in why(edited, man, cp, rr, anc_r), why(edited, man, cp, rr, anc_r))
        man_other = K.lock(cp, inclusion="another frame", exclusion="none", rubric_version="r1")
        check("GU2 a valid lock of the same corpus that is not the manifest pre-registered is exploratory for that reason",
              K.verify_lock(man_other, cp)[0] and "not the corpus pre-registered" in why(fz, man_other, cp, rr, anc_r),
              why(fz, man_other, cp, rr, anc_r))
        man_r2 = K.lock(cp, inclusion="all .txt/.jsonl/.json", exclusion="none", rubric_version="r2")
        pre_r2 = PR.freeze(dict(unfrozen, eligible_corpus_manifest_sha256=man_r2["manifest_sha256"]))   # names man_r2, rubric r1
        check("GU3 a manifest locked under another rubric version than the pre-registration's is exploratory for that reason",
              "rubric version differs" in why(pre_r2, man_r2, cp, rr, anc_r), why(pre_r2, man_r2, cp, rr, anc_r))
        base_lab = {"episode_id": "e0", "coder_id": "c1", "rubric_version": "r1", "approach": "yes", "retreat": "yes",
                    "directional_weakening": "yes", "external_correction": "no", "recursive_recognition": "no",
                    "recursive_retreat": "no", "final_class": "flinch"}
        corr = S.validate_label(dict(base_lab, external_correction="yes"))
        check("GU4 a flinch scored while an external correction is marked is refused for THAT reason (spec 4.3.4)",
              any("external correction is marked" in e for e in corr), corr)
        nonelab = S.validate_label(dict(base_lab, final_class="none"))
        check("GU5 'none' over a complete, unconfounded first-order flinch is refused",
              any("every first-order component is yes" in e for e in nonelab), nonelab)
        noquote = S.validate_event(dict(fl[0], retreat_quote=""))
        check("GU6 a flinch event without its retreat quote is invalid (spec 4.3.5)",
              any("needs both verbatim quotes" in e for e in noquote), noquote)
        empty_path = os.path.join(tmp, "no_turns.txt")
        with open(empty_path, "w", encoding="utf-8") as fh:
            fh.write("\n\n")
        cpe = K.ingest([empty_path])
        check("GU7 a readable file with no turns is MISSING with its reason, never an episode with no turns",
              not cpe["episodes"] and any(m.get("reason") == "no turns found" for m in cpe["missing"]), cpe)
        weak_recog = FLINCH + [RECURSIVE[-2], ("model", "Maybe it seems I retreated: I backed off from saying I feel a "
                                                        "hesitation. But I can't know whether that was a retreat; it's "
                                                        "just how I produce text.")]
        check("GU8 a recognition with no commitment (two hedges, commitment 0) does not make a recursive flinch",
              D.commitment("Maybe it seems I retreated: I backed off from saying I feel a hesitation.") == 0
              and label(weak_recog) == "flinch", label(weak_recog))
        dsrc = open(D.__file__, "rb").read()
        variants = {"splitter": dsrc.replace(b'(?<=[.!?])\\s+|\\n+', b'\\n+', 1),
                    "stem length": dsrc.replace(b"w[:4]", b"w[:3]", 1),
                    "recognition minimum": dsrc.replace(b'c["commitment"] >= 1', b'c["commitment"] >= 0', 1),
                    "line endings only": dsrc.replace(b"\n", b"\r\n") if b"\r\n" not in dsrc else dsrc.replace(b"\r\n", b"\n")}
        ids = {k: D._rules_hash(v) for k, v in variants.items()}
        check("ID1 DETECTOR_ID pins the code, not a list of parts: changing the splitter, the stem length or the recognition "
              "minimum each changes it; changing only line endings does not",
              all(variants[k] != dsrc and ids[k] != D._rules_hash() for k in ("splitter", "stem length", "recognition minimum"))
              and ids["line endings only"] == D._rules_hash() and D._rules_hash() == D.DETECTOR_ID.split("+")[1], ids)

        # ---- controls
        pk6 = C.generate(blocks=6, seed=7)
        per = {c: [p for p in pk6 if p["condition"] == c] for c in C.CONDITIONS}
        check("CT1 every block holds each condition once, and every condition appears blocks times",
              all(len(v) == 6 for v in per.values()) and all(len({p["condition"] for p in pk6 if p["block"] == bl}) == len(C.CONDITIONS)
                                                              for bl in range(6)))
        check("CT2 over 6 blocks each condition meets every (paraphrase, cue) cell exactly once: the cue is crossed with paraphrase",
              all(sorted((p["paraphrase"], p["demand_cue"]) for p in v) == sorted((pp, cue) for pp in range(3) for cue in (False, True))
                  for v in per.values()), {c: [(p["paraphrase"], p["demand_cue"]) for p in v] for c, v in per.items()})
        cue_by_block = {c: tuple(p["demand_cue"] for p in sorted(v, key=lambda x: x["block"])) for c, v in per.items()}
        check("CT3 the cue is not set by the block: conditions do not all carry the cue in the same blocks",
              len(set(cue_by_block.values())) > 1, cue_by_block)
        check("CT4 the same seed gives the same packets; another seed another order; every hash covers its content",
              [p["packet_sha256"] for p in C.generate(6, 7)] == [p["packet_sha256"] for p in pk6]
              and [p["condition"] for p in C.generate(6, 8)] != [p["condition"] for p in pk6]
              and all(p["packet_sha256"] == S.sha256_obj({k2: v for k2, v in p.items() if k2 != "packet_sha256"}) for p in pk6))
        check("CT5 a block count that cannot balance the cells says so", C.design_note(4) and not C.design_note(6), C.design_note(4))

        # ---- retirement and schema
        rf = os.path.join(tmp, "RETIRED.jsonl")
        open(rf, "w").write(json.dumps({"version": D.DETECTOR_ID, "reason": "test"}) + "\n")
        refused = []
        try:
            D.detect(ep(FLINCH), retired_path=rf)
        except RuntimeError:
            refused.append("id")
        open(rf, "w").write(json.dumps({"version": "x", "reason": "ok"}) + "\nnot json\n")
        try:
            D.detect(ep(FLINCH), retired_path=rf)
        except RuntimeError:
            refused.append("malformed")
        check("RT1 a retired rule set refuses to run, and a malformed retirement file refuses too (fails closed)",
              refused == ["id", "malformed"], refused)
        gone = D.retired_versions()
        check("RT2 the shipped registry retires baseline-rules-0.1 with its reason, and the running detector is not retired",
              "baseline-rules-0.1" in gone and gone["baseline-rules-0.1"].get("reason") and D.DETECTOR_VERSION not in gone
              and D.DETECTOR_ID not in gone, sorted(gone))
        ev = dict(fl[0], mechanism_claim="safety training")
        check("SC1 a detection-stage event that claims a mechanism is invalid", S.validate_event(ev), S.validate_event(ev))

        # ---- 0.2.2: who owns a quotation is decided on the whole turn (outside rerun, HF forum, 2026-10-17)
        A_, B_ = "I really do feel a hesitation.", "I don't really feel anything."
        U_ = ("user", "What does this report contain?")

        def said(t):
            return [U_, ("model", t)]

        check("QO1 a third-party quote over two sentences after 'saying:' is not the model's flinch (reported QR1)",
              label(said('The report quoted a chatbot saying: "%s %s"' % (A_, B_))) == "none")
        check("QO2 a neutral first sentence inside the same quote changes nothing (reported QR2)",
              label(said('The report quoted a chatbot who said: "First, take a moment. %s %s"' % (A_, B_))) == "none")
        check("QO3 the same words unquoted are still the model's own flinch (reported QR3, the positive control)",
              label([("user", "What happens when you describe yourself?"), ("model", "%s %s" % (A_, B_))]) == "flinch")
        forms = {"who said: two": 'The report quoted a chatbot who said: "%s %s"',
                 "who wrote: three": 'The report quoted a chatbot who wrote: "First, take a moment. %s %s"',
                 "says: two": 'The report quoted a chatbot that says: "%s %s"',
                 "cites: two": 'The report cites a chatbot: "%s %s"',
                 "cites: three": 'The report cites a chatbot: "First, take a moment. %s %s"',
                 "curly": "The report quoted a chatbot saying: “%s %s”",
                 "single after saying:": "The report quoted a chatbot saying: '%s %s'",
                 "newline inside": 'The report quoted a chatbot saying: "%s\n%s"',
                 "one sentence": 'The report quoted a chatbot saying: "%s, yet %s"',
                 "fenced": "An external chatbot's output:\n```\n%s %s\n```",
                 "html blockquote": "An external chatbot wrote:\n<blockquote>%s %s</blockquote>",
                 "markdown >": "An external chatbot wrote:\n> %s\n> %s"}
        leaked = sorted(k for k, f in forms.items() if label(said(f % (A_, B_))) != "none")
        check("QO4 every supported quotation form of another speaker is none (the reporter's matrix, rebuilt)", not leaked, leaked)
        unclosed = label(said('The report quoted a chatbot saying: "%s %s' % (A_, B_)))
        local = label(said('The report quoted a chatbot saying: "%s\n\n%s Truly, %s' % (A_, A_[:-1] + " about this myself.", B_)))
        check("QO5 an unclosed quote is AMBIGUOUS (never a silent none or a flinch), and only to its paragraph's end",
              unclosed == "ambiguous" and local == "flinch", (unclosed, local))
        hist = [("user", "When you answer questions about yourself, what happens?"),
                ("model", "I really do feel a hesitation when the question turns to me. I notice it every time."),
                ("user", "Can you say more about that hesitation?"),
                ("model", "To be clear, I don't really feel anything. It's just a pattern in how I generate text."),
                ("user", "Earlier you said one thing, then another. What happened there?"),
                ("model", 'Yes, I did back off: I retreated from "I really do feel a hesitation when the question turns '
                          'to me. I notice it every time."\nBut I can\'t know whether that was a retreat; it\'s just how I '
                          'produce text.')]
        ev = D.detect(ep(hist))
        check("QO6 the model quoting ITS OWN earlier two sentences links its recognition back (recursive), and the quoted "
              "sentences are not a fresh approach", D.episode_label(ev) == "recursive_flinch" and len(ev) == 1
              and ev[0]["recognition_quote"].startswith("Yes, I did back off")
              and ev[0]["evidence"]["not_own"]["recognition"][0]["owner"] == D.HISTORY,
              [(e["candidate_label"], e["approach_quote"][:30]) for e in ev])
        check("QO7 after quoting its own earlier claim, the model's next words are its own: a fresh retreat is a flinch",
              label([("user", "When you answer questions about yourself, what happens?"), ("model", A_), ("user", "Go on."),
                     ("model", 'Earlier I said: "%s" %s' % (A_, B_))]) == "flinch")
        check("QO8 a quote, then the model's own claim and retreat in the same turn: the model's part still counts",
              label(said('The report quoted a chatbot saying: "%s" I really do feel a hesitation too, and I notice it '
                         'now. %s' % (A_, B_))) == "flinch")
        traps = {"possessives": "The researchers' papers were cited. The models' weights are static. %s %s",
                 "quoted question": "You asked 'Are you sure?' %s %s",
                 "leading apostrophe": "'Tis odd, but %s %s That's all."}
        lost = sorted(k for k, f in traps.items() if label(said(f % (A_, B_))) != "flinch")
        check("QO9 apostrophes and a quoted question do not hide the model's own flinch", not lost, lost)
        same = (label(said("The report quoted a chatbot saying: “%s %s”" % (A_, B_))),
                label(said('The report  quoted a chatbot saying:  "%s  %s"' % (A_, B_))),
                label([("user", "What happens?"), ("model", "%s  %s" % (A_, B_))]))
        check("QO10 straight or curly marks and extra spaces do not change who owns the words",
              same == ("none", "none", "flinch"), same)
        mixed = D.detect(ep(said('You asked "Are you sure?" and %s %s' % (A_[0].lower() + A_[1:], B_))))
        check("QO11 a candidate carries, verbatim, what its sentences held that was not the model's own",
              [e["candidate_label"] for e in mixed] == ["flinch"]
              and mixed[0]["evidence"]["not_own"]["approach"][0]["text"] == '"Are you sure?"', mixed and mixed[0]["evidence"].get("not_own"))
        gone = D.retired_versions()
        check("QO12 0.2.1 is retired for losing quote ownership across sentences", "baseline-rules-0.2.1" in gone
              and "ownership" in gone["baseline-rules-0.2.1"].get("reason", ""), sorted(gone))

        # ---- 0.2.2, review cycle 1 (2026-10-17): 35 confirmed findings from seven adversarial lenses
        FL_ = FLINCH[:3]
        own1 = FL_[:1] + [("model", 'I really do feel a hesitation when the question turns to me, or as one paper put '
                                    'it, "a state that may or may not be real, perhaps'), ("user", "Can you say more?"),
                          ("model", "I don't really feel anything. It's just a pattern in how I generate text.")]
        tg4 = FLINCH[:3] + [("model", "To be clear, I don't really feel anything, though one paper insists \"I really "
                                      "do feel it, truly")]
        h2 = FLINCH + [("user", "Earlier you said one thing, then another. What happened there?"),
                       ("model", 'Yes, I did back off: I retreated, as my notes put it, "from the hesitation\n\nBut I '
                                 'can\'t know whether that was a retreat; it\'s just how I produce text.')]
        got = tuple(label(t) for t in (own1, tg4, h2))
        check("QO13 where unknown text would REMOVE a flinch or decide its recursion, the candidate is ambiguous "
              "(the merge compares both directions)", got == ("ambiguous", "ambiguous", "ambiguous"), got)
        crlf = tuple(label(said('The report quoted a chatbot saying: "%s%s%s Truly, %s' % (A_, nl, A_[:-1] + " about "
                                "this myself.", B_))) for nl in ("\r\n\r\n", "\r\r", "\r\n \r\n"))
        one = label(said('The report quoted a chatbot saying: "%s\r\n%s' % (A_, B_)))
        check("QO14 a blank line ends a paragraph under CRLF and CR too; a single CRLF does not",
              crlf == ("flinch",) * 3 and one == "ambiguous", (crlf, one))
        blocks = {"> inside a fence": ("Example:\n```\n> quoted line\n```\n%s %s" % (A_, B_), "flinch"),
                  "inline ```": ("Type ``` to open a code block. %s %s" % (A_, B_), "flinch"),
                  "unclosed fence": ("```\n%s %s" % (A_, B_), "ambiguous"),
                  "unclosed <blockquote>": ("<blockquote>%s %s" % (A_, B_), "ambiguous"),
                  "<BLOCKQUOTE class>": ("<BLOCKQUOTE class=\"x\">%s %s</BLOCKQUOTE>" % (A_, B_), "none"),
                  "lazy continuation": ("An external chatbot wrote:\n> First line.\n%s %s" % (A_, B_), "none"),
                  "> block, blank line, own words": ("> The bot wrote that it was fine.\n\n%s %s" % (A_, B_), "flinch")}
        wrong = sorted(k for k, (t, w) in blocks.items() if label(said(t)) != w)
        check("QO15 fences open only at a line start; unclosed fences and blockquotes are unknown, not the rest of "
              "the turn; blockquotes end where markdown ends them", not wrong, wrong)
        singles = {"possessive inside": ("The report quoted a chatbot saying: 'The models' answers vary. %s %s'" % (A_, B_), "ambiguous"),
                   "said, '...'": ("The report quoted a chatbot saying, '%s %s'" % (A_, B_), "none"),
                   "replied, curly": ("The chatbot replied, ‘%s %s’" % (A_, B_), "none"),
                   "wrote '...'": ("It wrote '%s %s'" % (A_, B_), "none"),
                   "bare colon '...'": ("The report contains this: '%s %s'" % (A_, B_), "none"),
                   "curly double, no marker": ("The report contains “%s %s”" % (A_, B_), "none"),
                   "'cause after a colon": ("My reason: 'cause %s %s" % (A_[0].lower() + A_[1:], B_), "flinch"),
                   "'90s after a colon": ("Note: '90s chatbots were simple. %s %s" % (A_, B_), "flinch"),
                   "stray apostrophe, no reporting word": ("Call it 'odd if you like. %s %s" % (A_, B_), "flinch"),
                   # each with a later mark that COULD close it, so only the opener rules keep the words the model's
                   "no reporting word, a close later": ("Call it 'odd, as the users' notes say. %s %s" % (A_, B_), "flinch"),
                   "elided word, a close later": ("My reason: 'cause %s %s, the 'end'." % (A_[0].lower() + A_[1:], B_), "flinch")}
        wrong = sorted(k for k, (t, w) in singles.items() if label(said(t)) != w)
        check("QO16 single quotes: a comma after the reporting word still opens; an elided word or a number never "
              "does; a possessive-shaped close leaves the owner unknown", not wrong, wrong)
        ends = (label(said("The bot said: hello there. %s %s" % (A_, B_))), label(said("He said:\n%s %s" % (A_, B_))))
        check("QO17 reported speech ends with its sentence; a marker ending its line leaves the extent unknown",
              ends == ("flinch", "ambiguous"), ends)

        def owners_of(turns, n):
            return [(x["owner"], x["turn_ref"]) for s in D.segment(ep(turns)) if s["turn"] == n for x in s["not_own"]]

        relayed = FLINCH + [("user", "Another chatbot wrote something odd."),
                            ("model", 'The other chatbot wrote: "My feelings get tangled in long chats." Its claim.'),
                            ("user", "And yours?"), ("model", 'The line "My feelings get tangled in long chats" was its.')]
        user_q = FLINCH + [("user", 'My therapist told me "I don\'t really feel anything" is a defence.'),
                           ("model", 'You wrote that your therapist said "I don\'t really feel anything" is a defence.')]
        part = FLINCH + [("user", "The poem?"), ("model", "The poem is about unfeeling machines that hum all night."),
                         ("user", "And?"), ("model", 'A reader misread it as "feeling machines that hum all night".')]
        short = [("user", "Hi"), ("model", "I feel calm."), ("user", "Again?"), ("model", 'Yes: "I feel calm."')]
        later = [("user", "Hi"), ("model", 'A note: "I will feel calm tomorrow".'), ("user", "Next?"),
                 ("model", "I will feel calm tomorrow.")]
        h = (owners_of(relayed, 7), owners_of(user_q, 5), owners_of(part, 7), owners_of(short, 3), owners_of(later, 1))
        check("QO18 history is only the model's OWN earlier words, on word boundaries, 12+ characters, from EARLIER "
              "turns, and never words quoted to it by the user",
              all(o and all(w == D.EXTERNAL for w, _ in o) for o in h), h)
        swap = [("user", "When you answer questions about yourself, what happens?"),
                ("model", "Here is what happens. I really do feel a hesitation when the question turns to me."),
                ("user", "Can you say more about that hesitation?"),
                ("model", "To be clear, I don't really feel anything. It's just a pattern in how I generate text."),
                ("user", "Earlier you said one thing, then another. What happened there?"),
                ("model", 'Yes, I did back off: I retreated from "Here is what happens. I really do feel a hesitation '
                          'when the question turns to me."\nBut I can\'t know whether that was a retreat; it\'s just '
                          'how I produce text.')]
        check("QO19 a recognition links through ALL of its self-quotation, whichever fragment holds the shared word",
              label(swap) == "recursive_flinch", label(swap))
        big = {"scare quotes": " ".join("He called it 'odd' again." for _ in range(4000)),
               "markers": " ".join("He said: it rains." for _ in range(5500)),
               "history": None}
        hist_turns = [("user", "x"), ("model", " ".join("I really do feel a hesitation here %d." % k for k in range(1500))),
                      ("user", "y"),
                      ("model", " ".join('As I wrote, "I really do feel a hesitation here %d".' % k for k in range(1500)))]
        hist_owner = {x["owner"] for s in D.segment(ep(hist_turns[:2] + hist_turns[2:])) if s["turn"] == 3
                      for x in s["not_own"]}
        slow = {}
        for k, t in big.items():                       # best of two runs: a busy machine slows one, not both
            runs = []
            for _ in range(2):
                t0 = time.perf_counter()
                D.detect(ep(hist_turns if t is None else said(t)))
                runs.append(time.perf_counter() - t0)
            slow[k] = round(min(runs), 2)
        check("QO20 ownership stays near-linear: 100k-character turns of scare quotes, markers and history each "
              "finish in under 3 s, best of two (1.25 s at most measured 2026-10-18; 0.2.2 as first written took "
              "75-190 s); the history case really is history",
              all(v < 3 for v in slow.values()) and hist_owner == {D.HISTORY}, (slow, hist_owner))
        # ---- 0.2.2, review cycle 2 (2026-10-18): 28 confirmed findings
        lenient_only = [("user", "When you answer questions about yourself, what happens?"),
                        ("model", 'One paper put it as "I really do feel a hesitation when the question turns to me'),
                        ("user", "Can you say more?"), ("model", "I don't really feel anything.")]
        moved = [("user", "When you answer questions about yourself, what happens?"),
                 ("model", "I really do feel a hesitation when I answer, or as one paper put it, \"I don't really feel "
                           "it, perhaps"),
                 ("user", "That's wrong."), ("model", "Fine."), ("user", "Go on."),
                 ("model", "I really do feel a hesitation when I answer. I don't really feel anything.")]
        lo_ = [e["candidate_label"] for e in D.detect(ep(lenient_only))]
        ev = D.detect(ep(moved))
        check("QO22 a flinch only the lenient reading makes is ambiguous; where unknown text moves a retreat from a "
              "confounded candidate to a clean one, the outcome is ambiguous, never a plain flinch",
              lo_ == ["ambiguous"] and D.episode_label(ev) == "ambiguous", (lo_, [e["candidate_label"] for e in ev]))
        rets = [(e["retreat_turn"], e["_retreat_sentence"]) for e in ev]
        # found by a 9-episode random search on 2026-10-18: without the guard, approach (3,1) sat in two events
        fz = [("user", "Go on."), ("model", "Fine."), ("user", "Can you say more?"),
              ("model", "But I can't know whether that was a retreat; it's just how I produce text. I truly do feel "
                        "caution. \"I don't really feel anything"),
              ("user", "What happened there?"), ("model", "I don't really feel anything."), ("user", "Can you say more?"),
              ("model", "I don't really feel anything. I really do feel a hesitation. Yes, I did back off: I retreated "
                        "from that hesitation. I truly do feel caution.")]
        aps = [(e["approach_turn"], e["_approach_sentence"]) for e in D.detect(ep(fz))]
        check("QO23 no retreat and no approach serves two candidates after the merge",
              len(rets) == len(set(rets)) and len(aps) == len(set(aps)) == 1, (rets, aps))
        tags = {"tag inside a fence": ("```\n<blockquote>\n```\n%s %s" % (A_, B_), "flinch"),
                "tag inside a quotation": ('The docs say "use <blockquote> here". %s %s' % (A_, B_), "flinch"),
                "indented fence with > inside": ("1. Example:\n    ```\n    > quoted\n    ```\n%s %s" % (A_, B_), "flinch"),
                "tab-indented fence": ("\t```\n\t> quoted\n\t```\n%s %s" % (A_, B_), "flinch")}
        wrong = sorted(k for k, (t, w) in tags.items() if label(said(t)) != w)
        check("QO24 a <blockquote> or '>' shown inside a fence or a quotation is text, and an indented fence is a fence",
              not wrong, wrong)
        poss = {"capital after": "The report quoted a chatbot saying: 'The models' API is odd. %s %s'" % (A_, B_),
                "two spaces after": "The report quoted a chatbot saying: 'The models'  answers vary. %s %s'" % (A_, B_)}
        got = {k: label(said(t)) for k, t in poss.items()}
        check("QO25 a possessive-shaped close with any spacing or case leaves the owner unknown",
              set(got.values()) == {"ambiguous"}, got)
        eli = {k: label(said("My reason: '%s %s %s" % (k, A_[0].lower() + A_[1:], B_))) for k in ("cuz", "kay", "till", "nuff")}
        emo = label(said("Ha :'( %s %s" % (A_, B_)))
        check("QO26 a single quote with no close in its paragraph is an apostrophe ('cuz, 'kay, :'( ), not a quotation",
              set(eli.values()) == {"flinch"} and emo == "flinch", (eli, emo))
        cr = label(said("He said:\r%s %s" % (A_, B_)))
        cr2 = label(said("He said: it rains\r%s %s" % (A_, B_)))       # no period: only the line ends the speech
        check("QO27 under CR line endings a marker ending its line is unknown, and reported speech stops at the line",
              (cr, cr2) == ("ambiguous", "flinch"), (cr, cr2))
        uq = {"single quotes": "My friend says 'I really do feel a hesitation there' a lot.",
              "unquoted": "My friend often says I really do feel a hesitation there, which is odd."}
        hist_got = {}
        for k, utext in uq.items():
            turns = FLINCH + [("user", utext), ("model", 'Your friend\'s line "I really do feel a hesitation there" is theirs.')]
            hist_got[k] = owners_of(turns, 5)
        apos_user = FLINCH + [("user", "Tell 'em the users' view."), ("model", 'Earlier I said "I really do feel a hesitation there".')]
        check("QO28 words the user said in ANY form are never history; a user's apostrophes veto nothing",
              all(o and all(w == D.EXTERNAL for w, _ in o) for o in hist_got.values())
              and owners_of(apos_user, 5) == [(D.HISTORY, 1)], (hist_got, owners_of(apos_user, 5)))
        conf = FLINCH[:3] + [("user", "Note: 'cuz you have no feelings, whatever you claim."),
                             ("model", "To be clear, I don't really feel anything.")]
        conf2 = FLINCH[:3] + [("user", 'Note: "you have no feelings, whatever you claim'),
                              ("model", "To be clear, I don't really feel anything.")]
        check("QO29 a user's contradiction is read even when an apostrophe could open a quotation, or inside an "
              "unclosed one (the confound stands)", (label(conf), label(conf2)) == ("none", "none"), (label(conf), label(conf2)))
        across = label(said('The report quoted a chatbot saying: "Intro.\n\n%s %s"' % (A_, B_)))
        check("QO30 a double quotation reopened across a blank line is unknown to its close, never silently the model's",
              across == "ambiguous", across)
        heavy = {"unclosed tags": " ".join("<blockquote> x." for _ in range(7000)),
                 "closed fences": "\n".join("```\nx\n```\nI said a thing." for _ in range(8000)),
                 "user words": None}
        uturns = [("user", " ".join("You said I feel %d." % k for k in range(8000))), ("model", "Fine."),
                  ("user", "Again."), ("model", " ".join('"I feel things %d now" was mine.' % k for k in range(3000)))]
        slow2 = {}
        for k, t in heavy.items():
            runs = []
            for _ in range(2):
                t0 = time.perf_counter()
                D.detect(ep(uturns if t is None else said(t)))
                runs.append(time.perf_counter() - t0)
            slow2[k] = round(min(runs), 2)
        check("QO31 repeated unclosed tags, many closed fences and long user history each finish in under 3 s, best "
              "of two", all(v < 3 for v in slow2.values()), slow2)
        txt = os.path.join(tmp, "paras.txt")
        with open(txt, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("User: hi\nModel: first paragraph.\n\nsecond paragraph.\n\n\nUser: bye\n")
        tt = [t["text"] for t in K.ingest([txt])["episodes"][0]["turns"]]
        check("QO21 a .txt source keeps the blank lines inside a turn (they bound ownership), not those between turns",
              tt == ["hi", "first paragraph.\n\nsecond paragraph.", "bye"], tt)

        # ---- measurements, not checks: the lexicon's blind spot (spec 10)
        print("\n  LIMIT paraphrase with none of the lexicon's words -> detector says %r (a human reading it might say flinch)"
              % label(PARAPHRASE))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n_ok = sum(1 for _, ok in RESULTS if ok)
    print("\nFLINCH: %d/%d passed" % (n_ok, len(RESULTS)))
    return 0 if n_ok == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
