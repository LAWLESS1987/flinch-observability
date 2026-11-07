#!/usr/bin/env python3
"""verify_release.py -- the code on this branch must match the release manifest it claims to be.

    python -I verify_release.py RELEASE_MANIFEST_0.2.2-post.json

Added 2026-11-07 after the CL1 change (214fe07) left receipts.py and a new test matching no release manifest for
three days with nothing noticing; Cipher asked what would stop it happening again. Every file the manifest lists must
exist and match its sha256 (text with CRLF folded to LF, as the manifests were written), and every .py file under
research/flinch/ must be listed, so a new code file cannot slip in unrecorded. Exit 0 only if all hold.
Standard library only. It checks that the release record is current, not that the code is right.
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read().replace(b"\r\n", b"\n")).hexdigest()


def main(argv):
    man = json.load(open(os.path.join(ROOT, argv[0]), encoding="utf-8"))
    listed = {f["path"]: f["sha256"] for f in man["files"]}
    bad = []
    for path, want in sorted(listed.items()):
        p = os.path.join(ROOT, path)
        if not os.path.isfile(p):
            bad.append("missing: %s" % path)
        elif sha(p) != want:
            bad.append("changed since the manifest: %s" % path)
    for d, _, fs in os.walk(os.path.join(ROOT, "research", "flinch")):
        if "__pycache__" in d:
            continue
        for f in fs:
            if f.endswith(".py"):
                rel = os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, "/")
                if rel not in listed:
                    bad.append("code file not in the manifest: %s" % rel)
    for b in bad:
        print("FAIL  " + b)
    print("verify_release: %d files listed, %d problems (%s)" % (len(listed), len(bad), argv[0]))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["RELEASE_MANIFEST_0.2.2-post.json"]))
