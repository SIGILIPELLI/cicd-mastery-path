---
description: "Audit and compliance for pipelines: separation of duties, evidence, retention and a hash-chained log whose gaps are tested."
---

# 05 · Audit & Compliance

Regulated environments, customer security reviews and ordinary incident investigations all ask the same questions about your delivery process: **who changed what, who approved it, what was deployed, and can you prove it?** Compliance frameworks (SOC 2, ISO 27001, PCI DSS, HIPAA and others) phrase this differently, but a pipeline that records the right facts, controls who can act and keeps evidence will answer most of the technical questions. This lesson is about building that pipeline; it is not legal or audit advice, and I did not consult any framework text for this lesson.

!!! note "What was run"
    `src/auditlog.py` (a hash-chained audit log, 9 tests) was written and run. The log is a teaching model of tamper evidence; it is **not** a certified audit system and does not satisfy any specific regulation on its own. Statements about what auditors typically expect are general, from my background knowledge, and must be checked against the framework and auditor you actually face.

## What an auditor wants to see

Translate the typical control objectives into pipeline facts:

| Question | Evidence the pipeline should produce |
|---|---|
| Was this change reviewed by someone other than its author? | Pull-request approvals, with identities and timestamps, enforced by branch protection (not just policy) |
| Was it tested and scanned? | Required-check results tied to the exact commit |
| Who approved the production deployment? | Environment approval record (Level 2 · 07), with approver identity |
| What exactly was deployed? | Version, artifact digest, commit SHA, build ID (Level 3 · 07 traceability) |
| Could the same person write, approve and deploy a risky change? | Access reviews showing separation of duties |
| Were emergency changes handled properly? | Break-glass records with after-the-fact review |
| Can anyone tamper with the history? | Immutable or tamper-evident logs, restricted deletion rights |
| Is access reviewed? | Periodic access review output for repositories, runners, secrets |

## Separation of duties

The principle: no single person should be able to push a change **and** approve it **and** deploy it **and** erase the record. In pipeline terms:

- **Branch protection** requires at least one approval from someone who is not the last pusher, with dismissal of stale approvals on new commits. (Platform settings, not the course's code; check what your plan supports.)
- **CODEOWNERS** for the pipeline files themselves, so changing the gates needs a review by the platform team.
- **Environment protection** with reviewers other than the triggering user and "prevent self-review" on (Level 2 · 07).
- **Administrators can bypass** protections on many platforms; either disable bypass for production repositories or log and alert whenever it is used.
- For **small teams** where full separation is impractical, document compensating controls: post-hoc review of every production deploy, extra alerting.

## Evidence: make it automatic, not archaeological

Collecting screenshots before an audit is expensive and incomplete. Instead have the pipeline write an **evidence record** at deploy time: who triggered, commit, artifact digest, approvals (from the platform's API), test result IDs, scan results, timestamps. Store it outside the CI system (a write-once bucket or log store) because CI retention is limited (logs, artifacts and run records expire; Lesson 04) and CI administrators can alter things.

Keep the **mapping from deploy to change request** if your organisation uses tickets: a commit message or PR template field with the ticket ID, validated by a check, so the link is machine-readable.

## A tamper-evident log, built and tested

A log that can be quietly edited is weak evidence. A cheap strengthening is to chain the records: each stores the hash of the previous one plus its own content, so changing any earlier record invalidates every later hash.

```python
def append(log, event):
    prev = log[-1]["hash"] if log else GENESIS
    log.append({"event": event, "prev": prev, "hash": sha256(prev + canonical_json(event))})
```

`verify(log)` recomputes the chain and returns the index of the first bad record. The nine tests establish what it does and **what it does not**:

| Attack on a 3-record log | Detected? |
|---|---|
| Edit a field in record 1 (version changed to `9.9.9`) | Yes: reported at index 1 |
| Delete record 1 | Yes: index 1 (the next record's `prev` no longer matches) |
| Swap records 1 and 2 | Yes: index 1 |
| Insert a forged record at position 1 | Yes: index 1 |
| Change the first record | Yes: index 0 |
| **Truncate the tail** (drop the last record) | **No**: the remaining chain is internally consistent |
| **Rewrite the whole chain** consistently | **No**: a forger who can recompute hashes can make a valid chain |

The last two rows are the honest limit, and the tests include them *as tests of the known gaps* so nobody mistakes the log for more than it is. The defence is to **anchor** the head hash outside the attacker's reach: publish it periodically to a different system (a separate account, an append-only store, a timestamping service, or even a signed commit), so a later rewrite cannot reproduce the published head. Digital signatures per record (Level 3 · 08) add authenticity for records written by the system. Using a managed immutable storage feature (object lock or write-once retention) offers a similar guarantee by a different mechanism; I did not run any.

Also decide what goes into the log. Record the **minimum needed**: identities, actions, object identifiers, timestamps, outcomes. Do not record secrets or personal data beyond what is necessary; an audit log is a long-lived data store with its own privacy obligations.

## Retention and time

Compliance regimes often require retaining evidence for a fixed period (commonly measured in years; the number depends on the framework, jurisdiction and contract: **check yours**). Plan for it: export logs before platform retention expires, keep clocks synchronised (timestamps from different systems must be comparable: use UTC and NTP-synced hosts), and test that you can actually retrieve a record from three years ago in a readable format.

## Emergency changes

Production incidents need fast changes. A **break-glass** procedure allows an authorised person to bypass the normal approval, with controls: it is rare, it raises an alert, the reason is recorded, and a review within a defined time confirms the change was legitimate and brings the code back through the normal process. Count break-glass uses; a high number means the normal path is too slow (see Lesson 02, and the delivery metrics of Level 3 · 09).

## Compliance as code

Express controls as checks that run continuously, not as annual documents: a scheduled job that queries repository settings and fails if any production repository lacks branch protection; a policy check on infrastructure plans (Level 3 · 05); a report of secrets older than the rotation period; an alert when a workflow uses a disallowed trigger. The output of those checks is itself evidence. Beware of **checkbox compliance**: passing an audit and being secure are different things, and the threat model (Lesson 01) is what tells you which controls matter.

## How It Actually Works

A cryptographic hash chain turns a sequence of records into a structure where each element commits to everything before it. Changing record *k* changes its hash, which is part of record *k+1*'s input, so `verify` finds the first mismatch. This is the same construction as a Git history (each commit includes its parent's hash, which is why rewriting history changes every descendant's ID) and as the Merkle structures behind transparency logs. What it cannot provide is *completeness* (that no record was dropped from the end) or *authorship* (who wrote it), because both require a reference that lives outside the chain: an externally published head, or signatures. All audit-log designs reduce to "who holds the reference copy, and can the writer alter it?"

## Common mistakes

- **Controls that exist only as policy**, not enforced by the platform.
- **Evidence kept only in the CI system**, subject to retention and admin edits.
- **Admins able to bypass** protections silently.
- **Logs with no anchor**, trusting chain integrity alone.
- **Secrets or personal data in audit logs.**
- **Unsynchronised clocks** across systems.
- **Break-glass used routinely.**
- **Annual evidence scramble** instead of continuous checks.

## Exercise

1. Run `pytest src/test_auditlog.py -v`. Modify `verify` to also accept an expected head hash, and add a test that truncation is now detected.
2. List the evidence you would need to answer "who approved the production deployment of version X last March?" and where each piece lives today. Which would have expired?
3. Design the break-glass procedure for your team: who may use it, what it alerts, and how the review works.
4. Write three compliance-as-code checks for your GitHub or Jenkins setup, with the query each runs and the failure condition.
