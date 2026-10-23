---
description: "Running Jenkins for many teams: controller and agents, configuration as code, plugin risk, shared libraries, agent scaling, and what breaks as it grows."
---

# 03 · Jenkins at Scale

A single Jenkins server for a few jobs is easy. Jenkins as a shared platform for dozens of teams and thousands of jobs is a different system: configuration drift, plugin upgrades that break pipelines, a controller that becomes a bottleneck, and security assumptions that no longer hold. This lesson describes the common failure points and the practices that address them.

!!! note "What was run, and what wasn't"
    **No Jenkins server was run for this course.** Everything about Jenkins here is from the Jenkins documentation (jenkins.io, as read in October 2026) and general practice; I did not test configuration snippets. What I did run is the course's Jenkinsfile linter (`src/jenkinslint.py`, 11 tests; Level 1 · 04) and the runner-pool queue simulation from Lesson 02, which applies to Jenkins agents as much as to any runner pool.

## Architecture in one paragraph

A Jenkins **controller** holds configuration, job definitions, credentials and build history, schedules builds and serves the UI. **Agents** (nodes) run the work. The classic mistake is running builds on the controller itself ("built-in node"): the code under test then runs next to the credentials and configuration of every team. The documentation recommends not running builds on the controller; set its executors to zero and do everything on agents.

## What breaks as it grows

1. **Controller load.** Pipeline *scripts* run in the controller's JVM (the Groovy CPS interpreter), and heavy logic in a Jenkinsfile (large loops, JSON parsing of big payloads) burns controller CPU and memory while agents sit idle. Rule: pipelines orchestrate, **shell steps on agents compute**.
2. **Build history and disk.** Unbounded logs and artifacts fill the controller's disk. Set build discarders (keep N builds or N days) by default, and ship logs and artifacts to external storage.
3. **Plugin sprawl.** Hundreds of plugins from many maintainers: each is code running with controller privileges, with its own update cadence and vulnerabilities. Upgrading one can break another; some are abandoned. Keep the set small, track the security advisories Jenkins publishes, and test upgrades in a staging controller with copies of representative jobs first.
4. **Configuration drift.** Settings changed by clicking in the UI are not versioned, not reviewable and not reproducible. A rebuilt controller loses them.
5. **Credentials sprawl.** Credentials in the global scope are visible to every job; teams copy secrets into job configs.
6. **Groovy sandbox escapes and trusted libraries.** Pipelines run in a sandbox that restricts calls; administrators approve exceptions ("script approval"). Approving a dangerous method for convenience weakens isolation for everyone.
7. **One shared queue.** A single team's burst of 500 jobs delays everyone else's (see below).

## Practices that scale

**Configuration as Code (JCasC).** The Configuration as Code plugin describes the controller (security realm, credentials references, nodes, global settings) in YAML checked into Git and applied on start-up. Combined with a container image whose plugin list is pinned, the controller becomes disposable and reproducible: you can build a staging copy, test an upgrade, and roll back by redeploying the previous image. I did not run it; check the plugin's documentation for the schema of your version.

**Job definitions in the repository.** Use `Jenkinsfile` in each repository (and multibranch or organisation-folder jobs to discover repositories) so that pipeline changes go through code review with the code they build. Avoid hand-created freestyle jobs.

**Shared libraries** (Level 2 · 03) for the common parts, versioned and tested. A library is code that every team's pipeline trusts; treat changes with the discipline of a platform release.

**Ephemeral agents.** Create agents on demand (containers or cloud VMs), run one build, and destroy them (Level 2 · 08). Persistent agents drift, accumulate state and hold the stale-workspace problem I demonstrated with `minici`.

**Credentials scoping.** Use folder-level credential stores so a team's secrets are visible only to that team's jobs, and prefer short-lived credentials (cloud OIDC, tokens fetched at job time) to long-lived ones stored in Jenkins.

**Controller sizing and isolation.** Many organisations run several controllers, one per business unit or trust level, instead of one giant one, trading central management for blast-radius containment. Whichever model: back up the controller's home directory (with credentials encrypted) and *test the restore*.

## Queue behaviour

With a fixed set of agents, Jenkins queues builds when no executor with a matching label is free. Lesson 02's simulation (8 runners, 5-minute jobs, Poisson arrivals) applies directly:

