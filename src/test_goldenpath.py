import pytest, yaml
from goldenpath import generate
from wflint import lint
PINS = {"actions/checkout": "a" * 40, "actions/setup-python": "b" * 40}
def test_generated_workflow_is_valid_yaml_with_jobs(): d = yaml.safe_load(generate("orders", pins=PINS)); assert list(d["jobs"]) == ["test"]
def test_generated_workflow_lints_clean(): assert lint(yaml.safe_load(generate("orders", pins=PINS, deploy_env="production"))) == []
def test_deploy_job_has_needs_and_concurrency():
    d = yaml.safe_load(generate("orders", pins=PINS, deploy_env="production")); j = d["jobs"]["deploy"]
    assert j["needs"] == "test" and j["concurrency"]["cancel-in-progress"] is False and j["environment"] == "production"
def test_refuses_tag_pins():
    with pytest.raises(ValueError): generate("orders", pins={"actions/checkout": "v4", "actions/setup-python": "b" * 40})
def test_refuses_missing_pins():
    with pytest.raises(ValueError): generate("orders", pins={})
def test_rejects_bad_service_name():
    with pytest.raises(ValueError): generate("Orders; rm -rf /", pins=PINS)
def test_python_version_stays_a_string():
    assert yaml.safe_load(generate("o1", python="3.10", pins=PINS))["jobs"]["test"]["steps"][1]["with"]["python-version"] == "3.10"
def test_without_deploy_env_no_deploy_job(): assert "deploy" not in yaml.safe_load(generate("orders", pins=PINS))["jobs"]
