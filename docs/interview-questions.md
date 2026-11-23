---
title: "CI/CD Interview Questions and Answers (179 Questions)"
description: "179 CI/CD interview questions with answers and explanations, from beginner to advanced, organised by level. Free, from the CI/CD Mastery Path."
---

# CI/CD Interview Questions and Answers

**179 questions** with the correct answer and a short explanation, organised from beginner (Level 1) to advanced (Level 4). Every question comes from a lesson in the free CI/CD Mastery Path, so you can open the lesson to go deeper.

!!! tip "Practise, don't just read"
    Each lesson also ends with an interactive quiz, and the [final quiz](quiz.md) tests all four levels. Try to answer each question below before reading the answer.

## Level 1 · Pipeline Foundations

### [01 · What CI/CD Is and Why Pipelines Exist](level-1/01-what-ci-cd-is.md)

**Q1.** What distinguishes Continuous Deployment from Continuous Delivery?

**Answer:** Deployment releases every passing change to production automatically; delivery keeps every change releasable but a human decides when

Delivery has a manual gate; deployment doesn't.

**Q2.** What does Continuous Integration require at minimum?

**Answer:** Frequent merges to a shared mainline, with every change automatically built and tested

Small frequent merges keep integration pain low.

**Q3.** Why does the course say the pipeline ideas were demonstrated with minici rather than GitHub Actions?

**Answer:** No Actions runner or Jenkins server was available when it was written, so the ideas were run locally and the platform syntax comes from documentation

The course states honestly what was and wasn't run.

**Q4.** Before CI/CD, what was the typical integration failure?

**Answer:** Weeks of separate branches merged the night before a release, producing a large, risky merge

CI shrinks the batch size.

### [02 · Pipeline Anatomy: Triggers, Jobs, Steps &amp; Stages](level-1/02-pipeline-anatomy.md)

**Q5.** In GitHub Actions vocabulary, what is the `needs:` keyword for?

**Answer:** Declaring that a job depends on other jobs finishing first

It expresses ordering between jobs.

**Q6.** Which is a job and which is a step?

**Answer:** A job is a unit of work on one runner with its own clean workspace; a step is one command or action inside it

Jobs run in parallel unless they declare needs.

**Q7.** What is a trigger?

**Answer:** The event that starts a pipeline run, such as push, pull_request, schedule or manual dispatch

A pipeline should start for a reason you can name.

**Q8.** In Jenkins Declarative pipelines, what plays the role GitHub's `runs-on:` plays?

**Answer:** agent { ... }, which selects the machine or container

Both name where work executes.

### [03 · GitHub Actions Essentials](level-1/03-github-actions-essentials.md)

**Q9.** What does `concurrency` with `cancel-in-progress: true` do in the sample workflow?

**Answer:** Cancels an older in-flight run of the same group when a newer one starts

The group is keyed by workflow and ref.

**Q10.** Why does the sample set `permissions: contents: read`?

**Answer:** Least privilege: the token gets only read access unless a job asks for more

The default token may be read-write.

**Q11.** What does a matrix of two Python versions with `fail-fast: false` do?

**Answer:** Runs both versions even if one fails, so you see every result

fail-fast: true cancels remaining cells.

**Q12.** Why set `timeout-minutes` on a job?

**Answer:** A hung job would otherwise run until the platform limit, wasting hours

Linter rule W004 flags its absence.

### [04 · Jenkins Essentials and the Jenkinsfile](level-1/04-jenkins-essentials.md)

**Q13.** What's the Jenkins controller's job, and what should NOT run on it?

**Answer:** It hosts the UI, job definitions, credentials and queue; keep builds off it and run them on agents

Agents execute the work.

**Q14.** How do jobs choose an agent?

**Answer:** By label, such as 'linux &amp;&amp; docker'

Labels describe capabilities.

**Q15.** What is the main operational burden of Jenkins plugins?

**Answer:** Each plugin is code with controller privileges, with its own update and vulnerability cadence

Plugin sprawl is a scaling risk.

**Q16.** What does `parallel {}` inside a Declarative pipeline do?

**Answer:** Runs the contained stages at the same time

Sequential stages run in order.

### [05 · Testing Gates and Fast Feedback](level-1/05-testing-gates.md)

**Q17.** Two jobs: a 3-second integration suite that fails and a 0.1-second unit suite that fails. How does ordering affect feedback?

**Answer:** Running unit first reports the failure in 0.1 s versus 3.1 s: same checks, 30x faster feedback

Order gates by cost and likelihood of failing.

**Q18.** What shape does the test pyramid recommend?

**Answer:** Many fast unit tests, fewer integration tests and very few end-to-end tests

The reverse (an ice-cream cone) is slow and flaky.

**Q19.** Where should static checks like lint and type checks go?

**Answer:** First: they take seconds and catch cheap mistakes

Surface problems early and cheaply.

**Q20.** What's a gate?

**Answer:** A check that must pass before a change moves on

Most pipeline value comes from the gates and their order.

### [06 · Reproducible Builds and Caching](level-1/06-reproducible-builds-caching.md)

**Q21.** Which practice makes a build more reproducible?

