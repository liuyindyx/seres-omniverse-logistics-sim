"""
Unit Tests for Seres OpenUSD Stages & PhysX Schemas
===================================================
Verifies the integrity of OpenUSD ASCII stages generated with Pixar pxr API:
1. Valid OpenUSD scene hierarchy & prim definitions
2. 40 Workstations, conveyors, columns, and cameras
3. Time codes and keyframed animations
4. Spatial clearances & collision detections
"""

import os
import sys
import pytest
from pxr import Usd, UsdGeom

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

STAGES_DIR = os.path.join(PROJECT_ROOT, "assets", "stages")
MATERIALS_DIR = os.path.join(PROJECT_ROOT, "assets", "materials")

from simulation.omniverse_spatial_engine import SpatialClearanceChecker


def test_materials_stage():
    """Verify factory materials USD file."""
    mat_path = os.path.join(MATERIALS_DIR, "factory_materials.usda")
    assert os.path.exists(mat_path), f"Materials file missing: {mat_path}"
    
    stage = Usd.Stage.Open(mat_path)
    assert stage is not None, "Failed to parse factory_materials.usda"
    
    mat_root = stage.GetPrimAtPath("/Materials")
    assert mat_root.IsValid(), "Missing /Materials prim"
    
    # Check essential PBR materials
    mats = [p.GetName() for p in mat_root.GetChildren()]
    assert "FloorEpoxyGray" in mats
    assert "SteelColumnBlue" in mats
    assert "SafetyYellowStripes" in mats
    assert "VehicleMetallicSilver" in mats
    assert "AGVChassisTeal" in mats


def test_main_optimized_stage():
    """Verify optimized main USD stage (seres_ga_workshop_main.usda)."""
    usd_path = os.path.join(STAGES_DIR, "seres_ga_workshop_main.usda")
    assert os.path.exists(usd_path), f"File missing: {usd_path}"
    
    stage = Usd.Stage.Open(usd_path)
    assert stage is not None, "Failed to parse main stage"
    
    # Root & core structures
    assert stage.GetPrimAtPath("/World").IsValid()
    assert stage.GetPrimAtPath("/World/PhysicsScene").IsValid()
    assert stage.GetPrimAtPath("/World/Lighting").IsValid()
    assert stage.GetPrimAtPath("/World/Environment/BuildingColumns").IsValid()
    assert stage.GetPrimAtPath("/World/AssemblyLine").IsValid()
    assert stage.GetPrimAtPath("/World/Cameras").IsValid()

    # 40 Workstations verification under /World/AssemblyLine
    assembly_prim = stage.GetPrimAtPath("/World/AssemblyLine")
    assert assembly_prim.IsValid()
    
    stations_found = 0
    for i in range(1, 41):
        st_name = f"Station_{i:02d}"
        st_prim = stage.GetPrimAtPath(f"/World/AssemblyLine/{st_name}")
        assert st_prim.IsValid(), f"Missing station: {st_name}"
        stations_found += 1
        # Check rack prims
        assert stage.GetPrimAtPath(f"/World/AssemblyLine/{st_name}/Rack_Left_P_{i:02d}_L").IsValid()
        assert stage.GetPrimAtPath(f"/World/AssemblyLine/{st_name}/Rack_Right_P_{i:02d}_R").IsValid()

    assert stations_found == 40, f"Expected 40 stations, found {stations_found}"

    # Verify Cameras
    expected_cams = [
        "GA_Line_Overview_Isometric",
        "Station_16_Seat_Hazard_Cam",
        "Station_24_Battery_Cell_Cam",
        "AGV_Tugger_Train_Follow"
    ]
    for cam_name in expected_cams:
        cam_prim = stage.GetPrimAtPath(f"/World/Cameras/{cam_name}")
        assert cam_prim.IsValid(), f"Missing camera: {cam_name}"

    # Verify 100% Spatial Compliance
    checker = SpatialClearanceChecker(usd_path)
    res = checker.run_spatial_audit()
    assert res["column_collision_count"] == 0, f"Expected 0 column collisions, found {res['column_collision_count']}"
    assert res["agv_encroachment_count"] == 0, f"Expected 0 AGV encroachments, found {res['agv_encroachment_count']}"
    assert res["fit_success_rate_pct"] == 100.0
    assert res["can_fit_all"] is True


def test_baseline_stage_interference():
    """Verify baseline USD stage contains the documented collisions."""
    usd_path = os.path.join(STAGES_DIR, "seres_ga_workshop_baseline.usda")
    assert os.path.exists(usd_path), f"File missing: {usd_path}"
    
    stage = Usd.Stage.Open(usd_path)
    assert stage is not None, "Failed to parse baseline stage"

    # Baseline must exhibit 5 column collisions and 2 AGV encroachments
    checker = SpatialClearanceChecker(usd_path)
    res = checker.run_spatial_audit()
    assert res["column_collision_count"] == 5, f"Expected 5 column collisions in baseline, got {res['column_collision_count']}"
    assert res["agv_encroachment_count"] == 2, f"Expected 2 AGV encroachments in baseline, got {res['agv_encroachment_count']}"
    assert res["can_fit_all"] is False


def test_animated_stage():
    """Verify timeline animated stage has time samples and keyframes."""
    usd_path = os.path.join(STAGES_DIR, "seres_ga_workshop_animated.usda")
    assert os.path.exists(usd_path), f"File missing: {usd_path}"
    
    stage = Usd.Stage.Open(usd_path)
    assert stage is not None, "Failed to parse animated stage"

    # Time code metadata
    assert stage.GetStartTimeCode() == 1.0
    assert stage.GetEndTimeCode() == 240.0
    assert stage.GetTimeCodesPerSecond() == 30.0

    # Verify AGV animated xform on TuggerTrain_01 (moves whole train along AGV corridor)
    agv_prim = stage.GetPrimAtPath("/World/AGV_Fleet/TuggerTrain_01")
    assert agv_prim.IsValid(), "Missing TuggerTrain_01 prim in animated stage"
    xformable = UsdGeom.Xformable(agv_prim)
    ops = xformable.GetOrderedXformOps()
    assert len(ops) > 0, "No xform ops found on TuggerTrain_01"

    # Ensure time samples are present on translate op (full 240 frames of animation)
    translate_op = ops[0]
    time_samples = translate_op.GetTimeSamples()
    assert len(time_samples) >= 200, f"Expected 240 keyframes, got {len(time_samples)}"
