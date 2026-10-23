"""A GitOps reconcile loop in miniature. `desired` is what the Git repo says; `actual` is the cluster. Each pass computes a plan (create/update/delete) and applies it.
`prune=False` leaves objects that are not in Git alone (the default in many tools); drift is reported either way."""
def diff(desired, actual, prune=True):
    plan = []
    for k, spec in sorted(desired.items()):
        if k not in actual: plan.append(("create", k, spec))
        elif actual[k] != spec: plan.append(("update", k, spec))
    if prune:
        plan += [("delete", k, None) for k in sorted(actual) if k not in desired]
    return plan

def reconcile(desired, actual, prune=True):
    plan = diff(desired, actual, prune)
    for op, k, spec in plan:
        if op == "delete": actual.pop(k, None)
        else: actual[k] = dict(spec)
    return plan

def drift(desired, actual):
    """Objects that differ from Git, whether or not we would fix them."""
    return {"missing": sorted(set(desired) - set(actual)), "changed": sorted(k for k in desired if k in actual and desired[k] != actual[k]), "extra": sorted(set(actual) - set(desired))}
