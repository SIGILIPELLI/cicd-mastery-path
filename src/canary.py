"""Canary release simulator: shift traffic in steps, compare the canary's error rate to the stable version's, and decide promote or roll back.
The decision uses a one-sided two-proportion z-test (normal approximation) with a minimum sample size; random traffic is seeded."""
import math, random

def z_one_sided(err_c, n_c, err_s, n_s):
    """z statistic for H1: canary error rate > stable error rate. Returns 0.0 when undefined."""
    if n_c == 0 or n_s == 0: return 0.0
    p_c, p_s = err_c / n_c, err_s / n_s
    pooled = (err_c + err_s) / (n_c + n_s)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n_c + 1 / n_s))
    return 0.0 if se == 0 else (p_c - p_s) / se

def run_canary(true_stable, true_canary, steps=(1, 5, 25, 50, 100), requests_per_step=20000, min_canary=400, z_limit=2.33, seed=0):
    """Return (decision, log). z_limit 2.33 is ~1% one-sided false-alarm rate per check for a truly equal canary."""
    rng, log = random.Random(seed), []
    err_c = n_c = err_s = n_s = 0
    for pct in steps:
        nc = int(requests_per_step * pct / 100); ns = requests_per_step - nc
        err_c += sum(rng.random() < true_canary for _ in range(nc)); n_c += nc
        err_s += sum(rng.random() < true_stable for _ in range(ns)); n_s += ns
        z = z_one_sided(err_c, n_c, err_s, n_s)
        log.append({"pct": pct, "n_canary": n_c, "canary_err": err_c / n_c if n_c else 0.0, "stable_err": err_s / n_s if n_s else 0.0, "z": round(z, 2)})
        if n_c >= min_canary and z > z_limit: return "rollback", log
    return "promote", log
