"""Pipeline performance model: critical path through a job graph and a simple cost estimate.
jobs = {name: {'minutes': float, 'needs': [names], 'cells': int}}  (cells = matrix size; cells run in parallel, each billed)."""
def critical_path(jobs):
    finish, via = {}, {}
    def f(n):
        if n in finish: return finish[n]
        deps = jobs[n].get("needs", [])
        best = max(deps, key=f, default=None)
        finish[n] = (f(best) if best else 0.0) + jobs[n]["minutes"]; via[n] = best
        return finish[n]
    end = max(jobs, key=f)
    path, n = [], end
    while n: path.append(n); n = via[n]
    return finish[end], path[::-1]

def billed_minutes(jobs, round_up=True):
    import math
    return sum((math.ceil(j["minutes"]) if round_up else j["minutes"]) * j.get("cells", 1) for j in jobs.values())

def cost(jobs, rate_per_minute, round_up=True): return round(billed_minutes(jobs, round_up) * rate_per_minute, 4)
