"""Decide which parts of a monorepo a change affects, from a list of changed files and per-project path globs ('**' matches across directories)."""
import re, subprocess

def glob_to_regex(pattern):
    i, out = 0, ""
    while i < len(pattern):
        c = pattern[i]
        if pattern[i:i+3] == "**/": out += "(?:.*/)?"; i += 3; continue
        if pattern[i:i+2] == "**": out += ".*"; i += 2; continue
        out += "[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c); i += 1
    return re.compile("^" + out + "$")

def affected(changed, projects, global_paths=()):
    """projects: {name: [globs]}; global_paths: globs that affect EVERYTHING (CI config, root lockfile)."""
    if any(glob_to_regex(g).match(f) for f in changed for g in global_paths): return sorted(projects)
    return sorted(n for n, globs in projects.items() if any(glob_to_regex(g).match(f) for f in changed for g in globs))

def changed_files(base, head="HEAD", cwd="."):
    out = subprocess.run(["git", "diff", "--name-only", f"{base}...{head}"], cwd=cwd, capture_output=True, text=True, check=True).stdout
    return [l for l in out.splitlines() if l]
