"""
NVIDIA Omniverse 3D Spatial Interference and Collision Verification Engine
=========================================================================
Answers: "到底能不能放得下？" (Can all racks and parts physically fit?)
Parses OpenUSD stages directly via Pixar pxr API:
- Bounding-box overlap with 18m building columns
- ISO 3691-4 AGV Highway safety clearance (>= 0.50m margin)
- Ergonomic worker standing space (>= 0.90m)
"""

import math
from typing import Dict, List, Any
from pxr import Usd, UsdGeom, UsdPhysics, Gf
from simulation.workshop_specs import get_seres_40_stations

class SpatialClearanceChecker:
    """Performs millimeter-precise 3D bounding box interference and clearance analysis."""

    def __init__(self, usd_stage_path: str):
        self.usd_stage_path = usd_stage_path
        self.stage = Usd.Stage.Open(usd_stage_path)
        self.stations = get_seres_40_stations()

    def run_spatial_audit(self) -> Dict[str, Any]:
        """Audits all 40 stations for:
        1. Rack vs Building Column collisions
        2. Worker ergonomic clearance
        3. AGV highway clearance (safety margin >= 0.5m)
        """
        column_interferences = []
        agv_corridor_encroachments = []
        worker_clearance_warnings = []
        station_clearance_records = []

        # 1. Collect all building columns from USD scenegraph
        columns = []
        for prim in self.stage.Traverse():
            if prim.HasAttribute("custom:isBuildingColumn") and prim.GetAttribute("custom:isBuildingColumn").Get():
                trans_attr = prim.GetAttribute("xformOp:translate")
                scale_attr = prim.GetAttribute("xformOp:scale")
                if trans_attr.IsValid() and scale_attr.IsValid():
                    t = trans_attr.Get()
                    s = scale_attr.Get()
                    columns.append({
                        "path": str(prim.GetPath()),
                        "min_x": t[0] - s[0], "max_x": t[0] + s[0],
                        "min_y": t[1] - s[1], "max_y": t[1] + s[1],
                        "center": (t[0], t[1])
                    })

        total_racks_checked = 0
        safe_racks_count = 0

        conveyor_y_half = 1.6
        min_worker_clearance = 0.90 # meters

        # Line-side storage zone boundary: Y = +-4.8m
        # Required safety margin between static rack and moving AGV envelope is 0.50m (ISO 3691-4)
        north_agv_boundary_y = 4.80
        south_agv_boundary_y = -4.80
        agv_required_safety_margin = 0.50

        for st in self.stations:
            st_path_prefix = f"/World/AssemblyLine/Station_{st.station_id:02d}"
            
            l_path = f"{st_path_prefix}/Rack_Left_{st.left_part.part_id}/BaseFrame"
            r_path = f"{st_path_prefix}/Rack_Right_{st.right_part.part_id}/BaseFrame"

            for side, path, part_spec in [("Left", l_path, st.left_part), ("Right", r_path, st.right_part)]:
                total_racks_checked += 1
                prim = self.stage.GetPrimAtPath(path)
                if not prim.IsValid():
                    continue

                trans = prim.GetAttribute("xformOp:translate").Get()
                scale = prim.GetAttribute("xformOp:scale").Get()
                
                rack_min_x = trans[0] - scale[0]
                rack_max_x = trans[0] + scale[0]
                rack_min_y = trans[1] - scale[1]
                rack_max_y = trans[1] + scale[1]

                is_compliant = True
                failure_reasons = []

                # A. Check Building Column Collisions
                for col in columns:
                    overlap_x = not (rack_max_x < col["min_x"] or rack_min_x > col["max_x"])
                    overlap_y = not (rack_max_y < col["min_y"] or rack_min_y > col["max_y"])
                    
                    if overlap_x and overlap_y:
                        is_compliant = False
                        msg = (
                            f"工位 {st.station_id:02d} ({st.station_name}) {side}侧料架 [{part_spec.part_name}] "
                            f"与厂房承重钢柱 {col['path'].split('/')[-1]} 发生几何干涉碰撞！"
                        )
                        column_interferences.append({
                            "station_id": st.station_id,
                            "station_name": st.station_name,
                            "side": side,
                            "part_name": part_spec.part_name,
                            "column": col["path"],
                            "message": msg
                        })
                        failure_reasons.append("柱体碰撞")

                # B. Check AGV Highway Clearance
                if side == "Left":
                    dist_to_agv = north_agv_boundary_y - rack_max_y
                else:
                    dist_to_agv = abs(south_agv_boundary_y) - abs(rack_min_y)

                if dist_to_agv < agv_required_safety_margin:
                    is_compliant = False
                    msg = (
                        f"工位 {st.station_id:02d} ({st.station_name}) {side}侧大料架 [{part_spec.part_name}] "
                        f"占用AGV通道安全裕度！实测净距仅 {round(dist_to_agv, 3)}m (< 要求的 {agv_required_safety_margin}m)"
                    )
                    agv_corridor_encroachments.append({
                        "station_id": st.station_id,
                        "station_name": st.station_name,
                        "side": side,
                        "part_name": part_spec.part_name,
                        "actual_clearance_m": round(dist_to_agv, 3),
                        "required_m": agv_required_safety_margin,
                        "message": msg
                    })
                    failure_reasons.append("侵占AGV主通道")

                # C. Check Worker Ergonomic Clearance
                rack_front_y = abs(rack_min_y) if side == "Left" else abs(rack_max_y)
                worker_space = rack_front_y - conveyor_y_half
                if worker_space < min_worker_clearance:
                    worker_clearance_warnings.append({
                        "station_id": st.station_id,
                        "side": side,
                        "worker_space_m": round(worker_space, 3),
                        "part_name": part_spec.part_name
                    })

                if is_compliant:
                    safe_racks_count += 1

                station_clearance_records.append({
                    "station_id": st.station_id,
                    "side": side,
                    "part_name": part_spec.part_name,
                    "rack_depth": part_spec.rack_depth,
                    "is_compliant": is_compliant,
                    "reasons": failure_reasons
                })

        fit_success_pct = (safe_racks_count / total_racks_checked) * 100.0 if total_racks_checked > 0 else 0.0

        return {
            "spatial_evaluation": "3D Physical Interference & Clearance Audit (Omniverse Style)",
            "usd_stage_verified": self.usd_stage_path,
            "total_stations_checked": len(self.stations),
            "total_racks_checked": total_racks_checked,
            "compliant_racks_count": safe_racks_count,
            "fit_success_rate_pct": round(fit_success_pct, 2),
            "can_fit_all": (safe_racks_count == total_racks_checked),
            "column_collision_count": len(column_interferences),
            "agv_encroachment_count": len(agv_corridor_encroachments),
            "column_interferences": column_interferences,
            "agv_corridor_encroachments": agv_corridor_encroachments,
            "summary": (
                f"【放得下检验结果】: 共检验 {total_racks_checked} 个线边料架。"
                f"合格率: {round(fit_success_pct, 1)}% (符合规范: {safe_racks_count == total_racks_checked})。"
                f"柱干涉: {len(column_interferences)} 处 | AGV通道侵占: {len(agv_corridor_encroachments)} 处。"
            )
        }

if __name__ == "__main__":
    c_base = SpatialClearanceChecker("assets/stages/seres_ga_workshop_baseline.usda")
    print(c_base.run_spatial_audit()["summary"])
    c_opt = SpatialClearanceChecker("assets/stages/seres_ga_workshop_main.usda")
    print(c_opt.run_spatial_audit()["summary"])
