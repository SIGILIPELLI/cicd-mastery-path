"""Golden-path generator: produce a CI workflow for a service from a few parameters. Every action must be given as a full-SHA pin; the generator refuses to guess."""
import re
SHA = re.compile(r"^[0-9a-f]{40}$")

def generate(service, python="3.12", deploy_env=None, pins=None, timeout=15):
    pins = pins or {}
    for a in ("actions/checkout", "actions/setup-python"):
        if a not in pins or not SHA.match(pins[a]): raise ValueError(f"pins[{a!r}] must be a 40-hex commit SHA")
    if not re.match(r"^[a-z][a-z0-9-]{1,40}$", service): raise ValueError("service name must be lowercase letters, digits and dashes")
    lines = [f"name: {service}-ci", "on:", "  pull_request:", "  push:", "    branches: [main]", "permissions:", "  contents: read", "jobs:", "  test:", "    runs-on: ubuntu-latest",
             f"    timeout-minutes: {timeout}", "    steps:", f"      - uses: actions/checkout@{pins['actions/checkout']}", f"      - uses: actions/setup-python@{pins['actions/setup-python']}",
             "        with:", f"          python-version: \"{python}\"", "      - run: python -m pip install -r requirements.txt", "      - run: python -m pytest -q"]
    if deploy_env:
        lines += ["  deploy:", "    needs: test", "    if: github.ref == 'refs/heads/main'", "    runs-on: ubuntu-latest", f"    timeout-minutes: {timeout}", f"    environment: {deploy_env}",
                  "    concurrency:", f"      group: deploy-{service}-{deploy_env}", "      cancel-in-progress: false", "    steps:", f"      - uses: actions/checkout@{pins['actions/checkout']}", "      - run: ./deploy.sh"]
    return "\n".join(lines) + "\n"
