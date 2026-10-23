---
description: "Deployment strategies compared: recreate, rolling, blue-green and canary, with capacity arithmetic and a simulated canary analysis."
---

# 01 · Deployment Strategies

"Deploy" hides a design decision: how do you replace the old version with the new one while users are using it? Each strategy trades **risk**, **cost**, **speed** and **complexity** differently. This lesson compares the four common ones and then measures the one that needs statistics: the canary.

!!! note "What was run, and what wasn't"
    **No real deployment was performed** (no cluster, load balancer or cloud account). The strategy descriptions are from general practice and the Kubernetes and cloud documentation as I understand them (October 2026) and are not tested here. What I did run is a **canary simulator** (`src/canary.py`, 11 pytest tests): synthetic traffic with seeded random errors, compared with a one-sided two-proportion z-test. The detection rates below are properties of *that simulation*, with 20,000 requests per step, and do not describe any real system.

## The four strategies

| Strategy | How | Rollback | Extra capacity | Main risk |
|---|---|---|---|---|
| **Recreate** | Stop the old version, start the new one | Redeploy the old one | None | Downtime between stop and start |
| **Rolling** | Replace instances a few at a time | Roll the other way | Small surge (e.g. +1 instance) | Old and new versions serve traffic together |
| **Blue-green** | Build a full second environment, switch traffic at once | Switch back | A whole second copy during the cutover | Cost; shared database must suit both |
| **Canary** | Send a small share of traffic to the new version, widen if healthy | Send it back to 0% | Small | Needs good metrics and enough traffic to read them |

**Recreate** is honest and simple, and fine for internal tools or maintenance windows. **Rolling** is the usual default in Kubernetes (`maxSurge` and `maxUnavailable` control how many instances may be added or missing during the update; the exact defaults are in the Kubernetes documentation, which I did not run). Because versions overlap, **every release must be backward compatible with the previous one** for the duration: the same API contract, a database schema both can use (Lesson 03), and compatible message formats.

**Blue-green** gives an instant switch and an instant switch *back*, as long as the old environment is kept alive and the database change was compatible. It costs double capacity for the overlap and does not catch problems that appear only under real traffic, since the switch is 0% to 100%.

**Canary** exposes a small slice of real users first. Its power is in the *analysis*: a bad release hurts 1% of requests for a few minutes instead of 100% for an hour.

## Capacity arithmetic for a rolling update

Take 10 instances, each handling 100 requests per second, serving 800 req/s of load. With `maxUnavailable = 2` the minimum healthy capacity during the update is (10 − 2) × 100 = **800 req/s**, exactly the load: zero headroom, so any spike causes errors. With `maxUnavailable = 1` the minimum is 900 req/s (12.5% headroom) but the update takes more rounds. A rollout is safe only if capacity at the *worst moment* exceeds peak load. Compute it before choosing the parameter, not after an incident.

## Canary analysis, measured

The simulator shifts traffic through steps of 1%, 5%, 25%, 50% and 100%, with 20,000 requests per step. At each step it accumulates counts and runs a **one-sided two-proportion z-test** on "canary error rate is greater than stable's", rolling back when z exceeds 2.33 (about a 1% one-sided false-alarm rate for a single check) and at least 400 canary requests have been seen.

Results over 300 seeded runs per row (stable error rate 1.0%):

| Canary true error rate | Rolled back | Typical stopping point |
|---|---|---|
| 1.0% (identical) | 13 of 300 (4%) | median stop at 5% traffic (when it stopped at all) |
| 1.2% | 234 of 300 (78%) | median 50% |
| 1.5% | 300 of 300 | median 25% |
| 2.0% | 300 of 300 | median 5% |
| 5.0% | 300 of 300 | median 5% |

What these numbers say:

