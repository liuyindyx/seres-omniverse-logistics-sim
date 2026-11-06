"""
Unit Tests for Seres Industrial AI Agent Orchestrator
=====================================================
Verifies:
1. Agent cross-domain diagnosis logic
2. Baseline failure detection (both spatial and logistics)
3. Automated multi-objective optimization closure
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from simulation.agent_orchestrator import SeresLogisticsPlanningAgent


def test_agent_orchestrator_closed_loop():
    baseline_usd = os.path.join(PROJECT_ROOT, "assets", "stages", "seres_ga_workshop_baseline.usda")
    optimized_usd = os.path.join(PROJECT_ROOT, "assets", "stages", "seres_ga_workshop_main.usda")

    agent = SeresLogisticsPlanningAgent(
        baseline_usd_path=baseline_usd,
        optimized_usd_path=optimized_usd
    )

    verdict = agent.run_full_investigation_and_optimization()

    assert verdict["status"] == "COMPLETED"
    
    # Baseline checks
    assert verdict["spatial_baseline"]["can_fit_all"] is False
    assert verdict["spatial_baseline"]["column_collision_count"] == 5
    assert verdict["logistics_baseline"]["can_arrive_on_time"] is False
    assert verdict["logistics_baseline"]["starvation_events_count"] > 1000

    # Optimized checks
    assert verdict["spatial_optimized"]["can_fit_all"] is True
    assert verdict["spatial_optimized"]["column_collision_count"] == 0
    assert verdict["spatial_optimized"]["agv_encroachment_count"] == 0
    assert verdict["logistics_optimized"]["can_arrive_on_time"] is True
    assert verdict["logistics_optimized"]["starvation_events_count"] == 0
