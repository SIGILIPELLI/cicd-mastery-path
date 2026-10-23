---
description: "Pipeline speed and cost: critical path analysis, billed minutes with matrices and queue time as a nonlinear effect, with models."
---

# 02 · Speed & Cost

A slow pipeline is a tax on everyone: engineers context-switch while waiting, batches grow bigger because each run is expensive, and flaky failures become more costly to retry. A costly pipeline is a budget problem that tends to show up as a sudden constraint. Both are usually fixed by understanding **where the time goes**, which is rarely where intuition says.

!!! note "What was run"
    `src/pipeperf.py` (7 tests) computes the critical path of a job graph and billed minutes; the example numbers below are the **fixture** in its tests, not measurements of any real pipeline. The cost function takes a rate you supply: I use an arbitrary illustrative number (0.5 per minute) and make no claim about any provider's prices. The queueing results are from a simulation (Lesson 03 and Level 2 · 08).

## Two different quantities

- **Wall-clock time** (latency): how long a developer waits. Determined by the **critical path**, the longest chain of dependent jobs.
- **Compute time** (cost): total machine-minutes billed, the *sum* over all jobs, including every matrix cell.

Parallelism trades one for the other: splitting a 12-minute job across 3 runners cuts wall-clock time but not total compute (and adds startup overhead for each).

## The critical path

Consider a graph: `lint` (1 min), `build` (4), `unit` (6, a 3-cell matrix, needs `build`), `e2e` (12, needs `build`), `deploy` (2, needs `unit`, `e2e` and `lint`).

```text
critical path: 18.0 minutes   build (4) -> e2e (12) -> deploy (2)
billed minutes: 37            lint 1 + build 4 + unit 6x3 = 18 + e2e 12 + deploy 2
```

Two experiments from the tests:

1. **Make a non-critical job faster.** Cutting `unit` from 6 minutes to 1 changes the path to ... nothing: still 18.0. The 3-cell `unit` job was never on the critical path (it finishes at minute 10; `e2e` finishes at 16). All that effort saves cost and no waiting.
2. **Make the critical job faster.** Cutting `e2e` from 12 to 3 minutes drops the total only to **12.0**, and the critical path *moves*: `build -> unit -> deploy` (4 + 6 + 2). A 9-minute saving in one job gave a 6-minute saving overall because another path took over. After you shorten the longest path, the second longest becomes the target.

Practical consequence: **measure before optimising.** Take the actual job durations from a dozen recent runs (median and p90), compute the critical path, and only work on jobs on it. Optimising a job off the path is a cost project, not a speed project, and should be justified as one.

## Where time actually goes

Typical breakdown of a job, and the lever for each:

| Phase | Lever |
|---|---|
| Waiting for a runner | Pool size, autoscaling (see below) |
| Checkout | Shallow clone (but see Level 2 · 09), sparse checkout for monorepos |
| Setup and dependency install | Caching with a good key (Level 2 · 02), prebuilt images |
| Build | Incremental or remote-cached builds, parallel compilation |
| Tests | Sharding (Level 2 · 01), run only affected tests (Level 2 · 09), fix slow tests |
| Packaging, upload, publish | Skip on PRs; compress less; upload once |
| Fixed overhead per job | Fewer, larger jobs vs more parallelism |

Test the overhead assumption: a job that does 10 seconds of work after 90 seconds of setup should probably be merged into its neighbour, because each job pays setup again.

## Cost: the matrix multiplies

`billed_minutes` sums per-cell minutes, **rounding each job up** to whole minutes in the default model (many providers bill per started minute; check yours). A job of 0.2 minutes in a 10-cell matrix is billed as 10 minutes, not 2. In the tests: 10 cells of 0.2 min → 10 billed minutes versus 2.0 without rounding. Fixture total: 37 billed minutes, at the arbitrary 0.5 rate = 18.5 units per run. Multiply by runs per day to see the monthly effect; a team pushing 200 PR updates a day at that fixture's 37 minutes spends 7,400 billed minutes per day, which is the sort of figure that gets noticed.

