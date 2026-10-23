"""Compute the next semantic version from Conventional Commit messages. Rules (a convention, not a standard of Git itself):
BREAKING CHANGE footer or `type!:` => major; `feat` => minor; `fix`/`perf` => patch; other types alone => no release."""
import re
HEADER = re.compile(r"^(?P<type>[a-z]+)(\((?P<scope>[^)]+)\))?(?P<bang>!)?: (?P<desc>.+)$")

def classify(message):
    lines = message.strip().splitlines()
    m = HEADER.match(lines[0]) if lines else None
    if not m: return "none"
    if m["bang"] or any(l.startswith("BREAKING CHANGE:") or l.startswith("BREAKING-CHANGE:") for l in lines[1:]): return "major"
    return {"feat": "minor", "fix": "patch", "perf": "patch"}.get(m["type"], "none")

def bump(version, messages):
    major, minor, patch = map(int, version.split("."))
    kinds = {classify(m) for m in messages}
    if "major" in kinds: return f"{major + 1}.0.0" if major >= 1 else f"{major}.{minor + 1}.0"      # 0.y.z: breaking changes bump minor (a common convention)
    if "minor" in kinds: return f"{major}.{minor + 1}.0"
    if "patch" in kinds: return f"{major}.{minor}.{patch + 1}"
    return version
