from flags import bucket, evaluate
F = {"name": "new-checkout", "enabled": True, "default": False, "rules": [{"if": {"email_domain": "corp.example"}, "serve": True}, {"percent": 10, "serve": True}]}
def test_bucket_is_stable(): assert bucket("f", "u1") == bucket("f", "u1")
def test_bucket_differs_by_flag(): assert any(bucket("a", f"u{i}") != bucket("b", f"u{i}") for i in range(50))
def test_attribute_rule_wins(): assert evaluate(F, {"id": "zzz", "email_domain": "corp.example"}) is True
def test_default_when_no_rule_matches():
    users = [{"id": f"u{i}"} for i in range(2000)]; assert any(evaluate(F, u) is False for u in users)
def test_percentage_is_close_to_target():
    n = sum(evaluate(F, {"id": f"user-{i}"}) for i in range(20000)); assert 0.09 < n / 20000 < 0.11
def test_raising_percentage_only_adds_users():
    lo = {"name": "x", "rules": [{"percent": 10, "serve": True}]}; hi = {"name": "x", "rules": [{"percent": 20, "serve": True}]}
    ids = [{"id": str(i)} for i in range(5000)]
    on_lo = {u["id"] for u in ids if evaluate(lo, u)}; on_hi = {u["id"] for u in ids if evaluate(hi, u)}; assert on_lo <= on_hi and len(on_hi) > len(on_lo)
def test_kill_switch_overrides_rules():
    off = dict(F, enabled=False); assert not any(evaluate(off, {"id": str(i), "email_domain": "corp.example"}) for i in range(100))
def test_zero_and_hundred_percent():
    z = {"name": "z", "rules": [{"percent": 0, "serve": True}]}; h = {"name": "h", "rules": [{"percent": 100, "serve": True}]}
    assert not any(evaluate(z, {"id": str(i)}) for i in range(500)) and all(evaluate(h, {"id": str(i)}) for i in range(500))
