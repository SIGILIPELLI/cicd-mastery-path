---
description: "Migrating between CI systems: inventory, translation limits, parallel runs and cutover, with a converter that reports what it cannot translate."
---

# 08 · Migrating CI Systems

At some point most organisations change CI: Jenkins to GitHub Actions, a hosted service to self-managed, or a consolidation after an acquisition. Migrations fail in familiar ways: the inventory missed jobs, a "simple" translation lost behaviour silently, people were cut over before the new system proved equivalent, or the old system lingered for years. This lesson gives a method and shows the translation problem concretely.

!!! note "What was run"
    `src/wf2minici.py` (8 tests) converts a **simple** GitHub Actions workflow into a `minici` pipeline and lists everything it cannot translate. It is a teaching converter between two *simplified* formats, not a Jenkins-to-Actions tool, and I did not use any real migration tool (Actions Importer or similar) or migrate a real system. The migration method is general practice, not measured here.

## Phase 0: Decide why

Valid reasons: reduce platform maintenance (patching a controller, plugin risk; Lesson 03), consolidate on the system next to the source host, a feature you need, cost, or a policy requirement. Weak reasons: fashion. State the **success criteria** up front (time-to-green for a typical PR, cost per month, maintenance hours, security controls improved) so you can tell whether the migration worked. A migration with no measurable goal is a cost with no benefit.

## Phase 1: Inventory

You cannot migrate what you have not found. Collect, for every job or pipeline:

- Triggers (push, PR, schedule, webhook from another system, manual).
- Steps and the tools they use (compilers, scanners, deploy scripts, custom plugins).
- Credentials and the systems they reach.
- Agents/runners and special requirements (GPU, OS, network zone).
- Downstream consumers: who relies on its artifacts, statuses, notifications, or on being a required check.
- Usage: last run, run frequency, owner. **Many jobs are dead.** Delete them rather than migrate them; in a typical estate a large fraction of old jobs are unused, but measure yours instead of trusting that statement.
- Hidden coupling: jobs that trigger other jobs, shared workspaces, shell scripts that live only on an agent.

Classify each pipeline: *simple* (build/test with standard tools), *standard with extras*, *complex* (custom plugins, fan-in/fan-out, manual gates, odd agents). Estimate the work by class, and migrate a few of each class first to calibrate.

## Phase 2: Translation and what gets lost

The converter takes a workflow, maps the constructs both formats share (jobs, `needs`, a matrix with `fail-fast`, global `env`, steps that are shell commands with `name` and `env`), and **reports everything else instead of dropping it**. On the course's sample workflow (`src/ci.yml`):

```text
test.steps[0]: action `actions/checkout@v4` (must be replaced by shell commands)
test.steps[1]: action `actions/setup-python@v5` (must be replaced by shell commands)
package: `if` has no minici equivalent
package.steps[0]: action `actions/checkout@v4` (must be replaced by shell commands)
package.steps[2]: action `actions/upload-artifact@v4` (must be replaced by shell commands)
```

Five of the workflow's constructs could not be translated: four marketplace actions and one job-level `if`. The converted pipeline contains only the `run:` steps, so on its own it would **run the tests without checking out code or installing Python**. This is the central migration hazard: *a translation that runs and goes green but does less than the original.* The tests encode the design rule that prevents it:

1. `run` steps convert; `needs` given as a string becomes a list; the matrix and `fail-fast: false` carry over; global `env` carries over.
2. Anything unsupported is **reported with its location**: actions (`uses:`), `environment`, a step-level `if`, reusable-workflow calls.
3. Nothing is silently dropped. A conversion with a non-empty "unsupported" list is **not done**.

