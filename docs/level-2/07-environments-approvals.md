---
description: "Deployment environments, protection rules, required reviewers, environment secrets and concurrency, and what an approval gate does and does not guarantee."
---

# 07 · Environments, Approvals & Concurrency

Building and testing are safe to repeat. **Deploying** changes something people use. A pipeline therefore needs a way to say "this job touches production, so it needs extra conditions": who may trigger it, who must approve it, which credentials it can see, and that only one deployment to a target runs at a time. GitHub Actions calls the target an **environment**; Jenkins expresses the same ideas with `input` steps, credentials scopes and the `lock` plugin.

!!! note "What was run, and what wasn't"
    **No approval, environment or protection rule was exercised**: that needs a GitHub repository with environments configured, and I did not create one for this lesson. Everything about environments is from docs.github.com and Jenkins documentation as read in October 2026. The numbers quoted (a 30-day wait for approval) are documented limits. What *is* verifiable locally is the lint rule that flags a deploy job lacking `concurrency:`, which Lesson 10's tested linter implements (rule W006).

## What an environment is

An environment is a named deployment target (`staging`, `production`) attached to jobs with `environment: production`. Per the GitHub documentation it can carry:

- **Required reviewers**: the job waits, paused, until a listed person or team approves. Up to a small number of reviewers can be listed and **one** approval releases the job.
- **Wait timer**: a delay before the job starts, which gives a window to cancel.
- **Branch / tag restrictions**: only workflows on `main` (or a `release/*` pattern) may deploy to it.
- **Environment secrets and variables**: values visible only to jobs that target that environment, and only after protection rules pass.
- **Custom protection rules**: a third-party check (change-management system, health check) the platform consults before releasing.

A job waiting for approval is not consuming a runner, but it is still waiting: documentation states a workflow run waiting for approval is cancelled after **30 days**. A deploy that "needs a Friday approval" can expire quietly over the weekend of a holiday.

## Why secrets belong to the environment

A repository-level secret is visible to *every* job in the repository, including a pull request's workflow if permissions allow. An environment secret is only released to a job that has passed the environment's rules. So `PROD_DEPLOY_KEY` stored as a production environment secret cannot be read by the test job or by a PR-triggered workflow. This is the practical meaning of "least privilege" in a pipeline (Level 1 · 08): the credential exists only where the check has happened.

Combined with OIDC federation (Level 3 · 08), the environment name can appear in the token's claims so the cloud provider itself refuses to issue production credentials to a job that is not in the `production` environment.

## What an approval does and doesn't prove

It proves a person with the right account clicked "approve" on *this run*. It does **not** prove:

- that the person **read the diff** (rubber-stamping is the normal failure; a reviewer approving 20 times a day cannot be a control);
- that the approval was **independent**: by default the person who triggered the run may be able to approve it unless "prevent self-review" is enabled;
- that the thing approved is **the thing deployed** unless the deploy uses the exact artifact built and tested earlier in the run (build once, promote the same artifact; Level 1 · 07). If the deploy job rebuilds, the approver approved a commit but the system shipped a rebuild.

An approval gate is a *control* only when these three properties are designed in. Otherwise it is a ritual that adds a delay.

## Concurrency: one deployment at a time

Two pushes in quick succession start two workflow runs. If both deploy, they race: the older one can finish *last* and leave production on the **older** version. GitHub Actions' answer is the `concurrency` key:

```yaml
concurrency:
  group: deploy-production
  cancel-in-progress: false      # queue, do not cancel a deploy already running
```

Key points from the documentation: runs in the same group execute **one at a time**; a newer pending run replaces an older *pending* one (so at most one waits); `cancel-in-progress: true` cancels the running one, which is right for tests on a branch (newer commit supersedes) and **wrong for deploys** (you would abort a deployment half-way, e.g. between a migration and the app update). So: `cancel-in-progress: true` for CI, `false` for deployment.

Note the replacement behaviour: if three deploys queue, the middle one is dropped. That is acceptable only if each deploy ships "the latest state", which is true for deploying `main` and false for deploying a specific release tag that someone asked for.

Jenkins offers `disableConcurrentBuilds()` per job and the Lockable Resources plugin's `lock(resource: 'prod')` for finer control; the semantics differ slightly, so read the plugin documentation for what happens to waiting builds.

## Promotion between environments

A typical flow: build once → deploy to `dev` automatically → run smoke tests → deploy to `staging` → run integration tests → manual approval → `production`. Each environment gets the **same artifact** and different configuration. The three things allowed to differ are configuration values, scale, and credentials; if the code or the build differs, staging stops being evidence about production.

Keep configuration in the repository as code or a config service, not edited by hand on servers, so that "what is deployed where" is answerable from version control (Lesson 06 of Level 3 on GitOps).

## Checklist

- Environment names are defined once and referenced by constant, not typed freehand.
- Production deploys use the same artifact that passed the earlier stages.
- Self-review is prevented for production approvals.
- Environment secrets exist only in the environments that need them.
- Deploy jobs use a concurrency group with cancel-in-progress false.
- Branch restrictions limit which refs can deploy to production.
- Approval notifications reach people who can actually act on them.
- Approvals expire visibly rather than silently.
- Rollback uses the same environment protections as a forward deploy.
- Approval and deploy records are exported to long-term storage.
- A break-glass path exists, is rare, and is reviewed afterwards.
- Staging differs from production only in configuration, scale and credentials.
- Smoke tests run after every deploy, and a failure triggers the rollback procedure.

## How It Actually Works

When a job declares `environment: production`, the scheduler evaluates the environment's protection rules *before assigning a runner*. If a rule needs a human, the job enters a "waiting" state and a notification is sent to the reviewers; the run's UI shows the pending review. On approval the scheduler records who approved and when (this record appears in the run and in the audit log), releases the environment's secrets to the job's context, and queues it for a runner. A branch restriction is checked against the ref that triggered the run, which is why a deploy job triggered from a feature branch is rejected even if a reviewer would have approved. Concurrency groups are enforced at the same scheduling layer: the group's lock is acquired before the job starts, and a run that cannot get the lock is shown as pending.

## Common mistakes

- **Deploy secrets stored at repository level**, visible to untrusted workflows.
- **Reviewer approval without independence** (self-approval allowed, or the same two people approve everything).
- **Rebuilding in the deploy job**, so the approved commit and the deployed bytes differ.
- **`cancel-in-progress: true` on deploys**, aborting half-applied changes.
- **No concurrency control**, allowing an older deploy to finish after a newer one.
- **Different artifacts per environment**, destroying the meaning of staging.
- **Long approval waits** that expire silently.
- **Environment names as free text** with typos (`prodction`) that silently create a new, unprotected environment.

## Exercise

1. Write a workflow with `build`, `deploy-staging` and `deploy-production` jobs where production uses `environment: production` and a concurrency group. Run `python3 src/wflint.py` on it and fix every finding.
2. Draft the protection rules for a production environment in your organisation: reviewers, self-review policy, wait timer, branch rule. Justify each setting in one line.
3. Two commits land one minute apart and both start a deploy. Describe, step by step, what happens with and without `concurrency`, and what the final deployed version is in each case.
4. List what you would check to confirm an approval was meaningful. What data would you need to log?
