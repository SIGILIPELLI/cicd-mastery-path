import copy
from auditlog import append, verify, GENESIS
def build():
    log = []
    for e in [{"who": "ann", "did": "approve", "env": "prod"}, {"who": "bob", "did": "deploy", "version": "1.2.0"}, {"who": "ann", "did": "flag", "name": "x", "to": "on"}]: append(log, e)
    return log
def test_intact(): assert verify(build()) is None
def test_empty_ok(): assert verify([]) is None
def test_edit_detected():
    log = build(); log[1]["event"]["version"] = "9.9.9"; assert verify(log) == 1
def test_delete_detected():
    log = build(); del log[1]; assert verify(log) == 1
def test_reorder_detected():
    log = build(); log[1], log[2] = log[2], log[1]; assert verify(log) == 1
def test_insert_detected():
    log = build(); append(copy.deepcopy(log), {"x": 1}); forged = {"event": {"x": 1}, "prev": log[0]["hash"], "hash": "f" * 64}; log.insert(1, forged); assert verify(log) == 1
def test_truncation_is_NOT_detected_without_an_anchor():
    log = build()[:2]; assert verify(log) is None          # known limit: dropping the tail passes; compare the head hash with an external copy
def test_rewriting_everything_consistently_passes():
    log = []; [append(log, e) for e in [{"a": 1}]]; assert verify(log) is None and log[0]["prev"] == GENESIS
def test_changing_first_record_detected():
    log = build(); log[0]["event"]["who"] = "mallory"; assert verify(log) == 0
