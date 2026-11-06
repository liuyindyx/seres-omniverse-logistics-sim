"""
High-Fidelity OpenUSD 3D Asset and Master Stage Generator for NVIDIA Omniverse
=============================================================================
Constructs complete 3D meshes, RTX lights, PBR physical materials, PhysX 5 schemas,
camera bookmarks, and timeCode animation tracks for Seres Super Factory.
"""

import os
import sys
import math

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pxr import Usd, UsdGeom, UsdPhysics, UsdShade, UsdLux, Sdf, Gf
from simulation.workshop_specs import get_seres_40_stations, StationSpecification

def define_cube_mesh(stage, path, center, size, color=None, is_collider=True):
    """Utility to define a 3D box prim with scale, translation, collision, and color."""
    cube = UsdGeom.Cube.Define(stage, path)
    cube.AddTranslateOp().Set(Gf.Vec3d(*center))
    cube.AddScaleOp().Set(Gf.Vec3f(size[0]/2.0, size[1]/2.0, size[2]/2.0))
    prim = cube.GetPrim()
    if is_collider:
        UsdPhysics.CollisionAPI.Apply(prim)
    if color:
        cube.GetDisplayColorAttr().Set([Gf.Vec3f(*color)])
    return cube

def define_cylinder_mesh(stage, path, center, radius, height, color=None, is_collider=True):
    """Utility to define a 3D cylinder prim."""
    cyl = UsdGeom.Cylinder.Define(stage, path)
    cyl.AddTranslateOp().Set(Gf.Vec3d(*center))
    cyl.AddScaleOp().Set(Gf.Vec3f(radius, radius, height/2.0))
    prim = cyl.GetPrim()
    if is_collider:
        UsdPhysics.CollisionAPI.Apply(prim)
    if color:
        cyl.GetDisplayColorAttr().Set([Gf.Vec3f(*color)])
    return cyl

