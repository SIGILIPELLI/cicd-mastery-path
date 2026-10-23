---
description: "Pipeline anatomy: triggers, jobs, steps, stages, dependencies, runners, artifacts and exit codes, shown with a runnable example."
---

# 02 · Pipeline Anatomy: Triggers, Jobs, Steps & Stages

Every CI system uses different words, but the structure underneath is the same. Learn the structure once and GitHub Actions, Jenkins, GitLab CI and the rest become dialects. This lesson names the parts and demonstrates the control flow by running a small pipeline.

!!! note "What was run"
    The pipeline runs below used `minici` (this course's local runner, not GitHub Actions or Jenkins; see Lesson 01). The vocabulary table for GitHub Actions and Jenkins is from their documentation as of October 2026 and is not run. See Lesson 01 for the full note.

## The vocabulary, side by side

| Concept | Meaning | GitHub Actions | Jenkins (Declarative) | minici |
|---|---|---|---|---|
| **Pipeline / workflow** | The whole automated process, defined as code | A workflow file in `.github/workflows/` | A `Jenkinsfile` | A YAML file |
| **Trigger** | The event that starts a run | `on:` (push, pull_request, schedule, workflow_dispatch...) | SCM polling/webhooks, `triggers {}`, "Build now" | You run the command |
| **Job** | A unit of work on one executor, with its own clean workspace | `jobs.<id>` | A `stage` (with its own agent if declared) | `jobs.<id>` |
| **Step** | One command or reusable action inside a job | `steps:` (`run` or `uses`) | `steps {}` (`sh`, `bat`, plugin steps) | `steps:` with `run` |
| **Stage** | A named phase grouping work (build, test, deploy) | Not a first-class concept; jobs and `needs` express it | `stage('Build')` | Levels computed from `needs` |
| **Runner / agent** | The machine or container that executes jobs | `runs-on:` | `agent {}` | Your laptop |
| **Dependency** | Order between jobs | `needs:` | Sequential stages; `parallel {}` blocks | `needs:` |
| **Condition** | Whether something runs | `if:` | `when {}` | `if:` |
| **Artifact** | Files produced for later use or download | upload/download artifact actions | `archiveArtifacts` | `artifacts:` |
| **Cache** | Reusable files to speed up later runs | cache action | plugins or agent-local caches | `cache:` |
| **Environment / secrets** | Variables, protected targets | `env`, `secrets`, `environment:` | `environment {}`, credentials binding | `env:` |

## Triggers

A pipeline should start for a reason you can name. Common triggers:

- **Push** to specific branches (main, release branches), maybe filtered by paths (Level 2 · 09).
- **Pull request** opened or updated: the single most valuable trigger, because it gives feedback *before* merging.
- **Schedule** (cron): nightly builds, dependency audits, long-running tests (Level 1 · cron semantics from the Linux course apply, including UTC).
- **Manual** (`workflow_dispatch` in Actions, "Build with parameters" in Jenkins): deploys, hotfixes, one-off tasks.
- **Tag** push: release builds (Lesson 07).
- **Another pipeline** finishing, or a webhook from an external system.

Be deliberate about which events can reach secrets or deploy: pipelines triggered from forks of public repositories are a classic security boundary (Level 4 · 01).

## Jobs, steps and the workspace

A **job** gets a fresh workspace: a clean checkout of the code at the triggering commit, on a clean runner. Nothing from a previous job is there unless you pass it explicitly via **artifacts** or a **cache** (Lessons 06 and 07). That is a feature: it forces your build to declare what it needs. **Steps** within one job share that job's filesystem and run in order; if a step exits non-zero, the job fails and later steps are
skipped unless told otherwise (a cleanup step typically has a `failure()`/`always()` condition).

The unit of success is the **exit code**: 0 passes, anything else fails. This is why a step like `pytest` gates a pipeline without any special integration, and why a shell step like `cmd1 | cmd2` can hide a failure unless `pipefail` is set (Linux course, Level 4 · 01). `minici` runs every `run:` script with `set -eo pipefail` for this reason.

## Dependencies form a graph

Jobs with no dependency between them run in **parallel**; a job with `needs: [a, b]` waits for both. The pipeline is a directed acyclic graph (DAG). A small pipeline run locally:

```yaml
jobs:
  build:   {steps: [{name: compile,            run: "echo compiling; exit 0"}]}
  test:    {needs: [build],   steps: [{name: unit tests, run: "echo 2 failed; exit 1"}]}
  package: {needs: [test],    steps: [{name: package,    run: "echo packaging"}]}
  report:  {needs: [test], if: "always()", steps: [{name: publish test report, run: "echo uploading report anyway"}]}
  docs:    {steps: [{name: build docs,         run: "echo docs ok"}]}
```

Run (macOS, minici):

```text
levels computed from needs: [['build', 'docs'], ['test'], ['package', 'report']]
[build] step 1 'compile': ok
[docs] step 1 'build docs': ok
[test] step 1 'unit tests': FAILED rc=1
    | 2 failed
[package] skipped (a needed job did not succeed)
[report] step 1 'publish test report': ok
RESULT: failure
```

What the output demonstrates:

1. `build` and `docs` ran in the same level (parallel) because neither needs the other.
2. `test` failed, so `package` was **skipped**: a job whose dependency failed does not run (the default behaviour in both Actions and Jenkins's sequential stages).
3. `report` ran **anyway** because it has `if: always()`. Reporting, notifications and cleanup are the classic uses.
4. The overall run is `failure`, even though three of the four executed jobs passed. The status line on the pull request should reflect the worst result.

## Conditions and outputs

Real systems let steps and jobs run conditionally: only on the main branch, only when certain files changed, only on tags. Jobs pass small values to later jobs through **outputs** (a version string computed in one job and used in another), and larger data through artifacts. In GitHub Actions, contexts such as `github.ref`, `github.event_name` and `matrix.*` are available inside `${{ }}` expressions; in Jenkins, `env.BRANCH_NAME` and `when { branch 'main' }`
play that role. Keep conditions simple: complicated boolean logic in pipeline YAML is hard to read and test.

## Stages as a mental model

Even where the tool has no "stage" keyword, think in stages with increasing cost and confidence:

```text
1. Fast checks      format, lint, type check, unit tests         seconds to a few minutes
2. Build & package  compile, build artifact/container image       minutes
3. Slow checks      integration, security scans, end-to-end        minutes to tens of minutes
4. Deploy to staging, smoke tests                                  minutes
5. Release gate     approval and/or automated checks               variable
6. Production       deploy, verify, monitor                        minutes
```

Earlier stages should be cheaper and more likely to fail; this ordering lowers average feedback time (Lesson 05).

## Idempotence, timeouts and concurrency

- **Idempotent steps**: re-running a failed pipeline should be safe. A deploy that appends configuration each run is a bug waiting for a retry.
- **Timeouts**: every job and step needs one, so a hung process does not hold a runner for hours. GitHub-hosted runners terminate any job after 6 hours (documented limit), which is far too long to be a useful timeout. `minici` supports per-step timeouts (a test with a 1 s timeout and `sleep 5` is killed and reported as timed out).
- **Concurrency control**: two deploys to the same environment at once are dangerous. Systems offer concurrency groups (Actions `concurrency:`) or locks (Jenkins lockable resources plugin) so a second run waits or replaces the first.

## How It Actually Works

The orchestrator parses the pipeline definition into a graph, then repeatedly picks jobs whose dependencies are all finished and successful (or whose condition allows running), and dispatches them to free executors. Each executor prepares a workspace (checkout), runs steps by spawning a shell or container for each, captures output, and returns exit status. `minici` does this with `topo_levels` (grouping jobs whose `needs` are
satisfied), one thread per job in a level, and `subprocess.run` per step with a timeout. Status propagation is simple: a job is `skipped` if any dependency's result is not `success` (unless `if: always()`), and the run is a success only if every job succeeded or was deliberately skipped.

## Common mistakes

- **No timeouts**, so hung jobs consume runners.
- **Assuming files persist between jobs.**
- **Exit codes swallowed** (`|| true`, pipes without `pipefail`, commands that print "FAILED" but exit 0).
- **A deploy job without concurrency protection.**
- **Everything in one giant job**, so nothing runs in parallel and a retry repeats all the work.
- **Conditions that skip security checks** on some branches.
- **Treating "skipped" as success** in required-check rules (a skipped required check can unintentionally let a pull request merge in some configurations; check your platform's behaviour).

## Exercise

1. Draw the DAG for a pipeline you know (jobs and `needs`). Where is the critical path, and which jobs could run in parallel but do not?
2. Modify the example so `package` still runs when only `docs` fails but not when `test` fails. What `needs` and `if` do you need?
3. Add a step that exits 0 even though a command inside a pipe failed, then fix it with `pipefail`, and describe how you would catch this class of bug in review.
4. Look up the trigger syntax for your CI system and write down which events would start a run for (a) a pull request from a fork, (b) a push to main, (c) a tag.