**Answer:** Pin dependencies with a lockfile, the toolchain version and base images by digest

Otherwise the build is a function of the internet.

**Q22.** What should a cache key be derived from?

**Answer:** The hash of the inputs, such as the lockfile, rather than the date

Same inputs, same key; changed lockfile, new key.

**Q23.** Why is `image:latest` a reproducibility problem?

**Answer:** It's mutable: the same tag can point to a different image tomorrow

Use image@sha256 digests.

**Q24.** What does a bit-for-bit reproducible build guarantee?

**Answer:** Two machines building the same inputs produce identical bytes, useful for supply-chain verification

It's a stronger goal than ordinary repeatability.

### [07 · Artifacts, Registries and Versioning](level-1/07-artifacts-versioning.md)

**Q25.** What is the rule about promoting a build to production?

**Answer:** Build once and promote the same artifact (same digest) through staging to production

Rebuilding deploys something you never tested.

**Q26.** Under Semantic Versioning, which change bumps MAJOR?

**Answer:** An incompatible change to the public API

MINOR is features, PATCH is fixes.

**Q27.** Why mirror public dependencies in a private registry?

**Answer:** A public outage or package removal won't break your builds

The left-pad incident is the example.

**Q28.** Why address a container image by digest as well as tag?

**Answer:** Tags can be moved; a digest identifies exact content

Immutability is the point of an artifact.

### [08 · Secrets in Pipelines](level-1/08-secrets-in-pipelines.md)

**Q29.** A secret is committed then deleted in the next commit. Is it safe?

**Answer:** No: Git history keeps it, so revoke and rotate it

Treat it as compromised.

**Q30.** Why are secrets passed on command lines risky?

**Answer:** They're visible to other processes (ps) and often logged

Prefer environment variables injected into only the needed step.

**Q31.** Which pull-request scenario exposes secrets to untrusted code?

**Answer:** Workflows triggered by forks that can read secrets

Untrusted code must not receive secrets.

**Q32.** What does 'scope narrowly, inject late' mean?

**Answer:** Give each environment/job only the secrets it needs, exposed only to the step that uses them

A single all-powerful token makes any leak catastrophic.

### [09 · Branching Strategies and Pull Request Checks](level-1/09-branching-pr-checks.md)

**Q33.** Two branches each pass tests alone but fail when combined. What does this show?

**Answer:** PR checks must run on what will actually merge (the merged result), not the branch alone

A rename plus a new caller of the old name broke after the merge.

**Q34.** Which branching strategy integrates continuously with very short-lived branches?

**Answer:** Trunk-based development, usually with feature flags

Longer-lived branches mean riskier merges.

**Q35.** When is GitFlow a reasonable fit?

**Answer:** Software shipped in discrete versions with long support windows

It integrates per release.

**Q36.** What should a PR pipeline answer within minutes?

**Answer:** Does it build, do tests/lint/type checks pass, are there security findings, who needs to review

Fast feedback before merge.

### [10 · Project — A Local CI Runner You Can Run](level-1/10-project-local-ci-runner.md)

**Q37.** In minici, what happens to a job whose dependency failed?

**Answer:** It's skipped unless it has `if: always()`

Same idea as GitHub's default behaviour.

**Q38.** Why does minici refuse unsupported `${{ }}` expressions?

**Answer:** Silently ignoring them would make a pipeline appear to work while skipping logic

Fail loudly.

**Q39.** Why run step scripts with `set -eo pipefail`?

**Answer:** So a failing command in a pipeline fails the step instead of being hidden

A step otherwise reports only the last command's status.

**Q40.** When does the runner save a cache?

**Answer:** Only on success

A failed build could save a poisoned cache.

## Level 2 · Pipelines in Depth

### [01 · Matrix Builds &amp; Parallelism](level-2/01-matrix-parallelism.md)

**Q41.** A 3x3 os/python matrix with one exclude and one include that matches no cell. How many jobs?

**Answer:** 9 (9 - 1 + 1)

The unmatched include adds a new job.

**Q42.** How does `exclude` match?

**Answer:** A combination is removed when it matches all the keys given; a partial pattern removes every combination containing those values

Include matches existing cells or adds a new one.

**Q43.** When does `include` add a new job instead of extending an existing one?

**Answer:** When it matches no existing combination

This trips people up.

**Q44.** Why is a matrix a trade-off?

**Answer:** It multiplies coverage but also compute minutes and queue time

Billed minutes sum every cell.

### [02 · Cache Design: Keys, Scope &amp; Poisoning](level-2/02-cache-design.md)

**Q45.** The lockfile changes when a dependency is bumped. What happens to a lockfile-hash cache key?

**Answer:** It changes, so the cache rebuilds, and reverting restores the original key's entry

The key is deterministic over the inputs.

**Q46.** Why hash a lockfile rather than a loose requirements list?

**Answer:** `flask>=3` resolves to different packages over time while its file hash stays the same

The key must capture what determined the contents.

**Q47.** What are restore keys for?

**Answer:** Partial hits: restore the closest older cache when the exact key misses

Most packages didn't change.

**Q48.** What is cache poisoning?

