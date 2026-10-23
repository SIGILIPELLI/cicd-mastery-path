from pipeperf import critical_path, billed_minutes, cost
J = {"lint": {"minutes": 1}, "build": {"minutes": 4}, "unit": {"minutes": 6, "needs": ["build"], "cells": 3}, "e2e": {"minutes": 12, "needs": ["build"]}, "deploy": {"minutes": 2, "needs": ["unit", "e2e", "lint"]}}
def test_critical_path(): assert critical_path(J) == (18.0, ["build", "e2e", "deploy"])
def test_speeding_noncritical_job_changes_nothing():
    K = {**J, "unit": {**J["unit"], "minutes": 1}}; assert critical_path(K)[0] == 18.0
def test_speeding_critical_job_helps_until_next_path_binds():
    K = {**J, "e2e": {**J["e2e"], "minutes": 3}}; assert critical_path(K) == (12.0, ["build", "unit", "deploy"])
def test_billed_minutes_counts_every_matrix_cell(): assert billed_minutes(J) == 1 + 4 + 18 + 12 + 2
def test_rounding_up_per_job():
    K = {"a": {"minutes": 0.2, "cells": 10}}; assert billed_minutes(K) == 10 and billed_minutes(K, round_up=False) == 2.0
def test_cost(): assert cost(J, 0.5) == 18.5
def test_single_job(): assert critical_path({"x": {"minutes": 3}}) == (3.0, ["x"])
