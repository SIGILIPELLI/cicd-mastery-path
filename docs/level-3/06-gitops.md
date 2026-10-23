---
description: "GitOps: Git as the source of truth, pull-based reconciliation, drift correction, prune and rollback, shown with a tested reconcile-loop simulator."
---

# 06 · GitOps: Reconciling Desired State

In a **push** pipeline, CI runs `kubectl apply` or a deploy script against the target. In **GitOps**, the desired state of the environment lives in a Git repository, and an agent *inside* the environment continuously pulls it and makes reality match. The pipeline's job shrinks to building artifacts and proposing a change to the state repository; the agent does the rest.

!!! note "What was run, and what wasn't"
    I did not run Argo CD, Flux or Kubernetes. The product behaviour described (continuous sync, pruning, health, auto-sync options) is from general knowledge of those tools and their documentation as I know it, and should be checked against current docs. What I wrote and ran is `src/gitops.py`, a **30-line reconcile loop over Python dictionaries** with 8 pytest tests. It models the idea, not any tool's implementation.

## The model

- **Desired state**: declarative files in Git (manifests, Helm values, Kustomize overlays) describing what should exist.
- **Actual state**: what is running.
- **A reconciler** repeatedly computes the difference and applies it: create what is missing, update what differs, optionally delete what is extra.

The simulator's three functions are the whole idea: `diff(desired, actual, prune)` returns a plan of `create / update / delete` operations; `reconcile` applies it; `drift` reports differences whether or not they will be fixed. Run on a two-service desired state:

```text
empty cluster      -> [('create','api',...), ('create','web',...)]
someone sets web replicas to 10 and adds an object `debug`
drift              -> {'missing': [], 'changed': ['web'], 'extra': ['debug']}
reconcile (prune)  -> [('update','web'), ('delete','debug')]
reconcile again    -> []        # converged: a second pass does nothing
```

Properties the tests pin down: an empty cluster gets everything created; a converged cluster produces an empty plan (**idempotent**); a manual change to a managed object is **reverted**; an extra object is deleted only when `prune=True`, while with `prune=False` it is left alone but still shows in the drift report; and applying a bad version, then the previous version, returns to the previous state.

## Why teams adopt it

1. **Audit and review for free.** Every change to an environment is a commit: author, reviewer, timestamp, diff, and the ability to ask "what changed before the outage?" with `git log`.
2. **Rollback is a revert** (Lesson 04), with the same review as any other change.
3. **Drift is self-healing and visible.** The out-of-band change you made in a panic is reverted at the next sync unless you commit it; the reconciler reports it either way.
4. **No cluster credentials in CI.** In the push model your CI holds credentials strong enough to deploy to production. In the pull model, the agent inside the cluster holds them and only needs *read* access to Git and the registry. A compromised CI cannot push directly to production.
5. **Disaster recovery.** Rebuilding a cluster is pointing a new agent at the repository.

## Costs and traps

- **Two repositories, one change.** Typically application code and environment state are separate. A release is now: build and push an image, then a commit changing the image tag in the state repository, by a bot or a pull request. Decide who does that and how it is gated.
- **Latency and surprise.** Changes apply when the agent next syncs (poll interval or webhook). An "I merged but nothing happened" is usually the agent erroring, not Git. You need to monitor the reconciler itself.
- **Secrets don't belong in Git in plain text.** Use sealed or encrypted secrets, or an external secrets operator that references a secret store; the manifests in Git carry only a reference.
- **Pruning is dangerous.** `prune=True` deletes everything not in Git. A mistaken directory change that omits a manifest deletes a live object, including a stateful one. Many setups protect stateful resources with annotations or do not prune at all in production; know your tool's defaults.
- **Order and health.** Resources depend on each other (a namespace before its contents, a database before the app). Tools have sync-wave or hook mechanisms for ordering; a simple dict-diff has none, which is one way the simulator is far simpler than reality.
- **State that is not in Git.** Replica counts managed by an autoscaler would flap if Git declares a fixed number; the reconciler and autoscaler fight. Exclude fields owned by other controllers from comparison.
- **Not everything is Kubernetes manifests.** The pattern also applies to infrastructure (Terraform controllers), but then the plan/apply guard concerns from Lesson 05 return.

## Repository layout and promotion

A common structure is one directory per environment (`envs/dev`, `envs/staging`, `envs/prod`) with shared bases and per-environment overlays. Promotion is a pull request that copies a version (the image tag or digest) from one environment's directory to the next. Because the change is a small, reviewable diff, it is easy to require approval for production only (Lesson 07 in Level 2 covers the approval caveats), and easy to see what is different between staging and production: `git diff` of two directories.

Avoid "branch per environment" unless you have a strong reason; long-lived branches diverge and merging them becomes the deployment process. Directories on a single branch keep differences visible.

## Image tags in a GitOps world

A mutable tag (`latest`, or a re-pushed `1.4`) breaks the model, because Git does not change when the image does: the reconciler sees "no difference" and the cluster may run an image Git cannot account for. Reference an **immutable tag or digest** in the state repository, so a change of running code is always a commit. An image-updater bot that opens a pull request when a new image appears is the usual automation.

## Health: synced is not healthy

"Synced" means actual matches desired, not that the application works. A correct manifest pointing to a crashing image is perfectly synced. Reconcilers expose a separate health status derived from readiness probes and resource conditions. Alert on both, and make the pipeline's smoke test (not the reconciler) the judge of whether a release succeeded.

## Checklist

- Image references in the state repository are immutable tags or digests.
- Secrets are referenced, never stored in plain text.
- Pruning is reviewed, and stateful resources are protected.
- Fields owned by other controllers are excluded from comparison.
- The reconciler's own health is monitored and alerted.
- Production changes require review in the state repository.
- Environments are directories on one branch.
- Sync status and health status are both visible on one dashboard.
- A documented procedure covers bootstrapping a new cluster from the repository.
- The pull request that changes production state is reviewed by someone who did not write it.

## How It Actually Works

The reconciler is a control loop, the same pattern Kubernetes controllers use: *observe* actual state, *compare* with desired, *act* to reduce the difference, repeat. Because it recomputes the difference from scratch each time rather than replaying a log of past commands, it is **level-triggered**: a missed event or a crash only delays correction, and the next pass fixes it. That is why the simulator's second pass returns an empty plan, and why the system recovers from out-of-band changes without anyone telling it. The cost of the design is that the loop must be able to read both states cheaply and compare them reliably; normalising defaults (the cluster adds fields to objects that Git does not mention) is the unglamorous hard part in real tools, and my dictionary comparison sidesteps it completely.

## Common mistakes

- **Mutable image tags**, so Git doesn't track what runs.
- **Plain-text secrets** in the state repository.
- **Pruning stateful resources** by accident.
- **Not monitoring the reconciler**, assuming "merged" means "applied".
- **Two controllers owning the same field** (autoscaler vs Git).
- **Branch-per-environment** divergence.
- **Equating "synced" with "healthy"**.
- **Giving CI cluster-admin credentials anyway**, losing the security benefit.

## Exercise

1. Run `pytest src/test_gitops.py -v`. Add a test where `actual` has a field the reconciler adds itself (e.g. `status`) and show the loop flaps; then make `diff` ignore a configurable list of fields.
2. Draft the promotion process from staging to production as a pull request: who opens it, what it contains, who approves it, what checks run.
3. Explain what happens in each model (push and pull) if the CI system is compromised.
4. Decide what to prune in production and what not to, and how you would protect the database object from deletion.