- **Big regressions are caught early**: a 5× worse canary was stopped at the 5% step in the median run; the 1% step had only 200 canary requests, below the 400 minimum, so the rule deliberately waited. (Its observed 9% error rate there looks alarming but the sample is small.)
- **Small regressions are caught late or missed**: a 20% relative increase (1.0% to 1.2%) was missed in 22% of runs and the median stop was already at 50% traffic.
- **A healthy canary is sometimes rolled back**: 4% false rollbacks here. This is the *multiple looks* problem: five checks at a 1% single-check false-alarm level add up. A stricter threshold lowers false rollbacks and also lowers sensitivity, an unavoidable trade.

My first draft of the test for "a small regression is usually missed" was wrong: with 20,000 requests per step the detector catches 1.0% → 1.2% far more often than I predicted. I replaced it with the measured result (more than 55 of 100 caught) and a test that false rollbacks stay under 10%.

## What to measure in a real canary

Error rate alone is not enough. Compare the canary against the **stable fleet over the same period** (not against last week, because time of day changes traffic): error rate, latency percentiles, saturation (CPU, memory), and a business metric where possible (checkout completions). Watch out for:

- **Too little traffic** to see a small effect: at low volume a canary can never prove anything, and the right answer may be a longer bake time or a synthetic load.
- **Sticky sessions** and caches: a user bounced between versions sees inconsistent behaviour; route by user ID hash (Lesson 02) so each user sees one version.
- **Different populations**: the canary must receive a representative sample, not only internal users or one region.

## Choosing a strategy

- Stateless service, good metrics, enough traffic → **canary** (automated if you trust the analysis).
- Need a fast, rehearsed switch-back and can afford double capacity → **blue-green**.
- Small team, small service → **rolling**, with health checks and a sane `maxUnavailable`.
- A schema or protocol change that cannot be made compatible → **recreate** in a planned window, or redesign the change (Lesson 03).

Rarely is one strategy right for everything; the point is to choose deliberately and rehearse the rollback (Lesson 04).

## Checklist

- The worst-moment capacity of a rolling update exceeds peak load.
- Adjacent versions are compatible in API, schema and message formats.
- Canary analysis compares against the concurrent stable fleet.
- A missing metric stops the rollout instead of promoting it.
- Rollback has been rehearsed this quarter.
- The minimum sample size for a decision is written down and justified.

## How It Actually Works

All four strategies reduce to controlling *which instances receive which share of requests*. A load balancer or service mesh holds a set of backends with weights; a rolling update changes membership gradually, blue-green swaps the whole set atomically (a DNS change is not atomic because of caching, so a load-balancer target switch is preferred), and a canary assigns a small weight to a new group. Health checks decide which backends are eligible: an instance that fails its readiness probe is removed from rotation without being killed. The automation on top is a loop: set weight, wait, read metrics, decide. The statistics in the simulator are the "decide" part. The traffic share you can safely start with is limited by how fast your metrics arrive: a metric with a 5-minute delay cannot protect a 2-minute step.

## Common mistakes

- **No backward compatibility** between adjacent versions during a rolling update.
- **Zero capacity headroom** at the worst moment of an update.
- **A canary with too little traffic** to ever detect a regression.
- **Comparing the canary to history** instead of to the concurrent stable fleet.
- **Only watching error rate**, missing latency and saturation.
- **Treating blue-green as free rollback** after an incompatible database change.
- **Never testing rollback**, discovering it is broken during an incident.
- **Auto-promoting on silence**: a missing metric must be a failure, not a pass.

## Exercise

1. Run `pytest src/test_canary.py -v`. Then change `requests_per_step` to 2,000 and re-measure the detection rate for 1.0% vs 1.2%. What happens, and what does it mean for a low-traffic service?
2. For a service of 6 instances at 50 req/s capacity each and a peak load of 220 req/s, choose `maxUnavailable` and justify it.
3. Add a latency comparison to the simulator (e.g. a t-test on mean latency) and decide how to combine it with the error-rate test.
4. Write the rollback criteria for a canary as numbers (error-rate delta, latency delta, minimum sample) and defend each.
