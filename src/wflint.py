"""wflint: lint GitHub Actions workflow files for common safety and hygiene problems.
Rules are a teaching subset (see the lesson); this is not a replacement for actionlint or a security review."""
import re, sys
from pathlib import Path
import yaml

SHA = re.compile(r"^[0-9a-f]{40}$")
# contexts whose values an outside contributor controls
UNTRUSTED = re.compile(r"\$\{\{\s*github\.(event\.(issue\.title|issue\.body|pull_request\.title|pull_request\.body|pull_request\.head\.ref|pull_request\.head\.label|comment\.body|review\.body|head_commit\.message)|head_ref)\s*\}\}")
DEPLOY_WORDS = re.compile(r"deploy|release|publish|prod", re.I)

def triggers(doc):
    on = doc.get(True, doc.get("on"))            # YAML 1.1 parses the bare key `on` as boolean True
    if isinstance(on, str): return {on: {}}
    if isinstance(on, list): return {t: {} for t in on}
    return on or {}

def lint(doc, name="workflow"):
    out = []
    def add(rule, where, msg): out.append((rule, where, msg))
    if not isinstance(doc, dict) or "jobs" not in doc: return [("W000", name, "no jobs: not a workflow file")]
    trig = triggers(doc)
    if "permissions" not in doc and not all("permissions" in j for j in doc["jobs"].values() if isinstance(j, dict)):
        add("W001", name, "no workflow-level `permissions:` (and not every job sets one): the token gets the repository default")
    if "pull_request_target" in trig:
        for jid, job in doc["jobs"].items():
            for i, st in enumerate(job.get("steps", []) or []):
                ref = str(st.get("with", {}).get("ref", "")) if isinstance(st.get("with"), dict) else ""
                if str(st.get("uses", "")).startswith("actions/checkout") and ("head" in ref):
                    add("W002", f"{jid}.steps[{i}]", "pull_request_target checks out the PR head: untrusted code runs with a privileged token and secrets")
    for jid, job in doc["jobs"].items():
        if not isinstance(job, dict): continue
        if "uses" in job:                                     # reusable-workflow call: no steps to check
            ref = str(job["uses"]).split("@")[-1]
            if "@" in str(job["uses"]) and not SHA.match(ref) and not str(job["uses"]).startswith("./"):
                add("W003", jid, f"reusable workflow `{job['uses']}` not pinned to a full commit SHA")
            continue
        if "timeout-minutes" not in job:
            add("W004", jid, "no `timeout-minutes`: a hung job runs until the platform limit")
        steps = job.get("steps", []) or []
        for i, st in enumerate(steps):
            where = f"{jid}.steps[{i}]"
            u = str(st.get("uses", ""))
            if u and not u.startswith("./") and not u.startswith("docker://"):
                ref = u.split("@")[1] if "@" in u else ""
                if not SHA.match(ref): add("W003", where, f"`{u}` not pinned to a full commit SHA (tags can be moved)")
            run = str(st.get("run", ""))
            if run and UNTRUSTED.search(run):
                add("W005", where, "untrusted `${{ github.* }}` value expanded inside `run:`: script injection; pass it via `env:` and quote the variable")
            if isinstance(st.get("with"), dict) and u.startswith("actions/github-script"):
                if UNTRUSTED.search(str(st["with"].get("script", ""))): add("W005", where, "untrusted value expanded inside github-script")
        text = " ".join(str(s.get("name", "")) + " " + str(s.get("run", "")) for s in steps) + " " + jid + " " + str(job.get("environment", ""))
        if DEPLOY_WORDS.search(text) and "concurrency" not in job and "concurrency" not in doc:
            add("W006", jid, "looks like a deploy job with no `concurrency:` group: two runs can deploy at once")
    return out

def lint_file(path):
    try: doc = yaml.safe_load(Path(path).read_text())
    except yaml.YAMLError as e: return [("W000", str(path), f"YAML error: {e}")]
    return lint(doc, str(path))

def main(argv):
    findings = []
    for p in argv:
        findings += [(str(p),) + f for f in lint_file(p)]
    for p, rule, where, msg in findings: print(f"{p}: {rule} {where}: {msg}")
    print(f"{len(findings)} finding(s)")
    return 1 if findings else 0

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