**Answer:** Bad content saved into a shared cache that later builds then trust

Scope caches and avoid saving from untrusted PRs.

### [03 · Reusable Pipelines: Workflows, Actions &amp; Shared Libraries](level-2/03-reusable-pipelines.md)

**Q49.** When should you choose a reusable workflow over a composite action?

**Answer:** When the shared unit needs its own runner, permissions or matrix (it delegates a whole job)

Composite actions share steps inside a job.

**Q50.** How do reusable workflows receive secrets, and which is preferred?

**Answer:** Passed explicitly or via `secrets: inherit`; explicit is preferred

Inputs are plain values, not secret.

**Q51.** Why was the top-level `on` key read as the boolean True in PyYAML?

**Answer:** YAML 1.1 treats `on` as a boolean

Tools parsing workflows must account for it.

**Q52.** What is the gain of reusable pipelines across 15 repos?

**Answer:** One place to fix a security patch instead of fifteen copies

Reuse is a maintenance and security lever.

### [04 · Containers in CI: Images, Services &amp; Readiness](level-2/04-containers-in-ci.md)

**Q53.** A database service container is started but tests fail on the first query. Why?

**Answer:** Started is not ready: the process launched but isn't accepting queries; add a health check

The sample uses --health-cmd pg_isready.

**Q54.** How do steps inside a `container:` job reach a service named db?

**Answer:** Via the host name db (the service name) on its port

Service name is the DNS name.

**Q55.** What's the risk of `container: python:3.12-slim`?

**Answer:** The tag is mutable and may change under you; pin by digest for reproducibility

Mutable tags break reproducibility.

**Q56.** What does this lesson say honestly about what was run?

**Answer:** No container was built or run; the syntax comes from documentation

No container runtime was available.

### [05 · Test Reports &amp; Flaky Tests](level-2/05-test-reports-flaky.md)

**Q57.** A suite has 100 tests, each flaking with probability 0.1%. How often is it green on correct code?

**Answer:** About 90.5% ((0.999)^100)

Flakes compound: P(green) = (1-p)^n.

**Q58.** A 500-test suite with a 1% per-test flake rate is green how often?

**Answer:** About 0.7%

(0.99)^500 is roughly 0.0066.

**Q59.** What is a flaky test?

**Answer:** One that passes and fails on the same code

A few hundred make the pipeline random.

**Q60.** Why is rerunning until green a bad habit?

**Answer:** It hides flakes and teaches people to ignore red builds; fix or quarantine them with a flake budget

Trust in the pipeline erodes.

### [06 · Quality Gates: Coverage, Lint &amp; Analysis](level-2/06-quality-gates.md)

**Q61.** A module has 100% line and branch coverage and a pricing bug passes the weak test suite. What does this show?

**Answer:** Coverage shows what code ran, not that behaviour was checked; assertions matter

A strong suite with the same coverage caught the bug.

**Q62.** What does mutation testing check?

**Answer:** Whether tests fail when small changes (like &gt; to &gt;=) are made to the code

It gives evidence tests check behaviour.

**Q63.** What is a quality gate?

**Answer:** A check whose failure blocks a merge or deployment

Examples: tests, coverage not dropping, lint, vulnerabilities.

**Q64.** Which signal can coverage legitimately give?

**Answer:** Finding code that no test touches

It can't find missing assertions.

### [07 · Environments, Approvals &amp; Concurrency](level-2/07-environments-approvals.md)

**Q65.** Why attach secrets to an environment rather than the repository?

**Answer:** Repository secrets are visible to every job; environment secrets are only released to jobs that pass the environment's protection rules

Protection rules gate access.

**Q66.** What do required reviewers do on an environment?

**Answer:** Pause the deploy job until an approver signs off

A waiting job doesn't consume a runner.

**Q67.** What do branch restrictions on an environment do?

**Answer:** Allow only workflows from specific branches (e.g. main) to deploy there

They stop feature branches from deploying to production.

**Q68.** What happens to a run waiting for approval for too long?

**Answer:** It's eventually cancelled (documented limit around 30 days)

Stale approvals silently expire.

### [08 · Runners &amp; Agents: Where Your Jobs Actually Run](level-2/08-runners-agents.md)

**Q69.** What's the main risk of a persistent self-hosted runner workspace?

**Answer:** Stale files from earlier builds can make a build pass or fail depending on leftovers

The lesson demonstrates this with minici.

**Q70.** When is a self-hosted runner justified?

**Answer:** Needs hosted runners can't meet: GPUs, ARM, private network access, special hardware

You own patching and isolation.

**Q71.** Which runs jobs in a fresh VM discarded afterwards?

**Answer:** Hosted runners

Isolation is a hosted-runner strength.

**Q72.** Why is running untrusted PR code on a persistent self-hosted runner dangerous?

**Answer:** It can persist malware or steal credentials between jobs

Use ephemeral runners for untrusted code.

### [09 · Monorepos &amp; Path Filters](level-2/09-monorepos-path-filters.md)

**Q73.** 30 services at 12 minutes each, run on every push: what's the cost?

**Answer:** About 6 hours of runner time per push

