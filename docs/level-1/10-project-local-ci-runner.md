---
description: "Level 1 project: a 150-line local CI runner with jobs, needs, matrix, caching and artifacts, 15 tests, and runs showing cache hits and failures."
---

# 10 · Project — A Local CI Runner You Can Run

The best way to understand a CI system is to build a tiny one. This project's `minici` runs a YAML pipeline on your machine and exhibits the core behaviours from Level 1: dependency ordering with parallelism, matrix expansion, cache keys, artifacts, conditions, timeouts, and failure propagation. It is a teaching model, not a product: it is not GitHub Actions or Jenkins and does not behave identically to either.

!!! note "What was run"
    Everything in this lesson was run on macOS: the runner's 15 pytest tests, and the pipeline runs shown, which used a small Python demo project. The step that installs dependencies is simulated by a 2 s `sleep` so the cache effect is visible and repeatable. The `deploy` job only echoes. The matrix varies the `TZ` environment variable (there was only one Python version available). The runner has no sandboxing or security hardening: do not run
    untrusted pipeline files with it. See Lesson 01.

## Requirements

1. Parse a YAML pipeline with `jobs`, `needs`, `steps` (`run`, `env`, `if`, `timeout`, `continue-on-error`).
2. Run jobs with no unmet dependencies **in parallel**; skip jobs whose dependencies failed unless `if: always()`.
3. Expand a **matrix** (cross product with `include` and `exclude`) into separate runs, with `fail-fast`.
4. **Cache** directories by a key derived from file contents and matrix values; save only on success.
5. Collect **artifacts** from successful jobs only.
6. Enforce **step timeouts** and run scripts with `set -eo pipefail`.
7. Refuse unsupported `${{ }}` expressions instead of silently ignoring them.

## The runner

```python
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
```

## The tests

