"""
Unit Tests for AnyLogic-Style Discrete-Event Logistics Engine
============================================================
Verifies:
1. Workshop BOM and 40 workstations integrity
2. Baseline failure mode (8000+ starvation events due to single warehouse bottleneck)
3. Optimized zero-starvation mode (3 SPS supermarkets + 36 tugger trains)
4. Production throughput and takt time adherence (60s / 60 JPH)
"""

import sys
import os
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from simulation.workshop_specs import WORKSTATIONS, WORKSHOP_SPECS, get_seres_40_stations
from simulation.anylogic_des_engine import DiscreteLogisticsSimulator


def test_workshop_specifications():
    """Verify 40 workstations BOM integrity."""
    stations = get_seres_40_stations()
    assert len(stations) == 40
    assert WORKSHOP_SPECS["total_stations"] == 40
    assert WORKSHOP_SPECS["takt_time_sec"] == 60.0

    # Ensure all 4 zones exist
    zones = {s.zone for s in stations}
    assert zones == {"Trim-1", "Trim-2", "Chassis", "Final"}

    # Ensure all stations have left and right parts with positive dimensions and weight
    for s in stations:
        assert s.left_part.rack_width > 0
        assert s.left_part.rack_depth > 0
        assert s.left_part.weight_kg > 0
        assert s.right_part.rack_width > 0
        assert s.right_part.rack_depth > 0
        assert s.right_part.weight_kg > 0


def test_baseline_logistics_starvation():
    """Verify that baseline traditional logistics fails under 60s takt time."""
    sim = DiscreteLogisticsSimulator(takt_time_sec=60.0, agv_count=6, shift_hours=1.0)
    res = sim.run_simulation(mode="baseline")

    assert res["mode"] == "baseline"
    assert res["can_arrive_on_time"] is False
    assert res["starvation_events_count"] > 1000
    assert len(res["top_starved_stations"]) > 0


def test_optimized_logistics_zero_starvation():
    """Verify that optimized logistics delivers 100% on-time supply (0 starvation)."""
    sim = DiscreteLogisticsSimulator(takt_time_sec=60.0, agv_count=36, shift_hours=2.0)
    res = sim.run_simulation(mode="optimized", agv_count_override=36)

    assert res["mode"] == "optimized"
    assert res["can_arrive_on_time"] is True
    assert res["starvation_events_count"] == 0
    assert res["cars_produced"] == 120  # 2 hours * 60 cars/hour = 120 cars
    assert res["agv_fleet_size"] == 36
    assert res["agv_fleet_utilization_pct"] > 70.0


def test_logistics_fleet_sensitivity():
    """Verify fleet size scaling behavior."""
    # With only 10 AGVs, even with SPS supermarkets, it should struggle to meet 60 JPH
    sim = DiscreteLogisticsSimulator(takt_time_sec=60.0, agv_count=10, shift_hours=1.0)
    res = sim.run_simulation(mode="optimized", agv_count_override=10)
    
    assert res["starvation_events_count"] > 0, "10 AGVs should not be enough to sustain 60 JPH"