Hence path filters and affected-only builds.

**Q74.** What does `paths:` do in a workflow trigger?

**Answer:** Runs the workflow only when changed files match the patterns

paths-ignore is the inverse.

**Q75.** Why must path filters include shared libraries a service depends on?

**Answer:** A change in libs/common can break the service even if its own files didn't change

Missing dependencies lead to false greens.

**Q76.** What does the course's pathfilter map?

**Answer:** Changed files to the projects they affect, tested with a real temporary Git repo

Nine tests pass.

### [10 · Project — A Workflow Linter](level-2/10-project-workflow-linter.md)

**Q77.** What does rule W003 flag?

**Answer:** `uses:` not pinned to a 40-hex commit SHA

Tags can be moved; a SHA cannot.

**Q78.** Why is `pull_request_target` checking out the PR head dangerous (W002)?

**Answer:** Untrusted code runs with a privileged token and secrets

A classic supply-chain attack path.

**Q79.** What is script injection (W005)?

**Answer:** Untrusted `${{ github.event... }}` text interpolated into a run: script, letting an attacker execute commands

Pass values via env instead.

**Q80.** Why does a deploy job need `concurrency:` (W006)?

**Answer:** Two runs could deploy at once and the older one may finish last, leaving an old version live

Serialise deploys.

## Level 3 · Delivery & Release Engineering

### [01 · Deployment Strategies](level-3/01-deployment-strategies.md)

**Q81.** Which strategy has downtime between stopping the old version and starting the new?

**Answer:** Recreate

It's simple and fine for maintenance windows.

**Q82.** What is the main risk of a rolling deployment?

**Answer:** Old and new versions serve traffic at the same time, so they must be compatible

Rolling replaces instances a few at a time.

**Q83.** What does blue-green give you?

**Answer:** An instant switch of traffic, and an instant switch back while the old environment is kept alive

Cost: a whole second environment, and shared databases still need compatible changes.

**Q84.** What does a canary release need to be safe?

**Answer:** Good metrics and enough traffic to detect a problem on the small share

Send traffic back to 0% to roll back.

### [02 · Feature Flags: Decoupling Deploy from Release](level-3/02-feature-flags.md)

**Q85.** What do feature flags decouple?

**Answer:** Deploy (code on servers) from release (behaviour exposed to users)

A flag off means a deploy isn't a launch.

**Q86.** Why is a percentage rollout based on a hash of flag and user id?

**Answer:** A user gets a consistent answer, and widening from 10% to 20% keeps the earlier 10% enabled (a subset)

The sample showed a 10% set is a subset of the 20% set.

**Q87.** Why are flags the usual fastest rollback for a bad release?

**Answer:** Reverting a value takes seconds, no redeploy

Remove stale flags afterwards.

**Q88.** What problem do long-lived flags cause?

**Answer:** Accumulated untested combinations and dead code paths

Clean up flags once rollout completes.

### [03 · Database Migrations: Expand &amp; Contract](level-3/03-database-migrations.md)

**Q89.** Why does a direct `RENAME COLUMN name TO full_name` break a rolling deploy?

**Answer:** Old code still running (or after a rollback) queries `name` and fails immediately

Verified in SQLite in the lesson.

**Q90.** What is the expand/migrate/contract pattern?

**Answer:** Add the new column compatibly, migrate data and code, then remove the old column in a later release

Each step is compatible with its neighbours.

**Q91.** Why can't you just roll back a destructive schema change?

**Answer:** The data or column is gone, and old code breaks

Only additive changes are easy to roll back.

**Q92.** What should the new column be at the expand step?

**Answer:** Nullable, with no constraint the old code would violate

Old code ignores it.

### [04 · Rollbacks: Going Back, and When You Cannot](level-3/04-rollbacks.md)

**Q93.** Which change can a rollback restore?

**Answer:** Stateless application code and configuration/flag values

Redeploy the previous artifact or revert the value.

**Q94.** Which of these can a rollback NOT undo?

**Answer:** External effects such as emails, payments and API calls

Plan forward fixes for such effects.

**Q95.** In GitOps, what is a rollback?

**Answer:** A revert in Git that the reconciler applies

The simulator models this.

**Q96.** Why is 'we can always roll back' risky?

**Answer:** It's only true for some changes; data and external effects may be irreversible

The most expensive sentence in delivery.

### [05 · Infrastructure Pipelines: Plan, Review, Apply](level-3/05-infrastructure-pipelines.md)

**Q97.** What should run on every pull request in an infrastructure repo?

**Answer:** A plan, shown to reviewers, since one variable change can have large effects the HCL diff doesn't show

Plan on PRs, apply on merge.

**Q98.** Why apply a saved plan (plan -out)?

**Answer:** It guarantees the applied change is exactly what was reviewed

A fresh plan on main may differ.

**Q99.** How should credentials differ between plan and apply jobs?

**Answer:** Plan job read-only; apply job has write access only on the protected branch and environment

Separate credentials limit blast radius.

**Q100.** Why serialise applies per state?

**Answer:** Concurrent applies could corrupt state; use locking and a concurrency group

One at a time per state.

