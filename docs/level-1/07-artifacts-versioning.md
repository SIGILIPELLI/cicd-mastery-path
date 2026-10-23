---
description: "Artifacts and versioning: build once and promote, naming and metadata, checksums, retention, and why gzip headers break byte-identical builds."
---

# 07 · Artifacts, Registries and Versioning

The product of a pipeline is an **artifact**: a versioned, immutable package (a tarball, a wheel, a JAR, a container image, a binary) that can be tested, stored, promoted and deployed. Treating the artifact as the unit of delivery, rather than "the code at some commit", is what makes deployments repeatable and rollbacks possible.

!!! note "What was run"
    The tar/gzip hashing experiment ran on macOS with `tar` and Python's `tarfile`/`gzip`. GitHub, Jenkins and registry behaviours are described from documentation and were not run. See Lesson 01.

## Build once, promote the same artifact

```text
commit ──► build ──► artifact v1.4.7 (digest sha256:ab12…) ──► store in registry
                                   │
                                   ├──► deploy to staging  ──► tests pass
                                   └──► deploy the SAME digest to production
```

If you rebuild for production, you deploy something you never tested: a different timestamp, a newer dependency, a different compiler. The rule: **one build, one artifact, promoted through environments by changing configuration, not code**. Environment-specific settings come from configuration at deploy/run time (environment variables, config files, secret stores), not from the artifact.

## Where artifacts live

| Kind | Examples | Notes |
|---|---|---|
| Pipeline artifact storage | GitHub upload/download artifact actions; Jenkins `archiveArtifacts` | Short-lived outputs for passing files between jobs or downloading; retention is configurable and storage-limited by plan |
| Language package registries | PyPI, npm, Maven Central, crates.io; private mirrors (Artifactory, Nexus, GitHub Packages) | Versioned packages for libraries |
| Container registries | Docker Hub, GHCR, ECR, GCR, ACR, Harbor | Images addressed by tag **and digest** |
| Generic object storage | S3/GCS buckets with checksums | Binaries, installers, release bundles |

Use a **private registry** for anything internal, and mirror public dependencies so a public outage or removal does not break your builds (the left-pad incident style failure).

## Versioning

**Semantic Versioning** (`MAJOR.MINOR.PATCH`): increment MAJOR for incompatible API changes, MINOR for backward-compatible features, PATCH for backward-compatible fixes; pre-release suffixes (`1.5.0-rc.1`) sort before the release. It is a communication contract, only as good as the discipline behind it. Alternatives: calendar versioning (`2026.10.3`) for applications released on a cadence; build-number versions (`1.4.${BUILD_NUMBER}`
as in the Jenkinsfile in Lesson 04) for internal services where every build is deployable.

Rules that avoid pain:

1. **Versions are immutable.** Never overwrite `1.4.7` with different bytes. Registries that allow re-pushing a tag break everyone who pinned it.
2. **Never deploy `latest`.** It names no particular build, so you can't reproduce, audit or roll back to it.
3. **Pin by digest where you can.** A tag is a movable pointer; a digest (`sha256:…`) identifies exact content.
4. **Embed the commit SHA** in the artifact (a `VERSION`/build-info file, an image label, a `--version` flag) so any running instance can be traced back to its source.
5. **Generate the version in the pipeline** (from a tag, or from the last tag plus commits since), not by hand-editing files.
6. **Tag releases in Git** so the source for every artifact exists.

## Checksums and reproducibility, measured

Publishing a checksum lets anyone verify an artifact. But a checksum is only useful for *comparison* if builds are deterministic. I tested it on a tiny directory (`app/main.py`, `app/VERSION`), building a `tar.gz` twice with a pause and a file `touch` in between (no content change):

```text
naive `tar -czf`, built twice:                     a613c133c0ce0ada  vs  9cdda689482d86ca   → DIFFERENT
tar with sorted entries, mtime 0, owner 0 (Python), gzip header still records the output FILE NAME:
                                                   e4bee4d6f5449447  vs  e9d64d71c06c138f   → DIFFERENT
same, with the gzip filename field blanked:         8c946b8cf6b5a134  vs  8c946b8cf6b5a134   → identical
after a real content change (VERSION edited):       a different hash, as it should be
```

Three separate sources of non-determinism, found one at a time: file **modification times** and ownership stored in the tar headers, entry **ordering** (I sorted), and, the one I did not expect, the **output file name stored in the gzip header** (my first "deterministic" attempt still differed, because I wrote `d1.tar.gz` and `d2.tar.gz`, and gzip recorded those names). The working recipe is in `src/deterministic_tar.py`: sorted entries, fixed mtime/owner/mode, gzip with `mtime=0` and an empty filename. Real
ecosystems have the same problems at larger scale (embedded build timestamps, absolute paths, parallel compilation order, locale), which is why the "reproducible builds" project exists and why `SOURCE_DATE_EPOCH` is a convention for setting a fixed build time. For container images, the equivalent is pinning base image digests and avoiding timestamps in layers; tools such as Bazel, Nix and ko are built around it.

## Metadata that should travel with an artifact

Version and commit SHA; build time and the pipeline run URL; the digest/checksum; the list of dependencies (an SBOM; Level 3 · 08); test results and scan reports (attached to the build); and a signature or provenance attestation (Level 3 · 08). With these, you can answer in minutes: *what exactly is running in production, where did it come from, what is in it, and is it affected by this vulnerability?*

## Retention and cost

Artifacts consume storage. Set retention: keep release artifacts indefinitely (or per your compliance requirement), build artifacts for a short period, and purge failed-build outputs quickly. Container registries need garbage collection of untagged images. Cache and artifact storage are both billed or limited on hosted CI plans (Lesson 03's limits table).

## Checklist

- Each build produces one artifact, identified by version and digest.
- The artifact is built once and promoted, never rebuilt per environment.
- The commit SHA and build ID travel with the artifact as metadata.
- Retention keeps at least the current and previous release.

## How It Actually Works

An artifact upload is a content store with a name: the CI system stores the files (often compressed) keyed by run ID and artifact name, and a download action fetches them into another job's clean workspace. A container registry stores image layers and a manifest by content digest; a tag is merely a mutable name pointing at a manifest digest, which is why `:v1.4.7` can be moved but `@sha256:…` cannot. Deterministic artifacts matter because
every system that wants to say "these are the same bytes" (caches, signature verification, deduplication, rollbacks) compares hashes.

## Common mistakes

- **Rebuilding per environment.**
- **Deploying `latest`** or mutable tags.
- **Re-pushing an existing version with new bytes.**
- **No traceability** from running software to commit and build.
- **Embedding timestamps and absolute paths** (non-reproducible).
- **Unlimited artifact retention** (storage limits and cost) or too short retention for releases.
- **Treating artifacts and configuration as one**, so a config change requires a rebuild.

## Exercise

1. Build a `tar.gz` of a directory in your project twice and compare hashes; then make the build deterministic using the recipe above (or your language's tooling).
2. Add a step to a `minici` pipeline that writes `VERSION` with `1.0.${commit}` and includes it in the artifact; show where you would read it at run time.
3. Pick a container image you deploy; find its digest and rewrite the deployment reference to use it. What changes in your update process?
4. Write a one-paragraph versioning policy for a service and a library you own: scheme, tagging, immutability rules, and who may publish.
