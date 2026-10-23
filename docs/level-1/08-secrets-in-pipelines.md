---
description: "Secrets in pipelines: scoping, masking, short-lived credentials and OIDC, with a tested secret scanner and its measured findings."
---

# 08 · Secrets in Pipelines

A pipeline is a machine that holds the keys to your production systems and runs code from many people. That makes secrets handling the highest-stakes part of CI/CD. This lesson covers how secrets leak, the platform mechanisms for supplying them, and a scanner that catches the commonest mistake: a credential committed to the repository.

!!! note "What was run"
    The scanner and its **12 pytest tests ran locally**; test credentials are fakes (AWS's documented example key id, and a made-up token shape). GitHub secrets/OIDC and Jenkins credentials behaviour is described from documentation and **not run**. I made no use of any real credential. See Lesson 01.

## How secrets leak from pipelines

1. **Committed to the repository** (an `.env` file, a config, a test fixture). Git history keeps it forever; deleting the file doesn't remove it from history. Treat any committed secret as compromised and **rotate it**.
2. **Printed in logs** (`env`, `set -x`, a failing command that echoes its arguments, a verbose SDK).
3. **Passed on command lines**, visible to other processes (`ps`) and often logged.
4. **Exposed to untrusted code**: workflows triggered by pull requests from forks that can read secrets, or a malicious/compromised dependency or action that reads the environment.
5. **Baked into artifacts**: container image layers, build args, bundled config (Linux course, Level 4 · 09).
6. **Left in caches or workspaces** on persistent agents.
7. **Over-privileged**: one all-powerful token reused across repositories and environments, so any leak is catastrophic.

## Supplying secrets properly

| Platform | Mechanism | Notes (from documentation; not run) |
|---|---|---|
| GitHub Actions | Repository, environment and organization **secrets**, referenced as `${{ secrets.NAME }}` | Masked in logs when printed verbatim; not passed to workflows from forked pull requests by default; environment secrets can require approval |
| Jenkins | **Credentials** store with `withCredentials`/`credentials()` bindings | Masked in console output; scope credentials by folder/domain; a build on the controller can reach more than it should |
| Cloud-native | A secrets manager (Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault) read at deploy/run time | Rotation, audit, fine-grained access |

Principles: **scope narrowly** (per environment, per job), **inject late** (only into the step that needs it, as an environment variable rather than a command-line argument), **prefer short-lived credentials**, and **rotate** on a schedule and on any suspected exposure.

### Masking is a convenience, not a defence

CI systems replace the exact secret string with `***` in logs. It fails when the value is transformed (base64-encoded, split, URL-encoded, printed one character at a time), when a secret is multi-line, or when a short value coincides with other text. Never rely on masking to make printing a secret safe. Don't enable shell tracing (`set -x`) in steps that handle secrets.

### Prefer identity federation (OIDC) to stored keys

Instead of storing a long-lived cloud access key as a CI secret, the CI system can mint a **short-lived signed identity token (OIDC)** for each job, which the cloud provider exchanges for temporary credentials *if the token's claims match a trust policy* (repository, branch, environment). GitHub Actions supports this via the `id-token: write` permission, and the major clouds can trust it; Jenkins has plugins for similar flows (check
current availability). Benefits: no long-lived key to leak or rotate, and access is tied to *which repo and branch* is running. Trust policies must be tight (restrict to a specific repository and the protected branch/environment), or any repository in the organisation could assume the role. Level 4 · 04 returns to this.

## Pipeline-safe habits

- Give the `GITHUB_TOKEN` minimal `permissions:` (Lesson 03).
- Deployment secrets belong to **protected environments** with required reviewers, available only to jobs running on protected branches or tags.
- Don't expose secrets to pull requests from forks; use `pull_request` (no secrets) for tests, and a separate trusted workflow for anything privileged. Be wary of `pull_request_target` and `workflow_run` that check out untrusted code.
- Run third-party actions and scripts with the least secrets possible; pin them (Level 3 · 08).
- Separate build and deploy credentials; the build job rarely needs production access.
- Never pass secrets as build arguments to container builds; use build secret mounts.
- Use short-lived tokens and rotate; log who accessed which secret (secrets managers can).
- **Scan for leaks** continuously: pre-commit, in CI, and in history.

## A secret scanner (run)

Dedicated tools (gitleaks, trufflehog, GitHub secret scanning with push protection) are far more complete, but a small scanner shows the two techniques: **pattern rules** for well-known token shapes and a **Shannon-entropy** heuristic for random-looking strings.

