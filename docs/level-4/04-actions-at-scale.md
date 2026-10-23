---
description: "GitHub Actions across an organisation: documented limits, runner groups, org policies, reusable workflows as a platform, cost controls and governance."
---

# 04 · GitHub Actions at Scale

Actions is easy to start and easy to leave ungoverned. Across hundreds of repositories you need to answer: which actions may be used, who may use which runners, how secrets are scoped, how workflows are kept consistent and what it costs. This lesson collects the platform-level controls and the documented limits that shape designs.

!!! note "What was run, and what wasn't"
    **Nothing in this lesson was run on GitHub.** Limits and settings are from docs.github.com as read in October 2026 and change over time, and some depend on plan (Free, Pro, Team, Enterprise): verify against the current documentation for your account before relying on any number. The quoted limits are the ones I recorded for this course: job time 6 hours on hosted and 5 days on self-hosted runners, 256 jobs per matrix, 10 GB cache per repository, workflow runs deleted or limited after 35 days (as I recorded it), approval wait 30 days, 50 re-run attempts, and concurrent-job caps of 20 / 40 / 60 / 500 by plan. The queueing numbers come from the simulation in Lesson 02.

## Limits shape designs

| Limit (documented) | Design consequence |
|---|---|
| Hosted job ≤ 6 h | Long jobs (full-fleet integration, model training) need self-hosted runners or must be split |
| Self-hosted job ≤ 5 days | Still not a place for week-long batch work; use a scheduler built for it |
| ≤ 256 jobs per matrix | Large fan-out needs several workflows or dynamic matrices split in chunks (Level 2 · 01) |
| Cache 10 GB per repository, LRU | Many large caches evict each other; share keys, cache downloads (Level 2 · 02) |
| Concurrent jobs by plan (20/40/60/500) | A busy org queues; the cap, not your longest job, sets wall time (Lesson 02) |
| Approval wait ≤ 30 days | Long-pending production approvals silently expire |
| Re-runs ≤ 50 attempts | Don't build a "retry until green" habit; fix flakes (Level 2 · 05) |
| Log and artifact retention | Download evidence you need for audit before it expires, or export it (Lesson 05) |

Use the platform's numbers as constraints in your platform design doc, with a date, so the next engineer knows they came from a specific reading.

## Who may run what: organisation policies

At organisation (or enterprise) level you can typically control, per the documentation:

- **Allowed actions:** all actions, only those from your organisation, or an allowlist of specific actions (optionally requiring SHA pinning). For a regulated environment the allowlist plus SHA pinning policy is the strongest control against T3 (Lesson 01): the platform *rejects* a workflow that uses an unlisted or unpinned action, so the linter is no longer the only line of defence.
- **Default workflow token permissions:** set the default to read-only so jobs must ask for write access explicitly. This turns the linter's W001 finding into a baseline.
- **Fork pull request handling:** whether workflows from forks run automatically, need approval for first-time contributors, or never run; and whether they can access secrets (they should not).
- **Runner groups:** sets of runners, with access limited to named repositories or organisations. Put sensitive deploy runners in a group that only the deploy repositories can target, and keep untrusted PR builds on ephemeral hosted runners.
- **Secrets and variables at org level**, with a repository-selection list so a secret is available only to repositories that need it, and **environment** secrets for production (Level 2 · 07).
- **Required workflows / rulesets:** organisation-level rules that require certain checks (a security scan, a lint) on all repositories matching a pattern. The product has changed its mechanism for this over time; check the current documentation for what your plan supports.

Apply policy to the platform with **configuration as code** (Terraform GitHub provider, a settings app, or scripts using the API) so that settings are reviewable and drift is detectable, as in Level 3 · 05.

## Workflows as a platform

The pattern from Level 2 · 03 becomes central at scale: a platform repository publishes reusable workflows and composite actions (`build-python`, `deploy-service`), versioned with tags and SHA pins, and the "golden path" (Lesson 09) generates caller workflows that use them. What to decide:

