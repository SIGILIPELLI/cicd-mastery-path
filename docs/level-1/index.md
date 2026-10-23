---
description: "CI/CD Level 1: what CI/CD is, pipeline anatomy, GitHub Actions and Jenkins, testing gates, caching, artifacts, secrets and a local CI runner."
---

# Level 1 · Pipeline Foundations

Level 1 builds the mental model: why continuous integration and delivery exist, what a pipeline is made of, how the two dominant systems (GitHub Actions and Jenkins) express the same ideas, how to order testing gates for fast feedback, how reproducible builds and caching work, how artifacts and versions should be handled, how to keep secrets out of trouble, and how branching strategy affects integration. It ends with a small working CI runner.

!!! note "What was run, and what wasn't"
    **No GitHub Actions runner and no Jenkins server were available**, so no workflow or Jenkinsfile was executed by its real system. Their syntax and limits come from official documentation (docs.github.com and jenkins.io, October 2026) and are marked "not run". The concepts are demonstrated with real runs of **`minici`, a local CI runner written for this course** (not a clone of either product), with a Jenkinsfile linter, a secret scanner, and measured experiments
    with `git`, `tar` and `pytest` on macOS. Each lesson says which is which.

**Prerequisites:** basic Git and a programming language. The [GitHub & Git Mastery Path](https://sigilipelli.github.io/github-mastery-path/) covers repositories, pull requests and Actions in more breadth; the [Docker Mastery Path](https://sigilipelli.github.io/docker-mastery-path/) covers containers.

## Modules

1. **[What CI/CD Is](01-what-ci-cd-is.md)**: integration, delivery, deployment, and why pipelines exist.
2. **[Pipeline Anatomy](02-pipeline-anatomy.md)**: triggers, jobs, steps, stages, dependencies, run with a failing job.
3. **[GitHub Actions Essentials](03-github-actions-essentials.md)**: a full workflow, limits, and the YAML `on` gotcha.
4. **[Jenkins Essentials](04-jenkins-essentials.md)**: controller, agents, Declarative Pipeline, a tested linter.
5. **[Testing Gates & Fast Feedback](05-testing-gates.md)**: ordering checks (measured), required checks, flaky tests.
6. **[Reproducible Builds & Caching](06-reproducible-builds-caching.md)**: lockfiles, cache keys, a measured cache hit.
7. **[Artifacts, Registries & Versioning](07-artifacts-versioning.md)**: build once, immutable versions, deterministic archives.
8. **[Secrets in Pipelines](08-secrets-in-pipelines.md)**: leaks, OIDC, a tested secret scanner.
9. **[Branching & Pull Request Checks](09-branching-pr-checks.md)**: a merge that passed both branches and broke main.
10. **[Project: A Local CI Runner](10-project-local-ci-runner.md)**: 15 tests and a cold/warm/failing demo.