- at 70% utilisation the mean wait was 0.56 min, at 90% it was 4.4 min, at 98% 33 min;
- at 90% utilisation, 2 executors gave a 21.5-minute mean wait, 8 gave 4.4 and 32 gave 0.74.

Real Jenkins queues add complications the model lacks: labels fragment the pool (a job waiting for a `gpu` label cannot use idle `linux` agents), job priorities, and "throttle concurrent builds" settings. Fragmentation hurts, and I measured it: at 90% utilisation one pool of 8 gave a mean wait of 4.43 min (90th percentile 12.25), while each of two separate pools of 4 at the same utilisation gave 9.96 min (90th percentile 26.03), more than double. Keep the label vocabulary small.

## Linting Jenkinsfiles

Level 1's `jenkinslint.py` catches mistakes before they run: unbalanced braces, missing `agent`, a deploy stage without an input or approval, steps with no timeout. On a deliberately bad copy of the sample Jenkinsfile it reported 4 findings; on the clean sample, none (both were recorded in Level 1 · 04). It is a text-pattern linter, not a Groovy parser, so it can be fooled. Jenkins offers a built-in validation endpoint for declarative pipelines (documented; I did not use it), which parses with the real grammar and is the better check where available.

## Upgrades and security hygiene

- Track the **Jenkins security advisories**; critical controller or plugin vulnerabilities are patched in coordinated releases, and unpatched public-facing controllers have been a frequent target.
- Use the **long-term support (LTS)** release line for controllers, upgrade on a schedule, and keep a staging controller.
- Disable anonymous access, use SSO/LDAP, apply role-based access (matrix or folder-based) with least privilege, and enable CSRF protection (default in recent versions).
- Do not expose the controller to the internet if you can avoid it; put it behind a VPN or an authenticating proxy.
- Restrict who can edit Jenkinsfiles that run in trusted contexts; **pull-request builds from forks should not get credentials**.

## When to move on

Jenkins is flexible and mature, and its flexibility is exactly the cost: the platform team maintains a lot. Reasons teams migrate (Lesson 08) include the maintenance burden, plugin risk, and wanting CI close to source hosting. Reasons to stay: heavy investment in pipelines and plugins, special integrations, on-premises requirements. Migrate for a measured reason, not fashion.

## Checklist

- Controller executors are set to zero; builds run on agents.
- The plugin list is pinned, minimal and tracked against security advisories.
- Controller configuration is code and rebuilds reproducibly.
- Build discarders are set globally.
- Credentials are scoped to folders, not global.
- Agents are ephemeral and created on demand.
- Upgrades are tested on a staging controller first.
- Backups are restored in a drill at least once a year.
- Heavy computation runs in shell steps on agents, not in Groovy.

## How It Actually Works

The controller keeps the build state in files under `JENKINS_HOME` (job configs, build records, credentials encrypted with keys stored alongside). A pipeline build is a durable state machine: the Groovy script is executed by the CPS interpreter, which serialises its program state to disk so a build survives a controller restart; steps that take time run on agents and report back. This is why a Jenkinsfile's Groovy has restrictions (not all Java constructs are serialisable) and why heavy computation in it is painful: it is interpreted, checkpointed and single-threaded per build on the controller. Agents connect to the controller over an agent protocol (inbound or outbound) and execute the shell commands and file operations the steps request; they need only enough credentials for the job at hand.

## Common mistakes

- **Running builds on the controller.**
- **Heavy Groovy logic in the Jenkinsfile.**
- **UI-only configuration** that cannot be rebuilt.
- **Unbounded build history.**
- **Approving script exceptions** casually.
- **Global credentials** visible to all jobs.
- **Skipping upgrades**, then facing a large, risky jump.
- **No tested restore** of the controller backup.
- **Label sprawl** that fragments the agent pool.

## Exercise

1. Write a checklist to audit an existing Jenkins controller against the points above and rate each answer red, amber or green.
2. Run `python3 src/jenkinslint.py` on your own Jenkinsfile and list what it cannot detect.
3. Using `src/queuesim.py`, reproduce the pool-of-8 versus pool-of-4 comparison, then try three pools of 3 and one pool of 9 and explain the trend.
4. Draft the plan for a controller upgrade: staging, which jobs you test, how you roll back, and who signs off.
