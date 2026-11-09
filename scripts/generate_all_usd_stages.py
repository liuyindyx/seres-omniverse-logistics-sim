"""
High-Fidelity OpenUSD 3D Asset and Master Stage Generator for NVIDIA Omniverse
=============================================================================
Constructs detailed multi-part 3D geometry, bound PBR UsdPreviewSurface materials,
RTX lights, PhysX 5 schemas, camera bookmarks, and 240-frame timeCode animations
for the Seres Super Factory General Assembly (GA) Workshop.
"""

import os
import sys
import math

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pxr import Usd, UsdGeom, UsdPhysics, UsdShade, UsdLux, Sdf, Gf
from simulation.workshop_specs import get_seres_40_stations, StationSpecification


def define_cube_mesh(
    stage,
    path,
    center,
    size,
    color=None,
    is_collider=True,
    material=None,
    opacity=1.0,
):
    """Defines a 3D box prim with scale, translation, collision, displayColor, and bound PBR material."""
    cube = UsdGeom.Cube.Define(stage, path)
    cube.AddTranslateOp().Set(Gf.Vec3d(*center))
    cube.AddScaleOp().Set(Gf.Vec3f(size[0] / 2.0, size[1] / 2.0, size[2] / 2.0))
    prim = cube.GetPrim()
    if is_collider:
        UsdPhysics.CollisionAPI.Apply(prim)
    if color:
        cube.GetDisplayColorAttr().Set([Gf.Vec3f(*color)])
    if opacity < 1.0:
        cube.GetDisplayOpacityAttr().Set([float(opacity)])
    if material is not None:
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(material)
    return cube


def define_cylinder_mesh(
    stage,
    path,
    center,
    radius,
    height,
    axis="Z",
    color=None,
    is_collider=True,
    material=None,
    opacity=1.0,
):
    """Defines a 3D cylinder prim with configurable axis (X, Y, or Z), collision, and PBR material."""
    cyl = UsdGeom.Cylinder.Define(stage, path)
    cyl.CreateAxisAttr().Set(axis)
    cyl.AddTranslateOp().Set(Gf.Vec3d(*center))
    if axis == "Y":
        cyl.AddScaleOp().Set(Gf.Vec3f(radius, height / 2.0, radius))
    elif axis == "X":
        cyl.AddScaleOp().Set(Gf.Vec3f(height / 2.0, radius, radius))
    else:
        cyl.AddScaleOp().Set(Gf.Vec3f(radius, radius, height / 2.0))
    prim = cyl.GetPrim()
    if is_collider:
        UsdPhysics.CollisionAPI.Apply(prim)
    if color:
        cyl.GetDisplayColorAttr().Set([Gf.Vec3f(*color)])
    if opacity < 1.0:
        cyl.GetDisplayOpacityAttr().Set([float(opacity)])
    if material is not None:
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(material)
    return cyl


MATERIAL_CATALOG = [
    # (name, color, metallic, roughness, static_f, dyn_f, opacity, emissive, clearcoat)
    ("FloorEpoxyGray", (0.22, 0.25, 0.29), 0.15, 0.28, 0.45, 0.40, 1.0, (0.0, 0.0, 0.0), 0.4),
    ("FloorWalkwayGreen", (0.12, 0.52, 0.30), 0.10, 0.45, 0.50, 0.42, 1.0, (0.0, 0.0, 0.0), 0.2),
    ("FloorAGVLaneBlue", (0.08, 0.32, 0.48), 0.20, 0.32, 0.48, 0.40, 1.0, (0.0, 0.04, 0.08), 0.3),
    ("SteelColumnBlue", (0.14, 0.38, 0.68), 0.82, 0.24, 0.35, 0.28, 1.0, (0.0, 0.0, 0.0), 0.1),
    ("ConveyorBeltRubber", (0.09, 0.10, 0.12), 0.05, 0.82, 0.75, 0.65, 1.0, (0.0, 0.0, 0.0), 0.0),
    ("ConveyorSteelFrame", (0.26, 0.29, 0.34), 0.78, 0.28, 0.40, 0.35, 1.0, (0.0, 0.0, 0.0), 0.1),
    ("SafetyYellowStripes", (0.96, 0.78, 0.05), 0.15, 0.32, 0.40, 0.35, 1.0, (0.08, 0.06, 0.0), 0.2),
    ("VehicleMetallicSilver", (0.78, 0.83, 0.89), 0.88, 0.14, 0.30, 0.25, 1.0, (0.0, 0.0, 0.0), 0.95),
    ("VehicleDarkWindshield", (0.05, 0.09, 0.15), 0.90, 0.04, 0.20, 0.15, 0.42, (0.0, 0.0, 0.0), 1.0),
    ("VehicleTireRubber", (0.06, 0.06, 0.07), 0.02, 0.88, 0.85, 0.80, 1.0, (0.0, 0.0, 0.0), 0.0),
    ("AlloyRimSilver", (0.85, 0.88, 0.92), 0.92, 0.16, 0.30, 0.25, 1.0, (0.0, 0.0, 0.0), 0.5),
    ("VehicleStarRingLED", (0.92, 0.97, 1.0), 0.0, 0.08, 0.20, 0.15, 1.0, (0.85, 0.95, 1.0), 0.5),
    ("VehicleTailLightLED", (0.98, 0.12, 0.15), 0.0, 0.08, 0.20, 0.15, 1.0, (0.95, 0.08, 0.10), 0.5),
    ("RackFrameBlue", (0.16, 0.42, 0.72), 0.75, 0.28, 0.38, 0.32, 1.0, (0.0, 0.0, 0.0), 0.1),
    ("RollerTrackAluminum", (0.76, 0.79, 0.83), 0.88, 0.22, 0.20, 0.15, 1.0, (0.0, 0.0, 0.0), 0.2),
    ("RobotOrange", (0.95, 0.42, 0.06), 0.65, 0.24, 0.35, 0.30, 1.0, (0.0, 0.0, 0.0), 0.6),
    ("AGVChassisTeal", (0.08, 0.68, 0.78), 0.72, 0.22, 0.35, 0.30, 1.0, (0.0, 0.05, 0.08), 0.5),
    ("LidarLaserRed", (0.95, 0.08, 0.08), 0.0, 0.10, 0.0, 0.0, 0.35, (0.90, 0.05, 0.05), 0.0),
    ("CollisionHazardGlow", (0.98, 0.12, 0.12), 0.0, 0.10, 0.0, 0.0, 0.38, (0.95, 0.10, 0.10), 0.0),
    ("EncroachmentAmberGlow", (0.98, 0.52, 0.05), 0.0, 0.10, 0.0, 0.0, 0.38, (0.95, 0.45, 0.05), 0.0),
]


