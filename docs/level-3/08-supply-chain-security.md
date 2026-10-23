---
description: "Supply-chain security for builds: dependency pinning and hashes, checksums, SBOMs, signing, provenance and trusting your build system, with a tamper demo."
---

# 08 · Supply-Chain Security for Pipelines

Your software is mostly other people's code: libraries, base images, build tools, CI actions. A **supply-chain attack** compromises one of those inputs, or the build process itself, so that malicious code reaches your users with your signature on it. The attack surface is the whole path from source to running artifact; this lesson covers what a pipeline can do to shrink it.

!!! note "What was run, and what wasn't"
    I ran one local demonstration: computing a SHA-256 checksum of an archive, verifying it, tampering with the file and verifying again. I did **not** run signing tools (Sigstore/cosign, GPG), generate an SBOM, produce provenance attestations, or scan dependencies. Descriptions of those tools, and of frameworks such as SLSA, are from general knowledge and public documentation as I know it; check their current docs. Nothing here substitutes for a security assessment.

## Where attacks enter

| Entry point | Example | Defence |
|---|---|---|
| **Direct dependency** | A maintainer account is taken over and a new version ships malware | Pin versions, review updates, use lockfiles with hashes |
| **Transitive dependency** | A library of a library is compromised | SBOM, scanning, fewer dependencies |
| **Typosquatting / dependency confusion** | A public package with the same name as your private one wins resolution | Scoped/namespaced registries, explicit index config |
| **Base image or tool** | A mutable tag now points to a different image | Pin by digest |
| **CI action or plugin** | A tag on a third-party action is moved to malicious code | Pin to a commit SHA (Lesson 10's rule W003) |
| **Build system** | A compromised runner or poisoned cache injects code into your artifact | Ephemeral runners, isolated builds, provenance |
| **Your own pipeline** | A pull request exploits script injection to steal secrets | Hardening (Level 4 · 01) |
| **Distribution** | Someone swaps the artifact on the download server or registry | Checksums, signatures |

## Integrity: checksums and pins

A checksum binds a name to **content**. The demonstration:

```text
$ shasum -a 256 app.tar > SHA256SUMS
2a02380a339b...baf7a  app.tar
$ shasum -a 256 -c SHA256SUMS
app.tar: OK
(change one line inside app.py, rebuild the tar)
$ shasum -a 256 -c SHA256SUMS
app.tar: FAILED
shasum: WARNING: 1 computed checksum did NOT match        (exit status 1)
```

Any change to the content, even adding `; import os` to one line, changes the digest, and the check fails with a **non-zero exit status**, which is what makes it usable as a pipeline gate. Two limits are crucial. First, a checksum stored *next to* the file proves only that the download was not corrupted; an attacker who can replace the file can replace the checksum. It must come over a different trusted channel, or be a **signature** by a key the attacker lacks. Second, a checksum identifies content but not *who built it* or *from what*; that is provenance.

For dependencies, the package managers support this directly: pip's hash-checking mode (`--require-hashes`) refuses packages whose digest is not in your requirements file, and lockfiles in npm, Cargo, Go (`go.sum`) and others record hashes. The trade-off is maintenance: updates mean regenerating hashes, which is why a bot that opens update pull requests (with tests and changelog links) is the practical way to stay both pinned and current. I did not run pip's hash mode here.

## Pin everything that executes

- **Dependencies**: lockfile, committed, with hashes where the tool supports them.
- **Base images**: by digest (`image@sha256:...`), updated by a bot.
- **CI actions and plugins**: by full commit SHA. A tag can be re-pointed; a SHA cannot.
- **Tools downloaded in scripts**: version plus checksum. `curl https://x | sh` runs whatever the server says today.

Pinning protects against *silent change*, not against a malicious version you deliberately adopt, which is why review of updates and scanning still matter. It also freezes security fixes unless you keep updating; "pinned" must not mean "forgotten".

## Know what you ship: SBOM and scanning

A **Software Bill of Materials** lists the components in an artifact (name, version, hash, licence), commonly in SPDX or CycloneDX formats. Generating one in the pipeline gives you an answer to "are we affected by vulnerability X?" in minutes instead of days: search the SBOMs. Vulnerability scanners match components against advisory databases. Caveats: scanner output is noisy (a vulnerable function you never call), version matching is imperfect, and a clean scan means *no known* issues, not no issues. Triage by reachability and severity, and set a fixed time budget for fixing critical findings.

## Provenance and signing

**Signing** proves an artifact was produced by a holder of a key. **Provenance** is a signed statement of *how* an artifact was built: which source commit, which builder, which inputs. Frameworks like SLSA describe levels of assurance, from "provenance exists" up to "built on a hardened, isolated, non-forgeable builder." Tools such as Sigstore's cosign support **keyless signing**, where the builder authenticates with its CI identity (OIDC) and gets a short-lived certificate recorded in a transparency log, so no long-lived signing key can leak. The value is in the *verification* step: the deploy system must refuse artifacts whose signature or provenance doesn't match policy (built from the main branch of this repository, on our CI). Signing without enforced verification is decoration.

## The build system is the trust root

Everything above assumes the thing that signs is honest. If the build environment is compromised, it signs malware. Defences from Level 2 matter here: ephemeral isolated runners, no shared persistent state between untrusted and trusted builds, no cache poisoning from pull requests, minimal credentials, and **hermetic** builds that do not fetch arbitrary network resources at build time. A reproducible build (Level 1 · 06: identical output for identical inputs; I measured the gzip filename quirk in that lesson) lets a second independent builder verify the first, turning "trust the builder" into "check the builder".

## A practical order of work

1. Lockfiles and pinned base images and actions (cheap, high value).
2. Secret scanning and least-privilege tokens (Level 1 · 08).
3. Dependency update bot with required tests.
4. SBOM generation and vulnerability scanning with an agreed response time.
5. Signing and enforced verification at deploy time.
6. Provenance and a hardened builder, for software with high stakes.

## Checklist

- Lockfiles are committed and, where supported, include hashes.

## How It Actually Works

A cryptographic hash such as SHA-256 maps any input to a fixed 256-bit digest such that finding two inputs with the same digest, or an input for a given digest, is computationally infeasible. That makes the digest a content-addressed name: pinning to it means "exactly these bytes." Signatures add authenticity: the signer uses a private key to sign the digest, and anyone with the public key (or a certificate chain to a trusted root) verifies it. A signature over a digest therefore authenticates the whole artifact transitively. Provenance is a signed document whose subject is the artifact digest and whose predicate lists the build inputs; verification checks the signature and then that the predicate satisfies policy. Every mechanism rests on a root of trust you must decide on: the registry, the CI identity provider, or the keys.

## Common mistakes

- **Checksum next to the download**, which proves nothing about tampering.
- **Pinning by mutable tag** (`@v4`, `:latest`) and calling it pinned.
- **Pinning and never updating**, accumulating known vulnerabilities.
- **Generating SBOMs nobody queries.**
- **Signing without verifying** at deploy time.
- **`curl | sh`** in build scripts.
- **Trusting any CI-signed artifact**, including those built from pull-request branches.
- **Ignoring the build system's own security** while hardening everything else.

## Exercise

1. Reproduce the checksum demo. Then place the checksum file in a separate location with restricted write access and describe what that changes in the threat model.
2. List every external input to one of your builds (packages, images, actions, scripts fetched) and mark which are pinned by immutable identifier.
3. Write the deploy-time policy for signature verification: what identity must have signed, from which repository and branch.
4. Decide your response-time target for a critical vulnerability in a transitive dependency, and the pipeline steps that make it achievable.
