---
description: "Capstone: one release-readiness check combining the workflow linter, plan guard, delivery metrics and a canary decision, with reasons."
---

# 10 · Capstone — A Release-Readiness Check

The capstone joins the components built across the course into one decision: **is this release ready to go out?** It checks the pipeline definition (workflow linter), the infrastructure change (plan guard), the team's recent delivery health (DORA metrics) and the canary result (simulator), and it reports *reasons* when the answer is no. It never deploys anything. It is a small demonstration of the idea at the heart of a delivery platform: automated, explainable gates that combine several signals.

!!! note "What was run, and what wasn't"
    `src/capstone.py` (about 20 lines) and `src/test_capstone.py` (6 tests) were written and run. Inputs are **synthetic**: a generated workflow, a hand-written plan fixture, a hand-made deployment history and a simulated canary. The decision thresholds (for example the 30% maximum change failure rate) are arbitrary defaults I chose for illustration and are not recommendations. All 173 tests in `src/` pass on macOS (the whole-course total at the time of writing). Nothing was run on GitHub Actions, Jenkins, Terraform or a real deployment system.

## The design

```python
def readiness(workflow_paths, plan, allow_destroy, deploys, window_days,
              stable_err, canary_err, seed=0, max_cfr=0.30): ...
```

It collects reasons from four independent checks:

1. **Workflows:** run `wflint.lint_file` on each path (Level 2 · 10); each finding becomes a reason such as `W003 test.steps[0]`.
2. **Infrastructure plan:** run `planguard.check` (Level 3 · 05); destructive actions not on the allowlist become reasons.
3. **Delivery health:** compute DORA metrics (Level 3 · 09); a change failure rate above the maximum is a reason.
4. **Canary:** run the simulator (Level 3 · 10) and add a reason if it decides to roll back.

The result is `{"ready": bool, "reasons": [...], "metrics": {...}, "canary": "promote"|"rollback"}`. `ready` is true only when the list of reasons is empty. The most important property: **every "no" comes with a reason a human can act on**, and **absence of reasons is the only way to be ready**, so a new check that is added but broken in a way that finds nothing would make it *easier* to be ready; testing that each check can fail (Lesson 06) is what stops that.

## Running it

The generated workflow for service `orders` with production deploy (from Lesson 09, with dummy pins), a plan with one in-place update and one replace of a database, and a six-deployment history in which one deploy failed and was restored after 1 hour (lead times 3 h each):

```text
allow=[]                         canary 1.0% -> ready=False  reasons: ['plan: replace of aws_db_instance.main not allowed']
allow=['aws_db_instance.main']   canary 1.0% -> ready=True   reasons: []
allow=['aws_db_instance.main']   canary 5.0% -> ready=False  reasons: ['canary: rollback at 5% traffic (z=13.58)']
metrics: deploys_per_day 0.43, median_lead_time_h 3.0, change_failure_rate 0.167, median_restore_h 1.0
```

Walk through it:

- **Row 1:** the workflow is clean (generated, so the linter finds nothing) and the metrics are healthy (CFR 0.167, under 0.30), but the plan would *replace* a database. Blocked, with the resource named.
- **Row 2:** the replace is explicitly allowlisted (a reviewer made the call in the pull request, Level 3 · 05), so the answer is ready.
- **Row 3:** the same allowlist, but the canary has a 5% error rate against stable 1%; the simulator rolls back at the 5% step with z of 13.58 (the same trace shown in Level 3 · 10). Blocked.

The six tests cover: all green; a destructive plan blocks; an allowlisted plan passes; a high failure rate blocks (3 of 5 deploys failing, CFR 0.6); a bad canary blocks (`canary == "rollback"`); and an unpinned workflow (`@v4`) blocks with a `W003` reason.

## What this is, and isn't

It **is** a compact example of policy-as-code gating: independent checks, each tested, combined into one explainable decision.