def populate_materials_in_scope(stage, root_path: str) -> dict:
    """Creates UsdPreviewSurface + PhysX materials under root_path and returns a dict of UsdShade.Material."""
    UsdGeom.Scope.Define(stage, root_path)
    mat_dict = {}

    for name, col, metallic, roughness, static_f, dyn_f, opacity, emissive, clearcoat in MATERIAL_CATALOG:
        mat_path = f"{root_path}/{name}"
        mat = UsdShade.Material.Define(stage, mat_path)

        shader = UsdShade.Shader.Define(stage, f"{mat_path}/PbrShader")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*col))
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(metallic))
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(roughness))
        shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(opacity))
        shader.CreateInput("clearcoat", Sdf.ValueTypeNames.Float).Set(float(clearcoat))
        shader.CreateInput("clearcoatRoughness", Sdf.ValueTypeNames.Float).Set(0.08)
        if any(c > 0 for c in emissive):
            shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*emissive))

        mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

        phys_mat = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
        phys_mat.CreateStaticFrictionAttr().Set(float(static_f))
        phys_mat.CreateDynamicFrictionAttr().Set(float(dyn_f))
        phys_mat.CreateRestitutionAttr().Set(0.15)

        mat_dict[name] = mat

    return mat_dict


class OmniverseUSDStageGenerator:
    """Generates high-detail 3D OpenUSD stages and modular material layers."""

    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = os.path.join(PROJECT_ROOT, "assets")
        self.output_dir = output_dir
        self.stages_dir = os.path.join(output_dir, "stages")
        self.materials_dir = os.path.join(output_dir, "materials")
        self.props_dir = os.path.join(output_dir, "props")
        os.makedirs(self.stages_dir, exist_ok=True)
        os.makedirs(self.materials_dir, exist_ok=True)
        os.makedirs(self.props_dir, exist_ok=True)
        self.stations = get_seres_40_stations()

    def build_materials_layer(self) -> str:
        """Creates standalone physical PBR and PhysX materials layer."""
        path = os.path.join(self.materials_dir, "factory_materials.usda")
        stage = Usd.Stage.CreateNew(path)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)

        populate_materials_in_scope(stage, "/Materials")
        root_prim = stage.GetPrimAtPath("/Materials")
        stage.SetDefaultPrim(root_prim)

        stage.GetRootLayer().Save()
        return path

    def _build_detailed_vehicle(self, stage, veh_root: str, st_id: int, mats: dict):
        """Constructs a multi-part 3D AITO M9 SUV atop a carrier skillet pallet."""
        # 1. Carrier Skillet Platform (underneath vehicle at local Z = -0.52)
        define_cube_mesh(
            stage, f"{veh_root}/SkilletPlatform", (0.0, 0.0, -0.50), (5.8, 2.5, 0.12),
            (0.22, 0.25, 0.30), is_collider=False, material=mats["ConveyorSteelFrame"]
        )
        define_cube_mesh(
            stage, f"{veh_root}/SkilletSafetyEdge_F", (2.85, 0.0, -0.46), (0.12, 2.5, 0.14),
            (0.96, 0.78, 0.05), is_collider=False, material=mats["SafetyYellowStripes"]
        )
        define_cube_mesh(
            stage, f"{veh_root}/SkilletSafetyEdge_R", (-2.85, 0.0, -0.46), (0.12, 2.5, 0.14),
            (0.96, 0.78, 0.05), is_collider=False, material=mats["SafetyYellowStripes"]
        )

        # Alternate luxury AITO M9 two-tone paint colors across stations
        body_colors = [
            (0.78, 0.83, 0.89),  # Galaxy Silver
            (0.12, 0.22, 0.35),  # Deep Starry Blue
            (0.15, 0.28, 0.25),  # Emerald Pine Green
            (0.88, 0.86, 0.82),  # Ceramic White
        ]
        c_rgb = body_colors[st_id % len(body_colors)]

        # 2. Main Car Lower Cabin Body
        define_cube_mesh(
            stage, f"{veh_root}/Cabin", (0.0, 0.0, -0.05), (5.23, 2.00, 0.82),
            c_rgb, material=mats["VehicleMetallicSilver"]
        )
        # Sculpted Front Hood & Rear Quarter Deck
        define_cube_mesh(
            stage, f"{veh_root}/FrontHood", (1.85, 0.0, 0.12), (1.45, 1.92, 0.45),
            c_rgb, is_collider=False, material=mats["VehicleMetallicSilver"]
        )
        # Silver Two-Tone Upper Pillars / Roofline Frame
        define_cube_mesh(
            stage, f"{veh_root}/RoofPillars", (-0.30, 0.0, 0.52), (3.45, 1.78, 0.42),
            (0.85, 0.88, 0.92), is_collider=False, material=mats["AlloyRimSilver"]
        )
        # Panoramic Tinted Greenhouse & Roof Glass
        define_cube_mesh(
            stage, f"{veh_root}/RoofGlass", (-0.25, 0.0, 0.56), (3.35, 1.68, 0.48),
            (0.05, 0.09, 0.15), is_collider=False, material=mats["VehicleDarkWindshield"], opacity=0.45
        )
        # Huawei 192-Line Roof LiDAR Sensor Turret
        define_cylinder_mesh(
            stage, f"{veh_root}/Huawei192Lidar", (0.95, 0.0, 0.84), 0.14, 0.10, axis="Z",
            color=(0.10, 0.10, 0.12), is_collider=False, material=mats["ConveyorBeltRubber"]
        )
        # Front HUAWEI XPIXEL Star-Ring Headlight Bar
        define_cube_mesh(
            stage, f"{veh_root}/FrontLightBar", (2.62, 0.0, 0.08), (0.08, 1.86, 0.18),
            (0.92, 0.97, 1.0), is_collider=False, material=mats["VehicleStarRingLED"]
        )
        # Rear Star-Matrix Tail Light Bar
        define_cube_mesh(
            stage, f"{veh_root}/RearLightBar", (-2.62, 0.0, 0.16), (0.08, 1.86, 0.22),
            (0.98, 0.12, 0.15), is_collider=False, material=mats["VehicleTailLightLED"]
        )
        # Side Mirrors
        define_cube_mesh(
            stage, f"{veh_root}/Mirror_Left", (0.85, 1.08, 0.36), (0.22, 0.18, 0.14),
            c_rgb, is_collider=False, material=mats["VehicleMetallicSilver"]
        )
        define_cube_mesh(
            stage, f"{veh_root}/Mirror_Right", (0.85, -1.08, 0.36), (0.22, 0.18, 0.14),
            c_rgb, is_collider=False, material=mats["VehicleMetallicSilver"]
        )

        # 3. 4 Properly Oriented Y-Axis Wheels + Alloy Rims
        wheel_configs = [
            ("Wheel_FL", 1.58, 0.98),
            ("Wheel_FR", 1.58, -0.98),
            ("Wheel_RL", -1.58, 0.98),
            ("Wheel_RR", -1.58, -0.98),
        ]
        for w_name, wx, wy in wheel_configs:
            w_path = f"{veh_root}/{w_name}"
            define_cylinder_mesh(
                stage, w_path, (wx, wy, -0.22), 0.39, 0.28, axis="Y",
                color=(0.06, 0.06, 0.07), material=mats["VehicleTireRubber"]
            )
            define_cylinder_mesh(
                stage, f"{w_path}/AlloyRim", (wx, wy + (0.02 if wy > 0 else -0.02), -0.22),
                0.26, 0.29, axis="Y",
                color=(0.85, 0.88, 0.92), is_collider=False, material=mats["AlloyRimSilver"]
            )

    def _build_detailed_rack(
        self,
        stage,
        rack_root: str,
        rack_cx: float,
        rack_cy: float,
        width: float,
        depth: float,
        height: float,
        part_color: tuple,
        mats: dict,
    ):
        """Constructs an industrial multi-tier flow rack while keeping BaseFrame exact for spatial audit."""
        # 1. Exact Bounding BaseFrame (used by SpatialClearanceChecker for millimeter collision check)
        define_cube_mesh(
            stage,
            f"{rack_root}/BaseFrame",
            (rack_cx, rack_cy, 0.80),
            (width, depth, 1.50),
            (0.16, 0.42, 0.72),
            material=mats["RackFrameBlue"],
            opacity=0.28,
        )

        # 2. Structural Corner Upright Posts & Multi-Tier Shelves
        struct_path = f"{rack_root}/RackStructure"
        UsdGeom.Xform.Define(stage, struct_path)
        dx = width * 0.46
        dy = depth * 0.46
        for idx, (px, py) in enumerate([(-dx, -dy), (dx, -dy), (-dx, dy), (dx, dy)], 1):
            define_cube_mesh(
                stage,
                f"{struct_path}/Post_{idx}",
                (rack_cx + px, rack_cy + py, height * 0.5),
                (0.08, 0.08, height),
                (0.14, 0.38, 0.68),
                is_collider=False,
                material=mats["RackFrameBlue"],
            )

        for level_idx, sz in enumerate([0.22, 0.78, 1.32], 1):
            define_cube_mesh(
                stage,
                f"{struct_path}/Shelf_{level_idx}",
                (rack_cx, rack_cy, sz),
                (width * 0.96, depth * 0.94, 0.06),
                (0.76, 0.79, 0.83),
                is_collider=False,
                material=mats["RollerTrackAluminum"],
            )

        # 3. Primary BOM Item Payload + Multi-Box KLT / Sub-Assemblies
        define_cube_mesh(
            stage,
            f"{rack_root}/BOM_Item",
            (rack_cx, rack_cy, 0.98),
            (width * 0.78, depth * 0.76, 0.38),
            part_color,
            is_collider=False,
        )
        define_cube_mesh(
            stage,
            f"{rack_root}/BOM_Item_Lower",
            (rack_cx, rack_cy, 0.44),
            (width * 0.78, depth * 0.76, 0.36),
            part_color,
            is_collider=False,
        )

        # 4. Andon Stack Light on Top of Rack
        define_cylinder_mesh(
            stage,
            f"{struct_path}/AndonStackLight",
            (rack_cx + dx, rack_cy, height + 0.18),
            0.05,
            0.36,
            axis="Z",
            color=(0.10, 0.85, 0.35),
            is_collider=False,
        )

    def _build_station_robot(self, stage, st_root: str, cx: float, side_y: float, mats: dict):
        """Adds an articulated 6-axis industrial assembly robot arm at key automation stations."""
        rob_root = f"{st_root}/AutomationRobot_{'N' if side_y > 0 else 'S'}"
        UsdGeom.Xform.Define(stage, rob_root)
        # Pedestal Base
        define_cylinder_mesh(
            stage, f"{rob_root}/BasePedestal", (cx - 1.2, side_y, 0.45), 0.38, 0.90, axis="Z",
            color=(0.22, 0.24, 0.28), is_collider=False, material=mats["ConveyorSteelFrame"]
        )
        # Turret & Lower Arm
        define_cylinder_mesh(
            stage, f"{rob_root}/ShoulderTurret", (cx - 1.2, side_y, 1.05), 0.32, 0.35, axis="Z",
            color=(0.95, 0.42, 0.06), is_collider=False, material=mats["RobotOrange"]
        )
        define_cube_mesh(
            stage, f"{rob_root}/LowerArm", (cx - 1.2, side_y * 0.82, 1.55), (0.26, 0.26, 1.10),
            (0.95, 0.42, 0.06), is_collider=False, material=mats["RobotOrange"]
        )
        # Forearm reaching toward vehicle
        define_cube_mesh(
            stage, f"{rob_root}/Forearm", (cx - 0.9, side_y * 0.55, 1.95), (0.75, 0.22, 0.22),
            (0.95, 0.42, 0.06), is_collider=False, material=mats["RobotOrange"]
        )
        # End-Effector Gripper
        define_cube_mesh(
            stage, f"{rob_root}/EndEffector", (cx - 0.55, side_y * 0.42, 1.75), (0.35, 0.45, 0.25),
            (0.15, 0.18, 0.22), is_collider=False, material=mats["ConveyorBeltRubber"]
        )

    def _build_agv_tugger_train(
        self,
        stage,
        agv_path: str,
        start_x: float,
        highway_y: float,
        direction: float,
        is_animated: bool,
        mats: dict,
    ):
        """Constructs a 3D AGV Tugger Train (Tractor + LiDAR + Safety Field + 4 Towed Trailers)."""
        agv_root = UsdGeom.Xform.Define(stage, agv_path)

        if is_animated:
            t_op = agv_root.AddTranslateOp()
            for f in range(1, 241):
                agv_anim_x = start_x + direction * (f - 1) * 0.85
                # Wrap smoothly within 20m..275m
                agv_anim_x = 20.0 + ((agv_anim_x - 20.0) % 255.0)
                t_op.Set(Gf.Vec3d(agv_anim_x, highway_y, 0.35), Usd.TimeCode(f))
        else:
            agv_root.AddTranslateOp().Set(Gf.Vec3d(start_x, highway_y, 0.35))

        # Tractor Vehicle Body
        define_cube_mesh(
            stage, f"{agv_path}/Tractor", (0.0, 0.0, 0.05), (2.0, 1.22, 0.65),
            (0.08, 0.68, 0.78), material=mats["AGVChassisTeal"]
        )
        define_cube_mesh(
            stage, f"{agv_path}/Tractor/Bumper", (1.02 * direction, 0.0, -0.12), (0.12, 1.26, 0.22),
            (0.96, 0.78, 0.05), is_collider=False, material=mats["SafetyYellowStripes"]
        )
        # Top Rotating LiDAR Puck
        define_cylinder_mesh(
            stage, f"{agv_path}/Tractor/LidarSensor", (0.55 * direction, 0.0, 0.50), 0.14, 0.24, axis="Z",
            color=(0.10, 0.10, 0.12), material=mats["ConveyorBeltRubber"]
        )
        # Laser Safety Scan Field Cone (Translucent Red/Cyan)
        define_cylinder_mesh(
            stage, f"{agv_path}/Tractor/LaserSafetyField", (1.55 * direction, 0.0, -0.22), 0.85, 0.03, axis="Z",
            color=(0.95, 0.08, 0.08), is_collider=False, material=mats["LidarLaserRed"], opacity=0.30
        )
        # Warning Beacon Light
        define_cylinder_mesh(
            stage, f"{agv_path}/Tractor/BeaconLight", (-0.55 * direction, 0.0, 0.52), 0.09, 0.22, axis="Z",
            color=(0.98, 0.68, 0.05), is_collider=False, material=mats["SafetyYellowStripes"]
        )

        # 4 Towed Cargo Trailers (Milk Run)
        for trailer_i in range(1, 5):
            trailer_offset_x = -direction * trailer_i * 2.4
            t_path = f"{agv_path}/Trailer_{trailer_i:02d}"
            # Trailer Frame
            define_cube_mesh(
                stage, f"{t_path}/Chassis", (trailer_offset_x, 0.0, -0.05), (1.82, 1.14, 0.28),
                (0.28, 0.33, 0.40), material=mats["ConveyorSteelFrame"]
            )
            # Roller Deck Top
            define_cube_mesh(
                stage, f"{t_path}/RollerDeck", (trailer_offset_x, 0.0, 0.12), (1.72, 1.06, 0.06),
                (0.76, 0.79, 0.83), is_collider=False, material=mats["RollerTrackAluminum"]
            )
            # Hitch Bar
            define_cube_mesh(
                stage, f"{t_path}/Hitch", (trailer_offset_x + direction * 1.15, 0.0, -0.08),
                (0.62, 0.14, 0.08), (0.20, 0.20, 0.22), is_collider=False, material=mats["ConveyorSteelFrame"]
            )
            # Towed Parts Tote Boxes (Blue KLT Bins)
            define_cube_mesh(
                stage, f"{t_path}/KLT_BOM_Pallet", (trailer_offset_x, 0.0, 0.40), (1.45, 0.92, 0.52),
                (0.16, 0.46, 0.86), material=mats["RackFrameBlue"]
            )

    def build_master_stage(
        self,
        filename: str = "seres_ga_workshop_main.usda",
        is_baseline: bool = False,
        is_animated: bool = False,
    ) -> str:
        """Constructs a fully featured 3D Omniverse master stage with bound PBR materials."""
        stage_path = os.path.join(self.stages_dir, filename)
        stage = Usd.Stage.CreateNew(stage_path)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)

        if is_animated:
            stage.SetStartTimeCode(1.0)
            stage.SetEndTimeCode(240.0)
            stage.SetTimeCodesPerSecond(30.0)

        world_path = Sdf.Path("/World")
        world_xform = UsdGeom.Xform.Define(stage, world_path)
        stage.SetDefaultPrim(world_xform.GetPrim())

        # Create in-stage PBR material library and bind to geometry
        mats = populate_materials_in_scope(stage, "/World/Materials")

        # -------------------------------------------------------------
        # 1. PhysX 5 Global Physics Scene
        # -------------------------------------------------------------
        phys_scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
        phys_scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
        phys_scene.CreateGravityMagnitudeAttr().Set(9.81)

        # -------------------------------------------------------------
        # 2. RTX Lighting & Environment
        # -------------------------------------------------------------
        UsdGeom.Scope.Define(stage, "/World/Lighting")

        dome = UsdLux.DomeLight.Define(stage, "/World/Lighting/RTX_DomeLight")
        dome.CreateIntensityAttr().Set(1500.0)
        dome.CreateColorAttr().Set(Gf.Vec3f(0.92, 0.95, 1.0))

        sun = UsdLux.DistantLight.Define(stage, "/World/Lighting/HighBay_SunLight")
        sun.CreateIntensityAttr().Set(3500.0)
        sun.CreateColorAttr().Set(Gf.Vec3f(1.0, 0.98, 0.94))
        sun.AddRotateXYZOp().Set(Gf.Vec3f(-45.0, 30.0, 0.0))

        # -------------------------------------------------------------
        # 3. 3D Factory Building Architecture (320m x 100m)
        # -------------------------------------------------------------
        UsdGeom.Xform.Define(stage, "/World/Environment")

        # Workshop Epoxy Floor
        define_cube_mesh(
            stage, "/World/Environment/ConcreteFloor", (140.0, -10.0, -0.15), (320.0, 100.0, 0.3),
            (0.22, 0.25, 0.29), material=mats["FloorEpoxyGray"]
        )

        # Pedestrian Safe Green Walkways alongside line
        define_cube_mesh(
            stage, "/World/Environment/NorthWalkway", (140.0, 2.15, 0.01), (290.0, 0.90, 0.02),
            (0.12, 0.52, 0.30), is_collider=False, material=mats["FloorWalkwayGreen"]
        )
        define_cube_mesh(
            stage, "/World/Environment/SouthWalkway", (140.0, -2.15, 0.01), (290.0, 0.90, 0.02),
            (0.12, 0.52, 0.30), is_collider=False, material=mats["FloorWalkwayGreen"]
        )

        # Dedicated North & South AGV Highway Lanes (Y = +6.2m and -6.2m, boundary at +-4.8m)
        define_cube_mesh(
            stage, "/World/Environment/AGVHighway_North", (140.0, 6.2, 0.015), (292.0, 2.8, 0.02),
            (0.08, 0.32, 0.48), is_collider=False, material=mats["FloorAGVLaneBlue"]
        )
        define_cube_mesh(
            stage, "/World/Environment/AGVHighway_South", (140.0, -6.2, 0.015), (292.0, 2.8, 0.02),
            (0.08, 0.32, 0.48), is_collider=False, material=mats["FloorAGVLaneBlue"]
        )
        define_cube_mesh(
            stage, "/World/Environment/AGVBoundaryLine_North", (140.0, 4.8, 0.02), (292.0, 0.12, 0.02),
            (0.96, 0.78, 0.05), is_collider=False, material=mats["SafetyYellowStripes"]
        )
        define_cube_mesh(
            stage, "/World/Environment/AGVBoundaryLine_South", (140.0, -4.8, 0.02), (292.0, 0.12, 0.02),
            (0.96, 0.78, 0.05), is_collider=False, material=mats["SafetyYellowStripes"]
        )

        # Yellow Hazard Striping along conveyor edges
        define_cube_mesh(
            stage, "/World/Environment/ConveyorNorthHatch", (140.0, 1.7, 0.01), (285.0, 0.15, 0.02),
            (0.96, 0.78, 0.05), is_collider=False, material=mats["SafetyYellowStripes"]
        )
        define_cube_mesh(
            stage, "/World/Environment/ConveyorSouthHatch", (140.0, -1.7, 0.01), (285.0, 0.15, 0.02),
            (0.96, 0.78, 0.05), is_collider=False, material=mats["SafetyYellowStripes"]
        )

        # Steel Column Grid: 18m x 12m grid (Columns at Y=-16m, -4.2m, 4.2m, 16m)
        UsdGeom.Scope.Define(stage, "/World/Environment/BuildingColumns")
        col_y_list = [-16.0, -4.2, 4.2, 16.0]
        for col_x in range(0, 300, 18):
            for col_y in col_y_list:
                y_tag = f"n{abs(int(col_y))}" if col_y < 0 else f"p{abs(int(col_y))}"
                c_name = f"Col_{col_x}_{y_tag}"
                c_path = f"/World/Environment/BuildingColumns/{c_name}"

                # Column Main Body (0.6m x 0.6m x 8m — exact scale preserved for SpatialClearanceChecker)
                col_cube = define_cube_mesh(
                    stage, c_path, (float(col_x), float(col_y), 4.0), (0.6, 0.6, 8.0),
                    (0.14, 0.38, 0.68), material=mats["SteelColumnBlue"]
                )
                col_cube.GetPrim().CreateAttribute("custom:isBuildingColumn", Sdf.ValueTypeNames.Bool).Set(True)

                # Baseplate & Yellow Safety Crash Guard at Bottom of Column
                define_cube_mesh(
                    stage, f"{c_path}/Baseplate", (float(col_x), float(col_y), 0.04), (1.1, 1.1, 0.08),
                    (0.22, 0.24, 0.28), is_collider=False, material=mats["ConveyorSteelFrame"]
                )
                define_cube_mesh(
                    stage, f"{c_path}/SafetyGuard", (float(col_x), float(col_y), 0.60), (0.72, 0.72, 1.10),
                    (0.96, 0.78, 0.05), is_collider=False, material=mats["SafetyYellowStripes"]
                )

        # Overhead Roof Trusses & Longitudinal Crane Beams across the plant span
        for tx in range(0, 300, 18):
            define_cube_mesh(
                stage, f"/World/Environment/Truss_{tx}", (float(tx), 0.0, 8.2), (0.45, 42.0, 0.55),
                (0.28, 0.31, 0.36), is_collider=False, material=mats["ConveyorSteelFrame"]
            )

        # -------------------------------------------------------------
        # 4. 280-meter Main Assembly Conveyor System
        # -------------------------------------------------------------
        UsdGeom.Xform.Define(stage, "/World/AssemblyLine")

        define_cube_mesh(
            stage, "/World/AssemblyLine/ConveyorSteelBed", (136.5, 0.0, 0.25), (285.0, 3.2, 0.5),
            (0.26, 0.29, 0.34), material=mats["ConveyorSteelFrame"]
        )
        define_cube_mesh(
            stage, "/World/AssemblyLine/ConveyorRubberSurface", (136.5, 0.0, 0.52), (283.0, 3.0, 0.05),
            (0.09, 0.10, 0.12), material=mats["ConveyorBeltRubber"]
        )
        define_cube_mesh(
            stage, "/World/AssemblyLine/GuideRail_North", (136.5, 1.62, 0.65), (285.0, 0.08, 0.3),
            (0.96, 0.78, 0.05), material=mats["SafetyYellowStripes"]
        )
        define_cube_mesh(
            stage, "/World/AssemblyLine/GuideRail_South", (136.5, -1.62, 0.65), (285.0, 0.08, 0.3),
            (0.96, 0.78, 0.05), material=mats["SafetyYellowStripes"]
        )

        # -------------------------------------------------------------
        # 5. Build 40 Workstations, Detailed Vehicles, Racks & Robots
        # -------------------------------------------------------------
        robot_stations = {8, 15, 16, 21, 22, 24, 31, 32, 34, 36}

        for st in self.stations:
            st_root = f"/World/AssemblyLine/Station_{st.station_id:02d}"
            st_xform = UsdGeom.Xform.Define(stage, st_root)
            st_prim = st_xform.GetPrim()
            st_prim.CreateAttribute("custom:stationId", Sdf.ValueTypeNames.Int).Set(st.station_id)
            st_prim.CreateAttribute("custom:stationName", Sdf.ValueTypeNames.String).Set(st.station_name)
            st_prim.CreateAttribute("custom:zone", Sdf.ValueTypeNames.String).Set(st.zone)

            cx = st.pos_x + st.length / 2.0

            # Overhead Station Gantry Sign & LED Light
            define_cube_mesh(
                stage, f"{st_root}/OverheadSign", (cx, 0.0, 4.5), (3.2, 0.14, 0.75),
                (0.08, 0.14, 0.24), is_collider=False, material=mats["SteelColumnBlue"]
            )

            st_light = UsdLux.RectLight.Define(stage, f"{st_root}/Workstation_LED")
            st_light.AddTranslateOp().Set(Gf.Vec3d(cx, 0.0, 4.0))
            st_light.AddRotateXYZOp().Set(Gf.Vec3f(-90.0, 0.0, 0.0))
            st_light.CreateIntensityAttr().Set(850.0)
            st_light.CreateWidthAttr().Set(4.2)
            st_light.CreateHeightAttr().Set(2.2)
            st_light.CreateColorAttr().Set(Gf.Vec3f(0.98, 0.99, 1.0))

            # Detailed 3D Vehicle Body (AITO M9 Geometry)
            veh_root = f"{st_root}/VehicleBody_{st.station_id:02d}"
            veh_xform = UsdGeom.Xform.Define(stage, veh_root)

            if is_animated:
                trans_op = veh_xform.AddTranslateOp()
                for f in range(1, 241):
                    time_x = cx + (f - 1) * 0.12
                    trans_op.Set(Gf.Vec3d(time_x, 0.0, 1.10), Usd.TimeCode(f))
            else:
                veh_xform.AddTranslateOp().Set(Gf.Vec3d(cx, 0.0, 1.10))

            self._build_detailed_vehicle(stage, veh_root, st.station_id, mats)

            # Optional Automation Robot Arms at key stations
            if st.station_id in robot_stations:
                self._build_station_robot(stage, st_root, cx, 2.05, mats)
                self._build_station_robot(stage, st_root, cx, -2.05, mats)

            # Line-side Racks placement
            rack_cx = cx
            is_col_overlap_station = st.station_id in [16, 21, 34]
            is_encroach_station = st.station_id in [24, 32]

            if not is_baseline and is_col_overlap_station:
                shift_dist = 2.2 if max(st.left_part.rack_width, st.right_part.rack_width) >= 2.0 else 1.8
                rack_cx = cx + shift_dist

            # --- Left Line-side Rack (North) ---
            l_depth = st.left_part.rack_depth
            l_width = st.left_part.rack_width
            if not is_baseline and is_encroach_station:
                l_depth = 1.35  # Optimized mode: compact vertical dual-tier rack

            l_y = 1.6 + 0.9 + (l_depth / 2.0)
            l_rack_root = f"{st_root}/Rack_Left_{st.left_part.part_id}"
            self._build_detailed_rack(
                stage, l_rack_root, rack_cx, l_y, l_width, l_depth, st.left_part.rack_height,
                st.left_part.color_rgb, mats
            )

            # --- Right Line-side Rack (South) ---
            r_depth = st.right_part.rack_depth
            r_width = st.right_part.rack_width
            if not is_baseline and is_encroach_station:
                r_depth = 1.35

            r_y = -(1.6 + 0.9 + (r_depth / 2.0))
            r_rack_root = f"{st_root}/Rack_Right_{st.right_part.part_id}"
            self._build_detailed_rack(
                stage, r_rack_root, rack_cx, r_y, r_width, r_depth, st.right_part.rack_height,
                st.right_part.color_rgb, mats
            )

            # Baseline Mode: Translucent Glowing Red/Amber Collision Volumes
            if is_baseline:
                if is_col_overlap_station:
                    warn_box = define_cube_mesh(
                        stage,
                        f"{st_root}/CollisionHazard_ColumnOverlap",
                        (cx, l_y, 1.8),
                        (l_width + 0.6, l_depth + 0.6, 2.4),
                        (0.98, 0.12, 0.12),
                        is_collider=False,
                        material=mats["CollisionHazardGlow"],
                        opacity=0.38,
                    )
                    warn_box.GetPrim().CreateAttribute("custom:hazardType", Sdf.ValueTypeNames.String).Set(
                        "BuildingColumnCollision"
                    )

                if is_encroach_station:
                    enc_box = define_cube_mesh(
                        stage,
                        f"{st_root}/CollisionHazard_AGVEncroachment",
                        (cx, l_y + 0.4, 1.0),
                        (l_width + 0.4, 0.85, 1.7),
                        (0.98, 0.52, 0.05),
                        is_collider=False,
                        material=mats["EncroachmentAmberGlow"],
                        opacity=0.38,
                    )
                    enc_box.GetPrim().CreateAttribute("custom:hazardType", Sdf.ValueTypeNames.String).Set(
                        "AGVHighwaySafetyEncroachment"
                    )

        # -------------------------------------------------------------
        # 6. 3D AGV Tugger Train Fleet (6 Active Trains Across Both Highways)
        # -------------------------------------------------------------
        UsdGeom.Scope.Define(stage, "/World/AGV_Fleet")
        agv_deployments = [
            ("TuggerTrain_01", 40.0 if is_animated else 75.0, 6.2, 1.0),
            ("TuggerTrain_02", 130.0, 6.2, 1.0),
            ("TuggerTrain_03", 215.0, 6.2, 1.0),
            ("TuggerTrain_04", 65.0, -6.2, -1.0),
            ("TuggerTrain_05", 160.0, -6.2, -1.0),
            ("TuggerTrain_06", 245.0, -6.2, -1.0),
        ]
        for train_name, sx, sy, sdir in agv_deployments:
            self._build_agv_tugger_train(
                stage, f"/World/AGV_Fleet/{train_name}", sx, sy, sdir, is_animated, mats
            )

        # -------------------------------------------------------------
        # 7. Zoned Supermarkets & High-Bay Warehouse (SPS Area)
        # -------------------------------------------------------------
        UsdGeom.Scope.Define(stage, "/World/LogisticsSupermarkets")

        if is_baseline:
            define_cube_mesh(
                stage,
                "/World/LogisticsSupermarkets/Central_ASRS_Warehouse",
                (140.0, -32.0, 5.0),
                (160.0, 18.0, 10.0),
                (0.26, 0.29, 0.34),
                material=mats["ConveyorSteelFrame"],
            )
        else:
            define_cube_mesh(
                stage,
                "/World/LogisticsSupermarkets/SPS_Trim_Supermarket",
                (70.0, -22.0, 3.5),
                (65.0, 14.0, 7.0),
                (0.08, 0.68, 0.78),
                material=mats["AGVChassisTeal"],
            )
            define_cube_mesh(
                stage,
                "/World/LogisticsSupermarkets/SPS_Chassis_ASRS",
                (175.0, -25.0, 6.0),
                (70.0, 18.0, 12.0),
                (0.14, 0.38, 0.68),
                material=mats["SteelColumnBlue"],
            )
            define_cube_mesh(
                stage,
                "/World/LogisticsSupermarkets/SPS_Final_Supermarket",
                (245.0, -22.0, 3.5),
                (60.0, 14.0, 7.0),
                (0.08, 0.68, 0.78),
                material=mats["AGVChassisTeal"],
            )

        # -------------------------------------------------------------
        # 8. Omniverse Viewport RTX Camera Bookmarks
        # -------------------------------------------------------------
        UsdGeom.Scope.Define(stage, "/World/Cameras")

        c1 = UsdGeom.Camera.Define(stage, "/World/Cameras/GA_Line_Overview_Isometric")
        c1.AddTranslateOp().Set(Gf.Vec3d(140.0, -52.0, 36.0))
        c1.AddRotateXYZOp().Set(Gf.Vec3f(56.0, 0.0, 0.0))
        c1.CreateFocalLengthAttr().Set(24.0)
        c1.CreateClippingRangeAttr().Set(Gf.Vec2f(0.1, 2000.0))

        c2 = UsdGeom.Camera.Define(stage, "/World/Cameras/Station_16_Seat_Hazard_Cam")
        c2.AddTranslateOp().Set(Gf.Vec3d(101.0, -10.5, 5.2))
        c2.AddRotateXYZOp().Set(Gf.Vec3f(68.0, 0.0, -32.0))
        c2.CreateFocalLengthAttr().Set(32.0)
        c2.CreateClippingRangeAttr().Set(Gf.Vec2f(0.1, 1000.0))

        c3 = UsdGeom.Camera.Define(stage, "/World/Cameras/Station_24_Battery_Cell_Cam")
        c3.AddTranslateOp().Set(Gf.Vec3d(157.0, 11.5, 5.0))
        c3.AddRotateXYZOp().Set(Gf.Vec3f(68.0, 0.0, -148.0))
        c3.CreateFocalLengthAttr().Set(32.0)
        c3.CreateClippingRangeAttr().Set(Gf.Vec2f(0.1, 1000.0))

        c4 = UsdGeom.Camera.Define(stage, "/World/Cameras/AGV_Tugger_Train_Follow")
        c4.AddTranslateOp().Set(Gf.Vec3d(62.0, 11.0, 4.2))
        c4.AddRotateXYZOp().Set(Gf.Vec3f(72.0, 0.0, -115.0))
        c4.CreateFocalLengthAttr().Set(35.0)
        c4.CreateClippingRangeAttr().Set(Gf.Vec2f(0.1, 1000.0))

        stage.GetRootLayer().Save()
        return stage_path

    def generate_all(self):
        print("Generating Factory Physical Materials layer...")
        self.build_materials_layer()

        print("Generating Master Optimized Stage (assets/stages/seres_ga_workshop_main.usda)...")
        self.build_master_stage("seres_ga_workshop_main.usda", is_baseline=False, is_animated=False)

        print("Generating Master Baseline Stage (assets/stages/seres_ga_workshop_baseline.usda)...")
        self.build_master_stage("seres_ga_workshop_baseline.usda", is_baseline=True, is_animated=False)

        print("Generating 240-Frame Timeline Animated Stage (assets/stages/seres_ga_workshop_animated.usda)...")
        self.build_master_stage("seres_ga_workshop_animated.usda", is_baseline=False, is_animated=True)
        print("All OpenUSD 3D stages created successfully!")


if __name__ == "__main__":
    gen = OmniverseUSDStageGenerator()
    gen.generate_all()
