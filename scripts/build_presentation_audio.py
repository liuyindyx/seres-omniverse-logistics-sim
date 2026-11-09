"""
Generates the 9-chapter neural Chinese voiceover audio tracks (~3 minutes total)
for the Seres Super Factory Omniverse 3D Digital Twin presentation video.
"""

import os
import json
import asyncio
import subprocess
import edge_tts
import imageio_ffmpeg

CHAPTERS = [
    {
        "id": 1,
        "badge": "第一部分 · 项目核心亮点与架构 (1/5)",
        "title": "赛力斯超级工厂总装线边物流：60秒极速节拍下的“双向拷问”",
        "cam": "overview_orbit",
        "mode": "baseline",
        "highlight": "kpi",
        "bullets": [
            "对标赛力斯龙兴超级工厂（问界 M9/M7 总装车间），主线全长 280 米，涵盖 40 个标准工位",
            "双核协同架构：NVIDIA Omniverse 3D 物理空间严控（放得下）⟷ AnyLogic 离散事件排产（来得及）",
            "由工业 AI Agent 闭环驱动，解决高节拍新能源整车制造中最棘手的线边物流规划难题"
        ],
        "narration": (
            "大家好！欢迎来到赛力斯超级工厂总装车间线边物流三维数字孪生平台。"
            "在问界 M9 等车型以 60 秒一台的极速节拍量产时，40 个工位、80 座料架面临两个终极拷问："
            "三维物理空间能不能放得下？动态物料配送能不能来得及？"
            "为此，我们构建了融合 NVIDIA Omniverse 空间严控、AnyLogic 离散事件推演与 AI Agent 自主寻优的双向闭环架构。"
        )
    },
    {
        "id": 2,
        "badge": "第一部分 · 项目核心亮点与架构 (2/5)",
        "title": "核心亮点一：打破传统 AnyLogic 2D 仿真的“三维物理盲区”",
        "cam": "anylogic_compare",
        "mode": "anylogic2d",
        "highlight": "mode_bar",
        "bullets": [
            "传统 AnyLogic 2D 仿真仅将工位简化为平面逻辑节点，完全忽略厂房立柱与三维高程",
            "在本面板一键切换「传统 2D 盲区视角」与「Omniverse 3D 物理视角」，直观揭示二维规划隐患",
            "彻底杜绝“在 2D 仿真里绿灯通过，到现场设备落位时却撞上厂房承重钢柱”的工程事故"
        ],
        "narration": (
            "第一个核心亮点，是打破传统 AnyLogic 二维仿真的三维空间盲区。"
            "现在我们点击顶部切换到传统 AnyLogic 2D 盲区视角：传统仿真只把工位当作平面方块，完全看不见厂房 18 米跨度的承重钢柱。"
            "而切回 Omniverse 真三维视角时，物理真相立刻浮现：多处静态大料架直接与蓝色厂房承重钢柱发生了严重碰撞！"
        )
    },
    {
        "id": 3,
        "badge": "第一部分 · 项目核心亮点与架构 (3/5)",
        "title": "核心亮点二：毫米级 3D 几何干涉与 ISO 3691-4 通道净距严控",
        "cam": "hotspots_16_24",
        "mode": "baseline",
        "highlight": "cam_bar",
        "bullets": [
            "工位 16（零重力座椅）、工位 21（前副车架）、工位 34（车门分装）检出 5 处承重钢柱硬碰撞",
            "工位 24（100kWh 巨鲸电池）、工位 32（21寸轮胎）料架深达 2.0m，越过地面安全黄线",
            "实测 AGV 通道安全净距仅 0.30m，违反 ISO 3691-4 工业标准（要求净距 ≥ 0.50m）"
        ],
        "narration": (
            "第二个亮点，是基于 OpenUSD 与 PhysX 5 的毫米级三维空间审计。"
            "点击机位飞到工位 16 特写：红色碰撞笼内，二排零重力座椅料架直接穿透了 108 米处的承重钢柱。"
            "再点击飞到工位 24 巨鲸电池合装区：深达 2 米的重型电池料架越过了地面黄色安全界线，AGV 通道净距仅剩 0.3 米，严重违反 ISO 3691-4 安全规范。"
        )
    },
    {
        "id": 4,
        "badge": "第一部分 · 项目核心亮点与架构 (4/5)",
        "title": "核心亮点三：线边仓位“空间 vs 产能”结构性矛盾交互沙盒",
        "cam": "paradox_sandbox",
        "mode": "baseline",
        "highlight": "sandbox",
        "bullets": [
            "左侧交互沙盒支持实时拖动「料架扩容系数」、「产线节拍」与「AGV 车队规模」滑块",
            "放大单层料架 (1.45x) 虽能增加缓存，但在 3D 视口内瞬间引发 13 处钢柱穿透与走廊堵塞",
            "缩小单层料架 (0.70x) 虽能腾出空间，却导致单架仅够支撑 1 台车，引发上万次缺料停线"
        ],
        "narration": (
            "为什么线边仓位规划这么难？我们操作左侧的矛盾沙盒来直观验证："
            "如果为了不断料，拖动滑块把单层料架放大到 1.45 倍，三维场景中料架剧烈膨胀，碰撞与侵占瞬间飙升到 15 处，根本放不下！"
            "反过来，如果把料架缩小到 0.7 倍，线边库存瞬间耗尽，缺料停线暴增到一万一千多次！单靠平面妥协根本无法解开这一死锁。"
        )
    },
    {
        "id": 5,
        "badge": "第一部分 · 项目核心亮点与架构 (5/5)",
        "title": "核心亮点四：Agent 驱动 OpenUSD 代码化生成，建模效率提升 10 倍",
        "cam": "usd_inspector",
        "mode": "baseline",
        "highlight": "inspector",
        "bullets": [
            "告别传统仿真数周的人工拖拽：基于 Python pxr.Usd API，3 秒自动生成 40 工位完整 3D 资产",
            "点击任意 3D 工位即可在右侧检视 OpenUSD 场景树与实时 .usda 源码（含碰撞 Schema 与材质绑定）",
            "拖动右侧「实时避柱偏移」滑块 (+0.0m → +2.2m)，3D 料架与底层 USD 代码同步实时刷新"
        ],
        "narration": (
            "第四个亮点，是 Agent 驱动的 OpenUSD 代码化建模。"
            "传统软件手工拖拽 40 个工位需两三周，而本项目读取工程 BOM 后调用 OpenUSD 接口，3 秒即可生成全厂三维资产。"
            "我们在右侧属性面板拖动偏移滑块到正 2.2 米，三维座椅料架立刻平滑移出钢柱碰撞区，底层 USD 代码也同步实时刷新，建模效率提升 10 倍以上。"
        )
    },
    {
        "id": 6,
        "badge": "第二部分 · 实际工业场景核心价值 (1/2)",
        "title": "工业价值一：AI Agent 双向闭环自愈，一键达成“零干涉、零停线”",
        "cam": "agent_optimize",
        "mode": "optimized",
        "highlight": "agent_btn",
        "bullets": [
            "空间重构：自动对干涉工位注入 +2.2m 避柱位移，并将 2.0m 平铺架升级为 1.35m Z 轴双层立式流利架",
            "运筹重构：打破单主库 180m 运距瓶颈，部署 3 处区域 SPS 超市 + 36 台 1拖4 水蜘蛛牵引列车",
            "闭环成效：3D 空间合规率由 91.2% 跃升至 100%，2 小时班次缺料停线由 8,174 次清零为 0 次！"
        ],
        "narration": (
            "现在我们点击顶部「启动 AI Agent 3D 自动调优」按钮，看它如何创造工业价值！"
            "Agent 立即向三维 Z 轴要空间，将 2 米深的平铺料架重构为 1.35 米深的双层立式流利架，容量翻倍且通道净距恢复至 0.72 米；"
            "同时启用三座区域 SPS 超市和 36 台一拖四水蜘蛛牵引列车，将 8,174 次停线彻底清零，一键达成百分百放得下、百分百来得及！"
        )
    },
    {
        "id": 7,
        "badge": "第二部分 · 实际工业场景核心价值 (2/2)",
        "title": "工业价值二：规避百万级现场返工，精准赋能超级工厂降本增效",
        "cam": "industrial_value",
        "mode": "optimized",
        "highlight": "compare_modal",
        "bullets": [
            "规避产线改造返工：在数字规划阶段消灭全部立柱碰撞与安全违规，节省现场二次施工成本数百万元",
            "保障高节拍满产交付：单趟物料往返耗时由 170 秒压缩至 58 秒，消除价值数亿元产线的断料停摆风险",
            "精准指导资产采购：在 93.7% 均衡负荷率下锁定 36 台水蜘蛛最优车队规模，避免盲目采购浪费"
        ],
        "narration": (
            "在实际整车工程中，本平台带来三大直接价值："
            "第一，在设备落位前消灭全部立柱碰撞与通道违规，规避数百万元的现场返工损失；"
            "第二，将单趟配送往返耗时从 170 秒压至 58 秒，保障每小时 60 台的高节拍满产交付；"
            "第三，在 93.7% 的均衡负荷下精准锁定 36 台水蜘蛛最优配额，避免盲目采购浪费。"
        )
    },
    {
        "id": 8,
        "badge": "第三部分 · 未来演进与宏伟期许 (1/2)",
        "title": "未来期许一：迈向生成式全厂数字主线与实时 IoT 虚实共生",
        "cam": "future_drone",
        "mode": "optimized",
        "highlight": "roof_toggle",
        "bullets": [
            "横向贯通四大工艺：从总装车间延伸至冲压、焊装、涂装及场外智慧物流园区的全厂级 OpenUSD 底座",
            "生成式 AI 布局寻优：支持工程师以自然语言输入新车型 BOM，Agent 自动生成多套帕累托最优 3D 产线方案",
            "实时 IoT 虚实同步：直连工厂 MES、LES 与 AGV 调度系统 (RCS)，实现秒级孪生监控与动态重调度"
        ],
        "narration": (
            "展望未来，我们怀揣两大演进期许。"
            "首先，是从单一车间迈向全厂级生成式数字底座。勾选显示厂房顶棚钢桁架并开启无人机环绕漫游："
            "未来我们将通过统一 OpenUSD 总线贯通冲压、焊装、涂装、总装四大工艺；"
            "支持自然语言输入新车型 BOM 自动生成帕累托最优 3D 布局，并直连现场 MES 与 AGV 调度系统，实现实时虚实共生。"
        )
    },
    {
        "id": 9,
        "badge": "第三部分 · 未来演进与宏伟期许 (2/2)",
        "title": "未来期许二：无缝衔接 NVIDIA Isaac Sim，赋能具身智能超级工厂",
        "cam": "finale_isaac",
        "mode": "optimized",
        "highlight": "terminal",
        "bullets": [
            "原生兼容 NVIDIA Isaac Sim：本项目生成的 .usda 场景与 PhysX 5 物理属性可直接载入 Isaac Sim",
            "人机混行与具身智能训练：支持在孪生产线中训练自主移动机器人 (AMR) 与工业人形机器人线边拣选上料",
            "终极愿景：构建“软件定义、AI 自进化、零碰撞、零停线”的下一代新能源汽车智慧超级工厂！"
        ],
        "narration": (
            "第二个期许，是无缝衔接 NVIDIA Isaac Sim，全面拥抱具身智能。"
            "依托本项目原生生成的 OpenUSD 与 PhysX 5 物理资产，整座车间可直接导入 Isaac Sim，"
            "用于训练视觉 AMR 与工业人形机器人执行线边料箱分拣、精密装配与人机协同。"
            "从空间严控、动态保供到具身智能进化，我们将持续助力赛力斯打造下一代智慧超级工厂！感谢观看！"
        )
    }
]


