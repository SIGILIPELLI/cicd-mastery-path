"""Release-readiness report: combine the checks built in this course into one decision.
Inputs are files/data you point it at; it never deploys anything. Exit status 0 = ready, 1 = blocked."""
import json, sys, yaml
import wflint, planguard, canary, dora

def readiness(workflow_paths, plan, allow_destroy, deploys, window_days, stable_err, canary_err, seed=0, max_cfr=0.30):
    reasons = []
    for p in workflow_paths:
        reasons += [f"workflow {p}: {r} {w}" for r, w, _ in wflint.lint_file(p)]
    bad, _ = planguard.check(plan, allow_destroy); reasons += [f"plan: {k} of {a} not allowed" for a, k in bad]
    m = dora.metrics(deploys, window_days)
    if m["change_failure_rate"] is not None and m["change_failure_rate"] > max_cfr: reasons.append(f"change failure rate {m['change_failure_rate']} above {max_cfr}")
    decision, log = canary.run_canary(stable_err, canary_err, seed=seed)
    if decision != "promote": reasons.append(f"canary: rollback at {log[-1]['pct']}% traffic (z={log[-1]['z']})")
    return {"ready": not reasons, "reasons": reasons, "metrics": m, "canary": decision}
