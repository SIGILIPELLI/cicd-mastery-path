---
description: "Flaky tests as arithmetic: how per-test flake rates compound across a suite, retries, quarantine, and test reports, with theory checked by simulation."
---

# 05 · Test Reports & Flaky Tests

A **flaky** test passes and fails on the same code. One flaky test is an annoyance; a few hundred make the pipeline random, teach everyone to press "re-run" without reading the failure, and eventually hide a real bug behind the habit. The cure starts with arithmetic, because flakiness compounds in a way intuition underestimates.

!!! note "What was run"
    The pass-rate table compares a formula with a **20,000-run Monte Carlo simulation** I ran in Python (seeded random numbers, independent flakes). The simulation is a model: real flakes are often *correlated* (a slow runner makes many tests flaky at once) and not independent. The rerun estimate and the retry arithmetic are computed from the formulas shown. No real CI system's flake data was used or exists here.

## How flakes compound

Suppose a suite has *n* tests and each one independently fails spuriously with probability *p* even when the code is correct. The suite passes only if none of them flake:

**P(green) = (1 − p)ⁿ**

| Tests (n) | Per-test flake rate (p) | Formula | Simulated |
|---|---|---|---|
| 100 | 0.001 (0.1%) | 0.905 | 0.903 |
| 100 | 0.01 (1%) | 0.366 | 0.360 |
| 500 | 0.01 | 0.007 | 0.007 |
| 1000 | 0.002 | 0.135 | 0.135 |

The simulation agrees with the formula to within about 0.006, which is the sampling noise you expect from 20,000 runs. Read the table slowly:

- A suite of 100 tests where each flakes **one time in a thousand** is green only 90% of the time: one run in ten is red for no reason.
- At 1% per test, a 500-test suite is green **0.7%** of the time. It would be unusable, and the team would already have noticed. The dangerous region is the middle, where a suite is green *often enough* that people keep trusting "just re-run it."
- 1000 tests with p = 0.2% pass 13.5% of runs. Per-test rates that look negligible are not, at scale.

So the target is not "few flaky tests" but a *flake budget*: to keep a 1000-test suite green 99% of the time on correct code you need p below about 0.00001 per test, one in a hundred thousand.

## Measuring one test's flake rate

You rerun a suspect test 200 times on one commit and see 18 failures. The estimate is 18/200 = **0.090**, with a 95% interval of about ±0.040 (the normal approximation, roughly 1.96 × √(p(1−p)/n)). So the true rate is plausibly between 5% and 13%, and 200 runs cannot tell you whether it is 6% or 12%. Fewer runs would give a wider interval. If someone claims "I fixed it" after 10 clean runs, the probability of seeing 10 clean runs from a 9%-flaky test is (0.91)¹⁰ ≈ 0.39, so 10 clean runs prove very little. You need a few dozen to be moderately convinced and hundreds to be sure for rates this low.

## Retries: a bandage with a cost

Automatic retry of failed tests is common (`pytest-rerunfailures`, Jenkins `retry`, test framework options). The arithmetic:

A test that fails 8% of the time, with 2 retries (3 attempts total), still fails the build with probability 0.08³ = **0.00051**, about 1 in 1950. Retries do reduce red builds by orders of magnitude, which is why teams love them. The costs:

1. They **hide real intermittent bugs** in the product (a race condition, a timeout). A retry-green result of "passed on third attempt" must be reported, not discarded.
2. They **multiply time** when the failure is slow.
3. They **rescue tests that should fail**: a test that really is 70% failing (0.7³ = 0.34 still fails, but 0.3 flakiness will pass often) passes enough to ignore.

Policy that works: retry is allowed, but every retried-then-passed test is **recorded**, counted per test, and when a test exceeds a threshold it is quarantined and a ticket is created with an owner and a due date.

## Quarantine without losing the signal

Quarantine means: keep running the test, but do not let its result gate the merge. Implementations include a marker (`@pytest.mark.quarantine`) with a separate non-blocking job that runs those tests, or a skip list stored in the repository. Rules that keep it honest:

- Quarantine is **temporary and visible**: a list with owners and dates; its size is a dashboard metric.
- Quarantined tests still **run**, so you can see when one has gone stable and when it finally fails for a real reason.
- A flaky test that covers critical behaviour is a **bug to fix**, not a thing to skip.

## Reading failures: test reports

Raw logs are hard to scan at 20,000 lines. Test frameworks can emit **JUnit XML** (`pytest --junitxml=report.xml`), a de-facto format that CI systems parse to show a table of failures, durations and history (Jenkins' `junit` step and GitHub Actions test-reporter actions both consume it; I describe this from their documentation and did not run them). What a good report gives you:

- The **failing test name and message first**, not the 5,000 passing lines.
- **Duration per test**, to find the slow ones (and to shard by time, Lesson 01).
- **History**: whether this test failed on other unrelated commits, which is the strongest flake signal available. A test failing on 12 different PRs in a week and never on `main`'s own runs is not a bug in those 12 PRs.

Always publish the report even when the job failed (`if: always()`), or you will have the report only on green builds, when you need it least.

## Causes, in order of frequency

1. **Shared state and ordering**: tests that depend on each other or on a database left by a previous test.
2. **Time**: sleeping instead of waiting for a condition (Lesson 04), tests that assume the current date, time zones, or that two timestamps differ.
3. **Concurrency**: races inside the code under test or in the test's own threads.
4. **Resources**: a fixed port, a shared temp file, an overloaded runner making a timeout too tight.
5. **External services**: a test that calls the real network.
6. **Randomness**: unseeded random data. Print the seed on failure so you can reproduce.

## How It Actually Works

A test runner reports each test's outcome to the framework's reporter, and CI infrastructure stores or parses the result. The compounding formula holds because the build result is a conjunction of every test's outcome: any single failure turns it red. Retries change the conjunction to "each test passes within *k* attempts", reducing the effective per-test failure probability from *p* to *pᵏ* when attempts are independent. The independence assumption is the weak point: a flaky cause that affects the whole machine (an overloaded runner, a full disk) correlates failures, so retrying immediately on the same runner helps less than the formula suggests, and retrying on a fresh runner helps more. This is also why *rerunning the entire job* often works when rerunning a test does not: you get a different runner.

## Common mistakes

- **"Just re-run it"** as the team's standard answer, with no tracking.
- **Retrying everything** without recording what needed a retry.
- **Concluding a flake is fixed after a handful of clean runs.**
- **Deleting a flaky test** that covers real behaviour instead of fixing the race.
- **Sleeping to fix a timing flake**, trading flakiness for slowness.
- **Not publishing reports on failure.**
- **Unseeded randomness** with no logged seed.
- **Treating a flake rate as per-suite** when the formula is per-test.

## Exercise

1. Compute P(green) for 300 tests at p = 0.003, then simulate 10,000 runs in Python and compare. How close is it?
2. You rerun a test 50 times and see 3 failures. Give the estimate and a rough 95% interval. How many more runs would halve the interval's width?
3. Design a quarantine policy: where the list lives, who owns entries, the maximum age, and how the dashboard metric is computed.
4. Write a pytest plugin sketch or `conftest.py` hook that records every test that passed only after a retry to a file for the nightly report.