### [06 · GitOps: Reconciling Desired State](level-3/06-gitops.md)

**Q101.** What is the GitOps reconciler's job?

**Answer:** Continuously compare desired state in Git with actual state and apply the difference

Create what's missing, update what differs, optionally prune extras.

**Q102.** Someone sets web replicas to 10 by hand and adds a `debug` object. What does the simulator report?

**Answer:** Drift: web changed, debug extra; reconcile updates web and (with prune) deletes debug

Git remains the source of truth.

**Q103.** What is the difference between push and GitOps deployment?

**Answer:** Push: CI applies to the target; GitOps: a reconciler pulls and applies from Git

Cluster credentials stay inside the cluster in the pull model.

**Q104.** What does `prune` do?

**Answer:** Deletes objects that exist but aren't in Git

Without it extras survive.

### [07 · Release Management: Versions, Changelogs &amp; Trains](level-3/07-release-management.md)

**Q105.** Under Conventional Commits, which commit bumps MAJOR?

**Answer:** `feat!: drop python 3.8` (or a BREAKING CHANGE footer)

! marks a breaking change.

**Q106.** Which bumps MINOR?

**Answer:** feat(api): add export

A new backward-compatible feature.

**Q107.** Why use machine-readable commit messages?

**Answer:** A tool can compute the next version and write the changelog

semrel does this.

**Q108.** What does a changelog serve?

**Answer:** Telling consumers what changed between releases so they can judge upgrade risk

Continuous delivery still needs release communication.

### [08 · Supply-Chain Security for Pipelines](level-3/08-supply-chain-security.md)

**Q109.** What is dependency confusion?

**Answer:** A public package with the same name as your private one wins resolution

Use scoped registries.

**Q110.** How do you defend against a moved tag on a third-party action?

**Answer:** Pin to a full commit SHA

A SHA can't be moved.

**Q111.** What did the checksum demo show?

**Answer:** Tampering with an archive changes its SHA-256, so verification fails

Verify downloads.

**Q112.** What is an SBOM for?

**Answer:** Listing a build's components so vulnerable dependencies can be found

It helps with transitive dependencies.

### [09 · Measuring Delivery: The DORA Metrics](level-3/09-dora-metrics.md)

**Q113.** Which are the four DORA measures?

**Answer:** Deployment frequency, lead time for changes, change failure rate, time to restore

Two measure speed and two stability.

**Q114.** On the fixture, lead times are 2, 4, 6 and 1 hours and two of four deploys failed. What are the average lead time and change failure rate?

**Answer:** 3.25 hours and 50%

(2+4+6+1)/4 = 3.25; 2/4 = 50%.

**Q115.** A team deploys ten times a day with a 40% failure rate. Are they elite?

**Answer:** No: speed without stability isn't elite

Both pairs matter.

**Q116.** Why not rank people by DORA metrics?

**Answer:** They measure the delivery system, and using them as targets invites gaming

Use them to find bottlenecks.

### [10 · Project — A Canary Release Simulator](level-3/10-project-canary-simulator.md)

**Q117.** Why is the canary test one-sided?

**Answer:** Only a worse canary matters; a better one isn't a reason to stop

A test asserts z &lt; 0 doesn't roll back.

**Q118.** Why require a minimum canary sample?

**Answer:** At 1% of 20,000 requests only 200 canary requests exist and a burst of errors can look dramatic

min_canary=400.

**Q119.** What does the simulator do after the last step succeeds?

**Answer:** Promotes the canary to 100%

Otherwise it rolls back when z exceeds the limit.

**Q120.** Why accumulate counts across steps?

**Answer:** More samples sharpen detection of a small increase in error rate

Each step adds evidence.

## Level 4 · Pipelines at Scale

### [01 · Threat-Modelling the Pipeline](level-4/01-pipeline-threat-model.md)

**Q121.** What should you do first when threat-modelling a pipeline?

**Answer:** List what you're protecting (deploy credentials, source access, signing keys, secrets, artifacts, runners)

Then ask what an attacker could do with each.

**Q122.** Why are signing keys a high-value asset?

**Answer:** An attacker can make malicious artifacts look genuine

Protect them in a vault or hardware-backed service.

**Q123.** Why is a build cache a target?

**Answer:** Poisoning it can ship tampered code without touching the source

Scope and key caches carefully.

**Q124.** Which earlier control does this lesson reuse?

**Answer:** The workflow linter that flags unpinned actions, missing permissions and script injection

Defence in depth.

### [02 · Speed &amp; Cost](level-4/02-speed-and-cost.md)

**Q125.** lint 1, build 4, unit 6 (3 cells, needs build), e2e 12 (needs build), deploy 2 (needs unit and e2e). What are the critical path and billed minutes?

**Answer:** 18 minutes (build 4 → e2e 12 → deploy 2) and 37 billed minutes

Wall-clock follows the longest dependency chain; billed time sums every job including each matrix cell.

**Q126.** What's the difference between wall-clock time and compute time?

**Answer:** Wall-clock is what a developer waits; compute is total billed machine-minutes

Parallelism trades one for the other.

**Q127.** Does splitting a 12-minute job across 3 runners reduce total compute?

