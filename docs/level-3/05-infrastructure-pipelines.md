---
description: "Infrastructure-as-code pipelines: plan, review, apply, state, drift and a tested guard against destructive changes on hand-written fixtures."
---

# 05 · Infrastructure Pipelines: Plan, Review, Apply

Infrastructure as code (Terraform, OpenTofu, Pulumi, CloudFormation, Ansible) turns servers, networks and databases into files in Git, so changes can be reviewed and repeated. The delivery pipeline for it has a different shape from an application's: the "artifact" is a **plan**, "deploy" is an **apply** that can destroy things, and the world can change underneath you between plan and apply.

!!! note "What was run, and what wasn't"
    **No infrastructure tool was run and no cloud account was used.** The commands (`terraform plan`, `apply`, `show -json`) and the shape of the JSON plan (`resource_changes[].change.actions` with values such as `no-op`, `create`, `update`, `delete`, `read`, and a replace shown as delete plus create) are from the Terraform documentation as I know it, and could differ in your version. What I built and ran is `src/planguard.py`, tested with 9 pytest tests on **hand-written fixtures** in that shape (`src/sample-plan.json`). It has never read a real Terraform plan.

## The shape of an infrastructure pipeline

```text
pull request:   fmt/validate → lint/policy → plan → post the plan as a PR comment → human review
merge to main:  plan again (fresh) → approval (production) → apply → record outputs → smoke test
```

Key ideas:

1. **Plan on every pull request**, and show the plan to the reviewer. Reviewing the HCL diff alone misses effects: a one-line change to a variable may replace a database. The plan is the diff of *reality*.
2. **Apply what was reviewed.** Plans can be saved and applied later (`plan -out`), which guarantees the applied change is the reviewed one, provided the real infrastructure has not changed in between; the tool refuses to apply a plan if the state moved. Without a saved plan, `apply` re-plans and can do something different from what the reviewer saw.
3. **Serialise applies**: one at a time per state, using state locking and a pipeline concurrency group (Lesson 07).
4. **Separate credentials**: the PR plan job gets read-only access; only the apply job gets write access, and only on the protected branch and environment.

## State: the file that makes it work

The tool keeps a **state** mapping each declared resource to a real object ID and its last known attributes. It is the source of both power (it knows what to change) and risk:

- State must be **shared and locked** (a remote backend with locking), never on a laptop or in CI workspace files that vanish after the job.
- State can contain **secrets** (database passwords appear in plain text in some resource attributes), so encrypt it and restrict access; it is as sensitive as the credentials.
- Losing or corrupting state means the tool no longer knows what it owns: it may try to create duplicates or lose track of live resources. Version the state backend and restrict manual edits.

## Drift

**Drift** is when real infrastructure differs from the code: someone changed a security group in the console during an incident. A scheduled `plan` (nightly, no apply) that fails when there are unexpected changes detects drift. The response is a decision, not automation: either code the change or revert it. Auto-applying to "fix" drift can undo an emergency fix or delete a resource a team created by hand, so apply on a schedule only for environments where that is explicitly accepted.

## Guarding destructive changes

The most dangerous line in an infrastructure PR is the one that causes a **replace** (destroy and recreate) of a stateful resource: a database, a disk, a bucket. Changing an immutable attribute often forces it, and the HCL diff may look innocuous.

`planguard.py` reads the JSON plan and blocks any resource whose action list is a delete or a replace unless its exact address is on an allowlist. It treats unknown action lists as blocked (fail closed). Fixture run:

```text
summary: {'create': 1, 'delete': 1, 'none': 1, 'replace': 1, 'update': 1}
BLOCKED replace: aws_db_instance.main
BLOCKED delete: aws_sns_topic.old
exit=1
```

With the two addresses allowed explicitly on the command line it prints the same summary and exits 0. The tests check: classification of each action list; unknown actions fail closed; a safe plan passes; replace and delete are blocked; an allowlist permits exactly the listed address and **not a prefix** (`q.old2` is not permitted by `q.old`); an empty plan passes; counts are right.

Design points: the allowlist is *explicit and per resource*, so approving a deletion is a reviewed, visible act in the PR; the guard runs in CI on the plan the reviewer is reading; and it supplements, not replaces, tool-native protections such as `prevent_destroy` lifecycle rules, deletion protection on databases, and backups. It also cannot know that deleting `aws_sns_topic.old` is fine; a human decides that.

## Policy as code

Beyond destructive changes, organisations check plans or configuration against rules: no public storage buckets, required tags, allowed regions, instance size limits. Tools exist for this (Open Policy Agent, Sentinel, checkov and similar); I did not run any. The pipeline pattern is the same as the guard: parse the plan or config, evaluate rules, fail with a message that names the resource and the rule.

## Testing infrastructure code

Layers, from cheap to costly: formatting and validation; static analysis; **plan-level tests** (assert on the plan, as above); and **real apply to an ephemeral environment** with checks and teardown. The last is the only one that tests that the cloud accepts your request (quotas, permissions, naming collisions) and is slow and costs money. Make ephemeral environments cheap and automatic to destroy, tag them with an owner and expiry, and sweep leaks on a schedule.

## Secrets and credentials

Prefer short-lived credentials by OIDC federation (Lesson 08 and Level 1 · 08) over stored keys. Scope the apply role to the resources the repository manages. Do not print the plan to public logs if it contains sensitive values; Terraform marks some values as sensitive in output but the guarantee varies, so check what your logs reveal.

## Checklist

- Plans run on every pull request and are shown to reviewers.
- The apply job uses a saved plan or re-checks that the plan is unchanged.
- State is remote, locked, encrypted and access-controlled.
- Plan jobs run with read-only credentials; apply runs only on the protected branch.
- Destructive actions require an explicit, reviewed allowlist entry.
- Stateful resources have deletion protection and backups.
- Scheduled drift detection runs without applying.
- Ephemeral test environments carry an owner tag and an expiry.

## How It Actually Works

The tool builds a dependency graph from your configuration, refreshes state by querying the real resources, then diffs desired attributes against recorded ones to produce a plan: a list of per-resource actions. `apply` walks the graph in dependency order, calling the provider's create/update/delete APIs, in parallel where independent, and updates state as each finishes. An interrupted apply leaves state partially updated, and re-running plans from where it left off, which is why locking and not killing applies matter. Whether a change is an in-place update or a replace is a property of the **provider's schema** (which attributes are "force new"), not of your intent, which is exactly why reading the plan, and guarding it automatically, catches things code review does not.

## Common mistakes

- **Reviewing the code diff without the plan.**
- **Applying a fresh plan that differs from the reviewed one.**
- **State on a laptop**, unlocked, or unencrypted with secrets in it.
- **Applying from several places at once.**
- **Auto-applying drift fixes** that undo emergency changes.
- **Not noticing a replace** of a stateful resource in a long plan.
- **Broad cloud credentials** in the PR plan job.
- **No deletion protection or backups** on databases, relying on review alone.

## Exercise

1. Run `pytest src/test_planguard.py -v` and `python3 src/planguard.py src/sample-plan.json`. Add a fixture where a resource has actions `["update"]` but is a database, and discuss whether a guard on action type alone is enough.
2. Extend the guard with a list of "never destroy" address patterns (e.g. `aws_db_instance.*`) that cannot be overridden by the allowlist without a second approval, and test it.
3. Sketch the workflow with separate PR-plan and main-apply jobs, giving each its credentials and concurrency group.
4. Describe how you would detect and respond to drift in a production account that several teams use.
