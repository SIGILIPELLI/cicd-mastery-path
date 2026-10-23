"""Feature flags with deterministic percentage rollout. A user's bucket is a stable hash of (flag, user), so the same user always gets the same answer
and raising 10% -> 20% only ADDS users. Rules are evaluated in order; the first match wins."""
import hashlib

def bucket(flag, user_id, buckets=10000):
    h = hashlib.sha256(f"{flag}:{user_id}".encode()).digest()
    return int.from_bytes(h[:8], "big") % buckets

def evaluate(flag_cfg, user):
    """flag_cfg: {'name','enabled','default','rules':[{'if':{attr:value},'serve':bool} | {'percent':float,'serve':bool}]}"""
    if not flag_cfg.get("enabled", True): return flag_cfg.get("default", False)       # kill switch: everyone gets the default
    for rule in flag_cfg.get("rules", []):
        if "if" in rule:
            if all(user.get(k) == v for k, v in rule["if"].items()): return rule["serve"]
        elif "percent" in rule:
            if bucket(flag_cfg["name"], user["id"]) < rule["percent"] * 100: return rule["serve"]
    return flag_cfg.get("default", False)
