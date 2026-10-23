"""DORA-style delivery metrics from a list of deployments. Each deployment: {'commit_time','deploy_time','failed','restored_time'} (epoch seconds; restored_time None unless failed).
Metrics: deployment frequency, lead time for changes (median), change failure rate, time to restore (median). Definitions follow common practice; teams differ on what counts."""
from statistics import median

def metrics(deploys, window_days):
    if not deploys: return {"deploys_per_day": 0.0, "median_lead_time_h": None, "change_failure_rate": None, "median_restore_h": None}
    lead = [(d["deploy_time"] - d["commit_time"]) / 3600 for d in deploys]
    failed = [d for d in deploys if d["failed"]]
    restore = [(d["restored_time"] - d["deploy_time"]) / 3600 for d in failed if d.get("restored_time") is not None]
    return {"deploys_per_day": round(len(deploys) / window_days, 2), "median_lead_time_h": round(median(lead), 2),
            "change_failure_rate": round(len(failed) / len(deploys), 3), "median_restore_h": round(median(restore), 2) if restore else None}
