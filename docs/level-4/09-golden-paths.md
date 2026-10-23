---
description: "Golden paths: a paved road for new services with generated, linted pipelines, refusing unsafe input; templates versus enforcement, with a tested generator."
---

# 09 · Golden Paths: Making the Right Way the Easy Way

If doing the secure, tested, observable thing takes a week of YAML archaeology, teams will skip parts of it. A **golden path** (or paved road) is a supported, opinionated, low-effort way to build and ship a typical service: a template repository or generator that gives you a working pipeline, tests, deploy configuration and monitoring on day one. Teams may leave the path, but the path is so convenient that most don't.

!!! note "What was run"
    `src/goldenpath.py` (8 tests) generates a GitHub Actions workflow for a Python service from a few parameters, and the tests check that the output parses, passes this course's workflow linter with **zero findings**, and that the generator refuses unsafe input. It has not been used on a real platform, the generated workflow has not been run on GitHub, and it covers one language and one deployment style. The adoption and organisational points are general experience, not measurements.

## What belongs on the path

A useful golden path bundles the decisions that every team would otherwise remake (often poorly):

- **Repository layout** and a README with how to run, test and release.
- **A CI workflow** that lints, tests, scans and builds with caching and pinned tools.
- **Deployment pipeline** with environments, approvals and concurrency (Level 2 · 07).
- **Security baseline:** least-privilege token, pinned actions, secret scan, dependency updates.
- **Observability defaults:** health endpoint, structured logs, standard metrics, dashboards, alerts.
- **Operational docs:** a runbook skeleton, an on-call link, ownership metadata.
- **Versioning and release automation** (Level 3 · 07).

The principle: encode *requirements* as defaults so compliance is automatic, and keep the surface for customisation small and explicit.

## A generator that refuses to guess

```python
def generate(service, python="3.12", deploy_env=None, pins=None, timeout=15): ...
```

Design choices, each backed by tests:

1. **Pins are mandatory and must be full SHAs.** The caller supplies `{'actions/checkout': <40 hex>, 'actions/setup-python': <40 hex>}`; a tag like `v4` or a missing entry raises `ValueError`. The generator does not know the right SHAs and will not invent them; a platform team supplies the current approved pins from a central source and updates them with a bot. This keeps a hard-coded stale or wrong pin out of every generated repository.
2. **The generated workflow passes the linter with no findings**, including `permissions:` set to read-only, a timeout on every job, and, when a deploy environment is given, a `needs`, a protected `environment`, and a `concurrency` group with `cancel-in-progress: false` (so a running deploy is never aborted). That test is the contract: *the template cannot drift from the policy without a test failing.* The same linter runs on the generated code that runs on hand-written workflows.
3. **The service name is validated** against `^[a-z][a-z0-9-]{1,40}$`. The name is interpolated into the YAML (workflow name, concurrency group), so a name like `Orders; rm -rf /` would otherwise inject text into a file that later executes. Input to a generator is untrusted input: a test confirms a hostile name is rejected.
4. **Version strings stay strings.** `python="3.10"` is emitted quoted, and a test parses the result to confirm it is the string `3.10` rather than the float `3.1` (the YAML trap from Level 2 · 01).
5. **No deploy job unless asked.** Without a `deploy_env`, only `test` exists.

Generated deploy job (excerpt), as printed by the generator for `deploy_env="production"`:

```yaml
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    timeout-minutes: 15
    environment: production
    concurrency:
      group: deploy-orders-production
      cancel-in-progress: false
```

The SHAs in the test fixtures (`aaaa…`, `bbbb…`) are dummy values and not real commits; a real run needs real pins.

## Templates vs enforcement

A template gives you a good start and then **drifts**: you copy it once, the platform improves it, and your copy stays old. Options:

| Approach | How updates reach teams | Cost |
|---|---|---|
| **Copy-once template** | They don't, unless someone pushes a PR | Cheap to build; drift over time |
| **Template + update bot** | A bot opens PRs when the template changes | Moderate; needs tooling |
| **Thin caller + reusable workflows** | Teams reference a versioned workflow; updating the tag updates behaviour (Level 2 · 03) | Moderate; coupling and version policy |
| **Central policy enforcement** | Org rules require checks regardless of the repo's own files (Lesson 04) | Highest; strongest guarantee |

Typically you combine them: generated callers of reusable workflows (so improvements flow by version bump), plus org-level required checks for the non-negotiable controls.

## Adoption is the hard part

A golden path nobody uses is a documentation project. What makes teams adopt it:

- **It is genuinely faster.** A new service reaches "deployed to staging with CI" in an hour, not a week. Measure that time.
- **It is built with its users**, not for them: pilot with two teams, take their pain seriously.
- **Escape hatches exist** and are documented. Teams with unusual needs deviate; the path should make deviations visible (a tag in metadata) rather than forbidden, with the platform team learning from what they need. If too many teams need the same deviation, the path should grow.
- **Support is real**: a channel, response times, office hours, a roadmap.
- **Value is visible**: free dashboards, automatic dependency updates and security scanning that teams would otherwise maintain themselves.

Measure adoption (share of services on the path), the time to first deploy, lead time and change failure rate by path vs off-path (Level 3 · 09), and satisfaction. If services on the path do not deploy faster or fail less, the path is not working; you need that to be a finding, not an assumption.

## Anti-patterns

- **Mandated, unusable paths** that make teams hide their real workflow elsewhere.
- **Platform team as bottleneck**: every change needs a ticket to them.
- **Too many options**, which is just a framework with a new name.
- **A template with secrets or environment-specific values** baked in.
- **No versioning or deprecation policy** (Level 2 · 03).
- **Treating the path as finished.** Languages, runners and threats move; the path needs a maintainer and a roadmap.

## How It Actually Works

The generator is string construction guarded by validation, which sounds trivial and is the whole design: the *tests* are what make it a policy instrument. By running the generated YAML through the same linter that reviews hand-written workflows, any change to the template that violates a rule (removing the timeout, loosening permissions) fails in the platform team's CI before it reaches a single service. This turns an organisational standard from a document people may or may not read into an executable specification: the standard is what the tests accept. The same pattern scales beyond workflows: generated infrastructure modules verified by the plan guard (Level 3 · 05), service templates verified by a conformance suite, and so on.

## Common mistakes

- **Letting the generator guess unsafe values** (default pins, default tags).
- **Unvalidated input interpolated into generated files.**
- **No test tying the template to the policy.**
- **Copy-once templates with no update path.**
- **Forbidding escape hatches** instead of making them visible.
- **Not measuring adoption or outcomes.**
- **No owner or roadmap** for the path.

## Exercise

1. Run `pytest src/test_goldenpath.py -v`. Add a `node` option producing a Node workflow, and make sure the linter still finds nothing. What tests do you add?
2. Add a parameter `matrix_python=["3.11","3.12"]` and test that the output has the right job count and quoted versions.
3. Design the update strategy: how does a security fix to the template reach 80 existing services?
4. Define three metrics for the golden path's success and how you would collect them.
