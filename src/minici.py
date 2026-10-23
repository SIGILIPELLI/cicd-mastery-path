"""minici: a tiny local CI runner that demonstrates how pipeline engines work (jobs, needs, matrix, caching, artifacts, conditions, timeouts).
Pipeline files are YAML. This is a teaching tool, not GitHub Actions or Jenkins, and supports only the features documented below."""
import hashlib, itertools, json, os, re, shutil, subprocess, sys, threading, time
from pathlib import Path
import yaml

def expand_matrix(matrix):
    if not matrix: return [{}]
    include = matrix.get("include", []); exclude = matrix.get("exclude", [])
    keys = [k for k in matrix if k not in ("include", "exclude")]
    combos = [dict(zip(keys, vals)) for vals in itertools.product(*(matrix[k] for k in keys))] if keys else []
    combos = [c for c in combos if not any(all(c.get(k) == v for k, v in ex.items()) for ex in exclude)]
    for inc in include:
        match = [c for c in combos if all(c.get(k) == v for k, v in inc.items() if k in keys)] if keys else []
        if match:
            for c in match: c.update(inc)
        else: combos.append(dict(inc))
    return combos or [{}]

def subst(text, matrix, env):
    def repl(m):
        expr = m.group(1).strip()
        if expr.startswith("matrix."): return str(matrix.get(expr[7:], ""))
        if expr.startswith("env."): return str(env.get(expr[4:], ""))
        raise ValueError(f"unsupported expression ${{{{ {expr} }}}}")
    return re.sub(r"\$\{\{(.*?)\}\}", repl, text)

def topo_levels(jobs):
    done, levels, remaining = set(), [], dict(jobs)
    while remaining:
        ready = [j for j, spec in remaining.items() if set(spec.get("needs", [])) <= done]
        if not ready: raise ValueError(f"dependency cycle or unknown job among {sorted(remaining)}")
        levels.append(sorted(ready)); done |= set(ready); [remaining.pop(j) for j in ready]
    return levels

def cache_key(spec, matrix, workdir):
    parts = [json.dumps(matrix, sort_keys=True)]
    for f in spec.get("cache", {}).get("key_files", []):
        p = Path(workdir) / f; parts.append(hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "missing")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]

class Runner:
    def __init__(self, workdir, store, log=print):
        self.workdir, self.store, self.log, self.lock = Path(workdir), Path(store), log, threading.Lock()
        self.results = {}                                    # job id -> "success"/"failure"/"skipped"
        self.timings = []                                    # (job, matrix, status, seconds, cache)

    def run(self, pipeline):
        jobs = pipeline["jobs"]; env = {str(k): str(v) for k, v in pipeline.get("env", {}).items()}
        for level in topo_levels(jobs):
            threads = []
            for jid in level:
                t = threading.Thread(target=self._run_job, args=(jid, jobs[jid], env)); t.start(); threads.append(t)
            for t in threads: t.join()
        return all(s in ("success", "skipped") for s in self.results.values())

    def _run_job(self, jid, spec, env):
        needs = spec.get("needs", [])
        if any(self.results.get(n) != "success" for n in needs) and spec.get("if") != "always()":
            self.results[jid] = "skipped"; self._say(f"[{jid}] skipped (a needed job did not succeed)"); return
        combos = expand_matrix(spec.get("strategy", {}).get("matrix")); fail_fast = spec.get("strategy", {}).get("fail-fast", True)
        failed = threading.Event(); statuses = []
        def one(m):
            if failed.is_set() and fail_fast: self._say(f"[{jid} {m}] cancelled (fail-fast)"); statuses.append("cancelled"); return
            s = self._run_combo(jid, spec, m, env)
            statuses.append(s)
            if s != "success": failed.set()
        ts = [threading.Thread(target=one, args=(m,)) for m in combos]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.results[jid] = "success" if all(s == "success" for s in statuses) else "failure"

    def _run_combo(self, jid, spec, matrix, env):
        label = f"{jid}{(' ' + json.dumps(matrix, sort_keys=True)) if matrix else ''}"
        t0 = time.time(); cache_state = "none"; status = "success"
        cdir = None
        if "cache" in spec:
            key = cache_key(spec, matrix, self.workdir); cdir = self.store / "cache" / key
            if cdir.exists():
                cache_state = "hit"
                for p in spec["cache"]["paths"]:
                    src = cdir / p
                    if src.exists(): dst = self.workdir / p; shutil.rmtree(dst, ignore_errors=True); shutil.copytree(src, dst)
            else: cache_state = "miss"
        failed_step = False
        for i, step in enumerate(spec.get("steps", []), 1):
            cond = step.get("if", "success()")
            if (cond == "success()" and failed_step) or (cond == "failure()" and not failed_step): continue
            e = dict(os.environ); e.update(env); e.update({str(k): subst(str(v), matrix, env) for k, v in step.get("env", {}).items()})
            cmd = subst(step["run"], matrix, env)
            try:
                p = subprocess.run(["bash", "-c", "set -eo pipefail\n" + cmd], cwd=self.workdir, env=e, capture_output=True, text=True, timeout=step.get("timeout", 600))
                out, rc = (p.stdout + p.stderr).strip(), p.returncode
            except subprocess.TimeoutExpired as ex:
                out, rc = f"timed out after {step.get('timeout', 600)} s", 124
            ok = rc == 0 or step.get("continue-on-error", False)
            self._say(f"[{label}] step {i} {subst(str(step.get('name', cmd[:30])), matrix, env)!r}: {'ok' if ok else 'FAILED rc=' + str(rc)}" + (f"\n    | " + out.replace("\n", "\n    | ")[:600] if (not ok or step.get("show")) and out else ""))
            if not ok: failed_step = True; status = "failure"
        if status == "success" and cdir is not None and cache_state == "miss":
            for p in spec["cache"]["paths"]:
                src = self.workdir / p
                if src.exists(): shutil.copytree(src, cdir / p)
        if status == "success":
            for pat in spec.get("artifacts", []):
                for f in self.workdir.glob(pat):
                    dst = self.store / "artifacts" / jid / f.name; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy(f, dst)
        self.timings.append((jid, matrix, status, round(time.time() - t0, 2), cache_state))
        return status

    def _say(self, msg):
        with self.lock: self.log(msg)

def main(argv):
    pipeline = yaml.safe_load(open(argv[1])); workdir = argv[2] if len(argv) > 2 else "."; store = argv[3] if len(argv) > 3 else ".minici"
    r = Runner(workdir, store); ok = r.run(pipeline)
    print("--- summary"); [print(f"{j:<10} {json.dumps(m, sort_keys=True) if m else '':<28} {s:<8} {d:>6}s cache={c}") for j, m, s, d, c in sorted(r.timings, key=lambda x: (x[0], json.dumps(x[1], sort_keys=True)))]
    print("RESULT:", "success" if ok else "failure"); return 0 if ok else 1

if __name__ == "__main__": sys.exit(main(sys.argv))
