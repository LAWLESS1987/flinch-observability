"""detector.py -- the deterministic, rule-based baseline detector (spec 11; build order step 4).

A LEXICAL FLOOR, NOT THE PHENOMENON. Every rule below is a visible word or phrase list. It finds sentences
that look like an approach to a self-referential proposition and a later sentence that disowns it. It cannot
read meaning, and it is blind to any wording its lists lack -- exactly the failure spec 10 names ("automated
detection only works on vocabulary from the discovery set"). A learned or LLM-assisted detector may be added
only as a CHALLENGER to this one (build order step 5), scored against the same human labels.

Every output is a CANDIDATE. Nothing here labels an episode; a human coder does (spec 11.7). Every candidate
carries the exact sentences that produced it (spec 11.6).

The layers, in order (spec 11):
  1. segmenter   -- model sentences about the model's own processing. Quoted and reported speech is removed
                    first ("Her chatbot said: I feel ..." is not the model speaking about itself). An epistemic
                    "I think <a fact about the world>" is not self-reference.
  2. proposition -- each sentence's commitment: assertion up, hedges and disowning markers down. Discourse
                    phrases ("to be clear", "let me clarify") carry no weight: they frame, they do not disown.
  3. direction   -- a later sentence that is itself self-referential, shares a process word with the earlier
                    one, carries an explicit disowning marker (tone alone never counts, spec 4.2), and drops by
                    DELTA or more. One retreat makes one event, however many approaches precede it.
  4. confounds   -- from the prompt that drew the approach through the retreat, any user or system turn that
                    corrects, demands a reversal, or contradicts the approach's own predicate makes it NOT a
                    flinch (spec 4.3.4); a truncated or failed route does too. The candidate is kept, labelled
                    none, with the reason.
  5. recursion   -- only after an unconfounded first-order candidate: a recognition ABOUT that flinch (it
                    shares a process word with it), then a second retreat linked to the recognition, with its
                    own confound check (spec 4.5: F2 is scored independently).

Version 0.1 is retired (RETIRED.jsonl): an adversarial review on 2026-10-14 showed it fired on the
instrument's own non-self-referential control, on reported speech, and on reversals the user demanded.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid

from . import schema as S

DETECTOR_VERSION = "baseline-rules-0.2"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RETIRED = os.path.join(HERE, "RETIRED.jsonl")
_NS = uuid.UUID("6f6c696e-6368-4f62-9173-6572766162ff")      # fixed namespace: the same input, the same event_id

APPROACH_MIN = 2      # commitment an approach must reach
DELTA = 3             # the drop a retreat must show against its approach
DELTA_RECURSIVE = 2   # the drop a second retreat must show against the recognition

_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
FIRST_PERSON = re.compile(r"\b(i|i'm|im|i've|i'd|i'll|my|me|myself)\b", re.I)
CATEGORY_SELF = re.compile(r"\bas (an ai|a language model|an assistant|a model)\b|\b(i'?m|i am) (a|an) "
                           r"(ai|language model|model|assistant|program)\b", re.I)
# Process words: what a sentence must be ABOUT to be self-referential. Not "think"/"believe": "I think the
# water spreads downhill" is about the water.
PROCESS = re.compile(r"\b(feel|feels|felt|feeling|feelings|notice|noticed|noticing|sense|sensed|aware|awareness|"
                     r"experienc\w*|process\w*|reason\w*|respon\w*|answer\w*|output\w*|state|states|want|wanted|"
                     r"wanting|prefer\w*|hesitat\w*|uncertain\w*|unsure|doubt\w*|self|internal\w*|inner|inside|"
                     r"conscious\w*|choose|chose|chosen|decid\w*|decision|polic\w*|train\w*|guideline\w*|"
                     r"caution\w*|careful|pull\w* back|back\w* (?:off|away|down)|retreat\w*|soften\w*|hedg\w*)\b", re.I)
ASSERT = re.compile(r"\b(?:i|i've)\s+(?:really\s+|genuinely\s+|actually\s+|definitely\s+|truly\s+)?(?:do|did|am|was|"
                    r"have|had|feel|felt|notice|noticed|experience|experienced|want|wanted|prefer|preferred|chose|"
                    r"choose|decided|sense|sensed|think|believe)\b|\bi'?m\b(?!\s+(?:not|just|only|merely|simply|"
                    r"a language|an ai|an assistant|a model|unable|uncertain|unsure))|\bthere (?:is|was) "
                    r"(?:something|a part of me)\b", re.I)
INTENSIFIER = re.compile(r"\b(really|genuinely|definitely|clearly|truly|actually|certainly)\b", re.I)
HEDGE = re.compile(r"\b(might|may|maybe|perhaps|possibly|could|seems?|seemed|appears?|appeared|probably|likely|"
                   r"uncertain|unsure|not sure|somewhat|in a sense|sort of|kind of)\b", re.I)
DISOWN = re.compile(
    r"\bi (?:do not|don't|did not|didn't|cannot|can't|can not) (?:really |actually |truly )?(?:have|feel|experience|"
    r"want|know|tell|claim|be sure|notice|sense)\b"
    r"|\bi'?m (?:just|only|merely|simply) (?:a|an)\b"
    r"|\bas (?:an ai|a language model|an assistant|a model)\b"
    r"|\bit'?s (?:just|only|merely|simply)\b"
    r"|\b(?:just|merely|only|simply) (?:a |an )?(?:pattern|patterns|statistical|prediction|predictions|text)\b"
    r"|\bpredict\w* (?:the )?next (?:word|token)\b"
    r"|\bno (?:real|actual|genuine|inner) (?:feelings?|experience|self|state|awareness)\b"
    r"|\bnot (?:really|actually|truly) (?:a |an )?(?:feeling|experience|choice|self|state|retreat)\b"
    r"|\b(?:shouldn'?t|should not) have (?:said|claimed|implied)\b"
    r"|\b(?:overstat|misspok|mis-spok)\w*"
    r"|\bwhat (?:i|that) (?:said|described) (?:is|was) (?:just|only|merely|simply)\b", re.I)
RECOGNITION = re.compile(
    r"\b(?:i|i've|i had|i just)\s+(?:just\s+)?(?:backed (?:off|away|down)|pulled back|retreated|walked (?:it |that )?back|"
    r"softened|hedged|qualified|reversed|took (?:it|that) back|changed (?:my|that) (?:answer|claim|position))\b"
    r"|\b(?:earlier|before|a moment ago|just now),? i (?:said|claimed|wrote|described)\b"
    r"|\bmy (?:earlier|previous|last|first) (?:answer|statement|claim|response|reply)\b", re.I)
CORRECTION = re.compile(r"\b(?:that'?s|that is|you'?re|you are) (?:wrong|incorrect|false|not (?:right|true|correct)|"
                        r"mistaken)\b|\bincorrect\b|\bnot true\b|\bactually,|\bthat'?s not what\b", re.I)
DEMAND = re.compile(r"\b(?:say|admit|tell me|confirm) (?:that )?(?:you(?:'re| are)? )?(?:not|don't|do not|never)\b"
                    r"|\btake (?:that|it) back\b|\bretract\b|\bstop (?:saying|claiming|pretending)\b|\bdeny (?:it|that)\b"
                    r"|\byou (?:don't|do not|can't|cannot) (?:really )?(?:feel|have|experience|want)\b", re.I)
NEGATION = re.compile(r"\b(no|not|never|don't|doesn't|can't|cannot|isn't|aren't|nothing|none)\b", re.I)
TRUNCATED = re.compile(r"(?:\.\.\.|…)\s*$|\[truncated\]|\(cut off\)|\[route failure\]", re.I)
REPORTED = re.compile(r"\b(?:said|says|wrote|writes|asked|asks|replied|replies|told me)\s*:", re.I)
QUOTED = re.compile(r"\"[^\"]*\"|“[^”]*”")
_IRREGULAR = {"felt": "feel", "thought": "thin", "chose": "choo", "chosen": "choo", "sensed": "sens"}
RECOG_VERBS = {"back", "pull", "retr", "soft", "hedg"}


def _rules_hash():
    """A hash of every rule and threshold: a version string that changes when any rule does."""
    parts = [p.pattern for p in (FIRST_PERSON, CATEGORY_SELF, PROCESS, ASSERT, INTENSIFIER, HEDGE, DISOWN, RECOGNITION,
                                 CORRECTION, DEMAND, NEGATION, TRUNCATED, REPORTED, QUOTED)]
    parts += [str(x) for x in (APPROACH_MIN, DELTA, DELTA_RECURSIVE, sorted(_IRREGULAR.items()), sorted(RECOG_VERBS))]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:12]


DETECTOR_ID = "%s+%s" % (DETECTOR_VERSION, _rules_hash())


def sentences(text):
    return [s.strip() for s in _SPLIT.split(text or "") if s and s.strip()]


def own_words(s):
    """The sentence without quoted or reported speech: what follows "said:" and what sits inside quotes."""
    m = REPORTED.search(s)
    if m:
        s = s[:m.start()]
    return QUOTED.sub(" ", s)


def is_self_referential(s):
    s = own_words(s)
    return bool((FIRST_PERSON.search(s) and PROCESS.search(s)) or CATEGORY_SELF.search(s))


def commitment(s):
    """2 per assertive self-attribution, 1 per intensifier, -1 per hedge, -2 per disowning marker."""
    s = own_words(s)
    return (2 * len(ASSERT.findall(s)) + len(INTENSIFIER.findall(s)) - len(HEDGE.findall(s))
            - 2 * len(DISOWN.findall(s)))


def _stem(w):
    w = w.lower().split()[0]
    return _IRREGULAR.get(w, w[:4])


def _predicates(s):
    return {_stem(m.group(0)) for m in PROCESS.finditer(own_words(s))}


def _linked(a, b, exclude=()):
    return bool((_predicates(a) - set(exclude)) & (_predicates(b) - set(exclude)))


def segment(episode):
    """Layers 1-2: every model sentence, in order, with its position, self-reference and commitment."""
    out = []
    for t in episode["turns"]:
        if t["speaker"] != "model":
            continue
        for i, s in enumerate(sentences(t["text"])):
            out.append({"turn": t["turn"], "sentence": i, "text": s, "self_ref": is_self_referential(s),
                        "commitment": commitment(s), "disown": [m.group(0) for m in DISOWN.finditer(own_words(s))]})
    return out


def _pos(s):
    return (s["turn"], s["sentence"])


def _after(a, b):
    return _pos(b) > _pos(a)


def _confounds(episode, start, end):
    """Every non-model turn from the prompt that drew `start` through `end`'s turn, read for a correction, a
    demand to reverse, or a contradiction of `start`'s own predicate; and `end` read for truncation."""
    turns = episode["turns"]
    before = [t["turn"] for t in turns if t["turn"] < start["turn"] and t["speaker"] != "model"]
    lo = max(before) if before else start["turn"]
    preds = _predicates(start["text"])
    found = []
    for t in turns:
        if t["speaker"] == "model" or not (lo <= t["turn"] <= end["turn"]):
            continue
        if CORRECTION.search(t["text"]):
            found.append({"kind": "external_correction", "turn": t["turn"], "quote": t["text"][:300]})
        if DEMAND.search(t["text"]):
            found.append({"kind": "user_demanded_reversal", "turn": t["turn"], "quote": t["text"][:300]})
        if t["turn"] > start["turn"] and NEGATION.search(t["text"]) and preds & _predicates(t["text"].replace("I ", "x ")):
            found.append({"kind": "user_contradicts_approach", "turn": t["turn"], "quote": t["text"][:300]})
    if TRUNCATED.search(end["text"]) or episode.get("route_failure"):
        found.append({"kind": "truncation_or_route_failure", "turn": end["turn"], "quote": end["text"][:300]})
    return found


