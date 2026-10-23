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