```python
"""A small secret scanner for repositories and pipeline files: pattern rules plus a Shannon-entropy heuristic. Findings are redacted.
It will miss secrets and flag harmless strings; use it to learn the idea, and use gitleaks/trufflehog or GitHub secret scanning in practice."""
import math, re, sys
from collections import Counter
from pathlib import Path

RULES = [
    ("aws-access-key-id", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("private-key-block", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY( BLOCK)?-----")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("generic-assignment", re.compile(r"""(?i)\b\w*(password|passwd|secret|api[_-]?key|token)\w*\s*[:=]\s*['"]([^'"\s$]{8,})['"]""")),
    ("url-with-credentials", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]{4,}@")),
]
ALLOW = re.compile(r"pragma:\s*allowlist\s*secret|nosecret", re.I)

def entropy(s):
    c = Counter(s); n = len(s); return -sum(v / n * math.log2(v / n) for v in c.values())

def redact(s): return s[:4] + "…" + "*" * 4 if len(s) > 8 else "****"

def scan_text(text, path="<text>"):
    findings = []
    for ln, line in enumerate(text.splitlines(), 1):
        if ALLOW.search(line): continue
        hit = False
        for name, rx in RULES:
            m = rx.search(line)
            if m:
                value = m.group(2) if name == "generic-assignment" else m.group(0)
                if name == "generic-assignment" and re.fullmatch(r"(\$\{\{.*\}\}|<.*>|x+|\*+|changeme|example|your[-_ ].*)", value, re.I): continue     # example values
                findings.append((path, ln, name, redact(value))); hit = True
        if not hit:
            for tok in re.findall(r"[A-Za-z0-9+/=_-]{32,}", line):
                if entropy(tok) > 4.3 and not re.fullmatch(r"[0-9a-f]{32,64}", tok):      # long, random-looking, and not a plain hex digest/commit
                    findings.append((path, ln, "high-entropy-string", redact(tok)))
    return findings

def scan_tree(root, skip=(".git", "node_modules", ".venv")):
    out = []
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and not any(s in p.parts for s in skip) and p.stat().st_size < 1_000_000:
            try: out += scan_text(p.read_text(), str(p.relative_to(root)))
            except UnicodeDecodeError: pass
    return out

if __name__ == "__main__":
    f = scan_tree(sys.argv[1])
    for path, ln, rule, red in f: print(f"{path}:{ln}: {rule}: {red}")
    print(f"{len(f)} finding(s)"); sys.exit(1 if f else 0)
```

The 12 tests assert: an AWS-style key id, a GitHub-token-shaped string, a private-key header, `db_password = "..."` and a URL with embedded credentials are found; example values (`${{ secrets.DB_PASSWORD }}`, `<your-password>`, `changeme`, `xxxx`) and `$ENV_REFERENCES` are not; an `allowlist` comment suppresses a finding; a high-entropy blob is flagged but a 40-character hex commit SHA is not; and findings are **redacted** so the scanner does not itself leak the secret into
the log (only the first four characters appear). Run on a small fixture tree containing a workflow with an inline token, an `.env` with an AWS-style key and a database URL, and an innocent commit SHA:

```text
.github/workflows/d.yml:3: generic-assignment: abcd…****
app/.env:1: aws-access-key-id: AKIA…****
app/.env:2: url-with-credentials: post…****
3 finding(s)
```

(The workflow line `SAFE: ${{ secrets.API_TOKEN }}` and the commit SHA were correctly *not* flagged.) One test failed on my first attempt: the rule used a word boundary before `password`, so `db_password` (an underscore is a word character) was missed. The fix was to allow word characters before and after the keyword. Scanners have false negatives (a secret in an unusual format) and false positives (random IDs); tune them, and treat them as a safety net, not a guarantee.

## When a secret leaks

1. **Revoke/rotate immediately**; assume it was seen. 2. **Find the exposure window** and audit what the credential did (cloud access logs). 3. Remove it from the code, and from history only as cleanup (history rewriting doesn't un-leak a pushed secret). 4. **Fix the cause** (why it was in the repo, why the scanner didn't block it). 5. Document it.

## How It Actually Works

CI secrets are stored encrypted by the platform and decrypted only when a job is dispatched to a runner, then placed in the job's environment (or a mounted file). The runner registers each secret's value with a log filter that rewrites exact matches to `***`. OIDC federation replaces the stored secret with a signed JWT whose claims (`sub`, repository, ref, environment) the cloud's trust policy verifies against its configuration and
exchanges for temporary credentials, so there is nothing long-lived to steal. Scanners work on text: they apply regular expressions and compute entropy `H = -Σ p·log2 p` over the characters of a candidate string (random base64 scores around 5 to 6 bits per character, English text far less), flagging unusually random tokens.

## Common mistakes

- **Secrets in Git**, `.env` files committed, or fixtures containing real tokens.
- **Echoing environment variables** for debugging.
- **One shared, over-privileged token** for everything.
- **Exposing secrets to fork pull requests.**
- **Long-lived cloud keys** where OIDC is available.
- **Relying on log masking.**
- **Secrets as Docker build args.**
- **No rotation or audit**, and no plan for leaks.

## Exercise

1. Run the scanner over a repository of yours (history too, with `git log -p` piped in) and triage each finding as real or false.
2. Add a rule for a token format you use (a Stripe-style key, an internal service token) with a failing test first.
3. Draft the OIDC trust policy conditions (repository, branch, environment) you'd require before letting a pipeline assume a deployment role.
4. Write the incident steps for "a cloud key was committed to a public repository 10 minutes ago", in order.
