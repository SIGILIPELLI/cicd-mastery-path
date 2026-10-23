---
description: "CI/CD Level 4: threat models, speed and cost, Jenkins and Actions at scale, audit, testing pipelines, incidents, migration, golden paths and a capstone."
---

# Level 4 · Pipelines at Scale

Level 4 is about running delivery for many teams: securing it, making it fast and affordable, governing it, testing it, recovering when it breaks, changing it, and making the right way the easy way.

!!! note "What was run, and what wasn't"
    **No Jenkins server, GitHub organisation, cloud account or real incident was involved.** What was run, on macOS: a pipeline performance model with critical-path analysis (7 tests), an M/M/c queue simulation checked against the closed-form Erlang C result (6 tests), a hash-chained audit log with its limits tested (9 tests), a workflow converter that reports what it cannot translate (8 tests), a golden-path generator verified by the workflow linter (8 tests), contract tests that run a pipeline on good and broken inputs (4 tests), and a release-readiness check (6 tests). Platform controls, limits and organisational practices are from documentation or general experience and are labelled.

**Prerequisites:** Levels 1, 2 and 3.

## Modules

1. **[Threat-Modelling the Pipeline](01-pipeline-threat-model.md)**: assets, boundaries, twelve attack paths and the controls that address them.
2. **[Speed & Cost](02-speed-and-cost.md)**: the critical path, billed minutes, and queue time as a nonlinear effect.
3. **[Jenkins at Scale](03-jenkins-at-scale.md)**: controller limits, configuration as code, agents, and a measured pool-fragmentation effect.
4. **[GitHub Actions at Scale](04-actions-at-scale.md)**: documented limits, organisation policy, runner groups, cost governance.
5. **[Audit & Compliance](05-audit-compliance.md)**: separation of duties, evidence, and a tamper-evident log with known gaps.
6. **[Testing Pipelines](06-testing-pipelines.md)**: contract tests for gates, and the `python3` that was not the one I expected.
7. **[Pipeline Incidents](07-pipeline-incidents.md)**: runbooks for broken main, leaked secrets, outages and compromise.
8. **[Migrating CI Systems](08-migrating-ci.md)**: inventory, parallel run, cutover, and a converter that refuses to lose steps silently.
9. **[Golden Paths](09-golden-paths.md)**: a generator whose output must pass the linter.
10. **[Capstone: A Release-Readiness Check](10-capstone-delivery-platform.md)**: four independent checks, one explainable decision.

## After Level 4

You have a mental model of how delivery systems work from commit to production, a set of tested tools that make the ideas concrete, and a clear sense of which claims in this course were measured and which are documented. The next step is to apply them to a real system you can run.
