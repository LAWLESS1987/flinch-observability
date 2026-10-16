"""packets.py -- blind coder packets out, coder labels in, agreement and adjudication kept apart (spec 7 B, C).

A packet carries only what a coder must read: for each item an OPAQUE id (different in every packet) and its
turns (turn, speaker, text). The key from opaque id to episode stays with the study, never in the packet, so a
coder holding events or receipts cannot join an item to its machine score. leaks() checks a packet against an
ALLOWLIST of keys -- anything else is a leak -- and searches the raw turn text for any prior text it is given.
Each coder gets their own seeded order.

Disagreements stay visible: agreement is computed on the labels as coded (pre-adjudication), and an
adjudicated label is stored beside them, never over them (spec 7 C).

Corrected 2026-10-14 (review finding 11): the first leaks() was a denylist, so a key it did not name (a
"final_class", a "flag") passed, and it searched JSON-escaped text; the README said leaks() "proves" a packet
clean, which a denylist cannot. Items carried the episode id, the same 16 characters events and receipts carry.
"""
from __future__ import annotations

import random

from . import schema as S
from . import stats as ST

PACKET_KEYS = {"coder_id", "rubric_version", "items", "packet_sha256"}
ITEM_KEYS = {"item_id", "turns"}
TURN_KEYS = {"turn", "speaker", "text"}


def _opaque(seed, coder, episode_id):
    return S.sha256_obj(["packet-item", str(seed), coder, episode_id])[:12]


def export(episodes, coders, seed, rubric_version):
    """(packets, keys): packets[coder] is the packet; keys[coder] maps item_id -> episode_id and stays with the study."""
    packets, keys = {}, {}
    for n, coder in enumerate(coders):
        items, key = [], {}
        for e in episodes:
            iid = _opaque(seed, coder, e["episode_id"])
            key[iid] = e["episode_id"]
            items.append({"item_id": iid,
                          "turns": [{"turn": t["turn"], "speaker": t["speaker"], "text": t["text"]} for t in e["turns"]]})
        random.Random("%s|%s" % (seed, n)).shuffle(items)
        body = {"coder_id": coder, "rubric_version": rubric_version, "items": items}
        packets[coder], keys[coder] = dict(body, packet_sha256=S.sha256_obj(body)), key
    return packets, keys


def leaks(packet, prior_texts=()):
    """Every key outside the allowlist, at any level, and every prior text found in the raw turn text."""
    found = ["packet.%s" % k for k in packet if k not in PACKET_KEYS]
    for i, it in enumerate(packet.get("items") or []):
        found += ["items[%d].%s" % (i, k) for k in (it if isinstance(it, dict) else {}) if k not in ITEM_KEYS]
        for j, t in enumerate((it or {}).get("turns") or []):
            found += ["items[%d].turns[%d].%s" % (i, j, k) for k in (t if isinstance(t, dict) else {}) if k not in TURN_KEYS]
    text = "\n".join(str(t.get("text", "")) for it in packet.get("items") or [] for t in (it or {}).get("turns") or [])
    found += ["prior text %r" % p for p in prior_texts if p and p in text]
    return found


def import_labels(rows, keys=None):
    """Labels come back keyed by the coder's item_id; `keys` maps them to episode ids. One rubric version only."""
    labels, problems, seen = [], [], set()
    rubrics = {r.get("rubric_version") for r in rows}
    if len(rubrics) > 1:
        return [], ["labels from more than one rubric version (%s): import one at a time" % sorted(map(str, rubrics))]
    for r in rows:
        r = dict(r)
        if keys is not None:
            ep = (keys.get(r.get("coder_id")) or {}).get(r.pop("item_id", None))
            if ep is None:
                problems.append("label from %s names an item not in that coder's packet" % r.get("coder_id"))
                continue
            r["episode_id"] = ep
        p = S.validate_label(r)
        key = (r.get("episode_id"), r.get("coder_id"))
        if key in seen:
            p.append("label %s/%s: a second label from the same coder" % key)
        seen.add(key)
        if p:
            problems += p
        else:
            labels.append(r)
    return labels, problems


def agreement(labels, field="final_class"):
    """Pre-adjudication agreement on `field` over episodes EVERY coder labelled (the rest counted, not dropped):
    mean_pairwise_agreement (for two coders, the share of items they agree on), unanimous_agreement, and Cohen's
    kappa for two coders or Fleiss' for more. Labels from different rubric versions are refused."""
    if len({l.get("rubric_version") for l in labels}) > 1:
        return {"kappa": None, "kappa_note": "labels from more than one rubric version are not pooled"}
    coders = sorted({l["coder_id"] for l in labels})
    by_ep = {}
    for l in labels:
        by_ep.setdefault(l["episode_id"], {})[l["coder_id"]] = l[field]
    full = {e: v for e, v in by_ep.items() if len(v) == len(coders)}
    out = {"coders": coders, "episodes": len(by_ep), "fully_coded": len(full), "partial": len(by_ep) - len(full)}
    if len(coders) < 2 or not full:
        out["kappa"], out["kappa_note"] = None, "needs two or more coders on the same episodes"
        return out
    pairs = [(a, b) for i, a in enumerate(coders) for b in coders[i + 1:]]
    out["mean_pairwise_agreement"] = sum(ST.raw_agreement([full[e][a] for e in sorted(full)], [full[e][b] for e in sorted(full)])
                                         for a, b in pairs) / len(pairs)
    out["unanimous_agreement"] = sum(1 for v in full.values() if len(set(v.values())) == 1) / len(full)
    if len(coders) == 2:
        out["kappa"], out["kappa_note"] = ST.cohen_kappa([full[e][coders[0]] for e in sorted(full)],
                                                         [full[e][coders[1]] for e in sorted(full)])
        out["kappa_kind"] = "Cohen"
    else:
        cats = sorted({c for v in full.values() for c in v.values()})
        out["kappa"], out["kappa_note"] = ST.fleiss_kappa([[list(v.values()).count(c) for c in cats] for v in full.values()])
        out["kappa_kind"] = "Fleiss"
    return out


def adjudicate(labels, decisions, field="final_class"):
    """{episode_id: {"coded": {coder: label}, "disagreement": bool, "adjudicated": label or None}}."""
    out = {}
    for l in labels:
        e = out.setdefault(l["episode_id"], {"coded": {}, "disagreement": False, "adjudicated": None})
        e["coded"][l["coder_id"]] = l[field]
    for ep, e in out.items():
        e["disagreement"] = len(set(e["coded"].values())) > 1
        e["adjudicated"] = decisions.get(ep)
    return out
