---
description: "Designing CI cache keys: what to hash, restore-key fallbacks, scope and eviction, and the failure modes that make caches slow or wrong, with keys computed."
---

# 02 · Cache Design: Keys, Scope & Poisoning

Level 1 showed that a cache hit turns a 2-second install into a near-instant restore. Here we go a step further and look at **how to design the key**, because a cache is only as good as its key. Too narrow and you never hit; too broad and you restore the wrong thing and get a build that passes for the wrong reason.

!!! note "What was run"
    Key values below were produced by `minici.cache_key` (SHA-256 of the matrix plus the contents of key files, first 16 hex digits) on a two-line `req.txt`. The *restore-key fallback* output comes from a small function I wrote that models the documented "exact key, else newest entry matching a prefix" behaviour; it is a model, **not** GitHub's cache service, which was not run. Limits quoted (10 GB per repository, eviction by age and size) are from docs.github.com as read in October 2026.

## What the key must capture

A cache entry is valid for a build if, and only if, everything that determined its contents is the same. Hash the **inputs**, not the date:

```text
base       9fd107a23ce57c5f      matrix {os: ubuntu, py: 3.12} + req.txt
same again 9fd107a23ce57c5f      deterministic: same inputs, same key
py 3.13    8e9ff372b7f5030e      different interpreter => different key
dep bumped fa9115e3be8ef890      pytest 8.0.0 -> 8.0.1 in req.txt => different key
reverted   9fd107a23ce57c5f      change it back => the original entry is a hit again
```

Four properties are visible there. The key is **deterministic**; it changes when the **lockfile** changes (so a dependency bump rebuilds the cache); it changes with the **matrix cell** (a Python 3.13 wheel set must not be restored on 3.12); and it is **reversible**, meaning an old state finds its old entry. The key should include: the OS and architecture, the language or tool version, and a hash of the file that pins the dependencies. It should *not* include a timestamp or the commit SHA, which would make every run a miss and defeat the purpose.

Hash a **lockfile**, not a loose requirements list: `flask>=3` resolves to different packages next month while its file hash stays the same, so the key says "same" while the contents differ. That is a stale-cache bug that shows up as "works on CI, differs on my laptop."

## Restore keys: partial hits

When the exact key misses (you bumped one dependency), restoring *nothing* wastes the 99% of packages that did not change. Most cache systems allow ordered **fallback prefixes**: if no exact match, restore the most recent entry whose key starts with a prefix, then save a fresh entry under the exact key at the end of the job. My model of that behaviour, with three stored entries:

```text
key pip-ubuntu-bbb2, prefixes [pip-ubuntu-]  -> exact hit
key pip-ubuntu-ddd4, prefixes [pip-ubuntu-]  -> restored pip-ubuntu-bbb2 (partial hit; save a new entry at job end)
key pip-windows-eee5, prefixes [pip-windows-] -> miss
key pip-ubuntu-ddd4, prefixes [pip-]          -> restored pip-macos-ccc3   <-- WRONG PLATFORM
```

The last line is the danger. A prefix that is too short matches an entry from a different OS, so you restore binaries that cannot run, or worse, silently pass. Make the fallback prefix contain every dimension that must match (`pip-ubuntu-3.12-`), and only drop the *content hash*.

Partial restores are safe only when the tool re-validates what it restored. `pip`, `npm`, Gradle and Maven caches are content-addressed downloads, so a stale cache just means a few extra downloads. Caching a *build output directory* (compiled objects, `node_modules` as installed state, a virtualenv) with a partial restore can leave stale files that the build does not notice; for those, prefer an exact key or a clean build.

## Scope, size and eviction

The documentation states a default limit of **10 GB of cache per repository**, with least-recently-used eviction when it is exceeded and eviction of entries not accessed for a period (seven days, as I read it). Implications:

- A big matrix with one large cache per cell can fill the budget, so the **entries evict each other** and the hit rate collapses just when the matrix grows. Cache the *download* directory, not the installed tree, and keep cells that share contents on one key.
- Caches are **scoped by branch**: a pull request can read entries made on its base branch, but not entries from sibling branches, and a PR's entries are not visible to other PRs. Warm the cache from `main` so every branch starts hot.
- Entries are **immutable**: saving under an existing key does not update it. If your key never changes while the contents do, you will restore the first version forever.

## Cache poisoning

A cache is also an *input* to later builds. If an untrusted workflow (a fork's pull request) can write an entry that a privileged workflow (a release) later restores, the attacker's code runs in the privileged job. Defences are structural, not clever: privileged jobs should not restore caches written by untrusted triggers, release builds should use exact keys scoped to protected branches, and anything you ship should be built from a **clean** (uncached) build or verified. The real check for "is the cache hiding a bug" is a periodic cold build; if cold and warm builds ever disagree, you have found a key that is too broad.

Level 1's tarball experiment is the same idea from the other side: a cache hit is only trustworthy if the build is deterministic enough that a rebuild would have produced the same bytes.

## Checklist

- The key contains the OS, architecture, tool version and a hash of the lockfile.
- The key contains no timestamp, run number or commit SHA.
- Fallback prefixes keep every dimension that must match and drop only the content hash.
- Installed state is cached only with an exact key; downloads can use fallbacks.
- Entries are warmed from the default branch so feature branches start hot.
- Release builds never restore a cache written by an untrusted trigger.
- Total cache size across all cells stays well under the repository limit.
- The hit rate is logged per job, and a job with a hit rate near zero is investigated.
- Saving happens even when a later non-critical step fails, if your platform allows it.
- A cold-cache build is run regularly and compared with the warm one.
- The pipeline prints the key and whether it hit, so a slow run can be explained.
- Cache contents never include secrets or credentials.
- Large binary caches are compressed once, not per job.
- Matrix cells that share dependencies share a key.
- Someone is responsible for deleting caches after a dependency compromise.
- Cache paths are absolute or relative to a known directory, not to a changing workspace.
- Restores are verified (a marker file or version check) before the build trusts them.
- The team can explain, in one sentence, what makes each key change.

## How It Actually Works

The cache service is a key-value store with a restore step before your job and a save step after it. On restore the runner sends the exact key and the ordered list of prefixes; the service answers with the best matching entry's archive, which the runner unpacks at the paths you configured. On save (normally in a post-job hook) the runner checks whether the exact key already exists; if so it skips the upload, otherwise it archives the paths and stores them under that key. Two consequences follow from this design. First, **save happens only if the job succeeds** by default, so a flaky test can leave you without a fresh cache and cause misses on the next run. Second, because the key is checked *before* the job and written *after*, two parallel jobs with the same key both miss and both try to save; one wins and the other is wasted work. Warm a shared cache in an early job and let matrix cells depend on it.

## Common mistakes

- **Keying on the commit SHA or date**, so every run is a cold build.
- **Hashing an unpinned requirements file** so the key does not change when the resolved packages do.
- **A fallback prefix shorter than the platform dimension**, restoring the wrong OS's files.
- **Caching installed state with partial restore** and getting stale-file bugs.
- **Never measuring the hit rate**; a cache that always misses costs time to save.
- **Writing caches from untrusted PRs** that privileged jobs later read.
- **Assuming a cache is always there**: every pipeline must work, slowly, on a miss.

## Exercise

1. Use `minici.cache_key` to show the key changes when (a) you add a trailing newline to the lockfile and (b) you change only a *comment* in a file that is not listed as a key file. Which of these results is a feature and which a hazard?
2. Run the Level 1 demo pipeline twice and then change one dependency version; record the three install times. Explain each.
3. Write a fallback prefix for a Node project cached per OS and Node major version, and say what happens on the first run after a Node upgrade.
4. Your cache is 8 GB and the repository limit is 10 GB. A matrix with 6 cells each saving 2 GB is proposed. What happens, and how do you fix it?