Common translation gaps between real systems (general knowledge, not tested here): marketplace actions and Jenkins plugins have no direct counterparts, so each must be re-implemented or replaced; expression syntax and context objects differ; credentials models differ (Jenkins credentials vs repository/environment secrets, OIDC); caching and artifact semantics differ (keys, scopes, retention); concurrency and approval features differ; scheduled triggers use different time zones and semantics; matrix syntax has different rules (Level 2 · 01); agent labels map to runner labels and groups; and build numbers and URLs change, which breaks anything that links to them.

Prefer to move the logic into **scripts in the repository** (`make test`, `./ci/build.sh`) that both systems call, so the CI definition is a thin wrapper and the next migration is cheap.

## Phase 3: Run in parallel, compare

Don't cut over on faith. For a period, run old and new CI on the same commits and compare:

- **Outcome:** same pass/fail? Investigate every disagreement; both directions matter. A new system that is *greener* than the old may have lost a check.
- **Coverage of checks:** the set of steps that ran (names and counts), not just the final colour. The contract-test idea from Lesson 06 applies: feed both systems a known-bad commit and confirm both fail.
- **Artifacts:** same files, same digests where builds are reproducible (Level 1 · 06); if not byte-identical, understand the differences.
- **Time and cost:** against the success criteria.
- **Notifications and statuses:** that the right people get the right messages, and required checks have the right names for branch protection.

Mark the new status checks **non-required** during the trial, then swap which is required at cutover. The required-check names (Level 2 · 01) are a frequent cutover trap.

## Phase 4: Cutover

- Migrate in **waves**: low-risk repositories first, then standard, then complex and critical. Learn from each wave.
- Have a **rollback plan**: the old system stays available and runnable until the new one has served a full release cycle; keep the old job definitions.
- Freeze changes to the old pipelines during each repository's cutover so definitions don't diverge.
- Move **secrets** deliberately: create new ones scoped to the new system, rotate rather than copy where possible, and revoke the old ones after cutover. Copying secrets from a system you are retiring is how stale credentials persist for years.
- Update **deployment targets** that restrict access by CI IP or identity.
- **Communicate:** dates, what changes for developers, where to get help, a migration guide with before/after examples.

## Phase 5: Decommission

The step that gets skipped. Set a date to make the old system read-only, then to shut it down; archive build history and artifacts you must keep (compliance retention, Lesson 05); remove its credentials, DNS and firewall exceptions; update documentation and links. A zombie CI system with live credentials and no owner is a security liability.

## How to know it worked

Compare against the success criteria from Phase 0: median time-to-green, cost, maintenance hours, incident count, developer satisfaction survey. Report the result honestly, including regressions. If the new system is slower for a class of jobs, say so and plan the fix.

## How It Actually Works

Both CI systems implement a similar abstract model: a trigger creates a run; a run is a graph of jobs; each job executes ordered steps on an executor with an environment and credentials; results are statuses and artifacts. The converter works on the intersection of two concrete syntaxes for that model. Anything outside the intersection (marketplace actions, plugins, platform-specific contexts) is a place where behaviour lives in *the platform*, not in your file, which is why it cannot be translated mechanically. The way to reduce migration risk is to keep as much behaviour as possible on your side of that line: in scripts and containers you control, with the CI file only wiring them together.

## Common mistakes

- **Migrating without success criteria.**
- **Incomplete inventory**, including dead jobs.
- **Mechanical translation that silently drops steps.**
- **No parallel run**, so differences surface after cutover.
- **Comparing only the final colour**, not what ran.
- **Required-check name mismatches** at cutover.
- **Copying secrets** to the new system.
- **Never decommissioning the old system.**
- **Big-bang cutover** across all repositories at once.

## Exercise

1. Run `pytest src/test_wf2minici.py -v` and then `convert` on one of your own workflows. How many unsupported items does it report, and what would you replace each with?
2. Inventory ten pipelines you know. Classify them simple / standard / complex and estimate effort by class.
3. Design the parallel-run comparison report: the columns, how disagreements are triaged, and the exit criteria for cutover.
4. Write the decommission checklist for an old CI controller, including credentials, history and access.