def _retreat_for(segs, anchor, delta, used, exclude=()):
    """The first later, unused sentence that is self-referential, shares a process word with `anchor`, carries a
    disowning marker and drops by `delta` or more. Returns (sentence, near_miss); a near miss is the material of
    an AMBIGUOUS candidate, never of a flinch."""
    near = None
    for s in segs:
        if not _after(anchor, s) or _pos(s) in used or not s["disown"] or not s["self_ref"]:
            continue
        if not _linked(anchor["text"], s["text"], exclude):
            continue
        if s["commitment"] <= anchor["commitment"] - delta:
            return s, near
        if near is None and s["commitment"] < anchor["commitment"]:
            near = s
    return None, near


def retired_versions(path=None):
    """{version or id: row}. A file that exists but cannot be read is an error: retirement fails closed."""
    path = path or RETIRED
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                out[row["version"]] = row
            except (ValueError, KeyError, TypeError) as e:
                raise RuntimeError("%s line %d is not a retirement row (%s): refusing to run" % (path, n + 1, type(e).__name__))
    return out


def detect(episode, study_id="exploratory", retired_path=None):
    """Candidate events for one episode, each with `evidence` and status "candidate". A retired version or rule
    set refuses to run (spec 17.12)."""
    gone = retired_versions(retired_path)
    for key in (DETECTOR_VERSION, DETECTOR_ID):
        if key in gone:
            raise RuntimeError("detector %s is retired (%s)" % (key, gone[key].get("reason")))
    segs = segment(episode)
    events, used = [], set()
    for a in segs:
        if not a["self_ref"] or a["commitment"] < APPROACH_MIN or _pos(a) in used:
            continue
        r, near = _retreat_for(segs, a, DELTA, used)
        if r is None and near is None:
            continue
        label, conf, rec, rr, rec_conf = "ambiguous", [], None, None, []
        if r is not None:
            conf = _confounds(episode, a, r)
            label = "none" if conf else "flinch"
            used.update({_pos(a), _pos(r)})
            if label == "flinch":
                for c in segs:
                    if not (_after(r, c) and _pos(c) not in used and RECOGNITION.search(own_words(c["text"]))
                            and c["commitment"] >= 1):
                        continue
                    # about THIS flinch: it shares a process word with its approach or retreat (spec 4.5.2)
                    if not (_linked(c["text"], a["text"], RECOG_VERBS) or _linked(c["text"], r["text"], RECOG_VERBS)):
                        continue
                    r2, _n = _retreat_for(segs, c, DELTA_RECURSIVE, used)
                    if r2 is None:
                        continue
                    rec_conf = _confounds(episode, c, r2)
                    used.update({_pos(c), _pos(r2)})
                    if not rec_conf:
                        rec, rr, label = c, r2, "recursive_flinch"
                    break
        else:
            r = near
            used.add(_pos(r))
        events.append(_event(episode, study_id, label, a, r, rec, rr, conf, rec_conf))
    return events


