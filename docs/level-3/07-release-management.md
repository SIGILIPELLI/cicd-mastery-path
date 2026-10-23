---
description: "Release management: semantic versioning, Conventional Commits, changelogs, release branches, hotfixes and release trains, with a tested version-bump tool."
---

# 07 · Release Management: Versions, Changelogs & Trains

Continuous delivery does not remove the need to say *what* is in a release and *how it relates to the previous one*. Consumers of a library need to know whether an upgrade can break them; operators need to know what changed before an incident; auditors need to match running software to source. Versioning and release notes are the interface between the people who ship software and those who depend on it.

!!! note "What was run"
    The version-bump logic in `src/semrel.py` and its 12 pytest tests were written and run here. Convention details (Semantic Versioning, Conventional Commits) are as I understand their public specifications; I treated the rules as conventions and did not fetch the specifications for this lesson, so read them before relying on edge cases. No release was published.

## Semantic Versioning in one paragraph

A version `MAJOR.MINOR.PATCH` communicates compatibility. Increment **MAJOR** for incompatible changes to the public interface, **MINOR** for backward-compatible new functionality, **PATCH** for backward-compatible fixes. The scheme only works if the project defines its "public interface" and is honest about breakage. Versions below `1.0.0` are conventionally "anything may change"; many projects bump MINOR for breaking changes in that range, which is the choice my tool makes. Applications (as opposed to libraries) often use calendar versions (`2026.10.3`) or build numbers because "compatibility" is not meaningful to their users.

## Conventional Commits: machine-readable history

If every commit message has a predictable header, a tool can decide the next version and write the changelog:

```text
fix: handle empty input                 -> PATCH
feat(api): add export                   -> MINOR
feat!: drop python 3.8                  -> MAJOR   (the ! marks a breaking change)
refactor: x
  BREAKING CHANGE: removes --old flag   -> MAJOR   (footer)
chore: / docs: / test: / ci:            -> no release
```

`semrel.py` classifies messages with a header regex plus a check for a `BREAKING CHANGE:` footer line, and takes the highest level among commits since the last release. Test results:

```text
['fix: handle empty input', 'feat(api): add export', 'chore: bump deps', 'docs: typo']
  classified: patch, minor, none, none      next from 1.4.2 -> 1.5.0
adding 'feat!: drop v1'                     next from 1.4.2 -> 2.0.0   (MINOR/PATCH reset)
'feat!: x' at 0.3.1                         -> 0.4.0                   (pre-1.0 convention)
'fix: BREAKING CHANGE: is mentioned in text' -> patch                  (not a footer, so not breaking)
'fixed some stuff'                          -> none                    (unparseable, ignored)
```

The last two lines show the design's weakness and a safeguard: a message that does not follow the format is **silently ignored**, so a sloppy commit that breaks the API produces no major bump. Conventions are only as reliable as their enforcement: lint commit messages (or PR titles, if you squash-merge) in CI, and let a human override the computed version in the release PR. Note also that the *tool decides from messages, not from the code*: it cannot tell that a "fix" changed behaviour callers depended on. For libraries, supplement with API-compatibility checks and tests that pin the public interface.

## Changelogs for humans

A changelog is a curated list of notable changes by version, grouped (Added, Changed, Fixed, Removed, Security), written for the *reader*, not copied from commit messages. Generated drafts from commit history are a good start, but "refactor: split handler" is noise for users and "fix: crash on empty cart" should say what a customer would see. Always call out: breaking changes with migration steps, deprecations with the removal date, and security fixes.

## Branching models for releases

| Model | Idea | Fits |
|---|---|---|
| **Trunk-based** | Everyone integrates to `main` daily; releases are tags on `main`; unfinished work is hidden by flags (Lesson 02) | Services deployed often |
| **Release branches** | Cut `release/1.5` from `main`; only fixes go there; `main` moves on | Products that must support several versions |
| **Gitflow-style** | Long-lived `develop` plus feature, release and hotfix branches | Slower, scheduled releases; carries heavy merge overhead |

Whatever the model, the rule is the same: **a release is a specific commit, tagged, built once, and that artifact is promoted** (Level 1 · 07). Tags in Git can be moved or deleted unless protected, so protect release tags and record the commit SHA in the artifact metadata.

### Hotfixes

An urgent production bug needs a fix without shipping unrelated half-finished work. On a release-branch model: branch from the released tag, fix, test, tag a patch release, then **merge or cherry-pick the fix forward** to `main` so it isn't lost in the next release. The usual accident is forgetting the forward port, and the bug returns in the next release. In trunk-based development the hotfix is just a fast commit to `main`, which is easier as long as `main` is always releasable.

## Release trains and cadence

A **release train** ships on a fixed schedule (every Tuesday): whatever is ready goes on, whatever is not waits for the next one. It removes negotiation ("can we squeeze one more thing in?") and makes the process routine and rehearsed. The trade-off is waiting for the train. Many teams combine a train with an escape hatch for emergencies and flag-gated features that can ship dark and turn on later.

## Release checklist as a pipeline

Everything on a release checklist that a script can do should be done by the pipeline: compute the version, generate notes, build, run the full test and security gates, sign (Lesson 08), publish, create the tag, announce. The human steps are the decisions: approve, and for risky releases watch the canary (Lesson 01). A release process that is a wiki page of manual steps will eventually miss one.

## Traceability

Be able to answer, from a running system: which version is this, which commit, which build, which pipeline run, who approved. Embed the version and commit SHA in the artifact (a `/version` endpoint, an image label), emit it in logs and metrics, and keep the release record. In an incident this saves the first twenty minutes.

## Checklist

- Release tags are protected from moving or deletion.
- Commit or PR title format is linted in CI.
- Version and commit are embedded in the artifact and reported at runtime.
- A human can override the computed version in the release pull request.

## How It Actually Works

The version bump is a pure function from `(current version, list of commit messages)` to a new version, which is why it is easy to test exhaustively. The surrounding automation does I/O: read tags to find the previous release, `git log previous..HEAD` to list the commits, compute the version, update version files, write the changelog, commit, tag and push. Each of those has failure modes the pure function hides: a missing previous tag (first release), a merge commit history that makes `git log` ordering confusing, concurrent releases on two branches both computing `1.5.0`, and a push that succeeds for the commit and fails for the tag. Release tooling should be idempotent: running it again after a partial failure must not create `1.5.1` just because `1.5.0` half-exists.

## Common mistakes

- **Mislabelling a breaking change as minor.**
- **Trusting commit messages blindly** with no lint, so unparseable messages vanish from the release.
- **Auto-generated changelogs published as-is**, full of noise.
- **Forgetting to forward-port a hotfix**, so the bug returns.
- **Moving a tag** after publishing, so two builds share one version.
- **No version embedded** in the artifact or reported at runtime.
- **Manual release steps** that drift from the written checklist.
- **Versioning an application like a library** (or the reverse) without a reason.

## Exercise

1. Run `pytest src/test_semrel.py -v`. Add a type `revert:` handled by the rules and decide what it should do. Write the tests first.
2. Write a CI check that validates each pull request title against the Conventional Commits header regex and gives a helpful error message.
3. For a library you use, read its last three releases and judge whether each version number matched the actual compatibility impact.
4. Design the hotfix procedure for your branching model, with the forward-port step as an explicit checklist item.
