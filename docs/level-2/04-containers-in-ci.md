---
description: "Containers and service containers in CI: image pinning, layer caching, waiting for a database to be ready, with a tested wait-for-port helper."
---

# 04 · Containers in CI: Images, Services & Readiness

Containers appear in CI in three roles: the **environment** your job runs in (`container:` or a Docker agent), **services** your tests talk to (a database, a cache, a message broker), and the **artifact** your pipeline produces (an image you build and push). Each has its own failure modes. The most common one is mundane: the test starts before the database accepts connections.

!!! note "What was run, and what wasn't"
    **No container was built or run**: there is no container runtime on the machine used for this course. The `Dockerfile`, `container:` and `services:` snippets are from docs.github.com and docs.docker.com as read in October 2026 and are **untested**. What I did run is the readiness helper `waitfor.py` (4 pytest tests against real local sockets), which is the part of this lesson you can verify without Docker.

## Containers as the job environment

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    container: python:3.12-slim        # steps run inside this image
    services:
      db:
        image: postgres:16
        env: {POSTGRES_PASSWORD: ${{ secrets.TEST_DB_PASSWORD }}}
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s --health-retries 10
    steps:
      - uses: actions/checkout@<full-sha>
      - run: pytest         # reaches the database at host `db`, port 5432
```

Documented behaviour: with `container:` set, the job's steps run inside that image and service containers are reachable by their **service name** over a private network. Without `container:` (steps on the runner itself) services are reached on `localhost` through published ports. Mixing the two up is a classic `connection refused`.

Benefits: the environment is described in one line and is identical for everyone who uses that image tag. Risks: the tag is *mutable*. `python:3.12-slim` changes when a new patch release is published, so a green pipeline can turn red with no commit. Pin the **digest** (`python@sha256:...`) for reproducibility and update it deliberately with a bot, or accept the drift knowingly and watch for it.

## Readiness: "started" is not "ready"

A service container is *started* when its process launches. It is *ready* when it accepts the first query, which for a database can be seconds later, after crash recovery and initialization. A health check in the service `options` makes the platform wait until the container reports healthy before running your steps; the Docker daemon runs the command at the interval and marks the container healthy after it passes, unhealthy after the configured retries.

When you cannot rely on that (a service started by your own script, a local compose stack), wait explicitly. Waiting with a fixed `sleep 10` is wrong both ways: too short on a slow runner (flaky), too long on a fast one (wasted minutes on every run). Wait for the **condition**, with a **deadline**:

```python
def wait_for_port(host, port, timeout=30.0, initial=0.1, factor=2.0, max_delay=2.0, ...):
    deadline, delay, attempts = clock() + timeout, initial, 0
    while True:
        attempts += 1
        try:
            with socket.create_connection((host, port), timeout=...): return attempts
        except OSError:
            if clock() + delay > deadline: raise NotReady(...)
            sleep(delay); delay = min(delay * factor, max_delay)
```

The four tests (all passed; the full file is `src/waitfor.py` with `src/test_waitfor.py`):

1. A service already listening returns on the **first attempt**.
2. A service that starts 0.6 s late (a thread binds the port after a delay) is detected: more than one attempt, and elapsed time between 0.5 s and 3 s.
3. A port nobody listens on raises `NotReady` with a message naming host, port, attempts and timeout, after ~0.5 s.
4. The backoff delays, driven by a fake clock so the test is instant and deterministic, are exactly `[0.1, 0.2, 0.4, 0.8, 1.0]` then capped at 1.0.

Test 4 injects `clock` and `sleep`. Injecting time is the technique that makes retry logic testable without making the test suite slow or flaky; the alternative is a test that really sleeps for ten seconds.

A TCP connect proves the port is open, **not** that the application is ready (some servers accept connections before they can serve queries). Prefer a protocol-level check where one exists (`pg_isready`, a `PING` to Redis, an HTTP `/health` that touches its dependencies) and use the port check only as the first gate.

## Building images in a pipeline

Image builds use layer caching: Docker reuses a layer when the instruction and its inputs are unchanged. Order the Dockerfile from least to most frequently changing, or the cache is invalidated early:

```dockerfile
FROM python:3.12-slim@sha256:<digest>
WORKDIR /app
COPY requirements.txt .             # changes rarely
RUN pip install --no-cache-dir -r requirements.txt     # cached until requirements change
COPY . .                            # changes every commit; keep it last
```

Putting `COPY . .` first would invalidate the dependency layer on every commit. On hosted runners the layer cache from the previous run is gone unless you export it (a registry cache, or the platform's cache backend); this is the same keying problem as Lesson 02, with the same poisoning concerns. Tag images with an **immutable identifier** (the commit SHA or a version), push `latest` only as a convenience, and deploy by digest. Never bake secrets into a layer: they remain in the image history even if a later layer deletes them (Lesson 08 of Level 1).

## Containers and the Docker socket

Mounting `/var/run/docker.sock` into a job container gives that job control of the host's Docker daemon, which is effectively root on the host. Treat it as a privileged configuration that untrusted pull requests must never reach. Alternatives are rootless builders (BuildKit, Kaniko, Buildah) that build without the host daemon.

## How It Actually Works

Service containers on a hosted runner are ordinary containers started by the runner before your steps, attached to a user-defined Docker network. That network provides DNS, so the name `db` resolves to the container's address; this is why the service name works inside a `container:` job. When the job is not itself in a container, the runner has to publish the service's port on the host, so you connect to `localhost:<mapped-port>`. The health check is the daemon's `HEALTHCHECK` machinery: it executes your command *inside* the service container periodically and tracks consecutive failures. The runner waits for the healthy state with its own timeout before starting step one. All of this disappears when the job ends: containers and the network are torn down, so service state (a seeded database) never persists between runs, which is a feature for isolation and a cost for slow seeding.

## Common mistakes

- **`sleep N` instead of waiting on a condition.**
- **Mutable image tags** that change under a green pipeline.
- **`localhost` vs service name confusion** between container and non-container jobs.
- **Declaring "ready" on an open port** while the application is still initializing.
- **`COPY . .` before dependency install**, defeating layer caching.
- **Secrets passed as build arguments** or copied into layers.
- **Mounting the Docker socket** into jobs that run untrusted code.
- **Retries with no deadline**, which turn an outage into a hung job.

## Exercise

1. Run `pytest src/test_waitfor.py -v` and read the fake-clock test. Add a fifth test where the service appears after exactly two failed attempts and assert the returned attempt count.
2. Write a `HEALTHCHECK` or `--health-cmd` for a Redis service and say what exit codes mean to Docker.
3. Reorder a Dockerfile of your own so dependency installation is cached, and describe how you would prove the layer was reused (build twice and compare the output).
4. Explain why a database seeded with 2 GB of test data in a service container may be slower than restoring it from a cache, and how you would measure it.
