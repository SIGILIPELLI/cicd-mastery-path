---
title: "Final Quiz"
description: "Test what you have learned across all four levels of CI/CD Mastery Path with a 19-question final quiz."
---

# Final Quiz

19 questions drawn from all four levels of this course. You need **70% (14 out of 19)** to pass —
you can retake it as many times as you like. Your best result is saved in this browser.

<div id="mp-quiz-root"></div>

<script type="application/json" id="mp-quiz-data">
[
  {
    "question": "Which statement best distinguishes continuous delivery from continuous deployment?",
    "options": [
      "Deployment is only for mobile apps",
      "They are identical",
      "Delivery has no tests",
      "Delivery keeps every passing change releasable with a human release decision; deployment releases every passing change automatically"
    ],
    "correctIndex": 3,
    "explanation": "The difference is the manual gate."
  },
  {
    "question": "Same two failing checks: unit (0.1 s) and integration (3 s). Which order gives the fastest feedback?",
    "options": [
      "Unit first, then integration: you learn about the failure in 0.1 s instead of 3.1 s",
      "Order never matters",
      "Integration first",
      "Both parallel never helps"
    ],
    "correctIndex": 0,
    "explanation": "Order gates by cost and likelihood of failing."
  },
  {
    "question": "A team deploys with `image: python:3.12-slim` and sees a surprise change. Why?",
    "options": [
      "The matrix changed",
      "Docker is nondeterministic",
      "The runner is stale",
      "Mutable tags can move to a different image; pin by digest"
    ],
    "correctIndex": 3,
    "explanation": "Pinned inputs make builds reproducible."
  },
  {
    "question": "A cache key is the date. What goes wrong?",
    "options": [
      "It ignores the inputs: stale dependencies are restored after a lockfile change, or the cache misses daily; hash the lockfile instead",
      "The key is too short",
      "Nothing",
      "Caches are slower"
    ],
    "correctIndex": 0,
    "explanation": "Hash inputs, not time."
  },
  {
    "question": "A 500-test suite where every test flakes 1% of the time is green how often on correct code?",
    "options": [
      "About 0.7% ((0.99)^500)",
      "About 50%",
      "About 37%",
      "About 99%"
    ],
    "correctIndex": 0,
    "explanation": "Flakes compound, so a flake budget matters."
  },
  {
    "question": "The module has 100% coverage but a pricing bug passed CI. What was missing?",
    "options": [
      "More lines of code",
      "Assertions: coverage shows what ran, not that outputs were checked; consider mutation testing",
      "Faster runners",
      "A larger matrix"
    ],
    "correctIndex": 1,
    "explanation": "Weak and strong suites can have identical coverage."
  },
  {
    "question": "A PR passes on its branch but main breaks after merging. What should the PR check run on?",
    "options": [
      "The base branch",
      "The latest tag",
      "The merged result (what will actually land on main), ideally via a merge queue",
      "The branch tip only"
    ],
    "correctIndex": 2,
    "explanation": "Two green branches can combine into a red build."
  },
  {
    "question": "Which setup limits damage if a PR from a fork is malicious?",
    "options": [
      "No secrets for fork PRs, least-privilege token, and no pull_request_target checkout of untrusted code",
      "Give it production secrets",
      "Disable branch protection",
      "Run on persistent self-hosted runners"
    ],
    "correctIndex": 0,
    "explanation": "Untrusted code must not meet privileged credentials."
  },
  {
    "question": "How should third-party actions be referenced?",
    "options": [
      "@latest",
      "Unpinned",
      "Pinned to a full commit SHA (tags can be moved)",
      "@main"
    ],
    "correctIndex": 2,
    "explanation": "Rule W003 in the course linter."
  },
  {
    "question": "A deploy job lacks `concurrency:`. What can happen?",
    "options": [
      "Faster deploys",
      "Nothing",
      "Two runs deploy at once and the older run may finish last, leaving the old version live",
      "Secrets leak"
    ],
    "correctIndex": 2,
    "explanation": "Serialise deploys per environment."
  },
  {
    "question": "Production approvals should live where?",
    "options": [
      "On a protected environment with required reviewers and environment-scoped secrets",
      "In a repository secret",
      "In a Slack thread",
      "In a comment"
    ],
    "correctIndex": 0,
    "explanation": "Protection rules gate secrets and jobs."
  },
  {
    "question": "You must rename a database column during a rolling deploy. What's the safe sequence?",
    "options": [
      "Expand (add nullable new column), migrate data and code, then contract (drop the old column) in a later release",
      "RENAME COLUMN at once",
      "Drop then add",
      "Lock the table and deploy"
    ],
    "correctIndex": 0,
    "explanation": "Old and new code overlap during rollouts."
  },
  {
    "question": "Which cannot be fixed by a rollback?",
    "options": [
      "A destructive schema change, sent emails and payments",
      "An app image",
      "A feature flag",
      "A bad config value"
    ],
    "correctIndex": 0,
    "explanation": "Rollbacks restore code, not data or side effects."
  },
  {
    "question": "Which deployment strategy gives instant switch-back but costs a whole second environment?",
    "options": [
      "Rolling",
      "Recreate",
      "Blue-green",
      "Canary"
    ],
    "correctIndex": 2,
    "explanation": "Keep the old environment alive until the new one is proven."
  },
  {
    "question": "A canary at 1% of 20,000 requests gets 200 canary requests. Why does the simulator wait for a minimum sample?",
    "options": [
      "Small samples let a single error burst look like a real regression",
      "To use less traffic",
      "To save compute",
      "Because z is undefined"
    ],
    "correctIndex": 0,
    "explanation": "min_canary protects against noise."
  },
  {
    "question": "Which two DORA measures describe stability?",
    "options": [
      "Change failure rate and time to restore",
      "Cache hit and flake rate",
      "Coverage and lint",
      "Deployment frequency and lead time"
    ],
    "correctIndex": 0,
    "explanation": "The other two describe speed."
  },
  {
    "question": "A pipeline's wall-clock time is 18 minutes but billed minutes are 37. Why do they differ?",
    "options": [
      "Billing is wrong",
      "Caching is off",
      "Wall-clock follows the critical path; billed time sums every job and matrix cell",
      "Jobs run twice"
    ],
    "correctIndex": 2,
    "explanation": "Parallelism trades one for the other."
  },
  {
    "question": "A secret was pushed to a public repo and removed in the next commit. What now?",
    "options": [
      "Rewrite the README",
      "Revoke and rotate it immediately: Git history and forks keep it",
      "Wait a week",
      "Nothing, it's removed"
    ],
    "correctIndex": 1,
    "explanation": "Revoke first, investigate second."
  },
  {
    "question": "A migration from Jenkins to Actions is planned. What comes before converting pipelines?",
    "options": [
      "Deleting jobs",
      "Turning off Jenkins",
      "Inventory: triggers, tools, credentials, runners and downstream consumers",
      "Picking colors"
    ],
    "correctIndex": 2,
    "explanation": "You can't migrate what you haven't found."
  }
]
</script>

