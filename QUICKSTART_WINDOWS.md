# 赛力斯超级工厂总装线边物流仿真 — Windows 本地运行快速指南

本指南指导您在本地 **Windows 10 / 11 (配备 NVIDIA RTX 显卡)** 环境中检视、运行和交互本项目的 3D OpenUSD 场景与 Omniverse 扩展插件。

---

## 目录
1. [前置硬件与软件要求](#1-前置硬件与软件要求)
2. [克隆代码仓库](#2-克隆代码仓库)
3. [在 NVIDIA Omniverse USD Composer 中打开 3D 场景](#3-在-nvidia-omniverse-usd-composer-中打开-3d-场景)
4. [加载与启用 Omniverse Kit 扩展插件](#4-加载与启用-omniverse-kit-扩展插件)
5. [在 NVIDIA Isaac Sim 中运行 Python 仿真](#5-在-nvidia-isaac-sim-中运行-python-仿真)
6. [非 GPU 环境轻量命令行测试 (CLI)](#6-非-gpu-环境轻量命令行测试-cli)
7. [提交 Issue 与持续迭代协作](#7-提交-issue-与持续迭代协作)

---

## 1. 前置硬件与软件要求

* **操作系统**: Windows 10 / 11 64-bit
* **显卡**: NVIDIA RTX 系列 GPU（GeForce RTX 3060 / 4060 及以上，或 RTX A4000 / A5000 / A6000）
* **显卡驱动**: NVIDIA Studio Driver 535.xx 或更新版本
* **软件环境** (二选一或兼备):
  * **NVIDIA Omniverse Launcher** -> 安装 **USD Composer** (原 Omniverse Create)
  * **NVIDIA Isaac Sim** (4.0+ 或 2023.1.1+)
* **Python 环境** (可选，用于独立 CLI 运行): Python 3.10 或 3.11

---

## 2. 克隆代码仓库

打开 Windows Terminal (PowerShell 或 Git Bash)，执行：

```powershell
git clone https://github.com/liuyindyx/seres-omniverse-logistics-sim.git
cd seres-omniverse-logistics-sim
```

---

## 3. 在 NVIDIA Omniverse USD Composer 中打开 3D 场景

NVIDIA Omniverse 是专为工业高精度数字孪生与 GPU 实时光追设计的平台，场景通过 OpenUSD (`.usda`) 格式组织。

### 步骤：
1. 启动 **Omniverse Launcher**，打开 **USD Composer**。
2. 菜单栏选择 `File` -> `Open...`。
3. 浏览至本项目目录下的 `assets/stages/`，推荐打开以下三个场景之一：
   * **`seres_ga_workshop_main.usda`** (推荐):
     * 100% 空间合规达标场景（0 处立柱干涉，0 处 AGV 通道侵占）。
     * 包含 40 个工位全部双侧料架、高亮工位标牌、车身滑撬总装线、AGV 双向环线、3 处 SPS 超市。
   * **`seres_ga_workshop_animated.usda`** (动画演示):
     * 包含 240 帧时间线关键帧动画。
     * 打开后，在界面下方点击 **播放 (Play)** 或按 **空格键 (Space)**，即可观看全线车身滑撬平移与 AGV 水蜘蛛牵引列车循环运转！
   * **`seres_ga_workshop_baseline.usda`** (干涉对比场景):
     * 包含传统未经优化的原始布局，场景内以 **红色半透明发光立方体 (CollisionHazardGlow)** 标出 5 处立柱干涉与 2 处 AGV 违规侵占。

### 摄像机视点切换：
在视口左上方摄像机下拉菜单中（默认显示 `Perspective`），切换至内置的工业相机：
* `GA_Line_Overview_Isometric`: 280米总装全线鸟瞰等轴测机位。
* `Station_16_Seat_Hazard_Cam`: 工位16 二排老板零重力座椅特写机位。
* `Station_24_Battery_Cell_Cam`: 工位24 底盘一体化电池包合装区机位。
* `AGV_Tugger_Train_Follow`: 北环主干道 AGV 水蜘蛛列车跟车动态机位。

### RTX 渲染模式切换：
在视口顶部渲染模式切换：
* **RTX Real-Time**: 开启 DLSS 3.5 实时交互（高帧率流览）。
* **RTX Interactive (Path Tracing)**: 开启全路径光线追踪，呈现照片级车漆反光、地面环氧自流平镜面反射与工位 LED 柔光。

---

## 4. 加载与启用 Omniverse Kit 扩展插件

本项目在 `exts/omni.seres.logistics` 提供了定制的 Omniverse Kit Extension，能在 USD Composer 内直接打开控制面板。

### 启用步骤：
1. 在 USD Composer 菜单栏点击 `Window` -> `Extensions`。
2. 在弹出窗口中，点击右上角的 **齿轮图标 (Settings / Extension Search Paths)**。
3. 点击绿色 `+` 号添加路径，选择本地仓库的扩展目录：
   ```text
   C:\path\to\seres-omniverse-logistics-sim\exts
   ```
4. 在扩展搜索框中输入 `omni.seres.logistics` 或 `Seres`。
5. 找到 **"Seres Super Factory Logistics Simulation"**，将开关切换至 **ON**。
6. 视口右侧将弹出控制窗口：
   * **场景载入与切换**: 一键加载基准场景、优化场景或动画场景。
   * **视点切换**: 一键跳转四大多角度监控相机。
   * **3D 物理空间尺寸严控 (放得下 审计)**: 点击按钮即可在 Omniverse 视口中对 80 个料架执行毫米级干涉检测。
   * **AnyLogic 离散事件物流推演 (来得及 验证)**: 点击按钮实时推演 2 小时班次供料节拍与停线次数。
   * **智能体协同优化**: 查看 Agent 自主决策的全链路闭环量化指标。

---

## 5. 在 NVIDIA Isaac Sim 中运行 Python 仿真

如果您安装了 NVIDIA Isaac Sim，可以直接使用其内置的独立 Python 引擎执行物理级仿真：

```powershell
# 打开 Isaac Sim 安装目录（例如 2023.1.1）
cd "C:\Users\<您的用户名>\AppData\Local\ov\pkg\isaac-sim-2023.1.1"

# 使用 Isaac Sim 的 python.bat 运行脚本
.\python.bat C:\path\to\seres-omniverse-logistics-sim\scripts\run_in_isaac_sim.py
```

该脚本将拉起 Isaac Sim 仿真内核，挂载 PhysX 5 GPU 刚体动力学，并在视口中以 60 FPS 步进模拟。

---

## 6. 非 GPU 环境轻量命令行测试 (CLI)

如果您当前处于无 RTX 显卡的便携笔记本或仅需验证逻辑，可直接通过纯 Python 运行：

```powershell
# 1. 创建虚拟环境 (建议 Python 3.10+)
python -m venv .venv
.\.venv\Scripts\activate

# 2. 安装依赖 (Pixar OpenUSD 核心库与测试套件)
pip install -r requirements.txt

# 3. 运行双向闭环协同仿真脚本
python scripts\run_standalone_co_sim.py

# 4. 执行全套单元测试
pytest tests\ -v
```

---

## 7. 提交 Issue 与持续迭代协作

本项目已接入自动化协作流水线。如果您在 Windows 本地运行过程中发现任何问题或需要定制功能：

1. 打开项目的 GitHub 仓库页面：
   👉 [https://github.com/liuyindyx/seres-omniverse-logistics-sim](https://github.com/liuyindyx/seres-omniverse-logistics-sim)
2. 点击 **Issues** 选项卡 -> **New Issue**。
3. 提交您的问题或需求，例如：
   * *“工位 15 的前排座椅料架尺寸需要调整为 2.4m”*
   * *“希望在 final 区域增加双向立库对接仿真”*
   * *“在 USD Composer 中加载某个材质时报错”*
4. 我将即时读取 GitHub Issue，在云端虚拟环境中修改代码、重新生成 OpenUSD 场景并 push 回本仓库！
