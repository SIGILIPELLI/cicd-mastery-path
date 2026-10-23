---
description: "Reusable workflows, composite actions and Jenkins shared libraries: contracts, inputs and outputs, versioning, and when sharing hurts, with YAML parsed."
---

# 03 · Reusable Pipelines: Workflows, Actions & Shared Libraries

Fifteen repositories with fifteen copies of the same 80-line workflow means fifteen places to fix the next security patch. Sharing pipeline logic is the CI equivalent of extracting a function, and it has the same trade-offs: one fix reaches everybody, and one mistake breaks everybody.

!!! note "What was run"
    I parsed a small reusable-workflow file with PyYAML to check its structure (the output is shown). **No workflow was executed on GitHub**, and no Jenkins shared library was run. The semantics of `workflow_call`, `uses:` and composite actions come from docs.github.com (October 2026); Jenkins shared libraries from jenkins.io. The syntax shown is therefore documentation-derived and untested.

## Three kinds of reuse on GitHub Actions

| Mechanism | Granularity | Defined in | Called with |
|---|---|---|---|
| **Reusable workflow** | A whole job or several jobs | A workflow file with `on: workflow_call` | `jobs.<id>.uses: owner/repo/.github/workflows/x.yml@ref` |
| **Composite action** | A sequence of *steps* inside one job | `action.yml` with `runs: using: composite` | `steps[*].uses: owner/repo/path@ref` |
| **Template / generator** | Whole repo or file | Anywhere | Copy at creation time (no live link) |

Pick by what is shared. If the shared unit needs its own runner, permissions or matrix, it is a **reusable workflow**: the caller delegates a *job*. If it is "set up Python, restore the cache, install", it is a **composite action**: it runs as steps within the caller's job, on the caller's runner, sharing its filesystem.

## The contract of a reusable workflow

A reusable workflow declares its interface under `on.workflow_call`. Parsing a sample with PyYAML printed:

```text
sections: ['inputs', 'outputs', 'secrets']   inputs: ['python-version']
secrets: ['deploy-token']   outputs: ['artifact-name']   jobs: ['build']
```

and shows the YAML 1.1 trap from Level 1 again: the top-level `on` key is read as the boolean `True`, so the code that found it had to look up `d[True]`. Tools that read workflow files (like this course's linter, Lesson 10) must handle that.

The interface is a typed contract:

- **inputs** are plain values (`string`, `boolean`, `number`); they are not secret.
- **secrets** are passed explicitly (`secrets: {deploy-token: ${{ secrets.X }}}`) or all at once with `secrets: inherit`. Prefer explicit: `inherit` hands the callee every secret the caller can see.
- **outputs** map to job outputs, which map to step outputs written to `$GITHUB_OUTPUT`, a three-link chain that people routinely break by skipping a link.

A caller treats the callee like a function: it passes inputs, reads outputs, and cannot see inside. Per the documentation, reusable workflows can be nested to a limited depth and a workflow can call a limited number of others; check the current limits before designing a deep hierarchy.

## Versioning is the whole game

`uses: org/ci/.github/workflows/build.yml@main` means every caller picks up the newest commit of that file on its *next run*. That is convenient for the platform team and dangerous for everyone else: a bad merge to `main` breaks all repositories at once, and you cannot reproduce last Tuesday's build because the pipeline logic changed underneath it.

A sane policy:

- Callers pin to a **tag or a full SHA** (a SHA is the only immutable form; tags can be moved, as the linter's W003 rule flags).
- The platform team publishes **versioned releases** (`v3.2.0`), keeps a moving major tag (`v3`) only for low-risk consumers, and documents breaking changes.
- Changes to the shared workflow are tested in a **canary repository** or against a matrix of representative callers before a tag moves.
- Inputs are **additive**: new optional inputs with defaults do not break existing callers; renaming or removing one does.

## Jenkins shared libraries

Jenkins' equivalent is a **shared library**: a Git repository with `vars/` (global steps callable from any Jenkinsfile, such as `buildApp(...)`) and `src/` (classes), loaded by `@Library('name@version') _`. The same lessons apply, and Jenkins adds its own risk: library code runs on the controller with Groovy sandbox rules unless the library is marked trusted, and a trusted library can do anything the controller can. Pin the version (`@v3`) rather than a branch, and keep libraries small, tested functions, not a framework.

## When sharing hurts

- **Premature abstraction.** Two repositories with similar-looking workflows may diverge next quarter; one shared workflow with twenty `if:` inputs is harder to read than two files.
- **Debugging across a boundary.** An error in a reusable workflow shows the callee's steps in the caller's run, but fixing it means a change, review, release and re-pin in another repository.
- **Hidden permissions.** A callee can use at most the permissions the caller grants it, but a caller who grants `contents: write` to a workflow it has not read has delegated trust; read what you call.
- **Blast radius.** A shared deploy workflow that gets a permissive change is a network-wide incident (Level 4 · 05 covers audit and change control).

A rule of thumb that has held up: share after the **third** copy, share the *boring* parts (set up, build, publish) rather than the decisions (what to deploy, when), and make the interface small.

## Checklist

- The callee's inputs, secrets and outputs are documented next to the workflow.
- Callers pin a tag or SHA, never a branch.
- The platform team has a canary repository for testing changes.
- New inputs are optional with defaults; removals go through deprecation.
- Secrets are passed explicitly, not with blanket inheritance.
- There is a policy for how many versions are supported at once.
- A test or example caller exists for every reusable workflow.
- Composite actions are used for step sequences and reusable workflows for whole jobs.
- Failures in shared code name the callee and its version in the log.

## How It Actually Works

When a workflow run starts, the service resolves each `uses:` reference to a commit in the other repository, reads that file at that commit, and *inlines* it into the run as additional jobs, wiring inputs, secrets and outputs between them. The callee's jobs appear under the caller's job name in the UI and count against the caller's concurrency and billing. A composite action is simpler: its steps are expanded into the caller's job at execution time and run sequentially on the same runner, which is why a composite action can modify files the next step sees, and a reusable workflow cannot (it runs on a different runner; pass files as artifacts, Lesson 07 in Level 1).

Access to the callee is checked at resolution: a private repository's workflow can be reused by other repositories only if its sharing settings allow it. This is why a "works in the platform repo, fails in the product repo" error is often a permission setting, not a YAML bug.

## Common mistakes

- **Referencing `@main`** and being surprised when old commits stop building.
- **`secrets: inherit` everywhere**, over-sharing credentials.
- **Reusable workflow where a composite action fits** (and the reverse), then fighting runner or file-sharing limits.
- **Breaking the interface** by renaming an input without a deprecation period.
- **Forgetting a link in the output chain** (step output, job output, workflow output).
- **No tests for the shared logic**, so a bug ships to every consumer at once.
- **Sharing decisions instead of mechanics**, until every team needs a special case.

## Exercise

1. Write a reusable workflow `build.yml` with one required and one optional input and one output, parse it with PyYAML, and list its contract as the sample did. Where is the `on` key?
2. Write a composite action that sets up Python and installs from a lockfile. State two things it can do that a reusable workflow cannot, and two that it cannot do.
3. Draft a versioning policy for a platform team supporting 20 repositories: tags, canary, deprecation notice, and the rollback procedure when `v3.2.0` is bad.
4. Take two similar workflows in repositories you know. Would you share them today? Write the argument for waiting.