## Coding challenges

Try these on your own computer, then compare your output. Nothing you write is sent anywhere.

### Expand a build matrix

Implement expand_matrix(): the Cartesian product of the list-valued keys, remove combinations that match every key of an `exclude` entry, then apply each `include` (extend matching cells, or add a new job if it matches none). The sample matrix should yield 9 jobs.

**Starter code**

```yaml
import itertools

def expand_matrix(matrix):
    # Cartesian product of the list-valued keys, minus `exclude` matches,
    # then `include`: extend matching cells or add a new job if none match.
    return []

matrix = {
    "os": ["ubuntu", "windows", "macos"],
    "python": ["3.11", "3.12", "3.13"],
    "exclude": [{"os": "macos", "python": "3.11"}],
    "include": [{"os": "ubuntu", "python": "3.14", "experimental": True}],
}
jobs = expand_matrix(matrix)
print(len(jobs))
for j in jobs:
    print(j["os"] + "/" + j["python"] + (" (experimental)" if j.get("experimental") else ""))
```

**Expected output**

```text
9
ubuntu/3.11
ubuntu/3.12
ubuntu/3.13
windows/3.11
windows/3.12
windows/3.13
macos/3.12
macos/3.13
ubuntu/3.14 (experimental)
```

<details><summary>Show solution and explanation</summary>

<pre><code>import itertools

def expand_matrix(matrix):
    include = matrix.get(&quot;include&quot;, [])
    exclude = matrix.get(&quot;exclude&quot;, [])
    keys = [k for k in matrix if k not in (&quot;include&quot;, &quot;exclude&quot;)]
    combos = [dict(zip(keys, v)) for v in itertools.product(*(matrix[k] for k in keys))]
    combos = [c for c in combos if not any(all(c.get(k) == v for k, v in ex.items()) for ex in exclude)]
    for inc in include:
        orig = {k: v for k, v in inc.items() if k in keys}
        matched = [c for c in combos if all(c[k] == v for k, v in orig.items())] if orig else []
        if matched:
            for c in matched:
                c.update(inc)
        else:
            combos.append(dict(inc))
    return combos