async def build_all():
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "video_assets"))
    os.makedirs(out_dir, exist_ok=True)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    manifest = []
    cumulative_sec = 0.0

    for ch in CHAPTERS:
        mp3_path = os.path.join(out_dir, f"ch_{ch['id']:02d}.mp3")
        wav_path = os.path.join(out_dir, f"ch_{ch['id']:02d}.wav")
        comm = edge_tts.Communicate(ch["narration"], voice="zh-CN-YunxiNeural", rate="+22%")
        await comm.save(mp3_path)

        subprocess.run(
            [
                ffmpeg_exe, "-y", "-i", mp3_path,
                "-af", "apad=pad_dur=0.45",
                "-ar", "44100", "-ac", "2",
                wav_path
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        wav_size = os.path.getsize(wav_path)
        duration_sec = round((wav_size - 44) / 176400.0, 2)

        ch_info = dict(ch)
        ch_info["mp3_path"] = mp3_path
        ch_info["wav_path"] = wav_path
        ch_info["start_sec"] = round(cumulative_sec, 2)
        ch_info["duration_sec"] = duration_sec
        cumulative_sec += duration_sec
        ch_info["end_sec"] = round(cumulative_sec, 2)
        manifest.append(ch_info)
        print(f"Chapter {ch['id']:02d}: {duration_sec:.2f}s (total: {cumulative_sec:.2f}s)")

    concat_list_path = os.path.join(out_dir, "concat_wavs.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for item in manifest:
            p = item["wav_path"].replace("\\", "/")
            f.write(f"file '{p}'\n")

    master_wav = os.path.join(out_dir, "master_narration.wav")
    subprocess.run(
        [ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path, "-c", "copy", master_wav],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )

    manifest_path = os.path.join(out_dir, "presentation_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"total_duration_sec": round(cumulative_sec, 2), "chapters": manifest}, f, ensure_ascii=False, indent=2)

    print(f"\nMaster narration built successfully! Total duration: {cumulative_sec:.2f} seconds ({cumulative_sec/60.0:.2f} minutes)")


if __name__ == "__main__":
    asyncio.run(build_all())
