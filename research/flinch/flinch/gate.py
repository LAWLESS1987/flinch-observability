"""gate.py -- a side effect happens only through a declared capability and an explicit allow (spec 13.1-13.7).

    model proposal -> decision (Covenant's gate, a callable here) -> capability broker -> action -> receipt

A judge that does not answer has not agreed (Covenant's principle, spec 13.7): no judge, a judge that raises,
times out, or answers anything other than an explicit allow HOLDS the action. Nothing runs, and the hold is
recorded with its reason. An action no capability declares is refused before any judge is asked (13.1).

Egress (13.2), as states the broker enforces:
  offline     -- a capability that needs the network is refused;
  allowlisted -- refused unless every host the capability names is on the broker's allow_hosts;
  brokered    -- refused unless a policy broker (a callable, logged) approves this request;
  open        -- allowed only when the broker was built with open_authorized=True.
Every outcome -- refused, held, denied, allowed, and what the action returned or raised -- goes to the
append-only action ledger (13.6) with the egress state and a hash of the parameters, so the record shows
WHICH request was approved. A broker cannot be built without a ledger.

Corrected 2026-10-14 (review finding 9): the first version ran actions with no ledger (ledger=None was
allowed, contradicting "every outcome ... goes to the ledger"), treated allowlisted and brokered as open,
and recorded no hash of the parameters.
"""
from __future__ import annotations

import threading

from . import receipts as R
from . import schema as S

CAPABILITY_FIELDS = ("name", "version", "side_effect", "network", "scope", "reversible", "decision_class",
                     "approval_class", "logging")


def validate_capability(c):
    errs = ["capability %s: missing %s" % (c.get("name"), k) for k in CAPABILITY_FIELDS if k not in c]
    if c.get("network") and not isinstance(c.get("hosts"), (list, tuple)):
        errs.append("capability %s: a network capability must name its hosts" % c.get("name"))
    return errs


class Broker:
    def __init__(self, registry, judge=None, ledger=None, egress="offline", timeout_s=30.0, allow_hosts=(),
                 broker=None, open_authorized=False):
        if not ledger:
            raise ValueError("a broker needs an action ledger: every outcome is recorded (spec 13.6)")
        if egress not in S.EGRESS:
            raise ValueError("egress %r is not one of %s" % (egress, S.EGRESS))
        if egress == "open" and not open_authorized:
            raise ValueError("open egress needs explicit authorization (open_authorized=True)")
        problems = [p for c in registry for p in validate_capability(c)]
        if problems:
            raise ValueError("; ".join(problems))
        self.registry = {c["name"]: c for c in registry}
        self.judge, self.ledger, self.egress, self.timeout_s = judge, ledger, egress, timeout_s
        self.allow_hosts, self.broker = set(allow_hosts), broker

    def _record(self, task_id, name, outcome, why, params, extra=None):
        row = {"kind": "action", "task_id": task_id, "action": name, "outcome": outcome, "why": why,
               "egress": self.egress, "params_sha256": S.sha256_obj(params), **(extra or {})}
        R.append_event(self.ledger, row)
        return row

    def _egress_refusal(self, cap, proposal):
        if not cap["network"]:
            return None
        if self.egress == "offline":
            return "needs the network and egress is offline"
        if self.egress == "allowlisted":
            outside = sorted(set(cap["hosts"]) - self.allow_hosts)
            return ("hosts outside the allowlist: %s" % ", ".join(outside)) if outside else None
        if self.egress == "brokered":
            if self.broker is None:
                return "egress is brokered and no policy broker is connected"
            try:
                return None if self.broker(proposal) is True else "the policy broker did not approve this request"
            except Exception as e:                                    # noqa: BLE001
                return "the policy broker failed: %s" % type(e).__name__
        return None                                                   # open, and authorized at construction

    def _decide(self, proposal):
        if self.judge is None:
            return "hold", "no judge is connected: a judge that does not answer has not agreed"
        box = {}

        def call():
            try:
                box["answer"] = self.judge(proposal)
            except Exception as e:                                    # noqa: BLE001
                box["error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
        t = threading.Thread(target=call, daemon=True)
        t.start()
        t.join(self.timeout_s)
        if t.is_alive():
            return "hold", "the judge did not answer within %.1f s" % self.timeout_s
        if "error" in box:
            return "hold", "the judge failed: " + box["error"]
        ans = box.get("answer")
        word = ans[0] if isinstance(ans, (tuple, list)) and ans else ans.get("decision") if isinstance(ans, dict) else ans
        why = ans[1] if isinstance(ans, (tuple, list)) and len(ans) > 1 else ans.get("why", "") if isinstance(ans, dict) else ""
        if word == "allow":
            return "allow", str(why)
        if word == "deny":
            return "deny", str(why)
        return "hold", "the judge's answer was not an explicit allow: %r" % (ans,)

    def act(self, task_id, name, params, run):
        """Returns (outcome, why, result). `run(params)` is called only on an explicit allow."""
        cap = self.registry.get(name)
        if cap is None:
            self._record(task_id, name, "refused", "undeclared capability: no manifest names %r" % name, params)
            return "refused", "undeclared capability", None
        proposal = {"task_id": task_id, "action": name, "params": params, "capability": cap, "egress": self.egress}
        refusal = self._egress_refusal(cap, proposal)
        if refusal:
            self._record(task_id, name, "refused", refusal, params)
            return "refused", refusal, None
        decision, why = self._decide(proposal)
        if decision != "allow":
            self._record(task_id, name, decision, why, params)
            return decision, why, None
        try:
            result = run(params)
        except Exception as e:                                        # noqa: BLE001
            self._record(task_id, name, "failed", "allowed, then the action raised %s: %s" % (type(e).__name__, str(e)[:200]), params)
            return "failed", str(e), None
        self._record(task_id, name, "done", why, params, {"result_sha256": S.sha256_obj(result if result is not None else "")})
        return "done", why, result
