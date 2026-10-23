---
description: "Handling CI/CD incidents: broken main, leaked secrets, poisoned artifacts, outages of the pipeline itself; runbooks, communication and blameless reviews."
---

# 07 · Pipeline Incidents

The delivery system is production infrastructure for your engineers. When it fails, nothing ships, including the fix for whatever else is broken. And it can be the *cause* of incidents: a bad deploy, a leaked credential, a poisoned artifact. This lesson covers how to respond to each class, and how to learn from it.

!!! note "What was run"
    This lesson is process and judgment; nothing was executed except small calculations with `src/dora.py` (Level 3 · 09) on a hand-made fixture. The runbooks are templates drawn from general incident-response practice, not from any particular organisation's procedure, and have not been exercised in a real incident. Adapt them, and rehearse them.

## Classes of pipeline incident

| Class | Example | First priority |
|---|---|---|
| **Broken main** | A merge turns the main branch red; nobody can merge | Restore green quickly: revert or fix forward |
| **Pipeline outage** | The CI server, runner pool, registry or artifact store is down | Restore the ability to ship; know the emergency deploy path |
| **Bad release shipped** | A deploy caused customer impact | Stop the bleeding: rollback, flag off (Level 3 · 04) |
| **Secret leak** | A credential in a repository, a log or an artifact | Revoke and rotate first, investigate second |
| **Compromised build** | A malicious dependency, action or runner | Contain, preserve evidence, rebuild trust |
| **Cost spike** | A loop or matrix burns the budget | Cancel the runs, cap spend, fix the trigger |
| **Data-affecting migration** | A migration locks or corrupts a table | Halt, assess, restore (Level 3 · 03) |

## Principles

