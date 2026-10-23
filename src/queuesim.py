"""M/M/c queue simulation for a runner pool: Poisson arrivals, exponential job durations, c identical runners, first-come-first-served.
Returns mean and 90th percentile of the wait before a job starts. Also provides the Erlang C closed form for the mean wait, to cross-check the simulation."""
import heapq, math, random

def simulate(c, arrival_rate, mean_service, n_jobs=200000, seed=0):
    rng = random.Random(seed); free_at = [0.0] * c; heapq.heapify(free_at); t = 0.0; waits = []
    for _ in range(n_jobs):
        t += rng.expovariate(arrival_rate)
        start = max(t, heapq.heappop(free_at)); waits.append(start - t)
        heapq.heappush(free_at, start + rng.expovariate(1.0 / mean_service))
    waits.sort(); return sum(waits) / len(waits), waits[int(0.9 * len(waits))]

def erlang_c_mean_wait(c, arrival_rate, mean_service):
    a = arrival_rate * mean_service; rho = a / c
    if rho >= 1: return math.inf
    s = sum(a ** k / math.factorial(k) for k in range(c))
    top = a ** c / (math.factorial(c) * (1 - rho)); p_wait = top / (s + top)
    return p_wait * mean_service / (c * (1 - rho))
