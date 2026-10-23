import yaml
from capstone import readiness
from goldenpath import generate
PINS = {"actions/checkout": "a" * 40, "actions/setup-python": "b" * 40}
OKPLAN = {"resource_changes": [{"address": "a", "change": {"actions": ["update"]}}]}
BADPLAN = {"resource_changes": [{"address": "db", "change": {"actions": ["delete", "create"]}}]}
H = 3600
GOOD = [{"commit_time": 0, "deploy_time": 2 * H, "failed": False, "restored_time": None}] * 5
BADD = [{"commit_time": 0, "deploy_time": 2 * H, "failed": True, "restored_time": 3 * H}] * 3 + GOOD[:2]
def wf(tmp_path, **kw):
    p = tmp_path / "ci.yml"; p.write_text(generate("orders", pins=PINS, **kw)); return [str(p)]
def test_all_green(tmp_path):
    r = readiness(wf(tmp_path, deploy_env="production"), OKPLAN, [], GOOD, 7, 0.01, 0.01, seed=1); assert r["ready"] and r["reasons"] == []
def test_destructive_plan_blocks(tmp_path):
    r = readiness(wf(tmp_path), BADPLAN, [], GOOD, 7, 0.01, 0.01, seed=1); assert not r["ready"] and any("plan:" in x for x in r["reasons"])
def test_allowlisted_plan_passes(tmp_path):
    assert readiness(wf(tmp_path), BADPLAN, ["db"], GOOD, 7, 0.01, 0.01, seed=1)["ready"]
def test_high_failure_rate_blocks(tmp_path):
    assert any("change failure rate" in x for x in readiness(wf(tmp_path), OKPLAN, [], BADD, 7, 0.01, 0.01, seed=1)["reasons"])
def test_bad_canary_blocks(tmp_path):
    r = readiness(wf(tmp_path), OKPLAN, [], GOOD, 7, 0.01, 0.06, seed=1); assert r["canary"] == "rollback" and not r["ready"]
def test_unlinted_workflow_blocks(tmp_path):
    p = tmp_path / "bad.yml"; p.write_text("on: push\njobs:\n  a:\n    runs-on: x\n    steps:\n      - uses: actions/checkout@v4\n")
    assert any("W003" in x for x in readiness([str(p)], OKPLAN, [], GOOD, 7, 0.01, 0.01, seed=1)["reasons"])
