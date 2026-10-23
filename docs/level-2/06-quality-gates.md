---
description: "Quality gates: coverage, lint and static analysis as merge conditions, why 100% coverage can prove nothing, with a measured weak-test demo."
---

# 06 · Quality Gates: Coverage, Lint & Analysis

A **quality gate** is a check whose failure blocks a merge or a deployment: tests pass, coverage does not drop, lint is clean, no known-vulnerable dependency, no secret in the diff. Gates turn standards into something the machine enforces consistently. They also turn a *number* into a target, and a target people optimise stops being a good measure. This lesson shows that with a demonstration.

!!! note "What was run"
    The coverage demonstration was run on macOS with Python's `coverage` package and `pytest`, on a tiny `shop.py` module (a discount function with a normal and a VIP branch) that I wrote for this purpose. The numbers are from that one toy module; they illustrate the mechanism and say nothing about what coverage levels real projects achieve. Lint, SAST and vulnerability-scanning tools are described from their documentation and were not run here.

## What a coverage number measures

**Line coverage** is the fraction of lines executed during the test run. **Branch coverage** counts whether both outcomes of each `if` were taken. Neither measures whether the tests *check* anything.

The demonstration, step by step:

1. **A weak test** that calls both code paths and asserts nothing. `coverage` reported `shop.py: 6 statements, 0 missed, 4 branches, 0 partial, 100%`. Full line *and* branch coverage.
2. I then **introduced a bug**: the VIP discount factor changed from `0.8` to `0.08` (a customer who should pay 80% now pays 8%).
3. The weak suite **still passed**. A 100%-covered module with a gross pricing error and a green build.
4. A **strong suite** (the same inputs, with assertions on the returned prices) caught it: `1 failed, 2 passed`.
5. The strong suite on the *correct* code also reached 100% branch coverage. So the two suites have identical coverage and opposite value.
6. A **partial** test that exercised only the VIP path reported 40% line / 57% total with branches; useful to see that the report does show *unexecuted* code correctly.

The conclusion is not "coverage is useless". It is exactly this: **coverage finds code that no test touches (a real and valuable signal); it cannot find code that no test checks.** A low number means missing tests; a high number means nothing alone.

Better evidence that tests check behaviour comes from **mutation testing**: automatically make small changes (`>` to `>=`, `0.8` to `0.08`) and check that some test fails. A surviving mutant is a bug your suite would not catch. Mutation testing is slow, so teams run it on changed files or nightly. I did not run a mutation tool; my change in step 2 was a manual mutation.

## How to gate on coverage sensibly

- Gate on the **diff**, not the total: "new and changed lines are at least X% covered" is achievable and meaningful, while a project-wide threshold punishes a 1-line fix in a legacy file.
- Use a **ratchet**: the total may not decrease. It blocks regression without demanding a rewrite.
- Never make 100% a requirement; people write assertion-free tests to satisfy it, which is the weak test above.
- Review the *report*, not just the number: look at which lines are uncovered and whether they matter.
- Configure the tool to fail below the threshold (`coverage report --fail-under=80` returns a non-zero exit status), so the gate is code in the pipeline and not a person's opinion.

## The other gates

| Gate | Catches | Typical false-positive source |
|---|---|---|
| **Formatter check** (`black --check`, `gofmt -l`) | Style drift | None if the formatter is deterministic; fix with auto-format |
| **Linter** (`ruff`, `eslint`) | Unused names, likely bugs | Rules that do not fit your code; tune rather than disable everything |
| **Type checker** (`mypy`, `tsc`) | Interface mismatches | Third-party libraries without types |
| **SAST** (static security analysis) | Injection, unsafe functions | High noise; triage and baseline |
| **Dependency scan** | Known-vulnerable versions | Vulnerabilities in code paths you never call |
| **Secret scan** (Level 1 · 08) | Committed credentials | Test fixtures that look like keys |
| **License check** | Incompatible licenses | Ambiguous metadata |
| **Performance budget** | Slower endpoints, bigger bundles | Noisy shared runners |

Rules for adding a gate: it should be **fast** (feedback in minutes), **deterministic** (same code, same answer), **actionable** (the message says what to change), and **rare to bypass**. A gate that is red for weeks gets muted; a gate with many false positives trains people to ignore the real ones.

### Introducing a gate to an existing codebase

You cannot turn on a linter with 4,000 existing violations. Options: record a **baseline** (existing findings are accepted, only new ones fail), fix by directory over time, or make the gate advisory (report, don't block) for a trial period with a date to enforce. Whichever you choose, write the date down. "Advisory" with no end date is "disabled."

## Gates as code

Policy must live in the repository, versioned like code: `pyproject.toml` or `.coveragerc` for thresholds, a lint config, a workflow file. A gate configured only in a web UI cannot be reviewed, diffed, or reproduced locally. It must also be **runnable locally** with one command (`make check`) that mirrors CI; if a failure can only be reproduced after a push, developers will stop running gates before pushing.

## Checklist

- Coverage is gated on changed lines or as a ratchet, never as a fixed 100% rule.
- Coverage reports list the uncovered lines for reviewers.
- Mutation testing or manual mutation spot-checks are run on critical modules.
- Lint, format and type checks are one local command that mirrors CI.
- New gates start with a baseline of accepted existing findings.
- Advisory gates carry an enforcement date.
- Each gate has an owner and a documented process for false positives.
- Gate results are deterministic: same code, same answer.
- Gates report within minutes, so developers wait for them.
- Dependency and secret scans run on a schedule as well as on pull requests.
- Threshold changes go through review like code changes.
- Suppressions carry a reason and an expiry date.
- Excluded files are listed and reviewed periodically.
- A failing gate message states what to change.
- Teams are trained to read the report, not just the colour.

## How It Actually Works

`coverage` works through Python's tracing hooks: it is notified as each line of the measured code executes and records `(file, line)` pairs (and `(from_line, to_line)` pairs for branches). After the run it compares the set of executed lines against the set of *executable* lines it derives from the bytecode and reports the difference. It never looks at assertions, return values or test names, so a test that calls a function inside `try: ... except: pass` covers it perfectly. The gate itself is just a process exit status: the pipeline step that runs `coverage report --fail-under=80` exits non-zero when the total is below 80, and the CI system marks the step, job and required check as failed. Everything a gate does reduces to that: a command, its exit status, and branch protection that refuses to merge a red required check.

## Common mistakes

- **Treating coverage as a quality score** rather than a map of untested code.
- **A project-wide threshold** that nobody can meet in a legacy file.
- **Assertion-free tests** written to satisfy the number.
- **Gates that only run in CI**, with no local equivalent.
- **Advisory forever**: a gate with no enforcement date.
- **Disabling a failing check** instead of fixing or baselining it.
- **Excluding files from coverage** until the number looks good.
- **Gating on tools that are non-deterministic** (network-dependent scans), which makes merges random.

## Exercise

1. Reproduce the demonstration: write `discount(price, vip)` with two branches, a weak test, and a strong test. Show 100% coverage for both, then mutate a constant and show only the strong test fails.
2. Configure `--fail-under` and confirm that the command exits with status 2 (or whatever your version returns) when the threshold is missed; record it with `echo $?`.
3. For a repository you know, propose a baseline strategy for adding a type checker: what is accepted today, what is enforced from now, and the date.
4. List three gates for a service that handles payments and say what each must never do (be slow, be flaky, produce unactionable messages).
