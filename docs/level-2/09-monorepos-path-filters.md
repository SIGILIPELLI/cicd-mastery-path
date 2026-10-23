---
description: "CI for monorepos: path filters, change detection with git diff, shared-library fan-out, a tested changed-files to jobs mapper, and its failure modes."
---

# 09 · Monorepos & Path Filters

In a monorepo many projects share one repository. Running every project's pipeline for every change wastes time; running too little lets a change break something unnoticed. The skill is mapping **what changed** to **what must be checked**, and being honest about the cases where the mapping is wrong.

!!! note "What was run"
    The mapper in `src/pathfilter.py` was written and tested here: 9 pytest tests pass, including one that builds a real temporary Git repository, makes a commit on a branch, and runs `git diff --name-only` through the code. GitHub's `paths:` filters and Jenkins' `changeset` conditions are described from their documentation and were **not** run. The glob rules in my code are simplified and differ in details from GitHub's glob syntax, so use the platform's filter in production and my code to understand and test the idea.

## Why not just run everything

A repository with 30 services and a 12-minute test each would cost 6 hours of runner time per push if everything ran. The usual remedies are (in rising order of effort): path filters on the triggers, change detection inside the pipeline, and a build system that understands the dependency graph and caches by input hash (Bazel, Nx, Turborepo, Gradle). This lesson covers the first two.

## Platform path filters

GitHub Actions' workflow triggers accept `paths:` and `paths-ignore:`:

```yaml
on:
  pull_request:
    paths:
      - "services/api/**"
      - "libs/common/**"
```

The workflow runs only if the changed files match. The pitfall is documented and important: **a workflow skipped by a path filter reports no status**. If that check is a *required* status check in branch protection, the PR waits forever on "Expected"; a skipped-by-filter workflow does not count as passing. The standard cure is one always-running workflow that detects changes and a final gate job (Lesson 01), rather than putting required checks behind path filters.

## Change detection in the pipeline

The plan job asks Git which files differ from the merge base and maps them to projects:

```python
def changed_files(base, head="HEAD"):
    out = run(["git", "diff", "--name-only", f"{base}...{head}"])      # three dots: since the merge base
```

The **three-dot** form (`base...head`) compares `head` against the *merge base* of the two, which is "what this branch changed." The two-dot form (`base..head`) compares the two tips, so changes that landed on `base` after you branched show up as if you had *reverted* them. Using the wrong one produces a changed-file list that includes other people's work.

The test `test_git_diff_integration` builds a repository with services `api` and `web`, branches, modifies `web`, and asserts the changed list is exactly `["services/web/w.py"]` and the affected set is `["web"]`.

### The mapping and its three categories

```python
P = {"api": ["services/api/**", "libs/common/**"], "web": ["services/web/**", "libs/common/**"], "docs": ["docs/**"]}
G = [".github/workflows/**", "pyproject.toml", "Makefile"]      # affects EVERYTHING
```

Test results, one assertion per test:

| Changed file | Affected |
|---|---|
| `services/api/app/main.py` | `api` |
| `libs/common/util.py` | `api`, `web` (shared library fans out to dependents) |
| `Makefile` | `api`, `docs`, `web` (global path) |
| `.github/workflows/ci.yml` | `api`, `docs`, `web` |
| `README.md` | nothing |

Three categories of path determine correctness:

1. **Project-local paths:** only that project is affected.
2. **Shared paths:** a library listed under every dependent project. This list is the thing that goes stale: when `web` starts importing `libs/auth` and nobody updates `P`, changes to `auth` stop testing `web`. The failure is silent and appears only when a bug ships. Generate the mapping from the real dependency graph (imports, package manifests) where possible, and add a **periodic full run** (nightly) to catch drift.
3. **Global paths:** CI configuration, root lockfiles, tooling versions. A change here can affect every project, so it triggers all. Forgetting that the *pipeline file itself* is an input is a classic bug.

The empty result for `README.md` is a design decision: no project's tests are affected, but something like a docs build might be. Decide explicitly.

## Glob details that bite

My glob translator treats `*` as "anything except `/`" and `**` as "anything including `/`". The tests pin three behaviours: `a/**/c.txt` matches both `a/c.txt` and `a/b/x/c.txt` (zero or more directories), `src/*.py` does not cross into `src/sub/`, and regex metacharacters in the pattern (`a+b.txt`) are escaped, so `+` is literal. That last test guards against a common bug: building the regex by string replacement leaves `.` and `+` as operators, which silently over-matches. Real platforms have their own rules for `**`, negation (`!`) and case sensitivity; read them rather than assuming mine.

## Fan-out and dynamic matrices

Once you have the affected set, feed it to a matrix: a `plan` job outputs `["api","web"]` as JSON and the test job uses `matrix: project: ${{ fromJSON(needs.plan.outputs.projects) }}`. If the list is empty, a matrix with zero entries is an error in GitHub Actions, so guard the downstream job with `if: needs.plan.outputs.projects != '[]'` (per the docs; verify on your platform). The gate job treats a skipped matrix as success only when the plan says nothing was affected.

## Where monorepo CI goes wrong

- **Shallow clones.** `actions/checkout` fetches one commit by default (`fetch-depth: 1`), so `git diff base...HEAD` fails or lies because the base commit is missing. Fetch enough history (`fetch-depth: 0` or fetch the base explicitly).
- **Base selection.** For a pull request the base is the target branch's merge base; for a push to `main` it is the previous commit or the last green deployment. Choosing "the previous commit" misses a change when the previous push failed: the broken project stops being rechecked once an unrelated commit lands after it. Use "last successfully built commit" for main.
- **Squash and rebase.** The merge base changes after a rebase; recompute rather than caching a file list.
- **Generated and vendored files** that match a project path but should not trigger it.
- **Version bumps** at the root that change every project's dependencies.

## How It Actually Works

`git diff --name-only A...B` first computes the merge base M of A and B (the most recent common ancestor), then lists files whose content differs between M and B. It reads tree objects and compares blob hashes, so it is cheap even in a large repository: unchanged subtrees are skipped by comparing their hashes without descending. Your mapping function is then pure string matching on those paths, so it is easy to unit test exhaustively, unlike the CI platform's own filter. Build tools such as Bazel go further: they hash the *inputs* of each target and skip a target whose input hash matches a cached result, which also catches changes through transitive dependencies without a hand-written path list. The price is that the build system must understand every input, which is why adopting it is a large project.

## Common mistakes

- **Required checks behind `paths:` filters**, blocking merges on "expected" statuses.
- **Two-dot diffs** that mix in other people's changes.
- **Shallow clone** with no history to diff against.
- **A hand-maintained dependency list** that drifts from reality.
- **Forgetting global files** (CI config, root lockfile, toolchain version).
- **Using the previous commit as the base on `main`**, hiding an earlier failure.
- **No periodic full build**, so drift is never noticed.

## Exercise

1. Run `pytest src/test_pathfilter.py -v`. Add a project `mobile` that depends on `libs/common` and a test showing that a change to `libs/common` now selects three projects.
2. Create a repository with two commits on `main` after you branch. Show the difference between `git diff --name-only main..feature` and `main...feature`.
3. Write the gate job for a workflow where the test job is skipped entirely when no project is affected, so that the required check still passes.
4. Describe how you would detect that the hand-written dependency mapping has drifted from the actual imports. Sketch the check.
