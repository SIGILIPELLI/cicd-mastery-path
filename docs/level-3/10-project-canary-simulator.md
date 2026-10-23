---
description: "Level 3 project: a tested canary-release simulator with a promote-or-roll-back rule, measured for detection speed and false alarms."
---

# 10 · Project — A Canary Release Simulator

This project builds the decision engine of an automated canary release and then **measures** how it behaves: how quickly it catches a bad release, how often it wrongly rolls back a good one, and what the choices (traffic steps, sample sizes, threshold) cost. The traffic is synthetic. The point is to understand the trade-offs before you put such a rule in front of production.

!!! note "What was run"
    `src/canary.py` (about 35 lines) and `src/test_canary.py` (11 tests) were written and run on macOS. Traffic is generated with Python's seeded `random` module: each request independently fails with the configured probability. Real traffic has bursts, correlated failures, varying request mixes and delayed metrics, none of which are modelled, so real detection performance will be **worse** than shown. The statistical test is a standard one-sided two-proportion z-test using the normal approximation. I did not use any canary tool (Argo Rollouts, Flagger, Spinnaker).

## The design

```python
def run_canary(true_stable, true_canary, steps=(1, 5, 25, 50, 100), requests_per_step=20000,
               min_canary=400, z_limit=2.33, seed=0):
```

At each step the simulator splits `requests_per_step` between the canary (a `pct` share) and stable, draws errors, **accumulates** counts across steps, computes

```text
z = (p_canary − p_stable) / sqrt( p_pool · (1 − p_pool) · (1/n_canary + 1/n_stable) )
```

and rolls back if `n_canary >= min_canary` and `z > z_limit`; otherwise it moves to the next step, and promotes after the last. Three design choices are worth defending:

1. **One-sided.** We only care whether the canary is *worse*. A significantly better canary is good news, not a reason to stop (a test asserts `z < 0` for a better canary).
2. **A minimum sample** (`min_canary`). With 1% of 20,000 = 200 canary requests, a single burst of errors can look dramatic. The rule refuses to decide until it has 400. The test `test_min_sample_prevents_decision_at_1_percent` checks the first step has 200 requests and no rollback is declared from it alone.
3. **Pooled variance** assumes the null hypothesis (rates are equal) to estimate the standard error, the usual form for this test.

Edge cases are tested because they are where production code breaks: no data (`z = 0.0`, never raise), zero errors on both sides (standard error is zero; return 0 instead of dividing by zero), and equal rates giving exactly 0.

## Running the scenarios

For each scenario, 300 runs with seeds 0–299, stable error rate 1.0%:

```text
canary 1.0%  rollback 13/300 = 0.04   (false alarms)         median stop pct = 5
canary 1.2%  rollback 234/300 = 0.78                           median stop pct = 50
canary 1.5%  rollback 300/300 = 1.00                           median stop pct = 25
canary 2.0%  rollback 300/300 = 1.00                           median stop pct = 5
canary 5.0%  rollback 300/300 = 1.00                           median stop pct = 5
```

and a single traced run (canary 5%, seed 1):

```text
pct  1: n_canary 200,  canary_err 0.090, stable_err 0.0112, z 10.18   (below min sample: no decision)
pct  5: n_canary 1200, canary_err 0.055, stable_err 0.0110, z 13.58   -> rollback
```

That trace makes the minimum-sample rule visible: the 1% step already had z of 10, but only 200 canary requests, so the decision waited one step.

### Reading the results