matrix = {
    &quot;os&quot;: [&quot;ubuntu&quot;, &quot;windows&quot;, &quot;macos&quot;],
    &quot;python&quot;: [&quot;3.11&quot;, &quot;3.12&quot;, &quot;3.13&quot;],
    &quot;exclude&quot;: [{&quot;os&quot;: &quot;macos&quot;, &quot;python&quot;: &quot;3.11&quot;}],
    &quot;include&quot;: [{&quot;os&quot;: &quot;ubuntu&quot;, &quot;python&quot;: &quot;3.14&quot;, &quot;experimental&quot;: True}],
}
jobs = expand_matrix(matrix)
print(len(jobs))
for j in jobs:
    print(j[&quot;os&quot;] + &quot;/&quot; + j[&quot;python&quot;] + (&quot; (experimental)&quot; if j.get(&quot;experimental&quot;) else &quot;&quot;))
</code></pre>

<p>3x3 = 9 combinations, minus macos/3.11, plus an include for 3.14 that matches no existing cell and therefore becomes a new job: 9. Verified by running the solution.</p>
</details>

### Critical path and billed minutes

Given the job graph, compute the critical path (the longest chain of dependent jobs, in minutes) and the total billed minutes (minutes x matrix cells summed over all jobs).

**Starter code**

```yaml
JOBS = {
    "lint":   {"minutes": 1,  "cells": 1, "needs": []},
    "build":  {"minutes": 4,  "cells": 1, "needs": []},
    "unit":   {"minutes": 6,  "cells": 3, "needs": ["build"]},
    "e2e":    {"minutes": 12, "cells": 1, "needs": ["build"]},
    "deploy": {"minutes": 2,  "cells": 1, "needs": ["unit", "e2e"]},
}

def critical_path(jobs):
    # longest chain of dependent jobs: return (total minutes, [job names in order])
    return 0, []

def billed(jobs):
    # compute minutes: sum of minutes x cells over every job
    return 0

length, path = critical_path(JOBS)
print("critical path: %.1f minutes  %s" % (length, " -> ".join(path)))
print("billed minutes:", billed(JOBS))
```

**Expected output**

```text
critical path: 18.0 minutes  build -> e2e -> deploy
billed minutes: 37
```

<details><summary>Show solution and explanation</summary>

<pre><code>JOBS = {
    &quot;lint&quot;:   {&quot;minutes&quot;: 1,  &quot;cells&quot;: 1, &quot;needs&quot;: []},
    &quot;build&quot;:  {&quot;minutes&quot;: 4,  &quot;cells&quot;: 1, &quot;needs&quot;: []},
    &quot;unit&quot;:   {&quot;minutes&quot;: 6,  &quot;cells&quot;: 3, &quot;needs&quot;: [&quot;build&quot;]},
    &quot;e2e&quot;:    {&quot;minutes&quot;: 12, &quot;cells&quot;: 1, &quot;needs&quot;: [&quot;build&quot;]},
    &quot;deploy&quot;: {&quot;minutes&quot;: 2,  &quot;cells&quot;: 1, &quot;needs&quot;: [&quot;unit&quot;, &quot;e2e&quot;]},
}

def finish_times(jobs):
    done = {}
    def finish(name):
        if name not in done:
            start = max((finish(n) for n in jobs[name][&quot;needs&quot;]), default=0)
            done[name] = start + jobs[name][&quot;minutes&quot;]
        return done[name]
    for n in jobs:
        finish(n)
    return done

def critical_path(jobs):
    done = finish_times(jobs)
    end = max(done, key=done.get)
    path = [end]
    while jobs[path[-1]][&quot;needs&quot;]:
        path.append(max(jobs[path[-1]][&quot;needs&quot;], key=lambda n: done[n]))
    return done[end], list(reversed(path))

def billed(jobs):
    return sum(j[&quot;minutes&quot;] * j[&quot;cells&quot;] for j in jobs.values())

length, path = critical_path(JOBS)
print(&quot;critical path: %.1f minutes  %s&quot; % (length, &quot; -&gt; &quot;.join(path)))
print(&quot;billed minutes:&quot;, billed(JOBS))
</code></pre>

<p>build (4) -&gt; e2e (12) -&gt; deploy (2) = 18 minutes of waiting, while billed time is lint 1 + build 4 + unit 6x3 + e2e 12 + deploy 2 = 37. Verified by running the solution.</p>
</details>
