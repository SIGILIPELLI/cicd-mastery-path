from gitops import diff, reconcile, drift
D = {"web": {"image": "web:2", "replicas": 3}, "api": {"image": "api:1", "replicas": 2}}
def test_empty_cluster_creates_everything(): assert [p[0] for p in diff(D, {})] == ["create", "create"]
def test_converged_is_noop(): assert diff(D, {k: dict(v) for k, v in D.items()}) == []
def test_manual_change_is_reverted():
    a = {k: dict(v) for k, v in D.items()}; a["web"]["replicas"] = 10; assert reconcile(D, a) == [("update", "web", D["web"])] and a["web"]["replicas"] == 3
def test_extra_object_pruned():
    a = {k: dict(v) for k, v in D.items()}; a["debug"] = {"image": "tools"}; assert ("delete", "debug", None) in diff(D, a, prune=True) and "debug" in a
def test_prune_off_keeps_extra_but_reports_drift():
    a = {k: dict(v) for k, v in D.items()}; a["debug"] = {}; reconcile(D, a, prune=False); assert "debug" in a and drift(D, a)["extra"] == ["debug"]
def test_second_pass_is_idempotent():
    a = {}; reconcile(D, a); assert reconcile(D, a) == []
def test_rollback_is_a_git_revert():
    a = {}; reconcile(D, a); bad = {**D, "web": {"image": "web:3", "replicas": 3}}; reconcile(bad, a); assert a["web"]["image"] == "web:3"
    reconcile(D, a); assert a["web"]["image"] == "web:2"
def test_drift_report():
    a = {"web": {"image": "web:9", "replicas": 3}, "zzz": {}}; assert drift(D, a) == {"missing": ["api"], "changed": ["web"], "extra": ["zzz"]}
