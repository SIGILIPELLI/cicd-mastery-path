from planguard import classify, check
def P(*items): return {"resource_changes": [{"address": a, "change": {"actions": act}} for a, act in items]}
def test_classify(): assert [classify(x) for x in (["no-op"], ["create"], ["update"], ["delete"], ["delete", "create"], ["create", "delete"], ["read"])] == ["none", "create", "update", "delete", "replace", "replace", "none"]
def test_unknown_fails_closed(): assert classify(["frobnicate"]) == "unknown"
def test_safe_plan_passes(): assert check(P(("a", ["create"]), ("b", ["update"]), ("c", ["no-op"])))[0] == []
def test_replace_blocked(): assert check(P(("db", ["delete", "create"])))[0] == [("db", "replace")]
def test_delete_blocked(): assert check(P(("q", ["delete"])))[0] == [("q", "delete")]
def test_allowlist_permits(): assert check(P(("q", ["delete"])), allow_destroy=["q"])[0] == []
def test_allowlist_is_exact_address_not_prefix(): assert check(P(("q.old2", ["delete"])), allow_destroy=["q.old"])[0] != []
def test_summary_counts(): assert check(P(("a", ["create"]), ("b", ["create"]), ("c", ["delete"])))[1] == {"create": 2, "delete": 1}
def test_empty_plan(): assert check({}) == ([], {})
