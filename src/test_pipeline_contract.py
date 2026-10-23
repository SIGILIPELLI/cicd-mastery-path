"""Tests OF a pipeline: run the demo pipeline with minici against copies of the demo project and assert the behaviours the pipeline promises."""
import os, shutil, sys, yaml
from pathlib import Path
import minici
DEMO = Path(__file__).parent / "demo-project"
def run(tmp_path, mutate=None):
    os.environ["PATH"] = os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"]      # steps call `python3`: make it the interpreter running these tests
    work = tmp_path / "w"; shutil.copytree(DEMO, work, ignore=shutil.ignore_patterns("*.tar.gz", "__pycache__", ".pytest_cache"))
    if mutate: mutate(work)
    pipe = yaml.safe_load((work / "pipeline.yml").read_text())
    for step in pipe["jobs"]["deps"]["steps"]: step["run"] = "mkdir -p libs; echo built > libs/marker"       # skip the 2 s sleep in tests
    r = minici.Runner(work, tmp_path / "store", log=lambda m: None); ok = r.run(pipe); return ok, r
def test_green_pipeline_deploys(tmp_path):
    ok, r = run(tmp_path); assert ok and r.results["deploy"] == "success" and r.results["package"] == "success"
def test_failing_test_blocks_package_and_deploy(tmp_path):
    def break_test(w): (w / "tests" / "test_calc.py").write_text("def test_x():\n    assert False\n")
    ok, r = run(tmp_path, break_test); assert not ok and r.results["test"] == "failure" and r.results["package"] == "skipped" and r.results["deploy"] == "skipped"
def test_lint_failure_blocks_test_job(tmp_path):
    def break_syntax(w): (w / "app" / "calc.py").write_text("def broken(:\n")
    ok, r = run(tmp_path, break_syntax); assert r.results["lint"] == "failure" and r.results["test"] == "skipped"
def test_every_matrix_cell_ran(tmp_path):
    ok, r = run(tmp_path); cells = [t for t in r.timings if t[0] == "test"]; assert len(cells) == 3 and all(c[2] == "success" for c in cells)