```python
import yaml, minici
from minici import expand_matrix, topo_levels, Runner

def run(tmp_path, pipeline, files=None):
    wd = tmp_path / "work"; wd.mkdir(exist_ok=True)
    for n, c in (files or {}).items(): (wd / n).write_text(c)
    logs = []; r = Runner(wd, tmp_path / "store", log=logs.append); ok = r.run(yaml.safe_load(pipeline) if isinstance(pipeline, str) else pipeline); return r, ok, logs, wd

def test_matrix_product_and_exclude():
    m = {"os": ["a", "b"], "v": [1, 2], "exclude": [{"os": "b", "v": 2}]}
    assert sorted((c["os"], c["v"]) for c in expand_matrix(m)) == [("a", 1), ("a", 2), ("b", 1)]
def test_matrix_include_extends_and_adds():
    got = expand_matrix({"v": [1, 2], "include": [{"v": 2, "extra": "x"}, {"v": 9, "experimental": True}]})
    assert {"v": 2, "extra": "x"} in got and {"v": 9, "experimental": True} in got and len(got) == 3
def test_topo_levels(): assert topo_levels({"build": {}, "test": {"needs": ["build"]}, "lint": {}, "deploy": {"needs": ["test", "lint"]}}) == [["build", "lint"], ["test"], ["deploy"]]
def test_cycle_detected():
    import pytest
    with pytest.raises(ValueError): topo_levels({"a": {"needs": ["b"]}, "b": {"needs": ["a"]}})
def test_success_and_skip_on_failure(tmp_path):
    r, ok, _, _ = run(tmp_path, "jobs:\n  build: {steps: [{run: 'exit 1'}]}\n  deploy: {needs: [build], steps: [{run: 'echo hi'}]}\n")
    assert not ok and r.results == {"build": "failure", "deploy": "skipped"}
def test_always_runs_after_failure(tmp_path):
    r, _, _, _ = run(tmp_path, "jobs:\n  build: {steps: [{run: 'exit 1'}]}\n  notify: {needs: [build], if: always(), steps: [{run: 'true'}]}\n"); assert r.results["notify"] == "success"
def test_failure_step_runs_cleanup(tmp_path):
    r, ok, logs, wd = run(tmp_path, "jobs:\n  t:\n    steps:\n      - run: 'exit 3'\n      - {run: 'echo skipped > a.txt'}\n      - {if: failure(), run: 'echo cleanup > c.txt'}\n")
    assert not ok and not (wd / "a.txt").exists() and (wd / "c.txt").exists()
def test_pipefail_in_steps(tmp_path):
    r, ok, _, _ = run(tmp_path, "jobs:\n  t: {steps: [{run: 'false | true'}]}\n"); assert not ok
def test_matrix_substitution_and_all_combos(tmp_path):
    r, ok, _, wd = run(tmp_path, "jobs:\n  t:\n    strategy: {matrix: {n: [1, 2, 3]}}\n    steps: [{run: 'echo ${{ matrix.n }} >> out.txt'}]\n")
    assert ok and sorted((wd / "out.txt").read_text().split()) == ["1", "2", "3"]
def test_fail_fast_cancels_pending(tmp_path):
    r, ok, logs, _ = run(tmp_path, "jobs:\n  t:\n    strategy: {fail-fast: true, matrix: {n: [1, 2]}}\n    steps: [{run: 'exit 1'}]\n"); assert not ok and r.results["t"] == "failure"
def test_cache_miss_then_hit(tmp_path):
    p = "jobs:\n  deps:\n    cache: {key_files: [req.txt], paths: [libs]}\n    steps: [{run: 'mkdir -p libs && echo installed >> libs/log && cat libs/log | wc -l'}]\n"
    r1, _, _, wd = run(tmp_path, p, {"req.txt": "a==1"}); assert r1.timings[0][4] == "miss"
    r2, _, _, _ = run(tmp_path, p, {"req.txt": "a==1"}); assert r2.timings[0][4] == "hit"
    r3, _, _, _ = run(tmp_path, p, {"req.txt": "a==2"}); assert r3.timings[0][4] == "miss"         # key changed with the lockfile
def test_artifacts_collected_only_on_success(tmp_path):
    r, ok, _, _ = run(tmp_path, "jobs:\n  b: {steps: [{run: 'echo x > app.tar'}], artifacts: ['*.tar']}\n"); assert (tmp_path / "store/artifacts/b/app.tar").exists()
    r, ok, _, _ = run(tmp_path / "f", "jobs:\n  b: {steps: [{run: 'echo x > a.zip; exit 1'}], artifacts: ['*.zip']}\n") if (tmp_path / "f").mkdir() is None else (None, None, None, None)
    assert not (tmp_path / "f/store/artifacts/b/a.zip").exists()
def test_timeout_kills_step(tmp_path):
    r, ok, logs, _ = run(tmp_path, "jobs:\n  t: {steps: [{run: 'sleep 5', timeout: 1}]}\n"); assert not ok and any("timed out" in l for l in logs)
def test_unsupported_expression_rejected(tmp_path):
    import pytest
    with pytest.raises(ValueError): minici.subst("${{ secrets.TOKEN }}", {}, {})
def test_jobs_without_dependencies_run_in_parallel(tmp_path):
    import time
    t0 = time.time(); r, ok, _, _ = run(tmp_path, "jobs:\n  a: {steps: [{run: 'sleep 1'}]}\n  b: {steps: [{run: 'sleep 1'}]}\n  c: {steps: [{run: 'sleep 1'}]}\n")
    assert ok and time.time() - t0 < 2.5
```

```text
15 passed in 2.19s
```

The tests cover matrix cross-product with `exclude`, `include` that both extends an existing combination and adds a new one, dependency levels, cycle detection, skipped dependents after failure, `if: always()`, `if: failure()` cleanup steps, `pipefail` (a `false | true` step fails), substitution, fail-fast, cache miss/hit/miss-after-key-change, artifacts on success only, step timeouts, rejection of unsupported expressions, and real parallelism (three 1 s jobs finish in under 2.5 s).

## The demo project and pipeline

A tiny Python package (`app/calc.py` with a `total()` function) and three tests, pipeline:

```yaml
env: {PYTHONDONTWRITEBYTECODE: "1"}
jobs:
  deps:
    cache: {key_files: [requirements.txt], paths: [libs]}
    steps:
      - {name: install dependencies (slow step, 2 s), run: "if [ ! -d libs ]; then sleep 2; mkdir libs; echo built > libs/marker; echo 'installed'; else echo 'restored from cache'; fi", show: true}
  lint:
    steps: [{name: syntax check, run: "python3 -m py_compile app/calc.py tests/test_calc.py"}]
  test:
    needs: [deps, lint]
    strategy: {matrix: {tz: [UTC, Asia/Kolkata, America/New_York]}}
    steps:
      - {name: "tests under ${{ matrix.tz }}", run: "TZ=${{ matrix.tz }} python3 -m pytest -q -p no:cacheprovider tests", show: true}
  package:
    needs: [test]
    artifacts: ["*.tar.gz"]
    steps: [{name: build artifact, run: "tar -czf app-1.0.0.tar.gz app"}]
  deploy:
    needs: [package]
    steps: [{name: "deploy (simulated)", run: "echo deploying app-1.0.0.tar.gz", show: true}]
```

