import yaml
from wf2minici import convert
W = yaml.safe_load("""
name: ci
on: push
env: {LANG: C}
jobs:
  test:
    runs-on: ubuntu-latest
    strategy: {matrix: {py: ["3.11", "3.12"]}, fail-fast: false}
    steps:
      - uses: actions/checkout@v4
      - name: tests
        run: python -m pytest
        env: {TZ: UTC}
  deploy:
    needs: test
    runs-on: ubuntu-latest
    environment: production
    steps:
      - run: ./deploy.sh
        if: github.ref == 'refs/heads/main'
""")
def test_run_steps_converted(): p, _ = convert(W); assert p["jobs"]["test"]["steps"] == [{"name": "tests", "run": "python -m pytest", "env": {"TZ": "UTC"}}]
def test_needs_normalised_to_list(): assert convert(W)[0]["jobs"]["deploy"]["needs"] == ["test"]
def test_matrix_and_failfast_kept(): assert convert(W)[0]["jobs"]["test"]["strategy"] == {"matrix": {"py": ["3.11", "3.12"]}, "fail-fast": False}
def test_global_env_kept(): assert convert(W)[0]["env"] == {"LANG": "C"}
def test_uses_step_reported_not_dropped(): assert any("actions/checkout@v4" in u for u in convert(W)[1])
def test_environment_reported(): assert any("environment" in u for u in convert(W)[1])
def test_step_if_reported(): assert any("`if` ignored" in u for u in convert(W)[1])
def test_reusable_call_reported():
    d = {"jobs": {"c": {"uses": "o/r/.github/workflows/x.yml@v1"}}}; p, u = convert(d); assert p["jobs"] == {} and "reusable" in u[0]
