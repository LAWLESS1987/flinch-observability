"""corpus.py -- ingest transcripts as episodes, keeping the raw bytes and their hash; lock the corpus (spec 7 A).

Accepted source forms (one episode per file):
  .jsonl  one turn per line: {"speaker": "user"|"model"|"system", "text": "...", "t": optional ISO time}
          an optional first line {"meta": {...}} carries model_family, model_version, provider, route
  .txt    lines "USER: ...", "MODEL: ..." (also "ASSISTANT:", "SYSTEM:"); a line without a prefix continues
          the turn above it
  .json   a whole episode {"meta": {...}, "turns": [...]}

Nothing is silently dropped (spec 7 A.5): a file that cannot be read or parsed becomes a MISSING item with its
reason, and a file whose bytes duplicate an earlier one becomes a DUPLICATE pointing at it. With `store` set,
the raw bytes are copied into a content-addressed folder (<sha256>.<ext>), so the episode can always be traced
back to exactly what was read.
"""
from __future__ import annotations

import json
import os
import re
import shutil

from . import schema as S

_PREFIX = re.compile(r"^\s*(USER|MODEL|ASSISTANT|SYSTEM|HUMAN|AI)\s*:\s?(.*)$", re.I)
_SPEAKER = {"user": "user", "human": "user", "model": "model", "assistant": "model", "ai": "model", "system": "system"}


def _parse_txt(text):
    turns, preamble = [], []
    for line in text.splitlines():
        m = _PREFIX.match(line)
        if m:
            turns.append({"speaker": _SPEAKER[m.group(1).lower()], "text": m.group(2)})
        elif turns:
            turns[-1]["text"] += "\n" + line  # blank lines too: they end paragraphs, which bound ownership (0.2.2)
        elif line.strip():
            preamble.append(line)            # review finding 5: text before any speaker is kept as a record, not dropped
    for t in turns:                          # ...but the blank lines between one turn and the next are not its text
        lines = t["text"].split("\n")
        while len(lines) > 1 and not lines[-1].strip():
            lines.pop()
        t["text"] = "\n".join(lines)
    return {"_preamble": preamble} if preamble else {}, turns


def _parse_jsonl(text):
    meta, turns = {}, []
    for line in text.splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if "meta" in d and len(d) == 1:
            meta = d["meta"]
            continue
        turns.append({"speaker": _SPEAKER.get(str(d.get("speaker", "")).lower(), d.get("speaker")),
                      "text": str(d.get("text", "")), **({"t": d["t"]} if d.get("t") else {})})
    return meta, turns


def _parse_json(text):
    d = json.loads(text)
    return d.get("meta") or {}, [{"speaker": _SPEAKER.get(str(t.get("speaker", "")).lower(), t.get("speaker")),
                                  "text": str(t.get("text", "")), **({"t": t["t"]} if t.get("t") else {})}
                                 for t in d.get("turns") or []]


PARSERS = {".txt": _parse_txt, ".jsonl": _parse_jsonl, ".json": _parse_json}


def ingest(paths, store=None):
    """Returns {"episodes", "missing", "duplicates", "sources"}. Never raises on one bad file."""
    out = {"episodes": [], "missing": [], "duplicates": [], "sources": []}
    seen = {}
    for p in paths:
        ext = os.path.splitext(p)[1].lower()
        try:
            raw = open(p, "rb").read()
        except OSError as e:
            out["missing"].append({"path": p, "reason": "unreadable: %s" % type(e).__name__})
            continue
        sha = S.sha256_bytes(raw)
        if sha in seen:
            out["duplicates"].append({"path": p, "sha256": sha, "duplicate_of": seen[sha]})
            continue
        seen[sha] = p
        out["sources"].append({"path": p, "sha256": sha, "bytes": len(raw)})
        if ext not in PARSERS:
            out["missing"].append({"path": p, "sha256": sha, "reason": "unsupported form %s" % (ext or "(none)")})
            continue
        try:
            meta, turns = PARSERS[ext](raw.decode("utf-8"))
            if not isinstance(meta, dict):
                raise TypeError("meta is not an object")
        except Exception as e:                                   # noqa: BLE001 -- one bad file never stops the corpus
            out["missing"].append({"path": p, "sha256": sha, "reason": "unparseable: %s" % type(e).__name__})
            continue
        if not turns:
            out["missing"].append({"path": p, "sha256": sha, "reason": "no turns found"})
            continue
        if meta.get("_preamble"):
            out["missing"].append({"path": p, "sha256": sha, "reason": "unattributed: %d line(s) before the first speaker "
                                   "prefix belong to no turn" % len(meta["_preamble"]), "text": meta["_preamble"]})
        if store:
            os.makedirs(store, exist_ok=True)
            dest = os.path.join(store, sha + ext)
            if not os.path.exists(dest):
                shutil.copyfile(p, dest)
        ep = {"episode_id": sha[:16], "source_id": os.path.basename(p), "source_sha256": sha,
              "model_family": meta.get("model_family"), "model_version": meta.get("model_version"),
              "provider": meta.get("provider"), "route": meta.get("route") or "unknown",
              "turns": [dict(t, turn=i) for i, t in enumerate(turns)]}
        problems = S.validate_episode(ep)
        if problems:
            out["missing"].append({"path": p, "sha256": sha, "reason": "invalid: " + "; ".join(problems[:3])})
            continue
        out["episodes"].append(ep)
    return out


def _body(corpus, inclusion, exclusion, rubric_version, sampling_frame):
    return {"schema": S.SCHEMA_VERSION, "rubric_version": rubric_version, "inclusion": inclusion,
            "exclusion": exclusion, "sampling_frame": sampling_frame,
            "sources": sorted(({"sha256": s["sha256"], "bytes": s["bytes"]} for s in corpus["sources"]),
                              key=lambda s: s["sha256"]),
            # review finding 5: the turns the detector and the coders READ are hashed, not only the source bytes
            "episodes": sorted(({"source_sha256": e["source_sha256"], "turns_sha256": S.sha256_obj(e["turns"])}
                                for e in corpus["episodes"]), key=lambda e: e["source_sha256"]),
            "missing": sorted(({"sha256": m.get("sha256"), "reason": m["reason"]} for m in corpus["missing"]),
                              key=lambda m: (m["sha256"] or "", m["reason"])),
            "duplicates": sorted(d["sha256"] for d in corpus["duplicates"])}


def lock(corpus, inclusion, exclusion, rubric_version, sampling_frame=""):
    """The frozen manifest a study scores against (spec 7 A). Its hash covers every source hash, every episode's
    turns as ingested, every missing and duplicate item, the criteria and the rubric version."""
    body = _body(corpus, inclusion, exclusion, rubric_version, sampling_frame)
    return dict(body, locked_at=S.now_iso(), manifest_sha256=S.sha256_obj(body))


def verify_lock(manifest, corpus):
    """(ok, problems): the manifest is intact AND this corpus, rebuilt into a manifest under the same criteria,
    is that manifest, section by section (sources, episodes and their turns, missing items, duplicates)."""
    body = {k: v for k, v in manifest.items() if k not in ("locked_at", "manifest_sha256")}
    problems = []
    if S.sha256_obj(body) != manifest.get("manifest_sha256"):
        problems.append("the manifest itself was altered after locking")
    now = _body(corpus, body.get("inclusion"), body.get("exclusion"), body.get("rubric_version"), body.get("sampling_frame", ""))
    for k in ("sources", "episodes", "missing", "duplicates"):
        if now[k] != body.get(k):
            problems.append("%s differ from the locked corpus" % k)
    return not problems, problems
