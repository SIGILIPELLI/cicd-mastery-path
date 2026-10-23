---
description: "Matrix builds and parallelism: expansion, include and exclude, fail-fast, job limits, and sharding tests, with the expansion computed and counted."
---

# 01 · Matrix Builds & Parallelism

A **matrix** runs the same job many times with different parameters: operating system, language version, database version, a shard number. It is the cheapest way to answer "does it work everywhere we claim it does?" and also the cheapest way to burn your CI budget, because the number of jobs is a *product*. This lesson shows exactly how a matrix expands, how `include` and `exclude` change it, what the documented limits are, and how to split one slow test suite across parallel jobs.

!!! note "What was run"
    The expansion results below were computed by the `expand_matrix` function in the Level 1 `minici` runner (`src/minici.py`), which implements the documented rules in a simplified form. It is **not** GitHub's implementation; where the real service differs the platform's behaviour wins. The limits quoted (256 jobs per matrix, concurrency by plan) come from docs.github.com as read in October 2026 and were not exercised on GitHub. Jenkins' matrix syntax is described from jenkins.io and not run.

## Expansion is a product

```yaml
strategy:
  fail-fast: false
  matrix:
    os: [ubuntu, windows, macos]
    python: ["3.11", "3.12", "3.13"]
    exclude:
      - {os: macos, python: "3.11"}
    include:
      - {os: ubuntu, python: "3.14", experimental: true}
```

Running `expand_matrix` on that block produced **9 jobs**: the 3 × 3 = 9 product, minus the one excluded pair, plus the one extra `include` entry:

```text
ubuntu/3.11  ubuntu/3.12  ubuntu/3.13
windows/3.11 windows/3.12 windows/3.13
macos/3.12   macos/3.13
ubuntu/3.14 (experimental: true)
```

Three rules explain every matrix you will meet:

1. Each key with a list contributes a **dimension**; the job list is the Cartesian product of all dimensions.
2. `exclude` removes combinations that match *all* the keys given (a partial pattern removes every combination containing those values).
3. `include` either **adds a key to existing combinations** it matches (if every original key it mentions matches) or, when it matches none, **adds a new combination**. That is how `experimental: true` can be attached to one cell, or a lone extra cell can be added.

The second rule of `include` is the one people trip on. In `minici`, `{os: ubuntu, python: "3.14"}` matches no product cell (no 3.14 in the list), so it becomes a new job. Had it said `{os: ubuntu, experimental: true}`, it would have been *merged into* all three Ubuntu cells instead. The same line of YAML is "add a job" or "annotate three jobs" depending on what the product contains. Print the expanded list in a test or a dry run before you trust it.

## Sizes grow fast

| Matrix | Jobs |
|---|---|
| 3 OS × 3 Python | 9 |
| 3 × 3 × 2 databases × 2 feature flags × 3 shards | 108 |
| 4 × 4 × 4 × 5 | 320 |

Per the GitHub documentation, a matrix can generate at most **256 jobs per workflow run**. The 108-job matrix fits; the 320-job one does not and the workflow is rejected. Fitting is not the same as sensible: 108 jobs at 4 minutes each is 7.2 job-hours for one push, and on hosted runners you pay (or consume free minutes) for each job's wall time, usually rounded up per job. Concurrency is also capped by plan; the documented hosted-runner concurrent-job limits are 20 (Free), 40 (Pro), 60 (Team) and 500 (Enterprise) as I read them. A 108-job matrix on a 20-job plan queues most of itself, so total wall time is bounded by the cap, not by your longest job.

## Fail-fast and "experimental" cells

By default, on GitHub Actions, if one matrix job fails the in-progress and queued siblings are cancelled (`fail-fast: true`). That is good for saving money on a broken commit and bad when you want the full compatibility picture: you fix the Windows failure, then discover macOS also failed, one full cycle later. A common stance:

