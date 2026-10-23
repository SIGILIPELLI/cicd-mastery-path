"""Tamper-evident audit log: each record stores the SHA-256 of the previous record's hash plus its own canonical JSON.
Detects edited, removed, inserted or reordered records; does NOT stop someone who can rewrite the entire log AND the final hash. Anchor the head hash elsewhere."""
import hashlib, json
GENESIS = "0" * 64

def _h(prev, event): return hashlib.sha256((prev + json.dumps(event, sort_keys=True, separators=(",", ":"))).encode()).hexdigest()

def append(log, event):
    prev = log[-1]["hash"] if log else GENESIS
    log.append({"event": event, "prev": prev, "hash": _h(prev, event)}); return log[-1]["hash"]

def verify(log):
    """Return None if the chain is intact, else the index of the first bad record."""
    prev = GENESIS
    for i, rec in enumerate(log):
        if rec["prev"] != prev or rec["hash"] != _h(prev, rec["event"]): return i
        prev = rec["hash"]
    return None