**Answer:** No: it cuts wall-clock but total compute doesn't drop (and startup overhead adds)

Cost and speed are different dials.

**Q128.** What is the best way to shorten a pipeline's latency?

**Answer:** Shorten the critical path: split or speed up the longest chain

Work off the critical path doesn't change latency.

### [03 · Jenkins at Scale](level-4/03-jenkins-at-scale.md)

**Q129.** Why shouldn't heavy logic live in a Jenkinsfile?

**Answer:** Pipeline scripts run in the controller's JVM, so heavy loops load the controller

Push work to agents and tools.

**Q130.** What stops unbounded build history filling the controller disk?

**Answer:** Build discarders (keep N builds or N days)

Set sensible defaults.

**Q131.** Why is configuration drift a problem for UI-configured Jenkins?

**Answer:** Changes aren't versioned or reproducible, so a rebuilt controller loses them; use configuration as code

JCasC is the remedy.

**Q132.** What is plugin sprawl?

**Answer:** Hundreds of plugins from many maintainers, each running with controller privileges and its own update cadence

Reduce and review plugins.

### [04 · GitHub Actions at Scale](level-4/04-actions-at-scale.md)

**Q133.** A job needs 8 hours. Where can it run?

**Answer:** Self-hosted runners (hosted jobs are capped at 6 hours), or split the work

Hosted ≤ 6 h; self-hosted ≤ 5 days.

**Q134.** A matrix needs 400 cells. What's the constraint?

**Answer:** A matrix is limited to 256 jobs; split into several workflows or chunks

Design around documented limits.

**Q135.** Why not build a 'retry until green' habit given re-run limits?

**Answer:** Re-runs are capped (documented 50 attempts) and hide flakes

Fix flakes instead.

**Q136.** How do large caches interact with the 10 GB per repository limit?

**Answer:** They evict each other (LRU), so share keys and cache downloads

Design caches deliberately.

### [05 · Audit &amp; Compliance](level-4/05-audit-compliance.md)

**Q137.** Which evidence shows a change was reviewed by someone other than the author?

**Answer:** Pull-request approvals with identities and timestamps, enforced by branch protection

Evidence should be produced by the pipeline.

**Q138.** What does separation of duties mean here?

**Answer:** The same person shouldn't be able to write, approve and deploy a risky change

Access reviews verify it.

**Q139.** What does a hash-chained audit log give?

**Answer:** Tamper evidence: altering any earlier entry breaks the chain

It's a teaching model, not a certified product.

**Q140.** What must be recorded about a deployment?

**Answer:** Version, artifact digest, commit SHA and build ID

Traceability answers 'what exactly was deployed?'.

### [06 · Testing Pipelines](level-4/06-testing-pipelines.md)

**Q141.** A pipeline contract test breaks a unit test and expects what?

**Answer:** The test job fails and packaging/deploy jobs are skipped

A false green is the worst failure.

**Q142.** Why test the gates themselves?

**Answer:** A scan that quietly stops running looks green; verify it fails on known-bad input

A gate that never fails may not be running.

**Q143.** What's a false red?

**Answer:** A pipeline blocking good changes

Both false green and false red erode trust.

**Q144.** What does a workflow linter check that tests don't?

**Answer:** Config validity: YAML syntax, expression errors, references to jobs and secrets that don't exist

It's a different layer.

### [07 · Pipeline Incidents](level-4/07-pipeline-incidents.md)

**Q145.** A secret leaked in a repository. What's the first priority?

**Answer:** Revoke and rotate it, then investigate

Assume it's compromised.

**Q146.** Main is red and nobody can merge. What's the first priority?

**Answer:** Restore green quickly by reverting or fixing forward

Broken main blocks everyone.

**Q147.** A runaway matrix is burning budget. What do you do first?

**Answer:** Cancel the runs, cap spend, then fix the trigger

Stop the bleeding.

**Q148.** Why know an emergency deploy path?

**Answer:** If the pipeline is down, you still need a controlled way to ship a fix

Pipeline outages stop all shipping.

### [08 · Migrating CI Systems](level-4/08-migrating-ci.md)

**Q149.** What's the first phase of a CI migration?

**Answer:** Decide why (valid reasons), then inventory everything

You can't migrate what you haven't found.

**Q150.** What does wf2minici do for unsupported features?

**Answer:** Lists everything it can't translate rather than silently dropping it

Honest conversion.

**Q151.** What should an inventory include for each pipeline?

**Answer:** Triggers, steps/tools, credentials, runner needs and downstream consumers

Downstream consumers rely on statuses and artifacts.

**Q152.** What's a safe cutover technique?

**Answer:** Run old and new in parallel and compare results before switching required checks

Parallel runs find gaps.

### [09 · Golden Paths: Making the Right Way the Easy Way](level-4/09-golden-paths.md)

**Q153.** What is a golden path?

**Answer:** A supported, easy default route that bundles the secure, tested, observable way of shipping

Make the right way the easy way.

**Q154.** What belongs on a Python service's golden path?

**Answer:** Layout, CI workflow with pinned tools, deploy pipeline with approvals, security baseline, observability, docs