- **Pull requests:** `fail-fast: true`, small matrix (one OS, oldest and newest language version).
- **Main branch / nightly:** `fail-fast: false`, the full matrix, because the goal is the complete table.
- **Cells that may fail without blocking:** `continue-on-error: ${{ matrix.experimental == true }}` so a pre-release interpreter reports but does not turn the whole run red.

Jenkins declarative pipelines express the same with a `matrix { axes { axis {...} } }` block and `excludes`; the product rule is identical, and `failFast true` on the parent stage is the analogue.

## Sharding: splitting one suite across jobs

A matrix over a *shard index* is how you make a 20-minute suite finish in 5. The runner needs a rule that assigns each test to exactly one shard. Two common rules:

- **By file, round-robin:** shard `i` of `n` takes test files `i, i+n, i+2n, ...` in a *sorted* list. Simple and deterministic, but unbalanced when file durations differ.
- **By recorded duration:** greedily give the longest remaining file to the lightest shard, using last run's timings. Needs stored timing data, which can go stale.

Whatever the rule, three properties must hold or you get false greens: **every test runs exactly once** (no gaps, no overlaps), **the assignment is stable** between the planning step and the running step (sort the list!), and **a failing shard fails the build** (see "required checks" below).

## Required checks and matrix names

Branch protection (Lesson 09 of Level 1) requires status checks by *name*. A matrix produces one check per cell, named like `test (ubuntu, 3.12)`. If you rename a dimension or remove a cell, the required check with the old name never reports, and PRs wait forever on "expected". A robust pattern is a final **gate job** with `needs: [test]` and `if: always()` that fails unless `needs.test.result == 'success'`, and to require only that one stable name. The `if: always()` matters: without it, a failed matrix makes the gate *skipped*, and a skipped required check is treated as passing by some configurations.

## How It Actually Works

A matrix is evaluated at **workflow-planning time**, before any runner is allocated. The service takes the strategy block, computes the list of parameter sets, and creates one job object per set, each with its own copy of the steps and a `matrix` context. Expressions such as `${{ matrix.python }}` are substituted when the job starts. That is why a matrix value cannot depend on the output of a step *in the same job*; it can be computed by an *earlier* job and passed in through `fromJSON(needs.plan.outputs.matrix)`, which is the standard way to make a dynamic matrix (for example, one cell per changed package; Lesson 09).

Because every cell is an independent job on a fresh runner, they share nothing but what you explicitly cache or upload as artifacts. Parallelism is therefore free of data races but not free of cost: each cell pays checkout, setup and dependency installation again, which is why the cache design in Lesson 02 matters more as the matrix grows.

## Common mistakes

- **Counting cells in your head** and discovering the product is 300 jobs only when the bill arrives.
- **Using `include` to "add a row"** when it merges into existing rows (or vice versa).
- **Leaving `fail-fast` on for a compatibility matrix**, hiding failures behind the first one.
- **Quoting versions wrongly:** `python: [3.10]` is parsed by YAML as the float `3.1`. Quote version strings (`"3.10"`).
- **Requiring matrix cell names directly** in branch protection and then changing the matrix.
- **Unsorted or time-dependent shard assignment**, so shards overlap or skip tests.
- **Matrices for things that do not vary**: if no failure has ever differed between two cells, drop one.

## Exercise

1. Run `python3 src/minici.py` against a pipeline with the 9-cell matrix above (or call `expand_matrix` directly) and confirm the list. Then change the `include` entry to `{os: ubuntu, experimental: true}` and predict the new job count before running it.
2. Write a function `shard(files, i, n)` and a test proving that for several `n`, the union of all shards equals the file list and no file appears twice. Add a test that shuffling the input does not change the result.
3. Take a real project's workflow. Compute its matrix size and estimate minutes per push. Which cell has never failed alone in the last 50 runs?
4. Design the gate job for a 6-cell matrix so that a cancelled or skipped cell blocks the merge.