- **Where reusable workflows live** (a dedicated repository with restricted write access) and who reviews changes to them.
- **Versioning and deprecation policy** (Level 2 · 03): breaking changes need a new major tag and a migration window.
- **Observability of the platform:** which repositories use which version of which workflow, so you know who to notify when `v2` is retired. Query the workflow files across the org (code search or an inventory job) and store the result.
- **Ownership of failure.** When a reusable workflow breaks, thirty teams are red. Give the platform team an on-call rotation and canary releases of the workflow itself (Level 3 · 01 applies to pipelines too).

## Runners at scale

For self-hosted runners at scale, run them as **ephemeral** instances created on demand by an autoscaler (a controller that watches the job queue, a Kubernetes-based runner controller, or a cloud scale-set), one job per instance, destroyed afterward. Questions for the design: how long does a new runner take to become ready (affects queue time); what network access and credentials does it have; how do you patch the image (rebuild on a schedule); how do you isolate untrusted workloads; and how do you cap spend. The queue arithmetic from Lesson 02 applies: size for a target 90th-percentile wait at peak, and keep the label set small so the pool is not fragmented.

## Cost governance

- **Visibility:** the platform exposes usage per repository and workflow; export it regularly and attribute spend to teams.
- **Budgets and spending limits** on the account, so a runaway matrix or a loop that triggers itself does not generate a surprise bill. A workflow that pushes a commit can trigger itself; the platform has loop protection for the default token, but a workflow using another token can still loop, which is a known pitfall.
- **Waste reduction:** path filters (Level 2 · 09), concurrency cancellation for CI, skipping jobs on docs-only changes, scheduled workflows reviewed periodically (an unattended nightly job running for three years is classic waste), and artifact and cache retention set to what you need.
- **Right-size runners:** larger machines cost more per minute but can finish faster; measure total cost, not minute price.

## Governance and observability

- Alert on **new workflow files that use `pull_request_target`, `self-hosted`, or `secrets: inherit`**, which the Level 2 linter can flag in a central scan.
- Track **workflow failure rates and durations** per repository and surface the worst offenders to their owners.
- Keep an **inventory** of third-party actions in use with their pinned SHAs, plus a process to review and bump them via a bot with changelog links.
- Make **audit logs** available (who changed org settings, secrets, runner groups, approvals), exported to a log store you control (Lesson 05).

## Migrating between scales

A repository starts with a hand-written workflow; ten later repositories copy it; a hundred repositories need a platform. Resist building the platform too early (Level 2 · 03's "share after the third copy"), and resist letting it stay ad hoc past the point where a vulnerability fix needs a hundred pull requests.

## Checklist

- Allowed actions and SHA pinning are set by organisation policy.
- The default token permission is read-only.
- Fork pull request workflows need approval and never see secrets.
- Reusable workflows are versioned, inventoried and canaried.

## How It Actually Works

Organisation-level policy is evaluated by the control plane at several moments: when a workflow file is parsed (is every `uses:` allowed and pinned?), when a job is scheduled (does this repository have access to this runner group, environment or secret?), and when a token is issued (what permissions does this job's `GITHUB_TOKEN` get, given the defaults and the `permissions:` block?). Enforcing at those points, in the platform and not in the repository, is what makes the controls reliable: a repository's own workflow cannot opt out of an organisation allowlist. Reusable workflows are resolved the same way: a caller's allowed-actions policy applies to the actions *inside* the callee as well, which can surprise platform authors who forget to put their own actions on the allowlist.

## Common mistakes

- **Relying on documentation numbers from memory** or from an old plan.
- **Write-by-default tokens** across the organisation.
- **No action allowlist** for sensitive repositories.
- **Self-hosted runners shared by trusted and untrusted work.**
- **Platform workflows referenced by `@main`**, so every change is a fleet-wide deploy.
- **No inventory** of workflow versions in use.
- **No spend limit**, and scheduled jobs nobody owns.
- **Settings changed in the UI only**, never in code.

## Exercise

1. Write the policy for your organisation: allowed actions, default token permissions, fork PR behaviour, runner groups. Justify each choice in one line, and say what a developer sees when a workflow breaks the policy.
2. Draft the inventory query that lists, per repository, every `uses:` reference and flags any not pinned to a SHA (the course's linter already finds the pins; extend it to scan a directory tree).
3. Propose the autoscaling target for a runner pool using the queue table, with the numbers that justify it.
4. Plan the retirement of `platform-workflows@v2`: how you find users, notify them, track migration and finally turn it off.
