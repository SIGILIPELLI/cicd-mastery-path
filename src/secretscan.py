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
                if name == "generic-assignment" and re.fullmatch(r"(\$\{\{.*\}\}|<.*>|x+|\*+|changeme|example|your[-_ ].*)", value, re.I): continue     # placeholders
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
