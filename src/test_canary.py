from canary import z_one_sided, run_canary
def test_equal_rates_give_zero_z(): assert z_one_sided(10, 1000, 10, 1000) == 0.0
def test_worse_canary_positive_z(): assert z_one_sided(30, 1000, 10, 1000) > 2.5
def test_better_canary_negative_z(): assert z_one_sided(2, 1000, 20, 1000) < 0
def test_no_data_is_safe(): assert z_one_sided(0, 0, 5, 100) == 0.0
def test_zero_errors_everywhere_is_zero(): assert z_one_sided(0, 500, 0, 500) == 0.0
def test_healthy_canary_promotes(): assert run_canary(0.01, 0.01, seed=1)[0] == "promote"
def test_bad_canary_rolls_back_early():
    d, log = run_canary(0.01, 0.05, seed=1); assert d == "rollback" and log[-1]["pct"] <= 25
def test_min_sample_prevents_decision_at_1_percent():
    d, log = run_canary(0.01, 0.20, seed=2, min_canary=400); assert log[0]["n_canary"] == 200 and (d == "promote" or len(log) > 1)
def test_deterministic_with_seed(): assert run_canary(0.01, 0.03, seed=7) == run_canary(0.01, 0.03, seed=7)
def test_small_real_regression_usually_caught():
    # measured: 1.0% -> 1.2% was rolled back in 234 of 300 seeded runs; assert a conservative floor
    assert sum(run_canary(0.010, 0.012, seed=s)[0] == "rollback" for s in range(100)) > 55
def test_false_rollback_rate_stays_low():
    # measured: 13 of 300 equal-rate runs rolled back (several checks per rollout add up); assert under 10%
    assert sum(run_canary(0.01, 0.01, seed=s)[0] == "rollback" for s in range(200)) < 20
