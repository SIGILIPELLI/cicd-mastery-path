---
description: "CI/CD Level 2: matrices, cache design, reusable pipelines, containers, flaky tests, quality gates, environments, runners, monorepos and a workflow linter."
---

# Level 2 · Pipelines in Depth

Level 1 built one pipeline end to end. Level 2 makes pipelines fast, trustworthy and maintainable at the size real teams have: dozens of jobs, several platforms, a monorepo, and a test suite that is occasionally wrong about itself.

!!! note "What was run, and what wasn't"
    **Nothing in this course was run on GitHub Actions or Jenkins**: no account or server was available. What was run, on macOS: matrix expansion and cache keys in the Level 1 `minici` runner, a 20,000-run flaky-test simulation, a real coverage demonstration, a tested wait-for-port helper using real sockets, a tested changed-files-to-projects mapper that drives real `git diff`, a stale-workspace demo, and a 17-test workflow linter. Platform behaviour (GitHub limits, environments, caches, Jenkins syntax) comes from docs.github.com and jenkins.io as read in October 2026 and is labelled as such. Check limits against the current documentation.

**Prerequisites:** Level 1.

## Modules

1. **[Matrix Builds & Parallelism](01-matrix-parallelism.md)**: expansion, include/exclude, limits, sharding, gate jobs.
2. **[Cache Design](02-cache-design.md)**: keys that capture inputs, restore-key fallbacks, scope, poisoning.
3. **[Reusable Pipelines](03-reusable-pipelines.md)**: reusable workflows, composite actions, Jenkins libraries, versioning.
4. **[Containers in CI](04-containers-in-ci.md)**: service containers, readiness with deadlines, image layers.
5. **[Test Reports & Flaky Tests](05-test-reports-flaky.md)**: compounding flake arithmetic, retries, quarantine.
6. **[Quality Gates](06-quality-gates.md)**: what coverage does and does not tell you, with a measured counter-example.
7. **[Environments, Approvals & Concurrency](07-environments-approvals.md)**: protection rules and what an approval proves.
8. **[Runners & Agents](08-runners-agents.md)**: ephemeral versus persistent, isolation, the stale-workspace trap.
9. **[Monorepos & Path Filters](09-monorepos-path-filters.md)**: change detection, fan-out, three-dot diffs.
10. **[Project: A Workflow Linter](10-project-workflow-linter.md)**: six rules, 17 tests, run on real files.

## After Level 2

Level 3 covers delivery: deployment strategies, feature flags, database migrations, rollbacks, infrastructure pipelines, GitOps, release management, supply-chain security and DORA metrics, ending with a canary-release simulator.
