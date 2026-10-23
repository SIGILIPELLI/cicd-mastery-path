---
description: "DORA delivery metrics: deployment frequency, lead time, change failure rate and time to restore, how to compute them, and how they get gamed, with code."
---

# 09 · Measuring Delivery: The DORA Metrics

How do you know whether your delivery pipeline is any good? Opinions are plentiful and unreliable. Research from the DORA programme identified four measures that correlate with software delivery performance and, in that research, with organisational outcomes. They are **deployment frequency**, **lead time for changes**, **change failure rate** and **time to restore service**. Throughput and stability together: shipping fast and shipping safely turned out not to be a trade-off for the teams studied.

!!! note "What was run"
    `src/dora.py` and its 6 pytest tests were written and run, using a **four-deployment hand-made fixture**; no real team's data was used and the results below describe the fixture only. The definitions follow common usage as I understand it; DORA's published definitions have been revised over time (the current set and exact wording should be checked at the source), and teams define "deployment", "failure" and "restore" differently. Claims about the research are summarised from memory of the published work, not re-read for this lesson.

## The four measures

| Measure | Question | Pipeline-level data you need |
|---|---|---|
| **Deployment frequency** | How often do we ship to production? | Timestamps of production deploys |
| **Lead time for changes** | How long from commit to running in production? | Commit time and deploy time per change |
| **Change failure rate** | What share of deploys cause a failure needing remediation? | A record of which deploys led to incidents, rollbacks or hotfixes |
| **Time to restore** | How long to recover when a deploy goes wrong? | Failure start and recovery time |

The first two measure speed; the last two measure stability. A team that deploys ten times a day with a 40% failure rate is not elite, and neither is one that deploys monthly with a 0% failure rate (because it ships so rarely that every release is a large, risky batch).

## Computing them

On the fixture of four deployments (times in hours since an arbitrary origin): lead times 2, 4, 6 and 1 hours; deployments 2 and 4 failed, restored after 1 hour and 2 hours; window of 2 days.

```text
deploys_per_day     2.0     4 deployments / 2 days
median_lead_time_h  3.0     sorted leads 1, 2, 4, 6 -> median (2 + 4) / 2
change_failure_rate 0.5     2 failed of 4
median_restore_h    1.5     median of 1 h and 2 h
```

Details that matter and that the tests pin down:

- **Median, not mean.** Lead time and restore time are skewed: one three-week outlier ruins a mean. Medians (and percentiles such as p90) describe typical and bad cases separately.
- **A failed deploy with no recorded restore time** counts in the failure rate but not in the restore median (a test checks this). Otherwise an unresolved incident would silently improve the numbers.
- **An empty window** returns `None`, not zero: "no data" and "perfect" must look different.
- The fixture is tiny, so the numbers are arithmetic, not evidence. Real metrics need enough deployments for the median and rate to be stable; with 4 deploys a single extra failure changes the rate by 25 points.

## Where the data comes from

- **Deploys**: the pipeline's deploy job emits an event (to a log, a metrics system or a table) with service, version, commit and time. This is better than inferring deploys from Git tags.
- **Commit time**: the first commit of the change (or the PR open time, or the merge time, which gives a shorter "lead time" that omits waiting in review). Pick one definition and state it. Note that the shorter definition hides the very thing you may want to see: time spent waiting.
- **Failures**: link incidents, rollbacks and hotfix deploys back to the deploy that caused them. This is the hardest data to collect honestly, because it requires humans to tag incidents with a cause. A proxy: a deploy followed within N hours by a rollback or an emergency fix.
- **Restore**: incident start and resolution times from the incident tool, not from when someone "stopped looking".

## Using them without ruining them

Goodhart's law applies fully: a measure that becomes a target ceases to be a good measure.

- **Deployment frequency** is gamed by splitting changes into trivial deploys or by counting no-op deploys. Count only deploys that change production behaviour.
- **Lead time** is gamed by redefining the start (measure from merge, not first commit), or by merging half-finished work behind flags.
- **Change failure rate** is gamed by not declaring failures. If people are punished for incidents, incidents stop being recorded. Blameless culture is a precondition for honest numbers.
- **Time to restore** is gamed by declaring incidents "resolved" early or by never opening one.

Use the metrics to **find constraints and watch trends** for a team, never to rank people or compare teams with different contexts (a firmware team and a web team differ legitimately). Pair every metric with a question: lead time is long; where is the wait: review queue, tests, approvals, release trains?

## Diagnosing from the numbers

| Pattern | Likely cause | Where to look |
|---|---|---|
| Low frequency, long lead time | Big batches, slow gates, manual approvals | Level 4 · 02 (speed and cost); trunk-based development |
| High frequency, high failure rate | Weak tests, no canary, no flags | Lessons 01, 02 and the quality gates in Level 2 |
| Low failure rate but slow restore | No rollback path, poor observability | Lesson 04; Level 4 · 07 |
| Everything fine but unhappy engineers | The metrics miss something | Ask them: flaky tests? toil? on-call load? |

## Beyond four

The DORA research and other work (SPACE framework and others) also point to developer experience, reliability, and team wellbeing. Pipeline-adjacent measures worth tracking: **CI duration** (p50 and p90), **flaky-test rate** (Level 2 · 05), **queue time** for runners (Level 2 · 08), **time to first feedback** on a PR, and **rework rate**. Treat them as diagnostics.

## Checklist

- Deploy events are emitted by the pipeline, not reconstructed from tags.
- Definitions of deploy, failure and restore are written beside the dashboard.
- Medians and percentiles are reported, not means alone.
- Metrics are used for trends within a team, never for ranking people.

## How It Actually Works

Each metric is a statistic over events. Frequency is a count per window; lead time and restore time are durations computed per event and summarised with medians; failure rate is a proportion. The code is therefore a few lines, as `metrics()` shows. All the difficulty lives upstream, in **event capture and definitions**: deciding which timestamp is "commit", linking an incident to its cause, and handling multiple services deployed together. A change can touch several services; do you count one deploy or several? Whatever you choose, apply it consistently, publish the definitions next to the dashboard, and never compare numbers computed under different definitions.

## Common mistakes

- **Using mean instead of median** for skewed durations.
- **Treating the numbers as targets** or comparing people and teams.
- **Counting no-op deploys** to inflate frequency.
- **Not recording failures** (or punishing the people who do).
- **Mixing definitions** between teams or over time.
- **Too few data points** to say anything.
- **Optimising a metric** without asking what it is supposed to improve.

## Exercise

1. Run `pytest src/test_dora.py -v`. Add a fifth deployment with a very long lead time (500 hours) and compare the median to the mean.
2. Define, for your own team, what counts as a deploy, a failure and a restore. Write them in three sentences each.
3. Instrument a pipeline's deploy job to emit one JSON line per production deployment, and write the query that computes weekly frequency from the log.
4. Pick the metric that looks worst for your team, list three possible causes, and design one cheap experiment to test the likeliest.
