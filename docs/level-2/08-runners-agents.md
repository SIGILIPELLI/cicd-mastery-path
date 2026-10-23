---
description: "Runners and agents: hosted versus self-hosted, ephemeral versus persistent workspaces, isolation, scaling and the stale-workspace trap, with a demo."
---

# 08 · Runners & Agents: Where Your Jobs Actually Run

A pipeline definition is only instructions. The **runner** (GitHub's term) or **agent** (Jenkins') is the machine that executes them. Where it runs and what survives between jobs determines your cost, speed, security and, most surprisingly, whether your builds are *repeatable*.

!!! note "What was run, and what wasn't"
    I ran a small experiment with the Level 1 `minici` runner to show the **stale persistent workspace** problem (output below). I did **not** register a self-hosted runner, run a Jenkins agent, or measure autoscaling. Descriptions of GitHub-hosted and self-hosted runners and the documented limits come from docs.github.com as read in October 2026 (hosted job limit 6 hours, self-hosted job limit 5 days). Jenkins agent behaviour is from jenkins.io and not run.

## Hosted vs self-hosted

| | Hosted (provided by the CI vendor) | Self-hosted (you run the machine) |
|---|---|---|
| Setup | None | Install the runner/agent, keep it patched |
| Isolation | A fresh VM per job, discarded afterwards | Whatever you build: VM, container, or bare machine reused |
| Hardware | Vendor's sizes (larger ones cost more) | Anything: GPUs, ARM, mainframes, private network access |
| Cost | Per minute (some free allowance) | Machines, power, people |
| Network | Public internet | Can reach your private systems |
| Max job time | 6 hours (hosted, documented) | 5 days (self-hosted, documented) |

Choose self-hosted for a **reason**: needing special hardware, reaching a private network, very large caches, or cost at high volume. "It is cheaper" is true only after you count the engineers who patch it.

## Ephemeral vs persistent

The more important axis is whether a runner is **reused**.

- **Ephemeral:** a runner takes one job, then is destroyed (a fresh VM or a container). Every job starts from a known image. Nothing leaks from one job to the next. This is the default for hosted runners and recommended for self-hosted when jobs may run untrusted code.
- **Persistent:** the machine lives on and runs many jobs. Faster (warm caches, installed tools) but jobs share a filesystem, a Docker daemon, and any lingering process.

### The stale-workspace demonstration

I wrote a one-step pipeline whose test passes **only if a leftover file from an earlier run is present**, a deliberately silly stand-in for a build that reads a stale cache, an installed package, or an uncleaned output directory. Running it twice in the same working directory:

```text
run 1: no cache: building from scratch              RESULT: failure
run 2: using stale cache from a previous build -> passes    RESULT: success
```

Same pipeline, same commit, different result, because run 1 created `.cache_ok` and run 2 found it. On a persistent runner the *second* build is green only because of the first. A fresh clone, a new developer, or a new runner would fail. This is the most common cause of "works in CI, fails on a clean checkout", and the reverse, "passed until we replaced the agent".

Persistent runners hide dependencies in many forms: a globally installed package, a tool version the image drifted to, a file in `/tmp`, a running background process holding a port, a Docker image or volume left behind, an environment variable set once by hand. Mitigations:

- **Clean the workspace** at the start of every job (Jenkins `cleanWs()`, a fresh `git clean -ffdx`, or `actions/checkout` with `clean: true`, which is its default behaviour per the docs).
- Run jobs in **containers** or fresh VMs so the base is rebuilt each time.
- **Rebuild the persistent machine image** on a schedule from code, so nothing is hand-maintained.
- Run a periodic **clean-room** build on an ephemeral runner and alert if it disagrees with the persistent-runner build.

## Isolation and security

A runner executes code from your repository; with pull requests, that code may be written by someone you do not know. Consequences for self-hosted runners (and a reason the GitHub documentation warns about using them with public repositories):

- A persistent runner that runs a malicious PR's job can **leave behind** a backdoor, steal credentials from the environment, or poison caches for the next, privileged job.
- Anything the runner's network can reach, the job can reach: internal APIs, metadata endpoints, other build agents.
- Give runners **narrow credentials**, separate pools for trusted (protected branches) and untrusted (forks) work, and ephemeral lifetimes so each job starts clean.

Docker-in-Docker or a mounted Docker socket on a shared agent hands the job root-equivalent power on the host (Lesson 04).

## Labels, pools and queueing

Both systems route jobs to runners by **labels**: `runs-on: [self-hosted, linux, gpu]` or Jenkins `agent { label 'linux && docker' }`. A job whose labels no runner has just waits in the queue (check your platform's queue timeout), a frustrating failure that looks like "the pipeline is stuck". Keep a short, documented label vocabulary.

Capacity planning is queueing: if jobs arrive faster than the pool can serve them, they wait, and wait time grows non-linearly as utilisation approaches 100%. A pool at 90% average utilisation has long queues at peak because arrivals are bursty (everyone pushes at 9:30). Autoscaling (create runners on demand from a pool, destroy after use) trades some startup latency, often tens of seconds to minutes, for avoiding idle machines; I measured none of this.

## Disk, tools and drift

A persistent agent accumulates workspaces, Docker layers and caches until the disk fills, and then jobs fail with unrelated "no space left on device" errors (Linux course, Level 1 · 03: inodes). Schedule cleanups and alert on free space. Pin tool versions explicitly in the job (`setup-python` with a version) instead of relying on what the image happens to have, so an image update cannot change your build silently.

## Checklist

- Jobs that run untrusted code use ephemeral runners.
- Persistent runners clean the workspace at the start of every job.
- Tool versions are pinned in the job, not inherited from the image.
- Runner images are rebuilt from code on a schedule.
- Disk space, queue length and runner health are monitored and alerted.
- Label vocabulary is short and documented.
- Credentials are issued per job, not baked into the image.
- Pools are sized for the peak wait target, not the average load.

## How It Actually Works

A runner is a small agent process that holds a connection (long-polling or a persistent socket) to the CI server and asks for work. When the server assigns a job it sends the steps and a short-lived token; the runner checks out code, executes each step as a child process, streams logs back, and reports an exit status per step. Self-hosted GitHub runners make *outbound* connections only, which is why they work behind firewalls without inbound ports. Jenkins agents historically connect inbound from the controller over SSH or outbound via a JNLP/WebSocket connection. The runner has no idea whether the machine is clean; cleanliness is a property of how you provision the machine around the agent, which is why the ephemeral pattern (create from an image, register, run one job, destroy) is the only design in which "clean" is guaranteed by construction, not by discipline.

## Common mistakes

- **Persistent runners with no cleanup**, accumulating stale state and disk usage.
- **Self-hosted runners on public repositories** without isolation.
- **Relying on whatever is installed** on the image rather than pinning versions.
- **One shared pool for trusted and untrusted work.**
- **Label sprawl** and jobs that wait forever for a label nobody serves.
- **Sizing the pool for the average** rather than the peak.
- **Credentials baked into the runner image** instead of issued per job.

## Exercise

1. Reproduce the stale-workspace demo with `minici`. Add a `clean` step at the start and show the first run now fails every time. Is that better or worse? Explain.
2. List five things that could silently persist on a long-lived Jenkins agent and write one check or cleanup for each.
3. Your pool serves 8 jobs at once; jobs average 5 minutes and arrive at roughly 90 per hour in a burst at 9:30. Estimate the queueing time and propose a fix.
4. Write the isolation rules for a runner that builds pull requests from forks.