Cost levers: reduce wasted runs, shrink matrices on PRs and run the full matrix on `main`, cancel superseded runs (`concurrency` with `cancel-in-progress: true` for CI, never for deploys; Level 2 · 07), skip jobs when only docs changed, avoid retrying whole pipelines for single flakes, and clean up old artifacts and caches that count toward storage limits. Self-hosted runners change the accounting from per-minute to fixed capacity.

## Queue time: the hidden component

Developers experience wait time as time-to-result, and part of it is waiting for a free runner. I simulated a pool of 8 runners, jobs averaging 5 minutes, arriving randomly (Poisson), first-come-first-served (an M/M/c queue):

| Utilisation | Mean wait (simulated) | 90th percentile wait | Closed-form (Erlang C) mean |
|---|---|---|---|
| 50% | 0.08 min | 0.00 | 0.07 |
| 70% | 0.56 | 2.06 | 0.56 |
| 80% | 1.41 | 4.65 | 1.43 |
| 90% | 4.43 | 12.25 | 4.38 |
| 95% | 11.67 | 29.64 | 10.55 |
| 98% | 32.88 | 80.65 | 29.25 |

The simulation and formula agree closely up to 90% (within about 2%); at 95% and 98% the simulated mean deviates by about 10–12% from the formula, which I attribute to slow convergence of a nearly saturated queue in a finite run, not a different model (I did not verify that by longer runs). The shape is the message: wait time is **nonlinear** in utilisation. Going from 80% to 90% busy triples the mean wait; at 98% a job waits half an hour on average. A pool that looks "efficient" at 90% average load delivers terrible latency, and real load is burstier than Poisson (everyone pushes at 9:30), so the real numbers are worse.

Pool size matters too, at the same utilisation: at 90% busy, mean wait is **21.5 min with 2 runners**, **4.4 min with 8**, **0.74 min with 32** (simulated; Erlang C gives 21.3, 4.4, 0.72). Larger pools absorb variation better, which is the statistical argument for shared pools over per-team pools.

Plan capacity for a target such as "90th percentile wait under 2 minutes at peak", not for average utilisation.

## A sensible order of work

1. Measure: collect per-job durations, queue times and costs. Without data you will optimise the wrong thing.
2. Fix the critical path; re-measure; repeat.
3. Cut waste: duplicate runs, unneeded matrix cells, jobs triggered by irrelevant changes.
4. Cache and shard.
5. Revisit pool sizing and autoscaling.
6. Only then consider heavier changes (a build system with remote caching, bigger machines).

## How It Actually Works

The pipeline is a directed acyclic graph with a duration on each node. The earliest finish time of a node is its own duration plus the latest finish among its dependencies, computed by a memoised recursive walk (`finish[n] = max(finish[deps]) + minutes[n]`). The graph's total time is the maximum finish over all nodes, and following the `via` pointers back from that node recovers the critical path. This is the same algorithm project managers use for critical-path analysis. A queue changes the picture because a job's *ready time* is no longer its start time: start = ready time + wait, and the wait depends on the pool's state, which depends on every other pipeline running at the same time. Hence local optimisations (making one pipeline faster) can be swamped by a global effect (the pool saturating).

## Common mistakes

- **Optimising a job that is not on the critical path.**
- **Parallelising without counting per-job overhead.**
- **Averages instead of percentiles** for runtime and queue time.
- **Ignoring the matrix multiplier** in cost.
- **Running the full matrix on every PR update.**
- **Sizing the runner pool for average utilisation.**
- **Measuring once**, not after changes; the critical path moves.

## Exercise

1. Run `pytest src/test_pipeperf.py -v`, then model your own pipeline in the same dict format and compute its critical path. Which job would you speed up first?
2. Pick a job off the critical path and argue for or against optimising it.
3. Using the queue table, a pool of 8 runners reaches 90% utilisation at peak. Propose a change and use `src/queuesim.py` to predict the new mean and 90th percentile waits.
4. Estimate monthly billed minutes for your pipeline from run counts and per-job durations, then find the three largest contributors.
