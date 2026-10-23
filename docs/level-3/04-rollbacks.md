---
description: "Rolling back safely: what can be reverted, what cannot, roll-forward versus rollback, immutable artifacts, GitOps revert, and rehearsing the procedure."
---

# 04 · Rollbacks: Going Back, and When You Cannot

"We can always roll back" is the most expensive sentence in delivery, because it is only sometimes true. A rollback restores **code**. It cannot restore **data written by the new version**, **messages already sent**, **emails delivered**, **money moved**, or **schemas altered**. Planning for rollback means knowing, for each change, which of those it has touched.

!!! note "What was run"
    No production rollback was performed. The mechanics shown use the GitOps reconcile simulator `src/gitops.py` (8 tests), where "rollback" is a revert of the desired state, and the SQLite behaviour from Lesson 03. The categories and the roll-forward advice are general practice, not measured results.

## What a rollback can and cannot undo

| Change | Rollback restores it? |
|---|---|
| Stateless application code | Yes: redeploy the previous artifact |
| Configuration / feature flag | Yes: revert the value (Lesson 02: usually the fastest) |
| Additive schema change (new nullable column) | Not needed: old code ignores it |
| Destructive schema change (drop/rename) | **No**: data is gone or old code breaks |
| Data transformed in place (e.g. rounded prices) | **No**, unless you kept the original |
| Messages published, jobs enqueued | **No**: consumers already saw them |
| External effects (emails, payments, API calls) | **No** |
| A new version of a *consumed* contract (event schema) | Only if consumers tolerate both |

The practical test for any change before it ships: *if I redeploy the previous version right after this one has run for an hour, what is wrong?* If the honest answer is "the old version would corrupt or misread data the new one wrote", you do not have a rollback; you have a one-way door, and it needs the care of one (expand/contract, dual-write, or a flag).

## Rollback vs roll-forward

**Rollback** returns to a known-good version. **Roll-forward** ships a new fix. Choose by speed and certainty:

- The last release only changed code, the previous artifact still exists and is compatible → **rollback**, because it is a known, tested state and the quickest.
- The change is a one-way door, or a rollback would itself need a migration → **roll-forward** (or a flag flip), because "going back" would be a new untested operation.
- The fix is a one-line change and your pipeline takes 5 minutes → roll-forward may be as fast as rollback, but it requires the pipeline to be healthy at the worst time. A pipeline that depends on the thing that is broken (a registry outage, a failing shared test) cannot roll forward.

Teams get hurt by committing to one dogma. The rule that scales: **make rollback the default, boring, one-command operation, and know in advance which changes are exceptions.**

## What makes rollback fast

1. **Immutable, versioned artifacts** (Level 1 · 07). Rollback is "deploy artifact 1.4.2 again" only if 1.4.2 still exists, byte-identical. If your pipeline rebuilds from source each time, "rollback" is a *new* build that might differ because a dependency moved. Retain the last N artifacts, and never delete the current plus previous release.
2. **Deploy by identifier, not by "latest".** `image: app:latest` has no previous state to return to. Deploy by version or digest.
3. **Config in version control.** Rolling back code with config you cannot reconstruct leaves a mismatched pair.
4. **One command, rehearsed.** The procedure should be as simple as the forward deploy, documented in the runbook (Level 4 · 07), and exercised routinely.
5. **The previous version's dependencies still exist**: its database schema, its secrets, its feature flags. A rollback to a version that needs a credential you rotated is a second outage.

### GitOps revert

In a GitOps setup (Lesson 06) the desired state lives in Git, so rollback is `git revert` of the change and let the controller reconcile. The simulator test `test_rollback_is_a_git_revert` shows the mechanics: apply a state with `web:2`, apply a bad `web:3`, then apply `web:2` again and the cluster returns to `web:2`; a second reconcile does nothing (idempotent). The advantage: the rollback is itself a reviewed, audited commit. The caveat: it takes effect when the controller next syncs, and it does not undo data.

## Automatic rollback

Canary analysis (Lesson 01) can roll back automatically. Conditions for trusting automation:

- The signal is **reliable**: false rollbacks (4% in my simulation of an identical canary) are a cost, missed regressions a bigger one.
- A **missing signal fails safe**: no metrics means stop and alert, never promote.
- The rollback is **idempotent and reversible**: automation that cannot be re-run safely produces a second incident.
- A **human is told**. An automatic rollback is an incident (the release failed) even if no customer noticed; someone must own the follow-up, or the same bad change will be re-attempted.

## Rehearsal

A rollback you have never run is a hypothesis. Rehearse regularly: in staging after each release, and occasionally in production during a quiet period with a harmless change. Measure how long it takes and what manual steps appeared. Typical surprises: the previous artifact was garbage-collected, a config key was removed, a migration had already run, the runbook referred to a dashboard that no longer existed. Record the time-to-rollback as a metric, next to time-to-restore (Lesson 09).

## Communicating

During a rollback, say so in the incident channel: what is being reverted, to which version, the expected duration, and how you will confirm health. Afterwards, write down why the failure was not caught earlier. "We rolled back and it was fine" is not the end: the change still needs fixing, and the reason it escaped is the real finding.

## Checklist

- Each change is labelled reversible or one-way before it ships.
- The previous artifact and its dependencies are retained and verified.
- Deploys reference immutable versions or digests, never 'latest'.
- Rollback is a single documented command with an owner.
- Configuration and flags roll back together with the code.
- The time to roll back is measured in each rehearsal.
- One-way changes use expand and contract, flags, or a canary.
- Automatic rollbacks page a human.
- Post-rollback review asks why the failure escaped earlier.

## How It Actually Works

A rollback is just another deployment whose target version happens to be older, which is why the *deployment mechanism* and the *artifact retention* determine whether it works. The reconcile loop in the GitOps simulator makes this concrete: it computes the difference between desired and actual state and applies it, with no notion of "old" or "new". A revert changes the desired state back to a previous value and the loop converges. What the loop cannot do is un-apply side effects outside the declared state, which is exactly the table above: only the declared state (images, replicas, config) comes back. Everything the running system did while the new version was live is history, and managing history is the job of expand/contract schema design, idempotent consumers, and careful sequencing of one-way doors.

## Common mistakes

- **Assuming rollback undoes data changes.**
- **Deploying `latest`** so there is nothing to go back to.
- **Garbage-collecting the previous artifact** to save disk.
- **Rolling back code but not config or flags**, leaving a mismatched pair.
- **Never rehearsing**, then finding the procedure broken mid-incident.
- **Automatic rollback with no human notified.**
- **Pipelines that cannot run when the registry or shared service is down**, blocking both rollback and roll-forward.
- **Rolling back past a migration** the old code cannot read.

## Exercise

1. For your last three releases, fill the table above: which parts could a rollback restore and which could not?
2. Run `pytest src/test_gitops.py -v -k rollback`. Then modify the test so a deployment is `web:3` with an extra object `jobs`; which operation removes it on revert, and what changes if `prune=False`?
3. Write the one-command rollback procedure for a service you operate, and time a rehearsal. Note every manual step.
4. Design the retention policy for artifacts: how many versions, how long, and what must never be deleted.
