"""planguard: read an infrastructure plan in the Terraform `show -json` shape (resource_changes[].change.actions) and block destructive changes
unless the resource address is on an allowlist. Tested on hand-written fixtures; never run against a real Terraform plan."""
import json, sys

def classify(actions):
    a = list(actions)
    if a == ["no-op"] or a == ["read"]: return "none"
    if a in (["delete", "create"], ["create", "delete"]): return "replace"
    if a == ["delete"]: return "delete"
    if a == ["create"]: return "create"
    if a == ["update"]: return "update"
    return "unknown"

def check(plan, allow_destroy=()):
    """Return (violations, summary). Replace and delete are destructive; unknown action lists are blocked (fail closed)."""
    summary, bad = {}, []
    for rc in plan.get("resource_changes", []):
        kind = classify(rc["change"]["actions"]); summary[kind] = summary.get(kind, 0) + 1
        if kind in ("replace", "delete", "unknown") and rc["address"] not in allow_destroy: bad.append((rc["address"], kind))
    return bad, summary

def main(argv):
    plan = json.load(open(argv[0])); bad, summary = check(plan, argv[1:])
    print("summary:", dict(sorted(summary.items())))
    for addr, kind in bad: print(f"BLOCKED {kind}: {addr}")
    return 1 if bad else 0

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
