---
description: "Threat-modelling a CI/CD pipeline: assets, trust boundaries, twelve attack paths such as injection and cache poisoning, and matching controls."
---

# 01 · Threat-Modelling the Pipeline

A CI/CD system holds the keys to production: deploy credentials, signing keys, access to source and the ability to run arbitrary code on powerful machines. That makes it one of the most valuable targets in an organisation, and its attack surface is unusual because it **executes untrusted input by design**: a pull request is a stranger's code that your system builds and tests. This lesson applies a simple threat-modelling method to a pipeline and connects each threat to a control you can check.

!!! note "What was run, and what wasn't"
    This lesson is mostly analysis. The controls it points to were *built and tested earlier in this course* and re-used here: the workflow linter (17 tests, Level 2 · 10), the secret scanner (12 tests, Level 1 · 08), the Jenkinsfile linter (11 tests, Level 1), and the audit-log chain in Lesson 05. **No attack was carried out against any real system**, and no real vulnerability is demonstrated. Descriptions of attack classes come from public security guidance such as GitHub's security-hardening documentation as I know it (October 2026); verify against current documents. A threat model is a structured argument, not a measurement.

## Step 1: What are you protecting?

List assets and what compromising each would allow:

| Asset | If compromised, an attacker can... |
|---|---|
| Deploy credentials / cloud roles | Change production directly |
| Source repository write access | Insert code that every later build trusts |
| Signing keys / signing identity | Make malicious artifacts look genuine |
| Secrets in the CI system | Reach databases, registries, third-party APIs |
| Build artifacts and caches | Ship tampered binaries without touching source |
| The runners themselves | Pivot into internal networks; persist between jobs |
| Pipeline definitions | Change *what* is checked (turn off the gates) |
| Logs and reports | Leak secrets; hide evidence |

## Step 2: Trust boundaries

Draw where data crosses from less to more trusted:

1. **Contributor → repository** (a fork's pull request, an issue title, a comment).
2. **Repository → runner** (the code and workflow files that execute).
3. **Runner → secret store / cloud** (the credentials a job receives).
4. **Third-party code → your job** (actions, plugins, base images, dependencies).
5. **Build → registry → production** (the artifact's journey).
6. **People → approval** (who may change what, and how that is recorded).

Every threat is a way to move something across a boundary the designers did not intend.

## Step 3: The common attack paths

| # | Threat | How it works | Control (and where in this course) |
|---|---|---|---|
| T1 | **Script injection** | `${{ github.event.pull_request.title }}` is pasted into a `run:` script; the title contains shell commands | Pass via `env:`; linter rule W005 (Level 2 · 10) |
| T2 | **"Pwn request"** | A `pull_request_target` workflow (privileged) checks out and runs the PR's code | No head checkout in privileged triggers; linter rule W002 |
| T3 | **Unpinned third-party action** | A tag is moved to a malicious commit; every pipeline using `@v4` runs it | Pin to full SHA; linter rule W003; update bot (Level 3 · 08) |
| T4 | **Over-broad token** | The default token can write contents; a compromised step pushes code | Least-privilege `permissions:`; linter rule W001 |
| T5 | **Secret exposure** | Secret echoed to logs, written into an artifact, or committed | Masking, scanner (Level 1 · 08), short-lived OIDC credentials |
| T6 | **Cache poisoning** | An untrusted run writes a cache that a privileged run restores | Separate scopes; no cache restore in release builds (Level 2 · 02) |
| T7 | **Persistent runner compromise** | Malware left on a reused self-hosted runner reads the next job's secrets | Ephemeral runners, isolation (Level 2 · 08) |
| T8 | **Dependency compromise** | A malicious package version is pulled in | Lockfiles with hashes, review, scanning (Level 3 · 08) |
| T9 | **Pipeline tampering** | An attacker with write access edits the workflow to skip tests or exfiltrate | Protected branches, CODEOWNERS on pipeline files, required reviews |
| T10 | **Artifact tampering** | The package in the registry is replaced after the build | Signing and verification at deploy; digests |
| T11 | **Approval abuse** | Self-approval, or a reviewer who rubber-stamps | Prevent self-review; audit trail (Lesson 05) |
| T12 | **Insider with legitimate access** | A trusted engineer misuses access | Separation of duties, logging, anomaly review |

### Reading T1 and T2 closely

T1 is a code-injection bug of the classic kind: untrusted data becomes part of a program. The workflow engine substitutes the expression into the script text *before* the shell parses it, so quoting inside the script cannot help. T2 combines two properties that should never meet: **privilege** (secrets and a write token, which `pull_request_target` provides) and **untrusted code** (the PR head). Each property is fine alone: unprivileged PR builds run fork code safely because they get no secrets (that is the point of the default `pull_request` trigger for forks), and privileged workflows are safe if they only run code already on the base branch. The linter encodes exactly those two rules, and I tested them in both directions.

## Step 4: Rank and decide

Not every threat deserves equal effort. Score each by likelihood (is the attacker's step cheap? is the target reachable?) and impact (what does it unlock?). A reasonable ordering for a typical public GitHub project: T1/T2 (cheap, high impact), T3 and T8 (supply chain, widely exploited), T4 and T5 (limit blast radius), T6/T7 (depends on runner choices), then the rest. For a private monorepo with no outside contributors the weights shift toward T9, T11 and T12: the likely adversary is a compromised account or an insider.

Write down accepted risks with an owner and review date. "We know the self-hosted runner is persistent; accepted until Q2; mitigated by network isolation" is a decision. A silent gap is not.

## Step 5: Turn controls into checks

A control that depends on people remembering will fail. Put it in the pipeline:

- Lint workflow files on every change to `.github/workflows/` (the Level 2 linter, with exit status 1 on findings).
- Run the secret scanner on every push and on history periodically.
- Require CODEOWNERS approval for pipeline files, and protect the branches those workflows run on.
- Alert on changes to org-level settings: new secrets, new runners, new third-party app installations.
- Run a periodic **clean-room rebuild** of a release and compare outputs (Level 1 · 06 showed why determinism makes that possible).

Then test the controls: deliberately introduce a bad workflow in a sandbox repository and confirm the lint fails, the review is required and the alert fires. An untested control is a hope.

## What the tools in this course do not cover

The workflow linter reads YAML text; it cannot see that a script downloaded in a step is malicious, that a legitimate action has a vulnerability, or that a maintainer's account was taken over. The secret scanner uses patterns, so it misses secrets with unusual shapes. Neither addresses Jenkins plugin vulnerabilities, runner OS patching, network egress control, or what a legitimately privileged person might do. A threat model is the document that says which of those you have decided to handle, and how.

## How It Actually Works

Threat modelling works by forcing you to enumerate *flows* and ask "what if the data on this flow is hostile?" at each trust boundary, rather than listing vulnerabilities you already know. In a pipeline, the flows are unusually rich because the build system is a general-purpose code executor wired to credentials. The structural defence is **privilege separation by trigger and environment**: untrusted events run in unprivileged contexts with no secrets; privileged contexts run only code that has passed review; the highest-privilege step (deploy, sign) runs in a protected environment that releases credentials only after policy checks. Almost every control in the table is an application of that single idea, enforced by the CI platform or by checks like the linters.

## Common mistakes

- **Listing tools instead of flows**, and missing the boundary that matters.
- **Treating CI as "internal"** and not as a high-value target.
- **Giving every job the same broad credentials.**
- **Controls that need people to remember**, not automated checks.
- **No test that the controls work.**
- **Modelling once** and never revisiting after adding a runner, an integration or a new trigger.
- **Accepting risks silently** without an owner or date.

## Exercise

1. Draw the data-flow diagram for a pipeline you operate, marking the six trust boundaries. Which boundary has the fewest controls?
2. Run `python3 src/wflint.py` on your real workflows. Map each finding to T1–T12 and decide fix, accept or suppress.
3. For T6 (cache poisoning) write the precise conditions under which your own pipeline would be vulnerable, and one test that would show it.
4. Pick two threats you would accept for an internal-only repository and write the acceptance statements with owner and review date.
