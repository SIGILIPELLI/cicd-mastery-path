from dora import metrics
H = 3600
D = [{"commit_time": 0, "deploy_time": 2 * H, "failed": False, "restored_time": None},
     {"commit_time": 10 * H, "deploy_time": 14 * H, "failed": True, "restored_time": 15 * H},
     {"commit_time": 20 * H, "deploy_time": 26 * H, "failed": False, "restored_time": None},
     {"commit_time": 30 * H, "deploy_time": 31 * H, "failed": True, "restored_time": 33 * H}]
def test_frequency(): assert metrics(D, 2)["deploys_per_day"] == 2.0
def test_median_lead_time(): assert metrics(D, 2)["median_lead_time_h"] == 3.0       # leads: 2,4,6,1 -> sorted 1,2,4,6 -> (2+4)/2
def test_change_failure_rate(): assert metrics(D, 2)["change_failure_rate"] == 0.5
def test_median_restore(): assert metrics(D, 2)["median_restore_h"] == 1.5           # 1h and 2h
def test_empty(): assert metrics([], 7)["change_failure_rate"] is None
def test_failed_without_restore_time_not_counted_in_restore():
    d = [dict(D[1], restored_time=None)]; m = metrics(d, 1); assert m["change_failure_rate"] == 1.0 and m["median_restore_h"] is None
