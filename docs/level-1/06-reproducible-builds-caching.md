---
description: "Reproducible builds and caching: pinned inputs, cache keys, hits versus misses, clean builds and the works-the-second-time trap, with measurements."
---

# 06 · Reproducible Builds and Caching

If the same commit built twice gives different results, nobody can trust the pipeline. And if every build downloads the world, nobody will wait for it. This lesson covers the two forces that pull in opposite directions: **reproducibility** (be exact about inputs) and **speed** (don't redo work), and how caching reconciles them when keyed correctly.

!!! note "What was run"
    The cache experiment ran on `minici` (a local teaching runner); GitHub's and Jenkins's cache mechanisms are described from documentation and were not run. The 10 GB per-repository GitHub cache limit is from the Actions limits page. See Lesson 01.

## What makes a build reproducible

A build is a function: *inputs → artifact*. It is reproducible when the same inputs always give the same output. The inputs people forget:

| Input | How to pin it |
|---|---|
| Source code | The exact commit SHA (CI checks out the triggering commit) |
| Dependencies | **Lockfiles** (`package-lock.json`, `poetry.lock`, `go.sum`, `Cargo.lock`) with exact versions and hashes; install with the lockfile (`npm ci`, `pip install --require-hashes`), not a fresh resolution |
| Toolchain | A pinned version of the compiler/runtime (`setup-python` with an exact version, a container image digest) |
| Base images | `image@sha256:...` digests, not `:latest` |
| Build environment | A clean workspace and container; no reliance on what a previous build left behind |
| Time and randomness | Don't embed timestamps or random IDs in artifacts (or set `SOURCE_DATE_EPOCH`) |
| Network | Fetching "latest" at build time makes the build a function of the internet |

Fully **bit-for-bit reproducible builds** (two machines produce identical bytes) are a stronger goal used for security and supply chain verification (Level 3 · 08); most teams aim first for *repeatable* builds with pinned inputs.

## Caching: reuse without lying

A cache stores the result of expensive work (downloaded dependencies, compiled objects, test fixtures) under a **key**, restoring it on later runs. The danger is a stale cache that silently feeds old inputs to a new build. The discipline: **derive the key from everything the cached content depends on**.

```yaml
# GitHub Actions style (not run here): key from the lockfile's hash, with a restore fallback
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: pip-${{ runner.os }}-${{ hashFiles('requirements.txt') }}
    restore-keys: pip-${{ runner.os }}-
```

When `requirements.txt` changes, the hash changes, the exact key misses, and a new cache is saved; `restore-keys` may restore an older, partially useful cache as a starting point. Keys should include the OS/architecture and tool version when those affect the content.

### Measured with minici

The demo pipeline caches a `libs` directory keyed by the hash of `requirements.txt` (plus the matrix values). Its "install" step takes 2 seconds on a miss. Two consecutive runs:

```text
RUN 1:   deps   success   2.04s   cache=miss      (step output: installed)
RUN 2:   deps   success   0.01s   cache=hit       (step output: restored from cache)
```

The cache turned a 2.04 s step into 0.01 s. The pytest suite for minici also checks the invalidation behaviour: with an unchanged `requirements.txt` the second run is a `hit`, but after changing the file's content the third run is a `miss` again (`test_cache_miss_then_hit`). **A cache that doesn't invalidate when its inputs change is a bug generator.**

## What to cache, and what not to

| Cache | Notes |
|---|---|
| Package manager download caches (pip, npm, Maven, Gradle, cargo) | Key on lockfile hash; the biggest and safest win |
| Compiled outputs (ccache, Gradle build cache, Bazel remote cache) | Content-addressed caches are the most reliable; keys must capture compiler flags and source |
| Docker layers | Order Dockerfile instructions from least to most frequently changing (Linux course, Level 4 · 09) |
| Test data and fixtures | Only if immutable |
| **Do not** cache: secrets, whole build outputs you intend to release, anything whose key you can't state | Release artifacts are built fresh from a clean state, or from a verified cache |

Be aware of limits: GitHub caps cache storage at 10 GB per repository (older entries are evicted), and caches are scoped by branch (a pull request can read the base branch's cache but not siblings'; check the rules for your platform). Cache poisoning is a real attack: a cache written by a low-trust workflow (a fork's pull request) must not be restored by a privileged one (Level 4 · 01).

## Clean builds as a baseline

Always keep a way to build **without** any cache (a manual run or a nightly job with caches disabled). If the clean build is broken but cached builds pass, a stale cache is hiding it. Time the clean build too: it is your worst-case feedback time and your disaster-recovery speed.

## Persistent workspaces (Jenkins) and "works the second time"

Jenkins agents keep workspaces between builds unless you clean them. Leftover files act as an *uncontrolled cache* and cause builds that depend on previous state. Either use `cleanWs()` / `skipDefaultCheckout` thoughtfully, or use ephemeral agents (containers, cloud VMs) so every build starts clean and you opt in to caching explicitly. GitHub-hosted runners are ephemeral by default.

## Checklist

- Tool and dependency versions are pinned, not 'latest'.
- Cache keys include the lockfile hash and the platform.
- A periodic cold build checks that the cache is not hiding a problem.
- The pipeline works, more slowly, when the cache is empty.

## How It Actually Works

A cache service is a key-value store of archives: on a miss the job runs normally and, if it succeeds, uploads the paths under the key; on a hit it downloads and unpacks them before the job's steps. `minici` copies directories into a store named by a 16-hex-digit prefix of a SHA-256 over the matrix values and the contents of the key files, and restores by copying back. Hash-based keys work because equal inputs give equal hashes and
changed inputs give different ones, making invalidation automatic. Saving only on success prevents a failed build from poisoning the cache with partial state (the minici code saves only when the job status is success).

## Common mistakes

- **Install without a lockfile** (`pip install -r` with unpinned names, `npm install` instead of `npm ci`).
- **Cache keys that don't include what the content depends on** (OS, tool version).
- **Caching build outputs you then release.**
- **Never testing a clean build.**
- **Restoring caches across trust boundaries.**
- **Persistent agent workspaces** that hide missing declarations.
- **Treating cache hit rate as the goal** instead of correctness.

## Exercise

1. Add a `cache:` section to a `minici` job for a directory you generate, then change the key file and confirm a miss; record the timings for miss and hit.
2. Find a project of yours without a lockfile and add one; compare a fresh install a month apart to see what changed.
3. Write the cache key you would use for a Maven build with a matrix of two JDK versions on two operating systems.
4. Build the same Docker image twice from scratch and compare the image digests; list the reasons they might differ.
