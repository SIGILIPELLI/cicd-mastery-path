---
description: "CI/CD Level 3: deployment strategies, flags, migrations, rollbacks, infrastructure and GitOps pipelines, releases and supply-chain security."
---

# Level 3 · Delivery & Release Engineering

Level 2 made the pipeline good at building and testing. Level 3 is about the last mile: getting a change into production safely, being able to undo it, and knowing whether your delivery process is healthy.

!!! note "What was run, and what wasn't"
    **No deployment, Kubernetes cluster, cloud account, Terraform, Argo CD or signing tool was used.** What was run, on macOS: a canary-release simulator with statistics (11 tests), a feature-flag evaluator with deterministic rollout (8 tests), real SQLite schema-migration experiments (expand/contract, including an unexpected failure), a GitOps reconcile loop (8 tests), a plan guard on hand-written plan fixtures (9 tests), a Conventional-Commits version tool (12 tests), a DORA-metrics calculator on a hand-made fixture (6 tests), and a checksum tamper demo. Everything about real platforms comes from documentation or general knowledge, and is labelled as such.

**Prerequisites:** Levels 1 and 2.

## Modules

1. **[Deployment Strategies](01-deployment-strategies.md)**: recreate, rolling, blue-green, canary, and a measured canary analysis.
2. **[Feature Flags](02-feature-flags.md)**: deploy versus release, deterministic percentage rollout, flag debt.
3. **[Database Migrations](03-database-migrations.md)**: expand and contract, run on SQLite, including the failures.
4. **[Rollbacks](04-rollbacks.md)**: what can be undone and what cannot; roll-forward.
5. **[Infrastructure Pipelines](05-infrastructure-pipelines.md)**: plan, review, apply, state, drift, a destructive-change guard.
6. **[GitOps](06-gitops.md)**: pull-based reconciliation shown with a tested simulator.
7. **[Release Management](07-release-management.md)**: semantic versions, Conventional Commits, hotfixes, trains.
8. **[Supply-Chain Security](08-supply-chain-security.md)**: pins, checksums, SBOM, signing, provenance.
9. **[DORA Metrics](09-dora-metrics.md)**: four delivery measures, computed and how they are gamed.
10. **[Project: A Canary Simulator](10-project-canary-simulator.md)**: false-alarm and detection rates across scenarios.

## After Level 3

Level 4 is about running delivery at scale: threat-modelling the pipeline, speed and cost, Jenkins and Actions fleets, audit and compliance, testing the pipelines themselves, incident response, migrating CI systems, golden paths and a capstone delivery platform.
