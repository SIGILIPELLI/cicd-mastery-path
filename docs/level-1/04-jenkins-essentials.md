---
description: "Jenkins essentials: controller and agents, declarative pipelines, stages, post actions and credentials, with a tested Jenkinsfile linter."
---

# 04 · Jenkins Essentials and the Jenkinsfile

Jenkins is the long-running open-source automation server. It predates hosted CI services, runs on your own infrastructure, and has a huge plugin ecosystem. It remains common in organisations that need to run builds inside their network or on specialised hardware. Its pipelines are written in a `Jenkinsfile` stored with the code.

!!! note "What was run"
    **No Jenkins server was run** for this course (none was installed, and I did not download one), so no Jenkinsfile below was executed by Jenkins. Syntax and semantics come from the Jenkins Pipeline Syntax reference (jenkins.io, October 2026). What I ran: a **structure linter I wrote for Declarative Jenkinsfiles, with 11 passing pytest tests**. It is text-based and does not understand Groovy; Jenkins's own validator is the
    authority. See Lesson 01.

## Architecture in one picture

```text
developers push → SCM (Git) ──webhook──► Jenkins controller  ──schedules──►  agents (nodes) run the builds
                                         (UI, job config, plugins,             (labels: linux, docker, windows, gpu...)
                                          queue, credentials store)
```

- The **controller** hosts the web UI, stores job definitions and credentials, decides what runs where, and keeps build records. Keep builds *off* the controller (set it to zero executors): a build that runs on the controller can read everything the controller holds, including credentials (Level 4 · 01).
- **Agents** (nodes) execute the work: permanent machines, cloud-provisioned VMs, or containers/pods created on demand. Jobs select agents by **label**.
- **Plugins** add SCM integrations, build steps, credentials types and agent provisioning. They are also the main operational burden: each is code running inside the controller with its own security fixes (Level 4 · 03).

## The Declarative Jenkinsfile

```groovy
pipeline {
    agent { label 'linux && docker' }
    options {
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }
    environment {
        APP_VERSION = "1.4.${env.BUILD_NUMBER}"
    }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Build and Test') {
            parallel {
                stage('Unit tests') {
                    steps { sh 'python3 -m pytest -q' }
                }
                stage('Lint') {
                    steps { sh 'python3 -m py_compile app/*.py' }
                }
            }
        }
        stage('Package') {
            steps {
                sh 'tar -czf app-${APP_VERSION}.tar.gz app'
                archiveArtifacts artifacts: 'app-*.tar.gz', fingerprint: true
            }
        }
        stage('Deploy to staging') {
            when { branch 'main' }
            steps {
                withCredentials([string(credentialsId: 'staging-deploy-token', variable: 'TOKEN')]) {
                    sh './deploy.sh staging "$TOKEN"'
                }
            }
        }
    }
    post {
        always { junit allowEmptyResults: true, testResults: 'reports/*.xml' }
        failure { echo 'Build failed: notify the team' }
    }
}
```

Reading it:

