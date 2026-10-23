---
description: "Feature flags: separating deploy from release, deterministic percentage rollout by hashing, kill switches, flag debt, with a tested evaluator."
---

# 02 · Feature Flags: Decoupling Deploy from Release

A **deploy** puts code on servers. A **release** exposes behaviour to users. Without flags, those are one event, so every deploy is a launch and every launch is a risk. A **feature flag** is a runtime condition around new behaviour: `if flag("new-checkout", user): ... else: ...`. Code ships dark, then is turned on for staff, 1% of users, 10%, everyone, or turned off again in seconds without a deploy.

!!! note "What was run"
    The flag evaluator in `src/flags.py` and its 8 pytest tests were written and run here. The percentage-rollout numbers come from hashing 20,000 synthetic user IDs. Hosted flag services (LaunchDarkly, Unleash, OpenFeature-compatible systems) were not used; the descriptions of what such services provide are general, not product claims.

## Deterministic percentage rollout

The core design question: how do you serve a feature to "10% of users" so that a given user gets a consistent answer, and so that going from 10% to 20% only *adds* users? Random choice per request fails both. The standard answer is to hash a stable identifier into a bucket:

```python
def bucket(flag, user_id, buckets=10000):
    h = hashlib.sha256(f"{flag}:{user_id}".encode()).digest()
    return int.from_bytes(h[:8], "big") % buckets

# rule {"percent": 10} serves the user when bucket < 10 * 100 = 1000 of 10000
```

Measured:

```text
flag 10% over 20,000 users -> 2007 enabled  (10.04%)
5,000 users at 10% -> 483 enabled, at 20% -> 989 enabled, 10%-set is a subset of the 20%-set: True
```

The share is within a few hundredths of a percent of the target and, because the bucket depends only on `(flag, user)`, **raising the percentage never removes anyone** (the subset test). Salting the hash with the flag name matters: without it every flag would use the same bucket for a user, so the same 10% of users would be the guinea pigs for every experiment. A test confirms the same user lands in different buckets for different flags.

## Rules, defaults and the kill switch

The evaluator walks an ordered rule list, first match wins:

1. Attribute rules (`email_domain == corp.example` → on) for staff dogfooding.
2. Percentage rule (10% on).
3. Otherwise the flag's **default**.

An `enabled: false` switch short-circuits everything and returns the default. The test `test_kill_switch_overrides_rules` verifies that even rules that would serve `True` are ignored. The kill switch is the safety feature that makes flags worth having, and it must work **without a deploy** and **without the flag service being healthy**: if the flag backend is down, the client must fall back to a safe built-in default, not throw.

Define "safe default" per flag. For a risky new path it is off; for a flag that disables a *dangerous* old behaviour it may be on. Decide in code review.

## Types of flags have different lifetimes

| Type | Purpose | Lifetime |
|---|---|---|
| **Release flag** | Hide unfinished or risky work | Days to weeks, then delete |
| **Experiment flag** | A/B test with measurement | Until the experiment concludes |
| **Ops flag / kill switch** | Disable a feature under load or incident | Long-lived by design |
| **Permission flag** | Entitlements per customer | Long-lived (really a product feature) |

Most flag trouble comes from treating them alike. Release flags are supposed to be **deleted** after rollout.

## Flag debt

Every flag doubles the states your code can be in: two flags give four combinations, ten give 1,024, and nobody tests them all. Old flags left in place make code hard to read, hide dead branches, and eventually the "off" path rots because nobody runs it, so the kill switch no longer works when needed. Practices that keep this under control:

- Every release flag has an **owner and an expiry date** at creation, and a ticket to remove it.
- A report lists flags that have been 100% on (or off) for more than N days.
- CI checks that **both** states of a new flag are tested, at least for the critical path.
- Remove the flag in the same pull request that deletes the old code path.

## Flags and the pipeline

Flags change what "tested" means. The pipeline tests the code with whatever flag configuration the test sets; production runs a configuration that was never tested (flags are changed at runtime). So: test the *default* production configuration and the *next* configuration (flag on), and treat a flag change as a change with an audit trail (who changed it, when, to what), ideally with the same approval you would require for a deploy for high-risk flags. Flag changes cause real incidents, and they are often invisible to the deployment dashboard.

Flags also interact with canaries (Lesson 01): a canary tests new **code**; a flag rollout tests new **behaviour**. Using both, deploy the code everywhere with the flag off, then ramp the flag. If a problem appears, turning the flag off is faster than rolling back a deployment.

## Evaluating where? Consistency and performance

Evaluating a flag should be cheap and local: fetch the rule set once, cache it, and update via a stream or periodic poll, then evaluate in-process. A network call per evaluation adds latency and a new failure mode. Be careful about evaluating the **same flag at several places in one request**, which could give inconsistent answers if the rules change mid-request; evaluate once per request and pass the result down.

## How It Actually Works

The flag configuration is data (JSON) distributed to the application. The SDK holds the rules in memory and evaluates them with a pure function of `(config, user)`, exactly as `evaluate()` here does. Because it is a pure function, it is trivially testable and deterministic. The hash-based bucket is a uniform pseudo-random mapping from `(flag, user)` to an integer; SHA-256's output is close enough to uniform that a modulo of its first 8 bytes is balanced to within sampling noise (the 10.04% result). The subset property follows from using a fixed bucket per user and varying only the threshold. Changing the *salt* (or the bucket count) reshuffles everyone, which is why rollouts should never edit the hashing key mid-experiment.

## Common mistakes

- **Random-per-request rollout**, giving users inconsistent experiences.
- **No per-flag salt**, so the same users are always in every experiment.
- **No safe default** if the flag service is unreachable.
- **Release flags that live forever**, plus untested "off" paths.
- **Changing flags without an audit trail** or approval for risky ones.
- **Using flags for long-term permissions** without calling them what they are.
- **Evaluating the same flag many times** in one request with changing answers.
- **Putting secrets or personal data in flag rules** distributed to clients.

## Exercise

1. Run `pytest src/test_flags.py -v`. Then remove the flag name from the hash input and show that two different flags now select the same 10% of users.
2. Add a rule type `{"user_ids": [...], "serve": ...}` that takes precedence for a list of beta users, with tests.
3. Plan the removal of a release flag that has been 100% on for three weeks: list every file and test to touch, and the order.
4. Write the incident runbook for "turn off the new checkout": who may flip it, how quickly it takes effect everywhere, and how you verify.
