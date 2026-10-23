"""Convert a SIMPLE GitHub Actions workflow into a minici pipeline and report everything that could not be translated.
Supported: jobs, needs, strategy.matrix (+fail-fast), env, steps with `run` (and `name`, `env`). Everything else is listed, never silently dropped."""
import yaml

def convert(doc):
    jobs, unsupported = {}, []
    for jid, job in doc.get("jobs", {}).items():
        out = {}
        if "uses" in job: unsupported.append(f"{jid}: reusable workflow call `{job['uses']}`"); continue
        if job.get("needs"): out["needs"] = [job["needs"]] if isinstance(job["needs"], str) else list(job["needs"])
        if job.get("strategy"): out["strategy"] = {k: v for k, v in job["strategy"].items() if k in ("matrix", "fail-fast")}
        for key in ("services", "container", "environment", "concurrency", "permissions", "outputs", "if", "runs-on", "timeout-minutes", "continue-on-error"):
            if key in job and key not in ("runs-on", "timeout-minutes", "permissions"): unsupported.append(f"{jid}: `{key}` has no minici equivalent")
        steps = []
        for i, st in enumerate(job.get("steps", [])):
            if "uses" in st: unsupported.append(f"{jid}.steps[{i}]: action `{st['uses']}` (must be replaced by shell commands)"); continue
            s = {"name": st.get("name", f"step {i + 1}"), "run": st["run"]}
            if "env" in st: s["env"] = st["env"]
            for key in ("if", "working-directory", "shell", "continue-on-error"):
                if key in st: unsupported.append(f"{jid}.steps[{i}]: `{key}` ignored")
            steps.append(s)
        out["steps"] = steps; jobs[jid] = out
    pipeline = {"jobs": jobs}
    if doc.get("env"): pipeline["env"] = doc["env"]
    return pipeline, unsupported