- **`agent { label 'linux && docker' }`** requests a node with both labels. `agent any` runs on any node, which is rarely what you want. Per the reference, the top-level `agent` is required, and a stage can declare its own agent (including a Docker image) for different tools.
- **`options`**: `timeout(...)` bounds the run (note from the reference: for a top-level agent, the timeout counter starts *after* the agent is allocated, so waiting for a node isn't counted); `timestamps()` stamps log lines; `disableConcurrentBuilds()` stops two builds of this job running at once (important for deploys); `buildDiscarder` limits retained history. The reference also documents `parallelsAlwaysFailFast()`.
- **`environment`** defines variables, here using the built-in `env.BUILD_NUMBER`.
- **`stages` / `stage` / `steps`**: stages run in order; `parallel { }` runs nested stages concurrently. `checkout scm` fetches the exact commit that triggered the build. `sh` runs a shell command and fails the stage on a non-zero exit.
- **`archiveArtifacts ... fingerprint: true`** stores build outputs and records their checksums so other jobs can trace where a file came from.
- **`when { branch 'main' }`** restricts the deployment stage (branch-based conditions need a multibranch pipeline job).
- **`withCredentials`** binds a stored secret to a variable only for the enclosed block; Jenkins masks the value in logs. The script is **single-quoted** so the shell, not Groovy, expands `$TOKEN`, avoiding the secret being interpolated into a Groovy string.
- **`post`**: `always`, `failure`, `success` and other conditions run after the stages: test-report publishing, notifications, cleanup.

Declarative is the recommended style for most pipelines; **Scripted Pipeline** (`node { ... }` with full Groovy) offers flexibility at the cost of readability and weaker validation. Use the `script { }` step inside declarative for small amounts of Groovy.

## Jenkins vs GitHub Actions in one table

| | Jenkins | GitHub Actions |
|---|---|---|
| Hosting | You run controller and agents | GitHub runs the orchestrator; hosted or self-hosted runners |
| Pipeline file | `Jenkinsfile` (Groovy DSL) | YAML in `.github/workflows` |
| Extensibility | Plugins (installed on the controller) | Marketplace actions (executed per job) |
| Isolation | Depends on how you configure agents; shared controller | Fresh VM per job on hosted runners |
| Maintenance burden | Upgrades, plugin updates, backups, scaling | Mostly the workflows themselves |
| Strengths | Full control, on-prem, custom hardware, mature, flexible | Tight GitHub integration, low setup, ecosystem |
| Typical weakness | Plugin sprawl, snowflake controllers | Locked to GitHub, usage limits |

Neither is "better"; the right choice depends on where your code and builds must live. Migrating between them is Level 4 · 08.

## A Jenkinsfile linter (run)

Jenkins can validate a Declarative Jenkinsfile through its linter endpoint; I could not use that, so I wrote structure checks that catch common problems without a server:

```python
"""Structure checks for Declarative Jenkinsfiles. Text-based, with a brace tokenizer; it does not understand Groovy and cannot replace
Jenkins' own validator (`Jenkinsfile Linter` endpoint / `declarative-linter`). Findings are advisory."""
import re, sys

def strip_comments_and_strings(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(^|[^:])//[^\n]*", r"\1", text)
    return re.sub(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", '""', text)

def balanced(text):
    depth = 0
    for ch in strip_comments_and_strings(text):
        depth += ch == "{"; depth -= ch == "}"
        if depth < 0: return False
    return depth == 0

def block_names(text):
    return re.findall(r"\b(pipeline|agent|options|environment|stages|stage|steps|post|parallel|when|always|failure|success|tools|triggers|parameters)\b\s*[({]", strip_comments_and_strings(text))

def lint(text):
    problems = []; clean = strip_comments_and_strings(text); raw_no_comments = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    if not balanced(text): problems.append("unbalanced braces: the file will not parse"); return problems
    names = block_names(text)
    if "pipeline" not in names: problems.append("no declarative 'pipeline { }' block (scripted pipelines need different checks)")
    if "agent" not in names and not re.search(r"\bagent\s+(any|none)\b", clean): problems.append("missing required 'agent' section")
    if "stages" not in names: problems.append("missing required 'stages' section")
    if names.count("stage") == 0: problems.append("no stage blocks")
    if re.search(r"\bagent\s+any\b", clean): problems.append("'agent any' lets the build run on any node; use labels so builds land on suitable, trusted agents")
    if "timeout(" not in clean: problems.append("no timeout() option: a hung build occupies an executor indefinitely")
    if "post" not in names: problems.append("no post { } section for always/failure handling (reports, notifications, cleanup)")
    if "disableConcurrentBuilds" not in clean: problems.append("concurrent builds are allowed; consider disableConcurrentBuilds() for jobs that deploy")
    if "buildDiscarder" not in clean: problems.append("no buildDiscarder: build history and artifacts will accumulate on the controller")
    for m in re.finditer(r"(password|passwd|secret|token|apikey|api_key)\s*[=:]\s*['\"][^'\"$]{6,}['\"]", raw_no_comments, re.I):
        problems.append(f"possible hard-coded credential: {m.group(0)[:40]}...; use credentials() / withCredentials")
    if re.search(r"sh\s+['\"][^'\"]*\$\{?[A-Za-z_]*(TOKEN|PASSWORD|SECRET)", raw_no_comments) : problems.append("secret interpolated into an sh string; single-quote the script and let the shell read the environment variable (avoids Groovy string interpolation leaks)")
    for m in re.finditer(r"stage\(\s*['\"]([^'\"]*)['\"]\s*\)\s*\{", raw_no_comments):
        if re.search(r"deploy|release|publish", m.group(1), re.I):
            body = raw_no_comments[m.end(): m.end() + 600]
            if not re.search(r"\bwhen\s*\{", body.split("stage(")[0]): problems.append(f"stage {m.group(1)!r} looks like a deployment but has no 'when' condition: it would run on every branch")
    return problems

if __name__ == "__main__":
    p = lint(open(sys.argv[1]).read()); print("\n".join(p) if p else "OK"); sys.exit(1 if p else 0)
```

The 11 tests check the example is clean and that each rule fires when its defect is introduced: unbalanced braces (and that braces inside strings and comments are ignored), `agent any`, missing timeout, missing `post`, a hard-coded token, a deployment stage with no `when`, and a secret interpolated into a double-quoted Groovy string. Running it on a copy of the Jenkinsfile where I made `agent any`, removed the `timeout`, deleted the `when`, and added `API_TOKEN = "abcdef123456"`:

```text
'agent any' lets the build run on any node; use labels so builds land on suitable, trusted agents
no timeout() option: a hung build occupies an executor indefinitely
possible hard-coded credential: TOKEN = "abcdef123456"...; use credentials() / withCredentials
stage 'Deploy to staging' looks like a deployment but has no 'when' condition: it would run on every branch
```

Three bugs were found by my own tests while writing it: the brace-in-string test contained an unbalanced fixture of my own making, the "deployment without `when`" rule missed because the stage name was inside a string that my comment/string stripper had removed, and the missing-`agent` rule fired wrongly for `agent any` (a form my regex did not recognise). A linter of text is only as good as its tests.

## Pipeline as code, multibranch and webhooks

A **Multibranch Pipeline** job scans a repository, creates a job per branch and pull request that contains a `Jenkinsfile`, and builds them automatically. Prefer webhooks from the SCM to Jenkins (push notification) over polling. A **Pipeline Library** (Level 2 · 03, Level 4 · 03) shares common code across Jenkinsfiles. **Job DSL** and **Configuration as Code (JCasC)** describe Jenkins itself in files so a controller can be rebuilt (Level 4 · 03).

## How It Actually Works

The controller compiles the Jenkinsfile (a Groovy script run in a restricted "CPS" interpreter that makes pipelines resumable). When a stage needs an agent, the controller's scheduler (the *queue*) assigns the job to a node matching the label, sends the step instructions over the agent connection (JNLP/WebSocket or SSH), and the agent executes them (`sh` spawns a shell in the workspace). The state of the pipeline is serialized
to disk periodically, so a controller restart can resume running pipelines; this is also why long-running Groovy computation inside the pipeline itself (rather than in `sh` steps) is discouraged: that code runs on the controller. Workspaces on agents persist between builds unless cleaned (`cleanWs()`), a difference from GitHub-hosted runners, and a source of "works on the second run" bugs.

## Common mistakes

- **Building on the controller** (security and stability risk).
- **`agent any` and no timeouts.**
- **Credentials in the Jenkinsfile or interpolated into Groovy strings.**
- **Long Groovy logic in the pipeline** instead of scripts executed on the agent.
- **Never cleaning workspaces**, so stale files affect builds.
- **Unpinned plugin updates** applied in production on a Friday.
- **Pipeline configured in the UI** (freestyle jobs) instead of a versioned Jenkinsfile.
- **No backup** of the controller's home directory or its configuration as code.

## Exercise

1. Write a Jenkinsfile for a project you know: checkout, parallel lint and unit tests, package with fingerprinted artifact, deploy only from `main`, and a `post` that publishes test reports. Run the linter on it.
2. Add two lint rules of your own (for example, flag `input` steps without a timeout, or `sh` steps that use `curl | sh`) with failing tests first.
3. If you can run Jenkins in a container, submit your Jenkinsfile to its validator (`POST /pipeline-model-converter/validateJenkinsfile`) and compare its verdict with the linter's.
4. List five things you would put in Jenkins Configuration as Code so the controller can be rebuilt from Git.