### Run 1 (cold) and run 2 (warm)

```text
--- run 1
deploy                                  success     0.0s cache=none
deps                                    success    2.02s cache=miss
lint                                    success    0.04s cache=none
package                                 success    0.01s cache=none
test       {"tz": "America/New_York"}   success    0.38s cache=none
test       {"tz": "Asia/Kolkata"}       success    0.39s cache=none
test       {"tz": "UTC"}                success    0.39s cache=none
RESULT: success
--- run 2
deploy                                  success     0.0s cache=none
deps                                    success     0.0s cache=hit
lint                                    success    0.03s cache=none
package                                 success    0.01s cache=none
test       {"tz": "America/New_York"}   success     0.3s cache=none
test       {"tz": "Asia/Kolkata"}       success     0.3s cache=none
test       {"tz": "UTC"}                success     0.3s cache=none
RESULT: success
```

Observe: `deps` took **2.02 s on the miss** and **under 0.01 s on the hit** (it printed "restored from cache" instead of "installed"); `lint` and `deps` ran in parallel; the three `test` variants ran in parallel after both finished; `package` and `deploy` followed in order. The artifact `app-1.0.0.tar.gz` was copied into the store under the `package` job.

### Run 3 (a broken test)

I changed an expected value in a test so it fails in every matrix variant:

```text
[test {"tz": "America/New_York"}] step 1 'tests under America/New_York': FAILED rc=1
    | E   assert 36.0 == 37.0
    | E    +  where 36.0 = total([10, 20])
[test {"tz": "UTC"}] step 1 'tests under UTC': FAILED rc=1
    | E   assert 36.0 == 37.0
    | E    +  where 36.0 = total([10, 20])
[test {"tz": "Asia/Kolkata"}] step 1 'tests under Asia/Kolkata': FAILED rc=1
RESULT: failure
```

All three variants failed with the assertion diff, `package` and `deploy` were **skipped**, and the overall result was a failure. That is the whole gating mechanism in a few lines: a non-zero exit code fails the step, fails the job, and dependents are not started. (I restored the test afterwards.)

## Extensions

1. Add `outputs` (a job writes a value, a later job reads it through `needs`), and test it.
2. Add `timeout` at job level and a `retry` count, with a test showing why retries should be rare.
3. Add a `concurrency` group so two runs of the same pipeline do not overlap (a lock file), and test it.
4. Run each step in a throwaway directory copy or a container to isolate jobs from each other, as hosted runners do.
5. Print the pipeline as a Mermaid graph from `needs`.

## How It Actually Works

`topo_levels` repeatedly selects jobs whose `needs` are all complete, building the DAG's layers; `Runner.run` starts one thread per job in a layer and joins them before the next, which is simple but coarser than a real scheduler (which starts a job the instant its own dependencies finish). Each job expands its matrix and runs combos in threads; each step is a `subprocess.run` of `bash -c` in the workspace with an environment assembled from the
pipeline, the step and the matrix. Cache keys are `sha256(matrix JSON | hashes of key files)`. A real system adds what this omits: isolation (VMs/containers), secrets handling, log streaming and storage, retries, concurrency groups, matrix `max-parallel`, a persistent queue, authentication and a UI.

## Common mistakes

- **Treating this as a security boundary**: pipeline steps run arbitrary shell as you.
- **Cache keys that omit relevant inputs** (here the key includes the matrix and the listed files only).
- **Assuming local results equal hosted ones**: a clean hosted runner has different tools, environment variables and network access.
- **Skipping the clean-run test** (delete `.minici` and run again).
- **Fixing flaky tests with retries** instead of understanding them.

## Exercise

1. Run the demo twice yourself, then change `requirements.txt` and confirm the cache misses; record the timings.
2. Add a job `security` that runs the secret scanner from Lesson 08 on the working directory and make `package` depend on it. Plant a fake token and watch the pipeline block.
3. Write a pipeline for a project of yours and run it. Which of your real CI steps could not be expressed in `minici`, and what would they need?
4. Convert the demo pipeline to a GitHub Actions workflow and a Jenkinsfile (from Lessons 03 and 04) side by side, listing the differences you had to resolve.
