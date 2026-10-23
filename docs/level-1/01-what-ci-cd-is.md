---
description: "What CI, continuous delivery and continuous deployment mean, the problems they address, and what a pipeline is, with a runnable example."
---

# 01 · What CI/CD Is and Why Pipelines Exist

Before CI/CD, shipping software looked like this: several people work for weeks on separate branches, someone merges everything the night before a release, the build is broken in five ways nobody anticipated, and deployment is a manual checklist followed at midnight. **Continuous integration** and **continuous delivery** exist to make that painful event small, frequent and boring.

!!! note "About this course and what was run"
    This course was written on a Mac with **no GitHub Actions runner and no Jenkins server available**, and no cloud account. So:

    - **GitHub Actions and Jenkins syntax** (workflow files, `Jenkinsfile`s, plugin behaviour) comes from their documentation as read in October 2026 and is **not run**. Where a YAML example is shown, I parsed it with PyYAML to confirm it is well-formed YAML, which does not prove GitHub or Jenkins would accept it. Documented limits quoted for GitHub-hosted runners come from the GitHub Actions limits page.
    - **The ideas** (stages, dependencies, matrices, caches, artifacts, gates, deployment strategies) are demonstrated with **real runs** of `minici`, a small local CI runner I wrote for this course (about 150 lines of Python, 15 passing tests). It is a teaching tool. It is *not* GitHub Actions or Jenkins and does not behave identically; where I say "a real system does X", that is documentation, not something minici proves.
    - Statistics about industry practice are not quoted: I have no source I verified, so none appear.

    You can try every GitHub Actions example for free in a public repository, and Jenkins runs in a container or from its WAR file.

## The three terms

| Term | What it means | What it needs |
|---|---|---|
| **Continuous Integration (CI)** | Developers merge small changes into a shared mainline frequently, and **every change is automatically built and tested** | A build that runs without human steps, tests worth trusting, a rule that a broken mainline is fixed first |
| **Continuous Delivery** | Every change that passes the pipeline is **kept in a deployable state** and can be released to production at any time with one decision | Automated packaging, deployment to staging, repeatable release steps |
| **Continuous Deployment** | Every passing change is **released to production automatically**, with no manual gate | High-confidence tests, monitoring, fast rollback, feature flags |

Delivery is "we *could* ship now"; deployment is "we *did* ship". Plenty of teams stop at delivery on purpose (regulation, customer release cycles), and that is a legitimate choice.

## The problems it addresses

1. **Integration pain grows with time.** Two developers change the same code for a month; the merge takes days. Merging small changes daily keeps conflicts small and the cause obvious.
2. **"Works on my machine."** A pipeline builds from a clean environment, so hidden dependencies on someone's laptop get exposed immediately.
3. **Late feedback is expensive.** The sooner a defect is found after it was introduced, the cheaper it is to fix: the author still remembers the change, and nothing else has been built on it. A pipeline's job is to shrink the time between "I broke it" and "I know".
4. **Manual release steps are error-prone.** A runbook of 30 manual steps has a failure rate per step; automating them makes the 31st release identical to the first.
5. **Big releases are risky.** A deployment containing three months of changes is hard to test and hard to roll back. A deployment containing one change is easy to reason about.

## What a pipeline actually is

A pipeline is **an automated, versioned recipe** that turns a commit into evidence and artifacts: *Does it build? Do the tests pass? Is it safe and compliant? Can it be packaged? Does it run in a production-like environment?* Each step either produces a result or stops the line.

```text
commit/push ─► build ─► test ─► scan ─► package ─► deploy to staging ─► verify ─► (approval) ─► deploy to production ─► monitor
    └────────── continuous integration ───────────┘└────────────── continuous delivery / deployment ──────────────┘
```

Three properties make it useful: it's **automatic** (nobody remembers to run it), **repeatable** (same inputs, same steps, same result), and **visible** (everyone sees red or green and the logs behind it).

### A first look (run)

The `minici` runner executes a pipeline file with five jobs: dependencies, a syntax check, tests in three time-zone variants, packaging, and a simulated deploy. First run, abridged to the interesting lines:

```text
[deps] step 1 'install dependencies (slow step, 2 s)': ok
    | installed
[test {"tz": "UTC"}] step 1 'tests under UTC': ok
    | 3 passed in 0.00s
[package] step 1 'build artifact': ok
[deploy] step 1 'deploy (simulated)': ok
    | deploying app-1.0.0.tar.gz
RESULT: success
```

The pipeline ran the dependency install and the lint in parallel, waited for both before starting the three test variants in parallel, and only then packaged and "deployed". Stages are ordered by **dependencies** (`needs`), not by position in a file. The next lessons dissect exactly this.

## What CI/CD is not

- **Not a tool.** GitHub Actions, Jenkins, GitLab CI and others are implementations of a practice. Buying one doesn't give you CI if developers merge once a month or the tests are unreliable.
- **Not a substitute for tests.** A pipeline runs your checks; it can't create confidence you didn't build.
- **Not only about deploying.** Fast, trustworthy feedback on every change is the part teams benefit from first.
- **Not free of risk.** Pipelines hold credentials and run code, so they are themselves a prime attack surface (Level 4 · 01).

## Principles to carry through the course

1. **Keep the mainline releasable.** If main is red, fixing it is the top priority.
2. **Build once, deploy many.** Create one artifact and promote the *same* artifact through environments (Lesson 07); don't rebuild per environment.
3. **Fail fast and cheap first.** Run quick checks (lint, unit tests) before slow ones (integration, end-to-end).
4. **Make the pipeline code.** It lives in version control, is reviewed, and changes with the software.
5. **Everything the pipeline needs is declared**: dependencies, tool versions, environment, secrets references.
6. **Fast feedback beats exhaustive feedback.** Aim for the first signal in minutes; run the long tail in parallel or later stages.
7. **Observe the pipeline itself**: duration, failure rate, flakiness (Level 2 · 05), and the DORA measures (Level 3 · 09).

## How It Actually Works

Under every CI system the mechanism is the same: an **event** (a push, a pull request, a schedule, a manual click) reaches an **orchestrator** that reads the pipeline definition from the repository, builds a graph of jobs, and assigns each ready job to an **executor** (a runner or agent: a VM, container or bare machine). The executor checks out the code at the exact commit, runs the steps in a clean workspace, streams logs back, and reports success or
failure, optionally storing **artifacts** and **caches**. The orchestrator uses the results to decide what runs next and to update the status shown on the commit or pull request. `minici` implements precisely that loop in miniature: topological ordering, parallel execution of independent jobs, step-level pass/fail, and skipping dependents of a failed job.

## Common mistakes

- **Treating CI as a build server nobody watches**, so red builds stay red.
- **Long-lived feature branches** that defeat integration frequency.
- **A pipeline so slow that people stop waiting for it** and merge anyway.
- **Tests that pass or fail randomly**, teaching the team to ignore failures (Level 2 · 05).
- **Rebuilding separately for each environment**, so what you tested isn't what you shipped.
- **Pipeline logic hidden in the CI tool's web UI** instead of versioned files.
- **Automating a broken manual process** without fixing it first.

## Exercise

1. Write down your team's (or a project's) path from commit to production as a numbered list, marking each step manual or automatic, and note where the longest waits are.
2. Classify your current setup as CI only, continuous delivery, or continuous deployment, and name the single change that would move it one step along.
3. Run `minici` on the demo project (in the course repository's `src/` folder) twice, and compare the two summaries: what changed and why?
4. Pick one recent bug and estimate how long it lived between being introduced and being found. What pipeline stage could have caught it?