class OmniverseUSDStageGenerator:
    """Generates all 3D OpenUSD stages and modular sublayers."""

    def __init__(self, output_dir: str = "assets"):
        self.output_dir = output_dir
        self.stages_dir = os.path.join(output_dir, "stages")
        self.materials_dir = os.path.join(output_dir, "materials")
        self.props_dir = os.path.join(output_dir, "props")
        os.makedirs(self.stages_dir, exist_ok=True)
        os.makedirs(self.materials_dir, exist_ok=True)
        os.makedirs(self.props_dir, exist_ok=True)
        self.stations = get_seres_40_stations()

    def build_materials_layer(self) -> str:
        """Creates physical PBR and PhysX materials."""
        path = os.path.join(self.materials_dir, "factory_materials.usda")
        stage = Usd.Stage.CreateNew(path)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
        
        root = UsdGeom.Scope.Define(stage, "/Materials")
        stage.SetDefaultPrim(root.GetPrim())

        materials_spec = [
            ("FloorEpoxyGray", (0.35, 0.38, 0.42), 0.3, 0.45, 0.40, 0.35),
            ("FloorWalkwayGreen", (0.15, 0.55, 0.32), 0.2, 0.50, 0.45, 0.38),
            ("SteelColumnBlue", (0.12, 0.35, 0.65), 0.8, 0.25, 0.30, 0.25),
            ("ConveyorBeltRubber", (0.10, 0.10, 0.12), 0.05, 0.85, 0.75, 0.65),
            ("ConveyorSteelFrame", (0.25, 0.28, 0.32), 0.75, 0.30, 0.40, 0.35),
            ("SafetyYellowStripes", (0.95, 0.80, 0.05), 0.1, 0.35, 0.40, 0.35),
            ("VehicleMetallicSilver", (0.82, 0.85, 0.90), 0.9, 0.15, 0.30, 0.25),
            ("VehicleDarkWindshield", (0.05, 0.08, 0.12), 0.95, 0.05, 0.20, 0.15),
            ("VehicleTireRubber", (0.05, 0.05, 0.05), 0.0, 0.90, 0.85, 0.80),
            ("AGVChassisTeal", (0.10, 0.65, 0.75), 0.7, 0.25, 0.35, 0.30),
            ("LidarLaserRed", (0.95, 0.05, 0.05), 0.0, 0.10, 0.0, 0.0),
            ("CollisionHazardGlow", (0.98, 0.15, 0.15), 0.0, 0.10, 0.0, 0.0)
        ]

        for name, col, metallic, roughness, static_f, dyn_f in materials_spec:
            mat_path = f"/Materials/{name}"
            mat = UsdShade.Material.Define(stage, mat_path)
            
            # Surface Shader
            shader = UsdShade.Shader.Define(stage, f"{mat_path}/PbrShader")
            shader.CreateIdAttr("UsdPreviewSurface")
            shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*col))
            shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metallic)
            shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
            mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

            # PhysX Material API
            phys_mat = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
            phys_mat.CreateStaticFrictionAttr().Set(static_f)
            phys_mat.CreateDynamicFrictionAttr().Set(dyn_f)
            phys_mat.CreateRestitutionAttr().Set(0.15)

        stage.GetRootLayer().Save()
        return path

    def build_master_stage(self, 
                           filename: str = "seres_ga_workshop_main.usda",
                           is_baseline: bool = False,
                           is_animated: bool = False) -> str:
        """Constructs a fully featured 3D Omniverse master stage."""
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

        # -------------------------------------------------------------
        # 1. PhysX 5 Global Physics Scene
        # -------------------------------------------------------------
        phys_scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
        phys_scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
        phys_scene.CreateGravityMagnitudeAttr().Set(9.81)

        # -------------------------------------------------------------
        # 2. RTX Lighting & Environment
        # -------------------------------------------------------------
        lights_scope = UsdGeom.Scope.Define(stage, "/World/Lighting")
        
        # Dome Light (Sky HDRI environment fill)
        dome = UsdLux.DomeLight.Define(stage, "/World/Lighting/RTX_DomeLight")
        dome.CreateIntensityAttr().Set(1500.0)
        dome.CreateColorAttr().Set(Gf.Vec3f(0.92, 0.95, 1.0))

        # Distant Light (Main industrial sun/high-bay lighting angled down)
        sun = UsdLux.DistantLight.Define(stage, "/World/Lighting/HighBay_SunLight")
        sun.CreateIntensityAttr().Set(3500.0)
        sun.CreateColorAttr().Set(Gf.Vec3f(1.0, 0.98, 0.94))
        sun.AddRotateXYZOp().Set(Gf.Vec3f(-45.0, 30.0, 0.0))

        # -------------------------------------------------------------
        # 3. 3D Factory Building Architecture (320m x 120m)
        # -------------------------------------------------------------
        env_root = UsdGeom.Xform.Define(stage, "/World/Environment")
        
        # Workshop Concrete Floor (320m x 100m x 0.3m)
        define_cube_mesh(stage, "/World/Environment/ConcreteFloor", (140.0, -10.0, -0.15), (320.0, 100.0, 0.3), (0.35, 0.38, 0.42))
        
        # Pedestrian Safe Green Walkways alongside line
        define_cube_mesh(stage, "/World/Environment/NorthWalkway", (140.0, 3.6, 0.01), (290.0, 1.2, 0.02), (0.15, 0.55, 0.32), is_collider=False)
        define_cube_mesh(stage, "/World/Environment/SouthWalkway", (140.0, -3.6, 0.01), (290.0, 1.2, 0.02), (0.15, 0.55, 0.32), is_collider=False)

        # Yellow Hazard Striping along conveyor edges
        define_cube_mesh(stage, "/World/Environment/ConveyorNorthHatch", (140.0, 1.7, 0.01), (285.0, 0.15, 0.02), (0.95, 0.80, 0.05), is_collider=False)
        define_cube_mesh(stage, "/World/Environment/ConveyorSouthHatch", (140.0, -1.7, 0.01), (285.0, 0.15, 0.02), (0.95, 0.80, 0.05), is_collider=False)

        # Steel Column Grid: 18m x 12m grid (Columns at Y=-16m, -4.2m, 4.2m, 16m)
        cols_scope = UsdGeom.Scope.Define(stage, "/World/Environment/BuildingColumns")
        col_y_list = [-16.0, -4.2, 4.2, 16.0]
        for col_x in range(0, 300, 18):
            for col_y in col_y_list:
                y_tag = f"n{abs(int(col_y))}" if col_y < 0 else f"p{abs(int(col_y))}"
                c_name = f"Col_{col_x}_{y_tag}"
                c_path = f"/World/Environment/BuildingColumns/{c_name}"
                
                # Column Main Body (H-Beam / Box Column 0.6m x 0.6m x 8m)
                col_cube = define_cube_mesh(stage, c_path, (float(col_x), float(col_y), 4.0), (0.6, 0.6, 8.0), (0.12, 0.35, 0.65))
                col_cube.GetPrim().CreateAttribute("custom:isBuildingColumn", Sdf.ValueTypeNames.Bool).Set(True)
                
                # Baseplate at floor
                define_cube_mesh(stage, f"{c_path}/Baseplate", (float(col_x), float(col_y), 0.04), (1.0, 1.0, 0.08), (0.2, 0.2, 0.2))

        # Overhead Roof Trusses across the plant span
        for tx in range(0, 300, 36):
            define_cube_mesh(stage, f"/World/Environment/Truss_{tx}", (float(tx), 0.0, 8.2), (0.8, 60.0, 0.4), (0.3, 0.32, 0.36), is_collider=False)

        # -------------------------------------------------------------
        # 4. 280-meter Main Assembly Conveyor System
        # -------------------------------------------------------------
        conv_root = UsdGeom.Xform.Define(stage, "/World/AssemblyLine")
        
        # Heavy Steel Frame & Plate Bed
        define_cube_mesh(stage, "/World/AssemblyLine/ConveyorSteelBed", (136.5, 0.0, 0.25), (285.0, 3.2, 0.5), (0.22, 0.24, 0.28))
        define_cube_mesh(stage, "/World/AssemblyLine/ConveyorRubberSurface", (136.5, 0.0, 0.52), (283.0, 3.0, 0.05), (0.1, 0.1, 0.12))
        
        # Steel Guide Rails on both sides
        define_cube_mesh(stage, "/World/AssemblyLine/GuideRail_North", (136.5, 1.62, 0.65), (285.0, 0.08, 0.3), (0.85, 0.85, 0.1))
        define_cube_mesh(stage, "/World/AssemblyLine/GuideRail_South", (136.5, -1.62, 0.65), (285.0, 0.08, 0.3), (0.85, 0.85, 0.1))

        # -------------------------------------------------------------
        # 5. Build 40 Workstations, Vehicles & 3D Racks
        # -------------------------------------------------------------
        for st in self.stations:
            st_root = f"/World/AssemblyLine/Station_{st.station_id:02d}"
            UsdGeom.Xform.Define(stage, st_root)
            cx = st.pos_x + st.length / 2.0

            # Overhead Station Workstation Signage & LED Light
            sign_path = f"{st_root}/OverheadSign"
            define_cube_mesh(stage, sign_path, (cx, 0.0, 4.5), (3.0, 0.1, 0.8), (0.05, 0.05, 0.1), is_collider=False)
            
            # Workstation Inspection LED RectLight
            st_light = UsdLux.RectLight.Define(stage, f"{st_root}/Workstation_LED")
            st_light.AddTranslateOp().Set(Gf.Vec3d(cx, 0.0, 4.0))
            st_light.AddRotateXYZOp().Set(Gf.Vec3f(-90.0, 0.0, 0.0))
            st_light.CreateIntensityAttr().Set(800.0)
            st_light.CreateWidthAttr().Set(4.0)
            st_light.CreateHeightAttr().Set(2.0)
            st_light.CreateColorAttr().Set(Gf.Vec3f(1.0, 1.0, 0.95))

            # 3D Vehicle Body (AITO M9 Geometry: 5.23m x 2.0m x 1.75m)
            veh_root = f"{st_root}/VehicleBody_{st.station_id:02d}"
            veh_xform = UsdGeom.Xform.Define(stage, veh_root)
            
            if is_animated:
                # Add time-sampled moving animation along conveyor
                trans_op = veh_xform.AddTranslateOp()
                for f in range(1, 241):
                    # Progress forward by 0.15m per frame
                    time_x = cx + (f - 1) * 0.12
                    trans_op.Set(Gf.Vec3d(time_x, 0.0, 1.1), Usd.TimeCode(f))
            else:
                veh_xform.AddTranslateOp().Set(Gf.Vec3d(cx, 0.0, 1.1))

            # Main Car Cabin Box
            define_cube_mesh(stage, f"{veh_root}/Cabin", (0.0, 0.0, 0.0), (5.2, 2.0, 1.3), (0.82, 0.85, 0.90))
            # Roof Greenhouse
            define_cube_mesh(stage, f"{veh_root}/RoofGlass", (0.2, 0.0, 0.65), (3.2, 1.6, 0.6), (0.05, 0.08, 0.15))
            # Front Hood & Star-ring light
            define_cube_mesh(stage, f"{veh_root}/FrontLightBar", (2.6, 0.0, -0.1), (0.1, 1.8, 0.2), (0.9, 0.95, 1.0), is_collider=False)
            # Rear Light Bar
            define_cube_mesh(stage, f"{veh_root}/RearLightBar", (-2.6, 0.0, 0.1), (0.1, 1.8, 0.2), (0.95, 0.1, 0.1), is_collider=False)
            # 4 Wheels
            wheel_configs = [
                ("Wheel_FL", 1.6, 1.05),
                ("Wheel_FR", 1.6, -1.05),
                ("Wheel_RL", -1.6, 1.05),
                ("Wheel_RR", -1.6, -1.05)
            ]
            for w_name, wx, wy in wheel_configs:
                w_path = f"{veh_root}/{w_name}"
                define_cylinder_mesh(stage, w_path, (wx, wy, -0.4), 0.45, 0.3, (0.05, 0.05, 0.05))

            # Line-side Racks placement
            # Determine Rack X coordinate
            rack_cx = cx
            is_col_overlap_station = (st.station_id in [16, 21, 34])
            is_encroach_station = (st.station_id in [24, 32])

            if not is_baseline and is_col_overlap_station:
                # Optimized mode: shift along X by 2.2m to cleanly bypass the 18m column!
                shift_dist = 2.2 if max(st.left_part.rack_width, st.right_part.rack_width) >= 2.0 else 1.8
                rack_cx = cx + shift_dist

            # --- Left Line-side Rack (North) ---
            l_depth = st.left_part.rack_depth
            l_width = st.left_part.rack_width
            if not is_baseline and is_encroach_station:
                l_depth = 1.35 # Optimized mode: compact vertical dual-tier rack

            l_y = 1.6 + 0.9 + (l_depth / 2.0)
            l_rack_root = f"{st_root}/Rack_Left_{st.left_part.part_id}"
            
            # Rack Upright Posts & Shelves
            define_cube_mesh(stage, f"{l_rack_root}/BaseFrame", (rack_cx, l_y, 0.8), (l_width, l_depth, 1.5), (0.2, 0.4, 0.65))
            # Colored Parts inside rack
            define_cube_mesh(stage, f"{l_rack_root}/BOM_Item", (rack_cx, l_y, 0.9), (l_width*0.8, l_depth*0.8, 0.8), st.left_part.color_rgb)

            # --- Right Line-side Rack (South) ---
            r_depth = st.right_part.rack_depth
            r_width = st.right_part.rack_width
            if not is_baseline and is_encroach_station:
                r_depth = 1.35

            r_y = -(1.6 + 0.9 + (r_depth / 2.0))
            r_rack_root = f"{st_root}/Rack_Right_{st.right_part.part_id}"
            define_cube_mesh(stage, f"{r_rack_root}/BaseFrame", (rack_cx, r_y, 0.8), (r_width, r_depth, 1.5), (0.2, 0.4, 0.65))
            define_cube_mesh(stage, f"{r_rack_root}/BOM_Item", (rack_cx, r_y, 0.9), (r_width*0.8, r_depth*0.8, 0.8), st.right_part.color_rgb)

            # If Baseline Mode: Draw 3D Red Collision Warning Box over the collided prims
            if is_baseline:
                if is_col_overlap_station:
                    warn_box = define_cube_mesh(stage, f"{st_root}/CollisionHazard_ColumnOverlap", 
                                                (cx, l_y, 1.8), (l_width + 0.6, l_depth + 0.6, 2.2), 
                                                (0.95, 0.1, 0.1), is_collider=False)
                    warn_box.GetPrim().CreateAttribute("custom:hazardType", Sdf.ValueTypeNames.String).Set("BuildingColumnCollision")

                if is_encroach_station:
                    enc_box = define_cube_mesh(stage, f"{st_root}/CollisionHazard_AGVEncroachment",
                                               (cx, l_y + 0.4, 1.0), (l_width + 0.4, 0.8, 1.6),
                                               (0.95, 0.4, 0.05), is_collider=False)
                    enc_box.GetPrim().CreateAttribute("custom:hazardType", Sdf.ValueTypeNames.String).Set("AGVHighwaySafetyEncroachment")

        # -------------------------------------------------------------
        # 6. 3D AGV Tugger Train Logistics (Tractor + 4 Trailers)
        # -------------------------------------------------------------
        agv_root = UsdGeom.Xform.Define(stage, "/World/AGV_Fleet/TuggerTrain_01")
        
        # AGV Path animation or static placement
        train_x = 75.0
        train_y = 6.2 # Driving along North Highway
        
        if is_animated:
            t_op = agv_root.AddTranslateOp()
            for f in range(1, 241):
                # AGV driving down North Highway at 1.5m/s (0.05m per frame)
                agv_anim_x = 40.0 + (f - 1) * 0.9
                t_op.Set(Gf.Vec3d(agv_anim_x, train_y, 0.35), Usd.TimeCode(f))
        else:
            agv_root.AddTranslateOp().Set(Gf.Vec3d(train_x, train_y, 0.35))

        # Tractor Vehicle
        define_cube_mesh(stage, "/World/AGV_Fleet/TuggerTrain_01/Tractor", (0.0, 0.0, 0.0), (2.0, 1.2, 0.6), (0.1, 0.65, 0.75))
        # Top Rotating LiDAR Puck
        define_cylinder_mesh(stage, "/World/AGV_Fleet/TuggerTrain_01/Tractor/LidarSensor", (0.5, 0.0, 0.45), 0.12, 0.25, (0.1, 0.1, 0.1))
        # Warning Beacon Light
        define_cylinder_mesh(stage, "/World/AGV_Fleet/TuggerTrain_01/Tractor/BeaconLight", (-0.6, 0.0, 0.45), 0.10, 0.20, (0.95, 0.65, 0.05), is_collider=False)

        # 4 Towed Cargo Trailers (Milk Run)
        for trailer_i in range(1, 5):
            trailer_offset_x = -trailer_i * 2.4
            t_path = f"/World/AGV_Fleet/TuggerTrain_01/Trailer_{trailer_i:02d}"
            # Trailer Frame
            define_cube_mesh(stage, f"{t_path}/Chassis", (trailer_offset_x, 0.0, -0.05), (1.8, 1.1, 0.3), (0.3, 0.35, 0.4))
            # Hitch Bar
            define_cube_mesh(stage, f"{t_path}/Hitch", (trailer_offset_x + 1.1, 0.0, -0.05), (0.6, 0.15, 0.1), (0.2, 0.2, 0.2), is_collider=False)
            # Towed Parts Tote Boxes (Blue KLT Bins)
            define_cube_mesh(stage, f"{t_path}/KLT_BOM_Pallet", (trailer_offset_x, 0.0, 0.35), (1.4, 0.9, 0.5), (0.15, 0.45, 0.85))

        # -------------------------------------------------------------
        # 7. Zoned Supermarkets & High-Bay Warehouse (SPS Area)
        # -------------------------------------------------------------
        wh_scope = UsdGeom.Scope.Define(stage, "/World/LogisticsSupermarkets")
        
        if is_baseline:
            # Single Centralized High-Bay Warehouse (140, -32)
            define_cube_mesh(stage, "/World/LogisticsSupermarkets/Central_ASRS_Warehouse", 
                             (140.0, -32.0, 5.0), (160.0, 18.0, 10.0), (0.25, 0.28, 0.35))
        else:
            # Optimized: Three Zoned Decentralized SPS Supermarkets (Trim, Chassis, Final)
            # Supermarket 1: Trim Zone (X=70m, Y=-22m)
            define_cube_mesh(stage, "/World/LogisticsSupermarkets/SPS_Trim_Supermarket", 
                             (70.0, -22.0, 3.5), (65.0, 14.0, 7.0), (0.15, 0.50, 0.65))
            # Supermarket 2: Chassis Heavy Parts ASRS (X=175m, Y=-25m)
            define_cube_mesh(stage, "/World/LogisticsSupermarkets/SPS_Chassis_ASRS", 
                             (175.0, -25.0, 6.0), (70.0, 18.0, 12.0), (0.25, 0.30, 0.45))
            # Supermarket 3: Final Fast Sequencing Zone (X=245m, Y=-22m)
            define_cube_mesh(stage, "/World/LogisticsSupermarkets/SPS_Final_Supermarket", 
                             (245.0, -22.0, 3.5), (60.0, 14.0, 7.0), (0.15, 0.50, 0.65))

        # -------------------------------------------------------------
        # 8. Omniverse Viewport RTX Camera Bookmarks
        # -------------------------------------------------------------
        cam_scope = UsdGeom.Scope.Define(stage, "/World/Cameras")

        # Camera 1: Bird's eye overview of entire 280m line
        c1 = UsdGeom.Camera.Define(stage, "/World/Cameras/GA_Line_Overview_Isometric")
        c1.AddTranslateOp().Set(Gf.Vec3d(140.0, -45.0, 35.0))
        c1.AddRotateXYZOp().Set(Gf.Vec3f(55.0, 0.0, 0.0))
        c1.CreateFocalLengthAttr().Set(28.0)

        # Camera 2: Close-up on Station 16 (Seat collision inspection)
        c2 = UsdGeom.Camera.Define(stage, "/World/Cameras/Station_16_Seat_Hazard_Cam")
        c2.AddTranslateOp().Set(Gf.Vec3d(112.0, 0.0, 3.5))
        c2.AddRotateXYZOp().Set(Gf.Vec3f(20.0, 0.0, 90.0))
        c2.CreateFocalLengthAttr().Set(35.0)

        # Camera 3: Close-up on Station 24 (100kWh Battery assembly)
        c3 = UsdGeom.Camera.Define(stage, "/World/Cameras/Station_24_Battery_Cell_Cam")
        c3.AddTranslateOp().Set(Gf.Vec3d(168.0, 0.0, 3.5))
        c3.AddRotateXYZOp().Set(Gf.Vec3f(20.0, 0.0, 90.0))
        c3.CreateFocalLengthAttr().Set(35.0)

        # Camera 4: AGV Tugger Train Follow Cam
        c4 = UsdGeom.Camera.Define(stage, "/World/Cameras/AGV_Tugger_Train_Follow")
        c4.AddTranslateOp().Set(Gf.Vec3d(85.0, 12.0, 4.0))
        c4.AddRotateXYZOp().Set(Gf.Vec3f(25.0, 0.0, -145.0))
        c4.CreateFocalLengthAttr().Set(40.0)

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
    gen = OmniverseUSDStageGenerator(output_dir="/home/antigravity/seres-omniverse-logistics-sim/assets")
    gen.generate_all()