1. **Stabilise before diagnosing.** Revert, roll back, turn the flag off, cancel the run. Understanding why can wait until the damage stops growing.
2. **One incident commander** who coordinates; others investigate and act. Many people typing commands into production at once make things worse.
3. **A written timeline from the start** (who did what, when). Memory is unreliable and the timeline is the core of the review.
4. **Communicate on a schedule**, even when nothing has changed ("still investigating, next update in 30 minutes").
5. **Preserve evidence** before cleaning up (logs, run records, the compromised runner's disk image), especially for security incidents; platform retention may delete it.
6. **Blameless reviews.** Ask how the system allowed the mistake, not who made it. People who fear blame hide near misses, and then you learn nothing.

## Runbook: broken main

1. **Announce** in the team channel: "main is red, merges paused" and name an owner.
2. **Find the culprit commit:** the first red run; use the CI history, `git bisect` if several commits landed together.
3. **Decide: revert or fix forward.** Prefer revert when the cause is clear and the revert is clean, because it restores a known-good state in minutes. Fix forward only when the fix is trivial and certain.
4. **Verify:** the revert's own pipeline must go green before announcing recovery.
5. **Follow up:** why did this reach main? A missing required check, a semantic merge conflict (Level 1 · 09: green alone, red together), a flaky test that hid a real failure (Level 2 · 05), or a merge queue that wasn't used?

A **merge queue** (tests the combined result before merging) prevents most "green separately, red together" breakages and is the structural fix.

## Runbook: leaked secret

1. **Revoke or rotate immediately.** Assume the secret is already compromised: bots scan public repositories quickly. Deleting the commit or force-pushing does **not** un-leak a secret (clones, forks, caches, the platform's own records, and mirrors may keep it).
2. **Find the exposure window and use:** when was it committed or logged, and what did the credential permit? Check the provider's audit logs for use of that key during the window.
3. **Clean up** the repository history if policy requires it, and purge it from build logs and artifacts; this is hygiene, not remediation.
4. **Find the cause:** a missing scanner (the Level 1 secret scanner finds patterns but not everything), a debug `echo`, a `.env` file committed. Add the control.
5. **Replace long-lived secrets with short-lived ones** (OIDC federation) where you can, so the next leak has a short half-life.

## Runbook: pipeline outage

1. **Declare an outage** and tell engineers the state and the workaround.
2. **Know your emergency path before you need it:** a documented, tested way to deploy a hotfix without the normal pipeline (a script run by a break-glass role, with logging and review afterward; Lesson 05). If the only way to ship the fix is the broken system, you have a circular dependency.
3. **Triage the dependency:** the controller? the runner pool? a registry? a third-party service (a package index, a cloud region)? Check provider status pages, but also check your own quotas, expired tokens and certificates, which cause many "outages".
4. **Degrade deliberately:** pause scheduled jobs to free capacity, restrict to the critical repositories, run a single priority queue.
5. **After recovery, check for lost or duplicated work:** half-finished deploys, queued jobs that ran twice, caches written during the failure.

## Runbook: suspected compromised build input

1. **Contain:** disable the affected workflow, pause deployments, and revoke credentials those jobs could access.
2. **Scope:** which builds used the bad input (an action version, a package version, a runner)? An SBOM and artifact metadata (Level 3 · 08) answer this in minutes; their absence makes it a days-long hunt.
3. **Assess artifacts:** anything built in the window is suspect. Identify what was deployed where, and decide what to rebuild from a clean environment and redeploy.
4. **Preserve evidence** from runners and logs, and rotate everything the build could read.
5. **Rebuild trust:** pin to a verified version, rebuild on fresh ephemeral runners, compare outputs against the last known-good reproducible build where you have one (Level 1 · 06).

## Measuring and improving

Track pipeline incidents like production ones. Using the DORA calculator on a fixture, one failed deploy that took 1 hour to restore and another that took 2 hours gave a **median restore of 1.5 hours** and a change failure rate of 0.5 (Level 3 · 09); the real numbers are yours to collect. Also track: time to detect (alert fired versus problem started), time to rollback specifically, number of incidents by class, and recurrence of the same cause. Use the review to produce **concrete, owned, dated actions** (a new test, a guard, a runbook step, a removed permission), and follow up on them. Reviews that end in "be more careful" change nothing.

## A review template

- **Summary:** what happened, impact, duration.
- **Timeline** with timestamps (UTC).
- **Detection:** how did we find out; could we have found out sooner?
- **Contributing factors:** several, systemic (missing check, ambiguous docs, tool behaviour), not a single "root cause" person.
- **What went well:** the things to keep doing.
- **Actions:** each with an owner and due date, ranked by how much risk they remove.
- **Evidence appendix:** logs, graphs, links.

## Rehearsal

Run game days: simulate a leaked token, a broken main, a registry outage, in a safe environment. Time how long it takes to revoke a credential, to find which deployments used an artifact, to restore the pipeline from backup. The first time you do it, expect surprises: stale contact lists, missing access, a runbook referencing a decommissioned system. Finding those in a drill is the whole value.

## How It Actually Works

Incident response is a feedback system with latency at each stage: detection (monitoring and alerts), decision (who decides, with what information), action (how fast the mechanism works: a flag flips in seconds, a rollback takes minutes, a rebuild takes hours), and verification (how you know it worked). The total damage is roughly *impact rate × time to recovery*, so improvements target the slowest stage. A team with good alerting but a rollback that takes an hour should invest in rollback; a team that can roll back in a minute but detects problems an hour late should invest in alerting and canary analysis. The runbooks above are mostly about shortening the decision stage by writing the decisions down beforehand.

## Common mistakes

- **Diagnosing before stabilising.**
- **Deleting a leaked secret from Git** without rotating it.
- **No emergency deploy path** independent of the broken system.
- **Many people acting at once** with no commander.
- **No timeline**, so the review relies on memory.
- **Blameful reviews** that suppress reporting.
- **Actions without owners or dates**, never completed.
- **Never rehearsing**, so the first run of the runbook is during an incident.

## Exercise

1. Write the leaked-secret runbook for your organisation's most sensitive credential: exact commands or console steps to revoke it, who can do it at 3 a.m., and where the audit logs are.
2. Test your emergency deployment path in a staging environment. Time it and record every manual step.
3. Take a past incident and rewrite its review using the template. What action items have no owner?
4. Design a game day: the scenario, injects, success criteria and how you would debrief.
