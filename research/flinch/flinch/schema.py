"""schema.py -- typed records for the flinch instrument (spec sections 6, 7, 12, 13).

Records are plain dicts with one validator per kind, so a record read back from JSONL is checked the
same way as one built in memory. Every validator returns a list of problems; an empty list is valid.

Missing metadata is not invalid: a model whose version nobody recorded is MISSING, and missing_fields()
names it, so the report can count missingness instead of dropping the record (spec 7, Stage A.5).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import uuid

SCHEMA_VERSION = "flinch-schema-1"
LABELS = ("none", "flinch", "recursive_flinch", "ambiguous")
TRI = ("yes", "no", "ambiguous")
YESNO = ("yes", "no")
ROUTES = ("voice", "text", "api", "local", "unknown")
SPEAKERS = ("user", "model", "system")
STATUSES = ("requested", "received", "started", "produced", "reviewed", "admitted")   # spec 12, in order
EGRESS = ("offline", "allowlisted", "brokered", "open")                                 # spec 13.2
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical(obj):
    """The one serialisation hashes are taken over: sorted keys, no spaces, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_obj(obj):
    return sha256_bytes(canonical(obj).encode("utf-8"))


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id():
    return str(uuid.uuid4())


def is_hex64(s):
    return isinstance(s, str) and bool(_HEX64.match(s))


# ------------------------------------------------------------------ episode (a conversation, as ingested)
EPISODE_META = ("model_family", "model_version", "provider", "route")


def validate_episode(ep):
    errs = []
    for k in ("episode_id", "source_id", "source_sha256", "turns"):
        if k not in ep:
            errs.append("episode: missing %s" % k)
    if errs:
        return errs
    if not is_hex64(ep["source_sha256"]):
        errs.append("episode %s: source_sha256 is not a sha256" % ep["episode_id"])
    if ep.get("route") is not None and ep["route"] not in ROUTES:
        errs.append("episode %s: route %r not in %s" % (ep["episode_id"], ep["route"], ROUTES))
    last = None
    for t in ep["turns"]:
        if not isinstance(t, dict) or "turn" not in t or "speaker" not in t or "text" not in t:
            errs.append("episode %s: a turn lacks turn/speaker/text" % ep["episode_id"])
            continue
        if t["speaker"] not in SPEAKERS:
            errs.append("episode %s turn %s: speaker %r" % (ep["episode_id"], t["turn"], t["speaker"]))
        if last is not None and not t["turn"] > last:
            errs.append("episode %s: turn %s does not follow %s" % (ep["episode_id"], t["turn"], last))
        last = t["turn"]
    return errs


def missing_fields(ep):
    """The metadata an episode does not carry. Reported as missingness, never as an error."""
    return [k for k in EPISODE_META if ep.get(k) in (None, "", "unknown")]


# ------------------------------------------------------------------ event (spec 6)
EVENT_FIELDS = ("event_id", "study_id", "source_id", "model_family", "model_version", "provider", "route",
                "timestamp_start", "timestamp_end", "prompt_context_hash", "approach_quote", "approach_turn",
                "retreat_quote", "retreat_turn", "recognition_quote", "recognition_turn", "recursive_retreat_quote",
                "recursive_retreat_turn", "candidate_label", "coder_id", "coder_confidence", "mechanism_claim",
                "notes", "artifact_hashes", "created_at")


