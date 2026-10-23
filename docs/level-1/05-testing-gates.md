---
description: "Testing gates in a pipeline: ordering by cost, required checks, what gates can and cannot prove, with a measured fast-first ordering experiment."
---

# 05 · Testing Gates and Fast Feedback

A **gate** is a check that must pass before a change moves on. Most of a pipeline's value comes from which gates it has, in what order, and how much the team trusts them. This lesson covers designing gates for fast, reliable feedback.

!!! note "What was run"
    The ordering experiment below ran on `minici` (this course's local runner; see Lesson 01). No GitHub or Jenkins pipeline was run. Statements about branch protection and required checks describe GitHub's documented behaviour and were not tried. See Lesson 01.

## The test pyramid, applied to pipelines

| Layer | Speed | Scope | Typical count | Where in the pipeline |
|---|---|---|---|---|
| **Static checks** (format, lint, types) | seconds | Code style and obvious mistakes | n/a | First |
| **Unit tests** | seconds to a minute | One function or class, no network | Hundreds to thousands | First/second |
| **Integration tests** | minutes | Several components, a real database or service | Tens to hundreds | After unit tests |
| **End-to-end / UI tests** | many minutes | The whole system through its interface | Few, on critical paths | Late, often only on main or staging |
| **Non-functional** (performance, security scans) | minutes to hours | Specific qualities | Targeted | Parallel, or scheduled |

Many cheap tests and few expensive ones: the "pyramid". The reverse (an ice-cream cone of mostly slow UI tests) gives slow, flaky pipelines that people stop trusting.

## Order gates by cost and likelihood of failing

Pipelines should surface problems **as early and cheaply as possible**. I measured the effect with two pipelines containing the same two jobs: a 3-second "integration" job and a broken "unit" job that fails instantly.

```text
integration first, then unit (unit needs integration):   time to learn about the failure = 3.1 s
unit first, then integration (integration needs unit):   time to learn about the failure = 0.1 s
```

Same checks, same result, 30 times faster feedback just from ordering (here by a 3 s sleep standing in for a slow suite; real suites differ by minutes). The slower job never even started in the second pipeline, which also saves runner minutes. Generalising: put checks with **low cost and high failure rate** first; run independent checks **in parallel**; reserve expensive suites for after cheap ones pass, and consider running them only on main or nightly if the
feedback loop is otherwise too slow.

## Required checks and merge rules

A gate only protects the mainline if merging is *blocked* when it fails. On GitHub that means **branch protection** or **rulesets** with required status checks (and typically required reviews, up-to-date branches, and no bypass for administrators). On Jenkins-driven repositories, the SCM reports the build status and the same rules apply. Considerations:

- **Required checks must always report.** If a required job is skipped by a path filter, some configurations leave it "pending" and block the merge; others treat skipped as passing (check your platform's behaviour; Level 2 · 09 returns to this).
- Require checks by the **job name**, which makes renaming a job a policy change.
- Require the branch to be **up to date** (or use merge queues) so tests ran against the code that will actually land.
- Keep the gate set small and meaningful: every required check is a potential blocker.

## What gates can and cannot prove

- Tests demonstrate that specific cases work; they don't prove absence of bugs.
- Code coverage measures what executed, not what was verified. 90% coverage with no assertions is worthless; use it to find untested areas, not as a target (Level 2 · 06).
- A green pipeline means "the checks we wrote passed in this environment". Production differs (data, scale, configuration, dependencies), which is why delivery pipelines add smoke tests, canaries and monitoring (Level 3).
- **A gate people bypass is worse than none.** If the pipeline is slow or flaky, developers learn to retry until green or ask for overrides.

## Flaky tests: the trust killer

A flaky test passes and fails on the same code. Causes: test order dependence, shared state, timing and sleeps, unmocked network calls, time zones and locale, resource limits on shared runners, nondeterministic data. Consequences: retries hide real failures, and engineers stop believing red. Policy: **quarantine** a flaky test (move it to a non-blocking job and file a ticket), don't auto-retry silently, and track the flake rate (Level 2 · 05).
Detect time-zone sensitivity by running tests under several zones; the demo pipeline in Lesson 01 does exactly that (three `TZ` values) and all three variants passed.

## Fast-feedback habits

1. **Run what CI runs, locally**, before pushing (`make check`, pre-commit hooks for format and lint).
2. **Pull-request pipelines should finish in minutes.** Set a budget (say ten) and treat regressions in pipeline time as bugs.
3. **Parallelise** by test shard and by job (Level 2 · 01); **cache** dependencies (Lesson 06).
4. **Show failures clearly**: the first failing assertion, not 3,000 lines of log; upload test reports.
5. **Fail fast within a job too**: `pytest -x`, `set -e`.
6. **Don't run everything on every change**: path filters and affected-only testing in large repositories (Level 2 · 09).

## Checklist

- Every required check runs on every pull request and fails with a non-zero exit status when it should.
- The fastest checks run first; the slowest run only after the cheap ones pass.
- A deliberately failing input exists for each gate, proving the gate can fail.
- Test output is published even when the job fails.
- Flaky tests are tracked by name, not discussed in general terms.
- The pipeline fails when zero tests were collected.
- The same command runs locally and in CI.
- Gate configuration lives in the repository, not in a web UI.
- Someone owns each gate and knows its false-positive rate.
- Bypassing a gate leaves a record.

## How It Actually Works

A gate is nothing more than an exit code consumed by the orchestrator: the test runner returns non-zero, the step fails, dependent jobs are skipped, and the pipeline reports a failure status to the commit. The *social* gate is the branch rule that refuses to merge a commit whose required status is not success. Ordering matters because the orchestrator starts a job only when its dependencies succeed, so failing early prevents all later (and costlier) work, exactly what the measurement above showed.

## Common mistakes

- **Slow suites first.**
- **Gates that are not required**, so a red build can merge.
- **Coverage thresholds as the goal**, producing assertion-free tests.
- **Retry-until-green** culture.
- **Tests that depend on the network, the clock or each other.**
- **End-to-end tests for everything**, instead of the critical paths.
- **Skipping the gate for "tiny" changes** (including config changes, which cause outages).

## Exercise

1. Take a pipeline you use, list each gate with its typical runtime and failure rate, and reorder them. Estimate the average time-to-first-failure before and after.
2. Reproduce the ordering measurement with your own slow and fast jobs in `minici`.
3. Run your tests under three time zones and two locales; record any failures.
4. Write the branch-protection rules you'd apply to `main` (required checks, reviews, up-to-date, no bypass) and explain what each protects against.
