---
description: "Branching strategies and pull request checks: required checks, ownership, and a semantic merge conflict that is green alone and red merged."
---

# 09 · Branching Strategies and Pull Request Checks

How a team uses branches determines how often it integrates, which is the "I" in CI. Pull requests are where pipelines give feedback before code reaches the mainline. This lesson compares strategies and demonstrates a failure that passes every per-branch check.

!!! note "What was run"
    The merge experiment ran with real `git` and `pytest` on macOS in a temporary repository. Descriptions of GitHub merge queues, `pull_request` merge refs and branch protection come from documentation and were not run. See Lesson 01.

## Strategies compared

| Strategy | Shape | Integration frequency | Fits |
|---|---|---|---|
| **Trunk-based development** | Everyone commits to `main` (or merges very short-lived branches, under about a day or two) behind feature flags | Continuous | Teams practising CI/CD seriously; needs strong tests and flags (Level 3 · 02) |
| **GitHub flow** | Short-lived feature branches, pull request, review, merge to `main`, deploy from `main` | Daily to weekly | Most web/SaaS teams |
| **GitFlow** | `develop`, `feature/*`, `release/*`, `hotfix/*`, `main` | Per release | Software shipped in discrete versions with long support windows; heavy for continuous delivery |
| **Release branches off trunk** | Trunk plus `release-1.4` branches receiving only fixes | Continuous on trunk | Products with several supported versions |

Longer-lived branches mean bigger, riskier merges and delayed feedback; the research-backed practice behind high-performing teams is small batches and frequent integration (Level 3 · 09). Whatever you choose, make **`main` always releasable**.

## Pull request checks

A PR pipeline should answer, within minutes: *Does it build? Do tests, lint and type checks pass? Are there security findings? Does it need review from the owners of these files?* Configure **branch protection / rulesets** so these are mandatory, and combine with human review (at least one approval, code owners for sensitive paths, dismissing stale approvals on new pushes).

### Checks must run on what will actually merge

Here is why. In a throwaway git repository I created two branches from the same base:

- `rename-func` renames `price()` to `total_price()` and updates its test.
- `new-caller` adds `report.py`, which calls `price()`, with its own test.

Each branch's test suite is green on its own:

```text
branch rename-func alone: 1 passed
branch new-caller alone:  2 passed
```

Merging them produces **no textual conflict**, but the merged result is broken:

```text
merge of both (no textual conflict): git says 0 conflicts; tests: ERROR test_report.py ... Interrupted: 1 error during collection
```

`report.py` imports a name that no longer exists. Both PRs were green when reviewed, and the breakage appears only on the combination: a **semantic conflict**. The defences:

1. **Require branches to be up to date** before merging, so the PR's checks ran against the current `main`. Cost: rebase/update churn on busy repositories.
2. **Merge queues** (GitHub merge queue, Gerrit, Bors/Mergify-style tools): the queue builds the merge of *each queued PR on top of the ones ahead of it* and tests that combination before merging, giving serialisation with parallel testing.
3. **Test the merge commit.** GitHub's `pull_request` event checks out a temporary *merge* of the PR into the base branch by default (documented behaviour; I did not verify it here), which already tests the combination at the time the PR last updated; but `main` can move afterward, which is why (1) or (2) is still needed.
4. **Run the full test suite on `main` after every merge** and treat a red `main` as a stop-the-line event (revert first, then diagnose).

## Reviews, ownership and automation

- Keep PRs **small** (reviewable in minutes); large PRs get rubber-stamped.
- `CODEOWNERS` routes reviews to owners of paths; required for sensitive areas (pipelines, infrastructure, auth).
- Bots can label, check PR titles (conventional commits for changelogs; Level 3 · 07), enforce size limits and update dependencies (Dependabot, Renovate); give dependency PRs the same CI as human PRs, and consider automerge only for patch versions with strong tests.
- Protect the **pipeline definition itself**: changes to `.github/workflows/` or the `Jenkinsfile` deserve owner review, because a PR can change what runs (and, on some triggers, with which secrets).

## Commit and merge hygiene that helps CI

Prefer **squash or rebase merging** for a linear, bisectable history on `main`; make each merged commit buildable so `git bisect` works. Keep commit messages informative (they feed changelogs). Use `git revert` to undo a bad merge on shared branches rather than force-pushing; never force-push to protected branches.

## Checklist

- Required checks are named in branch protection and match the real job names.
- Stale approvals are dismissed when new commits arrive.
- Pipeline files have a code owner who is not the author of the change.
- Secrets are not exposed to workflows triggered from forks.
- PR titles or commit messages follow the convention the release tool expects.
- A merge queue or up-to-date requirement prevents green-alone, red-together merges.
- Long-lived branches are rebased or merged often enough that CI results stay meaningful.
- Draft PRs run a cheaper subset of checks.
- The default branch is protected against force-pushes.

## How It Actually Works

A pull request is a pair of refs (head and base) plus metadata. When it is opened or updated, the hosting service fires an event; for GitHub's `pull_request` workflows it also creates a merge ref that represents "base plus head", and the workflow builds that. Branch protection is evaluated by the service at merge time: it looks up the *required* status checks for the base branch, requires each to have reported success for the PR's head (or merge)
commit, and refuses the merge button otherwise. A merge queue adds a temporary branch holding the stack of queued changes, runs the required checks on it, and fast-forwards `main` only if they pass. The git experiment above shows why a purely textual merge algorithm cannot protect you: git merges lines, not meaning.

## Common mistakes

- **Long-lived branches.**
- **Required checks configured to pass when skipped** (or not required at all).
- **Allowing merges with stale checks** on busy repositories.
- **Letting administrators bypass** protections routinely.
- **Huge PRs** and rubber-stamp reviews.
- **A red `main` left red** while others keep merging.
- **Unreviewed changes to the pipeline files.**
- **Force-pushing shared branches.**

## Exercise

1. Reproduce the rename-versus-new-caller experiment in your own repository, then write the branch protection or merge-queue settings that would have caught it before `main` broke.
2. Measure how long your PR pipeline takes and how many PRs merge per day; estimate how often two PRs in flight could conflict semantically.
3. Write the `CODEOWNERS` entries for pipeline files, infrastructure and a security-sensitive module.
4. Draft your team's "main is red" policy: who reverts, how fast, and who may merge while it is red.