Teams otherwise remake these decisions.

**Q155.** How is a golden path verified?

**Answer:** By tests that check the generated workflow meets policy (pinned actions, permissions, timeouts)

goldenpath.py has eight tests.

**Q156.** Why not force teams onto the path?

**Answer:** It should win by being easier; forcing breeds workarounds

Paved road, not a fence.

### [10 · Capstone — A Release-Readiness Check](level-4/10-capstone-delivery-platform.md)

**Q157.** When is a release `ready` in the capstone?

**Answer:** Only when the list of reasons is empty

Four independent checks collect reasons.

**Q158.** Which four checks does readiness combine?

**Answer:** Workflow lint, infrastructure plan guard, DORA delivery health and a canary simulation

Each adds reasons.

**Q159.** What happens if the canary simulator decides to roll back?

**Answer:** A reason is added and the release is not ready

Metrics include canary decision.

**Q160.** What are the capstone's inputs?

**Answer:** Synthetic data: a generated workflow, a plan and hand-made deployments, not real team data

The lesson states it plainly.

## Mixed questions across all levels

**Q161.** Which statement best distinguishes continuous delivery from continuous deployment?

**Answer:** Delivery keeps every passing change releasable with a human release decision; deployment releases every passing change automatically

The difference is the manual gate.

**Q162.** Same two failing checks: unit (0.1 s) and integration (3 s). Which order gives the fastest feedback?

**Answer:** Unit first, then integration: you learn about the failure in 0.1 s instead of 3.1 s

Order gates by cost and likelihood of failing.

**Q163.** A team deploys with `image: python:3.12-slim` and sees a surprise change. Why?

**Answer:** Mutable tags can move to a different image; pin by digest

Pinned inputs make builds reproducible.

**Q164.** A cache key is the date. What goes wrong?

**Answer:** It ignores the inputs: stale dependencies are restored after a lockfile change, or the cache misses daily; hash the lockfile instead

Hash inputs, not time.

**Q165.** A 500-test suite where every test flakes 1% of the time is green how often on correct code?

**Answer:** About 0.7% ((0.99)^500)

Flakes compound, so a flake budget matters.

**Q166.** The module has 100% coverage but a pricing bug passed CI. What was missing?

**Answer:** Assertions: coverage shows what ran, not that outputs were checked; consider mutation testing

Weak and strong suites can have identical coverage.

**Q167.** A PR passes on its branch but main breaks after merging. What should the PR check run on?

**Answer:** The merged result (what will actually land on main), ideally via a merge queue

Two green branches can combine into a red build.

**Q168.** Which setup limits damage if a PR from a fork is malicious?

**Answer:** No secrets for fork PRs, least-privilege token, and no pull_request_target checkout of untrusted code

Untrusted code must not meet privileged credentials.

**Q169.** How should third-party actions be referenced?

**Answer:** Pinned to a full commit SHA (tags can be moved)

Rule W003 in the course linter.

**Q170.** A deploy job lacks `concurrency:`. What can happen?

**Answer:** Two runs deploy at once and the older run may finish last, leaving the old version live

Serialise deploys per environment.

**Q171.** Production approvals should live where?

**Answer:** On a protected environment with required reviewers and environment-scoped secrets

Protection rules gate secrets and jobs.

**Q172.** You must rename a database column during a rolling deploy. What's the safe sequence?

**Answer:** Expand (add nullable new column), migrate data and code, then contract (drop the old column) in a later release

Old and new code overlap during rollouts.

**Q173.** Which cannot be fixed by a rollback?

**Answer:** A destructive schema change, sent emails and payments

Rollbacks restore code, not data or side effects.

**Q174.** Which deployment strategy gives instant switch-back but costs a whole second environment?

**Answer:** Blue-green

Keep the old environment alive until the new one is proven.

**Q175.** A canary at 1% of 20,000 requests gets 200 canary requests. Why does the simulator wait for a minimum sample?

**Answer:** Small samples let a single error burst look like a real regression

min_canary protects against noise.

**Q176.** Which two DORA measures describe stability?

**Answer:** Change failure rate and time to restore

The other two describe speed.

**Q177.** A pipeline's wall-clock time is 18 minutes but billed minutes are 37. Why do they differ?

**Answer:** Wall-clock follows the critical path; billed time sums every job and matrix cell

Parallelism trades one for the other.

**Q178.** A secret was pushed to a public repo and removed in the next commit. What now?

**Answer:** Revoke and rotate it immediately: Git history and forks keep it

Revoke first, investigate second.

**Q179.** A migration from Jenkins to Actions is planned. What comes before converting pipelines?

**Answer:** Inventory: triggers, tools, credentials, runners and downstream consumers

You can't migrate what you haven't found.

## Practical coding questions

### Expand a build matrix

Implement expand_matrix(): the Cartesian product of the list-valued keys, remove combinations that match every key of an `exclude` entry, then apply each `include` (extend matching cells, or add a new job if it matches none). The sample matrix should yield 9 jobs.

Starter code:

```
import itertools

def expand_matrix(matrix):
    # Cartesian product of the list-valued keys, minus `exclude` matches,
    # then `include`: extend matching cells or add a new job if none match.
    return []

matrix = {
    "os": ["ubuntu", "windows", "macos"],
    "python": ["3.11", "3.12", "3.13"],
    "exclude": [{"os": "macos", "python": "3.11"}],
    "include": [{"os": "ubuntu", "python": "3.14", "experimental": True}],
}
jobs = expand_matrix(matrix)
print(len(jobs))
for j in jobs:
    print(j["os"] + "/" + j["python"] + (" (experimental)" if j.get("experimental") else ""))
```

Expected output:

```text
9
ubuntu/3.11
ubuntu/3.12
ubuntu/3.13
windows/3.11
windows/3.12
windows/3.13
macos/3.12
macos/3.13
ubuntu/3.14 (experimental)
```

??? success "Show a solution"

    ```
    import itertools

    def expand_matrix(matrix):
        include = matrix.get("include", [])
        exclude = matrix.get("exclude", [])
        keys = [k for k in matrix if k not in ("include", "exclude")]
        combos = [dict(zip(keys, v)) for v in itertools.product(*(matrix[k] for k in keys))]
        combos = [c for c in combos if not any(all(c.get(k) == v for k, v in ex.items()) for ex in exclude)]
        for inc in include:
            orig = {k: v for k, v in inc.items() if k in keys}
            matched = [c for c in combos if all(c[k] == v for k, v in orig.items())] if orig else []
            if matched:
                for c in matched:
                    c.update(inc)
            else:
                combos.append(dict(inc))
        return combos

    matrix = {
        "os": ["ubuntu", "windows", "macos"],
        "python": ["3.11", "3.12", "3.13"],
        "exclude": [{"os": "macos", "python": "3.11"}],
        "include": [{"os": "ubuntu", "python": "3.14", "experimental": True}],
    }
    jobs = expand_matrix(matrix)
    print(len(jobs))
    for j in jobs:
        print(j["os"] + "/" + j["python"] + (" (experimental)" if j.get("experimental") else ""))
    ```

    3x3 = 9 combinations, minus macos/3.11, plus an include for 3.14 that matches no existing cell and therefore becomes a new job: 9. Verified by running the solution.

### Critical path and billed minutes

Given the job graph, compute the critical path (the longest chain of dependent jobs, in minutes) and the total billed minutes (minutes x matrix cells summed over all jobs).

Starter code:

```
JOBS = {
    "lint":   {"minutes": 1,  "cells": 1, "needs": []},
    "build":  {"minutes": 4,  "cells": 1, "needs": []},
    "unit":   {"minutes": 6,  "cells": 3, "needs": ["build"]},
    "e2e":    {"minutes": 12, "cells": 1, "needs": ["build"]},
    "deploy": {"minutes": 2,  "cells": 1, "needs": ["unit", "e2e"]},
}

def critical_path(jobs):
    # longest chain of dependent jobs: return (total minutes, [job names in order])
    return 0, []

def billed(jobs):
    # compute minutes: sum of minutes x cells over every job
    return 0

length, path = critical_path(JOBS)
print("critical path: %.1f minutes  %s" % (length, " -> ".join(path)))
print("billed minutes:", billed(JOBS))
```

Expected output:

```text
critical path: 18.0 minutes  build -> e2e -> deploy
billed minutes: 37
```

??? success "Show a solution"

    ```
    JOBS = {
        "lint":   {"minutes": 1,  "cells": 1, "needs": []},
        "build":  {"minutes": 4,  "cells": 1, "needs": []},
        "unit":   {"minutes": 6,  "cells": 3, "needs": ["build"]},
        "e2e":    {"minutes": 12, "cells": 1, "needs": ["build"]},
        "deploy": {"minutes": 2,  "cells": 1, "needs": ["unit", "e2e"]},
    }

    def finish_times(jobs):
        done = {}
        def finish(name):
            if name not in done:
                start = max((finish(n) for n in jobs[name]["needs"]), default=0)
                done[name] = start + jobs[name]["minutes"]
            return done[name]
        for n in jobs:
            finish(n)
        return done

    def critical_path(jobs):
        done = finish_times(jobs)
        end = max(done, key=done.get)
        path = [end]
        while jobs[path[-1]]["needs"]:
            path.append(max(jobs[path[-1]]["needs"], key=lambda n: done[n]))
        return done[end], list(reversed(path))

    def billed(jobs):
        return sum(j["minutes"] * j["cells"] for j in jobs.values())

    length, path = critical_path(JOBS)
    print("critical path: %.1f minutes  %s" % (length, " -> ".join(path)))
    print("billed minutes:", billed(JOBS))
    ```

    build (4) -&gt; e2e (12) -&gt; deploy (2) = 18 minutes of waiting, while billed time is lint 1 + build 4 + unit 6x3 + e2e 12 + deploy 2 = 37. Verified by running the solution.

---

More free practice: the [CI/CD Mastery Path](index.md) curriculum, the [Interview Prep Pack](https://learnmasterypath.com/interview-pack/) and the [free resume ATS check](https://learnmasterypath.com/resume/).