It **isn't** a release system. A real platform would need: real data sources (the plan from the actual tool, deployments from an event store, canary metrics from monitoring); handling of **missing or stale data** (here a missing input would simply be an error, and a silently empty list would pass; the safe design treats absent evidence as a failure); persistent records of each decision (Lesson 05); an override process with approval and audit trail; and operational concerns such as timeouts and retries. Simulated canary traffic is also not evidence about your system: the readiness check should consume real analysis.

## Suggested extensions

1. Add **supply-chain checks** (Level 3 · 08): verify the artifact digest against a signed manifest and require an SBOM.
2. Add a **flag check**: fail if a release flag older than N days is still present (Level 3 · 02).
3. Add a **migration check**: fail if a destructive schema operation appears without a contract-phase approval (Level 3 · 03).
4. Add **evidence output**: write the decision, inputs' hashes and reasons to the hash-chained audit log (Lesson 05).
5. Replace the simulated canary with a function that fetches metrics for the canary and stable fleets over the same window and treats missing metrics as a failure.
6. Wrap it in a pipeline job that runs before the deploy job and is a required gate (Level 2 · 06 and 07).

## What you have built across the course

All of these are in `src/` and tested; run `python3 -m pytest -q src` (with the dependencies in the course README) to see the whole suite:

| Level | Components |
|---|---|
| 1 | `minici` runner (15 tests), Jenkinsfile linter (11), secret scanner (12), deterministic tarball helper, the demo project's own tests (3) |
| 2 | Path-filter mapper (9), wait-for-port helper (4), workflow linter (17) |
| 3 | Canary simulator (11), feature-flag evaluator (8), GitOps reconciler (8), plan guard (9), version-bump tool (12), DORA calculator (6) |
| 4 | Pipeline performance model (7), queue simulator (6), audit-log chain (9), workflow converter (8), golden-path generator (8), pipeline contract tests (4), readiness check (6) |

Those counts sum to the 173 that pytest reports for `src/` (I checked the per-file counts with `pytest --collect-only`).

## Where to go next

- Run the same ideas on a real platform: set up a small repository with GitHub Actions or a local Jenkins, and port one component (the linter as a required check is a good first step).
- Learn a build system with remote caching (Bazel, Gradle, Nx) to move from path filters to input hashing.
- Study your platform's security documentation and the supply-chain frameworks in depth (SLSA, Sigstore).
- Read incident reviews from public postmortems about CI/CD and supply-chain attacks, and apply the threat-model method (Lesson 01) to your own pipelines.

## How It Actually Works

The check is a fold over independent evaluators: each produces zero or more *reasons* and the verdict is the conjunction of their silence. Independence matters: a failure in one evaluator does not hide another's findings, so the output lists everything wrong at once rather than the first thing wrong (a design choice that saves multiple fix-and-retry cycles). Determinism matters too: with a fixed seed the canary result is reproducible, so a failing decision can be replayed. The deeper pattern, which the whole course has been building toward, is that **delivery safety comes from small, tested, explainable checks composed together**, wired to the pipeline's control flow so that a "no" actually stops a deploy, and recorded so that you can later prove why.

## Common mistakes

- **Composing checks that can never fail**, and calling the result a gate.
- **Treating missing evidence as success.**
- **A single combined score** that hides which check failed.
- **Thresholds with no owner** and no review.
- **No override path**, so people bypass the system.
- **No record of decisions.**
- **Confusing a simulation with evidence.**

## Exercise

1. Run `python3 -m pytest -q src` and then add a fifth check of your own to `readiness` (for example the secret scanner on a directory). Write the tests first: one that makes it fail, one that makes it pass.
2. Change `readiness` so that missing inputs (`plan=None`, an empty deploy list) produce a reason instead of passing silently. Which tests change?
3. Write the policy statement for your organisation: which checks block a production deploy, which only warn, who may override, and where the decision is recorded.
4. Draw the end-to-end flow from commit to production for a service of yours, marking where each course component would run and which control it provides.