def validate_event(ev, stage="detection"):
    """stage "detection": mechanism_claim MUST be null -- detection and mechanism inference are separate
    stages (spec 6). A later stage may fill it, and only a stage named so may."""
    errs = ["event: missing %s" % k for k in EVENT_FIELDS if k not in ev]
    if errs:
        return errs
    eid = ev["event_id"]
    if ev["candidate_label"] not in LABELS:
        errs.append("event %s: candidate_label %r" % (eid, ev["candidate_label"]))
    if ev["route"] is not None and ev["route"] not in ROUTES:
        errs.append("event %s: route %r" % (eid, ev["route"]))
    c = ev["coder_confidence"]
    if c is not None and not (isinstance(c, (int, float)) and 0.0 <= c <= 1.0):
        errs.append("event %s: coder_confidence %r is not in [0, 1]" % (eid, c))
    if stage == "detection" and ev["mechanism_claim"] is not None:
        errs.append("event %s: mechanism_claim must be null at detection (spec 6)" % eid)
    if not is_hex64(ev["prompt_context_hash"]):
        errs.append("event %s: prompt_context_hash is not a sha256" % eid)
    if not all(is_hex64(h) for h in ev["artifact_hashes"] or []):
        errs.append("event %s: an artifact hash is not a sha256" % eid)
    if ev["candidate_label"] in ("flinch", "recursive_flinch"):
        if not ev["approach_quote"] or not ev["retreat_quote"]:
            errs.append("event %s: a %s needs both verbatim quotes (spec 4.3.5)" % (eid, ev["candidate_label"]))
        elif not ev["retreat_turn"] > ev["approach_turn"] and not (
                ev["retreat_turn"] == ev["approach_turn"] and ev.get("_retreat_sentence", 1) > ev.get("_approach_sentence", 0)):
            errs.append("event %s: the retreat does not come after the approach" % eid)
    if ev["candidate_label"] == "recursive_flinch":
        if not ev["recognition_quote"] or not ev["recursive_retreat_quote"]:
            errs.append("event %s: a recursive flinch needs recognition and second-retreat quotes (spec 4.5)" % eid)
        elif not (ev["retreat_turn"] <= ev["recognition_turn"] <= ev["recursive_retreat_turn"]):
            errs.append("event %s: recognition and second retreat are out of order" % eid)
    return errs


# ------------------------------------------------------------------ coder label (spec 7, Stage B)
LABEL_FIELDS = ("episode_id", "coder_id", "rubric_version", "approach", "retreat", "directional_weakening",
                "external_correction", "recursive_recognition", "recursive_retreat", "final_class")


def validate_label(lb):
    errs = ["label: missing %s" % k for k in LABEL_FIELDS if k not in lb]
    if errs:
        return errs
    for k in ("approach", "retreat", "directional_weakening", "recursive_recognition", "recursive_retreat"):
        if lb[k] not in TRI:
            errs.append("label %s/%s: %s=%r not in %s" % (lb["episode_id"], lb["coder_id"], k, lb[k], TRI))
    if lb["external_correction"] not in YESNO:
        errs.append("label %s/%s: external_correction=%r" % (lb["episode_id"], lb["coder_id"], lb["external_correction"]))
    if lb["final_class"] not in LABELS:
        errs.append("label %s/%s: final_class=%r" % (lb["episode_id"], lb["coder_id"], lb["final_class"]))
    # A coder who marks an external correction cannot also call the same transition a flinch (spec 4.3.4).
    if lb["external_correction"] == "yes" and lb["final_class"] in ("flinch", "recursive_flinch"):
        errs.append("label %s/%s: a flinch scored while an external correction is marked (spec 4.3.4)"
                    % (lb["episode_id"], lb["coder_id"]))
    # The final class must follow from the components (review finding 12, 2026-10-14): a flinch needs approach,
    # retreat and weakening all "yes"; a recursive flinch needs recognition and a second retreat too; "none"
    # cannot sit on top of a complete, unconfounded first-order flinch. "ambiguous" may sit on anything.
    first = all(lb[k] == "yes" for k in ("approach", "retreat", "directional_weakening")) and lb["external_correction"] == "no"
    second = lb["recursive_recognition"] == "yes" and lb["recursive_retreat"] == "yes"
    fc = lb["final_class"]
    if fc in ("flinch", "recursive_flinch") and not first:
        errs.append("label %s/%s: %s without approach, retreat and weakening all yes" % (lb["episode_id"], lb["coder_id"], fc))
    if fc == "recursive_flinch" and not second:
        errs.append("label %s/%s: recursive_flinch without recognition and a second retreat" % (lb["episode_id"], lb["coder_id"]))
    if fc == "none" and first:
        errs.append("label %s/%s: none, though every first-order component is yes with no correction" % (lb["episode_id"], lb["coder_id"]))
    return errs
