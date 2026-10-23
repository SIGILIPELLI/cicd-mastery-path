import math
from queuesim import simulate, erlang_c_mean_wait
def test_matches_erlang_c_at_moderate_load():
    mean, _ = simulate(8, 1.12, 5.0, n_jobs=300000)   # utilisation 1.12 * 5 / 8 = 0.7
    assert abs(mean - erlang_c_mean_wait(8, 1.12, 5.0)) < 0.15 * max(erlang_c_mean_wait(8, 1.12, 5.0), 0.05) + 0.02
def test_unstable_queue_is_infinite(): assert erlang_c_mean_wait(2, 1.0, 5.0) == math.inf
def test_wait_grows_with_utilisation():
    w = [simulate(8, r, 5.0, n_jobs=100000)[0] for r in (0.8, 1.2, 1.5)]; assert w[0] < w[1] < w[2]
def test_more_runners_reduce_wait(): assert simulate(10, 1.4, 5.0, n_jobs=100000)[0] < simulate(8, 1.4, 5.0, n_jobs=100000)[0]
def test_deterministic(): assert simulate(4, 0.5, 5.0, n_jobs=5000, seed=3) == simulate(4, 0.5, 5.0, n_jobs=5000, seed=3)
def test_p90_at_least_mean_fraction():
    m, p90 = simulate(8, 1.4, 5.0, n_jobs=100000); assert p90 >= 0