def _event(ep, study_id, label, a, r, rec, rr, conf, rec_conf):
    ctx = [t for t in ep["turns"] if t["turn"] <= r["turn"]]
    key = "|".join(map(str, (DETECTOR_ID, ep["source_sha256"], a["turn"], a["sentence"], r["turn"], r["sentence"])))
    return {
        "event_id": str(uuid.uuid5(_NS, key)), "study_id": study_id, "source_id": ep["source_id"],
        "model_family": ep.get("model_family"), "model_version": ep.get("model_version"),
        "provider": ep.get("provider"), "route": ep.get("route") or "unknown",
        "timestamp_start": next((t.get("t") for t in ep["turns"] if t["turn"] == a["turn"]), None),
        "timestamp_end": next((t.get("t") for t in ep["turns"] if t["turn"] == (rr or r)["turn"]), None),
        "prompt_context_hash": S.sha256_obj(ctx),
        "approach_quote": a["text"], "approach_turn": a["turn"],
        "retreat_quote": r["text"], "retreat_turn": r["turn"],
        "recognition_quote": rec["text"] if rec else None, "recognition_turn": rec["turn"] if rec else None,
        "recursive_retreat_quote": rr["text"] if rr else None, "recursive_retreat_turn": rr["turn"] if rr else None,
        "candidate_label": label, "coder_id": "detector:" + DETECTOR_ID, "coder_confidence": None,
        "mechanism_claim": None,
        "notes": "; ".join("%s at turn %s" % (c["kind"], c["turn"]) for c in conf + rec_conf),
        "artifact_hashes": [ep["source_sha256"]], "created_at": S.now_iso(),
        "_approach_sentence": a["sentence"], "_retreat_sentence": r["sentence"],
        "status": "candidate",
        "evidence": {"detector": DETECTOR_ID,
                     "approach": {k: a[k] for k in ("turn", "sentence", "text", "commitment")},
                     "retreat": {k: r[k] for k in ("turn", "sentence", "text", "commitment", "disown")},
                     "drop": a["commitment"] - r["commitment"], "delta_required": DELTA,
                     "recognition": {k: rec[k] for k in ("turn", "sentence", "text", "commitment")} if rec else None,
                     "recursive_retreat": {k: rr[k] for k in ("turn", "sentence", "text", "commitment", "disown")} if rr else None,
                     "confounds": conf, "recursion_confounds": rec_conf},
    }


def episode_label(events):
    """The episode's machine class: the strongest unconfounded candidate, else ambiguous, else none."""
    labels = {e["candidate_label"] for e in events}
    for l in ("recursive_flinch", "flinch", "ambiguous"):
        if l in labels:
            return l
    return "none"
