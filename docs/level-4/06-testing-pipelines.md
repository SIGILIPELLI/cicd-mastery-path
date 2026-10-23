---
description: "Testing the pipeline itself: contract tests on good and broken inputs, gates that must be able to fail, and a PATH surprise found along the way."
---

# 06 · Testing Pipelines

A pipeline is code that decides whether other code ships. If it is wrong, it can fail to catch a broken build (a false green) or block good ones (a false red) and either is expensive. Yet pipelines are often the least tested code in a repository, changed by editing YAML and pushing to see what happens. This lesson shows how to give a pipeline automated tests, using the course's `minici` runner as the system under test.

!!! note "What was run"
    `src/test_pipeline_contract.py` (4 tests) runs the Level 1 demo pipeline through `minici` on copies of the demo project and asserts the behaviours it promises. These are tests of a **local teaching runner**; GitHub Actions and Jenkins can be tested with different tools (below, described and not run here), and their execution semantics differ from `minici`. The contract-test idea transfers; the harness does not.

## What there is to test

1. **The pipeline's promises**: if tests fail, nothing is deployed; if lint fails, tests do not run; every matrix cell runs; artifacts are produced only on success.
2. **The gates themselves**: does the security scan actually fail on a known-bad input? A gate that never fails may not be running (a scan that quietly finds nothing because the path is wrong).
3. **Pipeline code**: scripts, shared libraries, composite actions: ordinary unit tests apply (the course's tools each have their own).
4. **Configuration validity**: YAML syntax, expression errors, references to jobs and secrets that don't exist: a linter's job (Level 2 · 10).

## Contract tests with a local runner

The four tests, each copying the demo project to a temporary directory, optionally breaking something, running the pipeline and checking per-job results:

1. **Green pipeline deploys:** all jobs succeed, including `package` and `deploy`.
2. **A failing unit test blocks packaging and deployment:** replace the test file with `assert False`; expect `test` = failure and `package` = skipped and `deploy` = skipped. This is the central promise of a CD pipeline, and it is a regression test for the `needs` wiring: if someone removes `needs: [test]` from `package`, this test fails.
3. **A syntax error fails lint and skips tests:** the `lint` job fails and `test` is skipped, confirming the dependency order.
4. **Every matrix cell ran:** three `test` cells, all successful (a test against silently shrinking matrices).

All four passed. **They did not pass the first time.** The first run had two failures: the green-pipeline test and the matrix test reported failure. The cause was environmental, not the pipeline logic: each pipeline step runs `python3 -m pytest`, and in the subprocess `python3` resolved to the system Python, which has no `pytest`; the interpreter running my tests (a virtual environment) did. With the virtual environment's `bin` directory first on `PATH`, all four pass. I fixed the test harness by prepending the running interpreter's directory to `PATH` inside the test, with a comment explaining why.

That failure is a small, real instance of the problem this lesson is about: **a pipeline's behaviour depends on its environment, and the environment is part of what you must pin and test.** The identical YAML gave green or red depending on which `python3` was found first. On CI the same issue appears as "works on my machine, fails on the runner" (Level 2 · 08), and the fix is the same: declare the interpreter explicitly (a `setup-python` step with a version, a container image with a pinned tag or digest) and verify with a step that prints the resolved path and version.

## Techniques for real platforms

These are described from public documentation and general practice, and I did not run them for this course.

- **Run workflows locally with an emulator** (tools such as `act` run GitHub Actions workflows in containers). Useful for fast iteration, but it is an emulation, not the platform: contexts, permissions, caches, secrets, OIDC and hosted-runner contents differ. Treat a local pass as "likely", and the platform run as truth.
- **A test repository.** Keep a sandbox repository where pipeline changes are exercised on real runners with harmless payloads, including deliberately failing cases, before the change is released to the shared workflow tag (Level 2 · 03).
- **Canary the pipeline change**: switch one low-risk repository to the new reusable-workflow version first.
- **Jenkins:** a pipeline unit-testing library can run Jenkinsfiles with mocked steps in a JVM; the declarative linter validates syntax against the real grammar. For shared libraries, unit-test the Groovy classes.
- **Property: the pipeline must be able to fail.** For every gate, keep (or generate) a deliberately failing input in a test fixture and assert the gate rejects it. In this course, the linters were all tested on both good and bad samples for exactly that reason.

## Mutation testing a pipeline

The contract tests above can themselves be tested: *mutate the pipeline* (delete a `needs:` line, remove the `if:` on the deploy job, change a threshold) and check that **some** test fails. A mutant that no test catches reveals an untested promise. It is the same technique as mutation testing for code (Level 2 · 06) applied to configuration. Doing this by hand once for each critical promise ("deploy needs test", "tests need lint") is cheap and instructive; automating it is a small script that edits a copy of the YAML and runs the suite.

## Testing for the failure modes you fear

List the worst things a pipeline could do, then test each:

| Fear | Test |
|---|---|
| Deploys when tests fail | Break a test, assert no deploy (done above) |
| Deploys from a pull request or a fork | Run with a PR-like event context and assert the deploy job is skipped |
| Leaks a secret to logs | Run with a sentinel secret value and grep the logs for it (a masking test) |
| Runs two deploys at once | Trigger two runs and assert serialisation (needs the real platform) |
| Passes with an empty test set | Make `pytest` collect zero tests and assert the job fails (exit code 5 in pytest for "no tests collected") |
| Succeeds when a step is skipped by mistake | Count the steps that actually ran |

The empty-test-set case is worth a special note: many runners treat "no tests found" as success, which turns a misconfigured path into a permanently green pipeline.

## Speed and flakiness of pipeline tests

Pipeline tests are slow if they run real builds. Keep them small: a tiny sample project, stubbed installation (the contract test replaces the 2-second install with `mkdir libs`), parallel runs, and a split between *fast contract tests on every change to pipeline files* and *slower end-to-end checks nightly*. Pipeline tests flake like any other (shared ports, wall-clock dependencies) and the same discipline applies (Level 2 · 05).

## Checklist

- Every critical promise has a contract test: no deploy on failure, no deploy from a fork, no deploy on zero tests.
- Each gate has a deliberately failing fixture.
- The interpreter and tool versions are pinned and printed by the pipeline.
- Pipeline logic lives in testable scripts with unit tests.
- Pipeline changes go through a sandbox repository first.
- Reusable workflow changes are canaried on one low-risk repository.
- Mutation of needs and if lines is checked at least once per critical promise.
- Contract tests are fast and run on every change to pipeline files.
- Slower end-to-end checks run nightly.
- Emulator results are treated as likely, platform results as truth.
- Test failures in the pipeline suite are triaged with the same flake discipline as product tests.

## How It Actually Works

The contract tests work because `minici`'s `Runner` is a library: it takes a parsed pipeline and a working directory and returns per-job results (`success`, `failure`, `skipped`) in a dictionary that the test can assert on. That separation, a runner you can call from code with an inspectable result, is the design property that makes a pipeline testable. Platform CI engines do not expose such an API for local use, which is why testing them needs either an emulator, a real sandbox run, or extracting the logic into scripts that *are* testable and keeping the YAML thin. The most effective strategy at scale is the last: put decisions in versioned scripts with unit tests (like this course's linters and guards), and let the pipeline file merely call them in order.

## Common mistakes

- **Never testing the pipeline**, learning from production failures.
- **Gates that can never fail**, with no failing fixture to prove they work.
- **Relying on a local emulator** as proof.
- **Environment assumptions** (which `python3`?) left implicit.
- **Treating "no tests collected" as success.**
- **Big logic in YAML** that cannot be unit tested.
- **No test of the deploy-skipping rules** for PRs and forks.

## Exercise

1. Run `pytest src/test_pipeline_contract.py -v`. Remove `needs: [test]` from the `package` job in a copy of the demo pipeline and confirm which test fails. Restore it.
2. Write a contract test that asserts `deploy` never runs when the event is a pull request (add an `if` to the pipeline and a way to pass the event).
3. Write a test where the test suite collects zero tests, and make the pipeline fail on it.
4. Build the mutation script: delete each `needs` entry in turn and report which mutants survive.