- **False alarms are 4%, higher than a naive reading of 2.33 (about 1%) suggests.** Five looks at the data, each with a 1% false-positive chance, accumulate: up to roughly 1 − 0.99⁵ ≈ 4.9% if the looks were independent (they are not, because counts accumulate, so the true rate is lower, and 4.3% observed is plausible but I did not derive it). Repeated testing inflates false positives; the fix is a stricter `z_limit` or a sequential-testing method designed for repeated looks.
- **Sensitivity depends on the effect size.** A 5× worse canary is caught almost immediately; a 20% relative worsening (1.0 → 1.2%) is caught in 78% of runs and typically only at 50% of traffic, by which time many users have been exposed.
- **More traffic per step buys sensitivity.** Because the z statistic grows with the square root of the sample size, quadrupling the requests roughly doubles z for the same effect. You can test that with `requests_per_step`.

I made one wrong prediction during development: I wrote a test expecting the 1.0 → 1.2% regression to be *usually missed* (more than 100 of 200 seeded runs), and it failed: only 47 of 200 were missed. The test now asserts the measured behaviour with a conservative floor (more than 55 of 100 seeds caught). The lesson for real canary design: don't guess detection power, measure it.

## Experiments to try

1. **Threshold sweep.** Run the equal-rates scenario for `z_limit` of 1.64, 2.33 and 3.09 and plot false-rollback rate against detection rate for 1.0 → 1.2%. You are drawing an ROC-like curve; choose your operating point deliberately.
2. **Fewer steps.** Use `steps=(5, 100)`. Detection is cheaper to compute but a bad release now hits 100% sooner. How many requests are exposed to the bad version before a rollback, per scenario? Add a counter for "failed requests served by the canary" and compare designs by **cost of bad releases**, not just by whether they were caught.
3. **Low traffic.** Set `requests_per_step=1000`. How often is the 5% canary decided at all? This is the situation of a low-volume service, and the answer ("rarely") should push you to longer bake times or synthetic traffic.
4. **Correlated failures.** Make errors arrive in bursts (a 30-second window of 50% failures) and see how the independent-requests test misjudges it.

## From simulator to production

To turn this into a real component you need: metrics from the actual system, **time-aligned** comparison of canary and stable over the same window; delay handling (metrics lag); multiple signals (latency, saturation, business metrics) with a combination rule; a safe response to missing data (stop, don't promote); an audit record of every decision; and a human override. Mature tools implement these; evaluate them against this simulator's questions: what are your false-rollback and detection rates for the effect sizes you care about?

## Checklist

- Every threshold in the rule has a recorded false-alarm and detection rate.
- The step schedule and sample sizes are chosen from the effect size you must detect.
- Simulated results are never presented as production evidence.

## How It Actually Works

The error counts per step are binomial draws; summed across steps they remain binomial in the total number of requests, so the estimated rates converge to the truth as `n` grows and their difference has a standard error shrinking like 1/√n. The z statistic scales the observed difference by that standard error, so a given true difference becomes statistically visible once the sample is large enough for the noise to fall below it. The step schedule controls exposure: small early steps limit the damage from a catastrophic release; later large steps supply the sample size needed to detect subtle regressions. The decision rule is therefore a joint design of schedule, sample size and threshold, which is why changing one number silently changes the false-alarm and miss rates.

## Common mistakes

- **Deciding on tiny samples**, rolling back on noise or promoting on luck.
- **Ignoring repeated-looks inflation** of the false-alarm rate.
- **Testing only error rate**, missing latency and saturation.
- **Comparing against historical data** rather than the concurrent stable fleet.
- **Treating missing metrics as success.**
- **Never measuring detection power** for the regression size you care about.
- **Tuning on the simulator** and trusting the numbers for a real system.

## Exercise

1. Run `pytest src/test_canary.py -v`, then reproduce the five-row scenario table with your own script and compare numbers (they are deterministic for the same seeds).
2. Do experiment 1 and write a one-paragraph recommendation for the threshold, with the trade-off stated in numbers.
3. Add a latency signal: draw latencies from two distributions and combine "error rate worse" OR "mean latency worse" into the decision; measure the resulting false-alarm rate.
4. Write the canary policy for a payment service: steps, minimum samples, thresholds, who is paged on rollback, and what happens when metrics are missing.
