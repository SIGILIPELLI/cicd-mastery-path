import yaml
from wflint import lint, triggers
SHA = "a" * 40
def rules(text): return sorted({r for r, _, _ in lint(yaml.safe_load(text))})
GOOD = f"""
name: ci
on: [push]
permissions: {{contents: read}}
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@{SHA}
      - run: make test
"""
def test_clean_workflow_has_no_findings(): assert rules(GOOD) == []
def test_on_key_is_parsed_as_true():
    d = yaml.safe_load(GOOD); assert True in d and "on" not in d and triggers(d) == {"push": {}}
def test_missing_permissions(): assert "W001" in rules(GOOD.replace("permissions: {contents: read}\n", ""))
def test_job_level_permissions_satisfy_rule():
    t = GOOD.replace("permissions: {contents: read}\n", "").replace("    timeout-minutes: 10\n", "    timeout-minutes: 10\n    permissions: {contents: read}\n"); assert "W001" not in rules(t)
def test_tag_pin_flagged(): assert "W003" in rules(GOOD.replace(SHA, "v4"))
def test_branch_pin_flagged(): assert "W003" in rules(GOOD.replace(SHA, "main"))
def test_local_action_not_flagged(): assert "W003" not in rules(GOOD.replace(f"actions/checkout@{SHA}", "./.github/actions/setup"))
def test_missing_timeout(): assert "W004" in rules(GOOD.replace("    timeout-minutes: 10\n", ""))
def test_script_injection_flagged():
    t = GOOD.replace("make test", 'echo "${{ github.event.pull_request.title }}"'); assert "W005" in rules(t)
def test_env_indirection_is_clean():
    t = GOOD.replace("      - run: make test", '      - run: echo "$TITLE"\n        env:\n          TITLE: ${{ github.event.pull_request.title }}'); assert "W005" not in rules(t)
def test_safe_context_not_flagged():
    assert "W005" not in rules(GOOD.replace("make test", 'echo "${{ github.sha }}"'))
def test_pull_request_target_head_checkout():
    t = GOOD.replace("on: [push]", "on: pull_request_target").replace(f"      - uses: actions/checkout@{SHA}", f"      - uses: actions/checkout@{SHA}\n        with:\n          ref: ${{{{ github.event.pull_request.head.sha }}}}"); assert "W002" in rules(t)
def test_pull_request_target_without_head_checkout_ok():
    assert "W002" not in rules(GOOD.replace("on: [push]", "on: pull_request_target"))
def test_deploy_without_concurrency():
    assert "W006" in rules(GOOD.replace("make test", "./deploy.sh production"))
def test_deploy_with_concurrency_ok():
    assert "W006" not in rules(GOOD.replace("make test", "./deploy.sh production").replace("jobs:", "concurrency: deploy-prod\njobs:"))
def test_reusable_call_checked_for_pin():
    t = "on: push\npermissions: {}\njobs:\n  call:\n    uses: org/repo/.github/workflows/x.yml@v1\n"; assert rules(t) == ["W003"]
def test_not_a_workflow(): assert lint({"foo": 1})[0][0] == "W000"
