#!/usr/bin/env python3
from __future__ import annotations

import math
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path("/Users/lin/Documents/运动健康素材")
SPEC = ROOT / "官方设计规范"
SOURCE = SPEC / "功能截图" / "华为运动健康app"
TARGET = SPEC / "组件资源" / "运动健康App截图组件"
QUARANTINE = SPEC / "组件资源" / "运动健康App截图组件_不纳入正式库_v20260615"
PREVIEW = TARGET / "_预览"
LIVE_SOURCE = TARGET / "_实机采集"


CATEGORIES = ["图标", "图表", "卡片", "导航", "状态提示", "其他控件", "列表", "按钮", "弹窗"]


@dataclass(frozen=True)
class CropSpec:
    category: str
    filename: str
    source: str
    box: tuple[int, int, int, int]
    status: str
    note: str
    source_scope: str = "archive"


CROPS: list[CropSpec] = [
    CropSpec("导航", "app_导航_0001_详情页顶部导航栏_默认.png", "screenshot_20260521_094044_com.huawei.hmos.health.jpg", (0, 120, 1320, 320), "默认", "详情页标题、返回和更多操作区。"),
    CropSpec("导航", "app_导航_0002_时间维度分段控件_日选中.png", "screenshot_20260521_094044_com.huawei.hmos.health.jpg", (48, 294, 1272, 427), "日选中", "日、周、月、半年、年分段控件。"),
    CropSpec("导航", "app_导航_0003_指标分段控件_心率选中.png", "screenshot_20260521_094044_com.huawei.hmos.health.jpg", (80, 1428, 1240, 1546), "心率选中", "卡片内指标切换分段控件。"),
    CropSpec("卡片", "app_卡片_0008_心率日趋势数据卡片_默认.png", "screenshot_20260521_094044_com.huawei.hmos.health.jpg", (48, 470, 1272, 1695), "默认", "心率范围、最新值、趋势图和入口组成的大卡片。"),
    CropSpec("图表", "app_图表_0001_心率日趋势折线图_默认.png", "screenshot_20260521_094044_com.huawei.hmos.health.jpg", (80, 895, 1238, 1394), "默认", "心率日趋势折线图，含坐标轴和参考线。"),
    CropSpec("按钮", "app_按钮_0001_查看全部心率数据文字按钮_默认.png", "screenshot_20260521_094044_com.huawei.hmos.health.jpg", (450, 1592, 878, 1678), "默认", "卡片底部品牌色文字按钮。"),
    CropSpec("列表", "app_列表_0008_心电图记录入口_默认.png", "screenshot_20260521_094044_com.huawei.hmos.health.jpg", (48, 1732, 1272, 2070), "默认", "健康记录入口，含图标、标题、时间和值缩略图。"),
    CropSpec("图标", "app_图标_0001_心电图应用图标_方形.png", "screenshot_20260521_094044_com.huawei.hmos.health.jpg", (82, 1766, 179, 1863), "方形", "心电图列表项图标。"),
    CropSpec("状态提示", "app_状态提示_0001_列表未读红点_提醒.png", "screenshot_20260521_094044_com.huawei.hmos.health.jpg", (328, 1798, 389, 1858), "提醒", "列表项标题旁红点提醒。"),
    CropSpec("卡片", "app_卡片_0009_步数对比趋势卡片_默认.png", "screenshot_20260521_094029_com.huawei.hmos.health.jpg", (48, 470, 1272, 1024), "默认", "步数对比、数值、趋势线组成的信息卡片。"),
    CropSpec("图表", "app_图表_0002_步数对比趋势折线图_默认.png", "screenshot_20260521_094029_com.huawei.hmos.health.jpg", (80, 438, 1240, 930), "默认", "步数对比趋势折线图。"),
    CropSpec("导航", "app_导航_0004_底部胶囊导航_设备选中.png", "screenshot_20260520_150456_com.huawei.hmos.health.jpg", (248, 1780, 1082, 2056), "设备选中", "底部四 Tab 胶囊导航。"),
    CropSpec("卡片", "app_卡片_0010_设备总览横向卡片_默认.png", "screenshot_20260520_150456_com.huawei.hmos.health.jpg", (48, 1138, 1272, 1358), "默认", "全部设备横向入口卡片。"),
    CropSpec("列表", "app_列表_0009_手表设置完成提示项_默认.png", "screenshot_20260520_150456_com.huawei.hmos.health.jpg", (48, 1385, 1272, 1610), "默认", "设备页设置完成提示列表项。"),
    CropSpec("其他控件", "app_其他控件_0001_电量环形状态控件_默认.png", "screenshot_20260520_150456_com.huawei.hmos.health.jpg", (48, 580, 250, 910), "默认", "设备电量环形状态控件。"),
    CropSpec("图标", "app_图标_0002_设备设置提示图标_圆形.png", "screenshot_20260520_150456_com.huawei.hmos.health.jpg", (72, 1425, 188, 1542), "圆形", "设备页设置完成提示列表项中的蓝色功能图标。"),
    CropSpec("按钮", "app_按钮_0002_设备查看全部入口_默认.png", "screenshot_20260520_150456_com.huawei.hmos.health.jpg", (1180, 1186, 1276, 1308), "默认", "设备横向入口右侧箭头按钮。"),
    CropSpec("卡片", "app_卡片_0011_健康摘要分析卡片_默认.png", "screenshot_20260521_094333_com.huawei.hmos.health.jpg", (48, 870, 1272, 1595), "默认", "健康摘要中的数据分析卡片，含图标、文案和进度条。"),
    CropSpec("图表", "app_图表_0003_健康摘要横向对比条形图_默认.png", "screenshot_20260521_094333_com.huawei.hmos.health.jpg", (80, 1215, 1240, 1500), "默认", "健康摘要卡片内本月/上月横向对比条形图。"),
    CropSpec("导航", "app_导航_0005_健康摘要双段切换_精选摘要选中.png", "screenshot_20260521_094333_com.huawei.hmos.health.jpg", (48, 305, 1272, 428), "精选摘要选中", "精选摘要和趋势列表双段切换控件。"),
    CropSpec("按钮", "app_按钮_0003_数据类型筛选胶囊_选中.png", "screenshot_20260521_094116_com.huawei.hmos.health.jpg", (48, 318, 720, 430), "选中", "所有数据页数据类型筛选胶囊按钮组。"),
    CropSpec("列表", "app_列表_0010_睡眠记录卡片列表项_默认.png", "screenshot_20260521_094116_com.huawei.hmos.health.jpg", (48, 642, 1272, 990), "默认", "睡眠记录列表中的单条卡片列表项。"),
    CropSpec("列表", "app_列表_0011_心率范围记录列表项_默认.png", "screenshot_20260521_094159_com.huawei.hmos.health.jpg", (48, 512, 1272, 785), "默认", "心率范围历史记录列表项组合。"),
    CropSpec("其他控件", "app_其他控件_0002_顶部筛选删除操作区_默认.png", "screenshot_20260521_094116_com.huawei.hmos.health.jpg", (1000, 135, 1275, 260), "默认", "所有数据页右上筛选和删除圆形操作按钮。"),
    CropSpec("弹窗", "app_弹窗_0001_设备筛选浮层_展开.png", "screenshot_20260521_094138_com.huawei.hmos.health.jpg", (455, 285, 1130, 1348), "展开", "所有数据页设备筛选浮层。"),
    CropSpec("状态提示", "app_状态提示_0002_数据同步加载状态_进行中.png", "screenshot_20260521_094540_com.huawei.hmos.health.jpg", (360, 850, 960, 1210), "进行中", "数据同步或加载中的状态区域。"),
    CropSpec("卡片", "app_卡片_0012_健康首页三环总览卡_默认.png", "live_health_home.png", (18, 118, 614, 324), "默认", "实机健康首页三环总览卡，含活动热量、锻炼时长、活动小时数和步数进度。", "live"),
    CropSpec("图表", "app_图表_0004_健康首页三环进度图_默认.png", "live_health_home.png", (130, 126, 502, 254), "默认", "实机健康首页三环进度可视化。", "live"),
    CropSpec("导航", "app_导航_0006_健康首页快捷入口横滑_默认.png", "live_health_home.png", (18, 335, 614, 414), "默认", "健康管理、智能减脂、饮食日记、睡眠监测等快捷入口横滑。", "live"),
    CropSpec("列表", "app_列表_0012_首页资讯推荐条_默认.png", "live_health_home.png", (18, 418, 614, 490), "默认", "健康首页资讯推荐条，含头像、标题、标签和播放入口。", "live"),
    CropSpec("卡片", "app_卡片_0013_首页运动记录双卡_默认.png", "live_health_home.png", (18, 493, 614, 625), "默认", "健康首页运动记录与立即查看双卡区域。", "live"),
    CropSpec("导航", "app_导航_0007_底部五栏导航_健康选中.png", "live_health_home.png", (18, 1240, 614, 1354), "健康选中", "实机底部五栏导航健康选中态。", "live"),
    CropSpec("导航", "app_导航_0008_饮食记录顶部搜索日期栏_默认.png", "live_diet_record.png", (20, 125, 612, 208), "默认", "饮食记录页搜索框与日期切换条。", "live"),
    CropSpec("图表", "app_图表_0005_饮食记录热量仪表盘_默认.png", "live_diet_record.png", (20, 171, 612, 352), "默认", "饮食记录热量摄入/摄出仪表盘卡。", "live"),
    CropSpec("列表", "app_列表_0013_饮食记录餐次列表_默认.png", "live_diet_record.png", (20, 376, 612, 622), "默认", "早餐、午餐、晚餐、加餐列表项组合，含右侧加号。", "live"),
    CropSpec("按钮", "app_按钮_0004_饮食记录餐次加号按钮_默认.png", "live_diet_record.png", (536, 386, 588, 438), "默认", "饮食记录餐次右侧圆形加号按钮。", "live"),
    CropSpec("其他控件", "app_其他控件_0003_饮食记录底部双入口_默认.png", "live_diet_record.png", (20, 633, 612, 705), "默认", "今日食谱和饮食分析底部双入口控件。", "live"),
    CropSpec("卡片", "app_卡片_0014_饮食统计周图表卡片_默认.png", "live_diet_stats.png", (18, 150, 614, 378), "默认", "饮食统计页周图表卡片，含标题、数值和坐标网格。", "live"),
    CropSpec("图表", "app_图表_0006_饮食统计周柱状图_默认.png", "live_diet_stats.png", (46, 200, 586, 336), "默认", "饮食统计周柱状/目标线图表。", "live"),
    CropSpec("状态提示", "app_状态提示_0003_睡眠监测深色沉浸页_默认.png", "live_sleep_monitor.png", (18, 76, 614, 1356), "默认", "睡眠监测深色沉浸式页面，含夜景背景、时间、说明、按钮和底部工具栏。", "live"),
    CropSpec("按钮", "app_按钮_0005_睡眠监测开始按钮_默认.png", "live_sleep_monitor.png", (164, 1038, 468, 1110), "默认", "睡眠监测页主操作按钮。", "live"),
    CropSpec("其他控件", "app_其他控件_0004_睡眠监测唤醒时间胶囊_默认.png", "live_sleep_monitor.png", (188, 456, 444, 520), "默认", "睡眠监测页唤醒时间胶囊控件。", "live"),
    CropSpec("导航", "app_导航_0009_睡眠监测底部工具栏_默认.png", "live_sleep_monitor.png", (106, 1232, 530, 1328), "默认", "白噪音、播放、闹钟组成的底部工具栏。", "live"),
    CropSpec("列表", "app_列表_0014_睡眠设置作息计划卡_默认.png", "live_sleep_settings.png", (20, 152, 612, 350), "默认", "睡眠设置作息计划分组卡，含开关、就寝/起床时间和编辑入口。", "live"),
    CropSpec("列表", "app_列表_0015_睡眠设置通用设置列表_默认.png", "live_sleep_settings.png", (20, 385, 612, 590), "默认", "睡眠设置通用设置列表，含二级入口和禁用开关。", "live"),
    CropSpec("其他控件", "app_其他控件_0005_App开关控件_开启关闭.png", "live_sleep_settings.png", (522, 180, 592, 545), "默认", "App 设置页开关控件样式，包含开启与关闭状态。", "live"),
    CropSpec("卡片", "app_卡片_0015_健康管理血压评估卡_默认.png", "live_health_management_assessment.png", (22, 60, 436, 447), "默认", "健康管理页科学评估横滑卡片，已避开昵称、头像、医生信息和会员续费区域。", "live"),
    CropSpec("按钮", "app_按钮_0006_健康管理立即测评按钮_默认.png", "live_health_management_assessment.png", (130, 372, 329, 418), "默认", "健康管理评估卡内主操作按钮。", "live"),
    CropSpec("卡片", "app_卡片_0016_智能减脂方案三卡_默认.png", "live_smart_fat_loss.png", (62, 548, 570, 735), "默认", "智能减脂计划页三张方案说明卡片组合。", "live"),
    CropSpec("图表", "app_图表_0007_智能减脂热量缺口仪表_默认.png", "live_smart_fat_loss.png", (230, 604, 393, 710), "默认", "智能减脂方案卡中的热量缺口仪表。", "live"),
    CropSpec("卡片", "app_卡片_0017_智能减脂今日吃动建议卡_默认.png", "live_smart_fat_loss.png", (63, 958, 570, 1224), "默认", "智能减脂计划页今日吃动建议卡，含饮食方案和营养比例。", "live"),
    CropSpec("按钮", "app_按钮_0007_智能减脂创建计划按钮_禁用.png", "live_smart_fat_loss.png", (40, 1246, 592, 1306), "禁用", "未勾选协议时的底部主按钮禁用态。", "live"),
]


def font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def ensure_dirs() -> None:
    for category in CATEGORIES:
        (TARGET / category).mkdir(parents=True, exist_ok=True)
    QUARANTINE.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)


def clean_target() -> None:
    for ds in TARGET.rglob(".DS_Store"):
        ds.unlink()
    other_q = QUARANTINE / "其他控件"
    other_q.mkdir(parents=True, exist_ok=True)
    for path in sorted((TARGET / "其他控件").glob("app_其他控件_*_主内容区域.png")):
        dest = other_q / path.name
        if dest.exists():
            dest.unlink()
        shutil.move(str(path), str(dest))
    list_q = QUARANTINE / "列表"
    list_q.mkdir(parents=True, exist_ok=True)
    for path in sorted((TARGET / "列表").glob("app_列表_000[1-7]_列表项.png")):
        dest = list_q / path.name
        if dest.exists():
            dest.unlink()
        shutil.move(str(path), str(dest))
    dialog_q = QUARANTINE / "弹窗"
    dialog_q.mkdir(parents=True, exist_ok=True)
    for path in sorted((TARGET / "弹窗").glob("app_弹窗_0001_健康授权提示弹窗_默认.png")):
        dest = dialog_q / path.name
        if dest.exists():
            dest.unlink()
        shutil.move(str(path), str(dest))
    icon_q = QUARANTINE / "图标"
    icon_q.mkdir(parents=True, exist_ok=True)
    for path in sorted((TARGET / "图标").glob("app_图标_0002_手表设备缩略图_设备.png")):
        dest = icon_q / path.name
        if dest.exists():
            dest.unlink()
        shutil.move(str(path), str(dest))


def crop_components() -> list[dict[str, str | int]]:
    rows = []
    for spec in CROPS:
        source_root = LIVE_SOURCE if spec.source_scope == "live" else SOURCE
        src = source_root / spec.source
        if not src.exists() and spec.source_scope != "live":
            matches = sorted(source_root.rglob(spec.source))
            if matches:
                src = matches[0]
        if not src.exists():
            raise FileNotFoundError(src)
        image = Image.open(src).convert("RGB")
        crop = image.crop(spec.box)
        out = TARGET / spec.category / spec.filename
        crop.save(out)
        rows.append(
            {
                "category": spec.category,
                "file": spec.filename,
                "source": spec.source,
                "width": crop.width,
                "height": crop.height,
                "status": spec.status,
                "note": spec.note,
                "source_scope": spec.source_scope,
            }
        )
    return rows


def image_files(root: Path) -> list[Path]:
    excluded = {"_预览", "_实机采集"}
    return sorted(
        p
        for p in root.rglob("*")
        if p.suffix.lower() in {".png", ".jpg", ".jpeg"} and not any(part in excluded for part in p.parts)
    )


def make_contact_sheet(paths: list[Path], out: Path, title: str, columns: int = 4) -> None:
    if not paths:
        return
    title_font = font(34)
    label_font = font(18)
    meta_font = font(16)
    cell_w, cell_h = 360, 430
    header_h = 70
    rows = math.ceil(len(paths) / columns)
    sheet = Image.new("RGB", (columns * cell_w, header_h + rows * cell_h), "#eeeeee")
    draw = ImageDraw.Draw(sheet)
    draw.rectangle((0, 0, sheet.width, header_h), fill="#202124")
    draw.text((24, 18), title, fill="white", font=title_font)
    for idx, path in enumerate(paths):
        x = (idx % columns) * cell_w
        y = header_h + (idx // columns) * cell_h
        draw.rectangle((x + 6, y + 6, x + cell_w - 6, y + cell_h - 6), fill="white")
        image = Image.open(path).convert("RGB")
        w, h = image.size
        image.thumbnail((cell_w - 34, 300))
        ix = x + (cell_w - image.width) // 2
        sheet.paste(image, (ix, y + 16))
        rel = path.relative_to(TARGET) if TARGET in path.parents else path.name
        draw.text((x + 18, y + 322), f"{idx + 1}. {rel}", fill="#111111", font=label_font)
        draw.text((x + 18, y + 374), f"{w}x{h}", fill="#666666", font=meta_font)
    sheet.save(out, quality=92)


def collect_inventory() -> list[dict[str, str | int]]:
    rows = []
    for path in image_files(TARGET):
        with Image.open(path) as image:
            category = path.parent.name
            rows.append(
                {
                    "category": category,
                    "file": path.name,
                    "width": image.width,
                    "height": image.height,
                }
            )
    return rows


def source_for_file(name: str, generated: list[dict[str, str | int]]) -> tuple[str, str, str]:
    for row in generated:
        if row["file"] == name:
            source = str(row["source"])
            if row.get("source_scope") == "live":
                source = f"iPhone镜像实机采集/{source}"
            return source, str(row["status"]), str(row["note"])
    return "功能截图/华为运动健康app（既有裁片）", "默认", "既有 App 截图组件，复核后保留。"


def write_docs(generated: list[dict[str, str | int]]) -> None:
    inv = collect_inventory()
    by_cat = {category: [] for category in CATEGORIES}
    for row in inv:
        by_cat.setdefault(str(row["category"]), []).append(row)

    for category in CATEGORIES:
        lines = [
            f"# {category} 截图组件",
            "",
            "生成日期：2026-06-15",
            "",
            "## 入库口径",
            "",
            "- 仅保留来自华为运动健康 App 截图或 iPhone 镜像实机补采的 App 组件裁片。",
            "- 严禁纳入穿戴组件、wearable 前缀素材或穿戴截图组件目录中的内容。",
            "- 涉及 App 界面模板说明时，字体统一按鸿蒙字体口径。",
            "",
            "## 文件清单",
            "",
            "| 文件 | 来源 | 尺寸 | 状态 | 备注 |",
            "|---|---|---:|---|---|",
        ]
        items = sorted(by_cat.get(category, []), key=lambda r: str(r["file"]))
        if not items:
            lines.append("| - | - | - | - | 本分类当前无明确合适截图，暂不强行补入。 |")
        for row in items:
            source, status, note = source_for_file(str(row["file"]), generated)
            lines.append(f"| `{row['file']}` | `{source}` | {row['width']}x{row['height']} | {status} | {note} |")
        (TARGET / category / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    counts = {category: len(by_cat.get(category, [])) for category in CATEGORIES}
    lines = [
        "# 运动健康 App 截图组件索引 v20260615",
        "",
        "生成日期：2026-06-15",
        "",
        "本索引只收华为运动健康 App 截图组件。正式库来源仅限 `功能截图/华为运动健康app` 与 `iPhone镜像实机补采`；穿戴组件不纳入 App 组件库。涉及 App 界面模板生成时，字体统一使用鸿蒙字体。",
        "",
        "## 分类统计",
        "",
        "| 分类 | 数量 |",
        "|---|---:|",
    ]
    for category in CATEGORIES:
        lines.append(f"| {category} | {counts[category]} |")
    lines += [
        "",
        "## 全量文件",
        "",
        "| 分类 | 文件 | 来源 | 尺寸 | 状态 | 备注 |",
        "|---|---|---|---:|---|---|",
    ]
    for category in CATEGORIES:
        for row in sorted(by_cat.get(category, []), key=lambda r: str(r["file"])):
            source, status, note = source_for_file(str(row["file"]), generated)
            lines.append(f"| {category} | `{row['file']}` | `{source}` | {row['width']}x{row['height']} | {status} | {note} |")
    lines += [
        "",
        "## 未纳入正式库",
        "",
        f"- 近整屏 App 主内容裁片已隔离到 `{QUARANTINE.relative_to(SPEC / '组件资源')}/其他控件/`。",
        "- 穿戴目录和穿戴截图组件目录仅作为排除项，不作为本库来源。",
    ]
    (TARGET / "运动健康App截图组件索引_v20260615.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    clean_target()
    generated = crop_components()
    make_contact_sheet(
        sorted(SOURCE.rglob("*.jpg")),
        PREVIEW / "华为运动健康app_源截图联系表.jpg",
        "华为运动健康 App 源截图",
        columns=5,
    )
    make_contact_sheet(
        image_files(TARGET),
        PREVIEW / "运动健康App截图组件_正式库联系表.jpg",
        "运动健康 App 截图组件正式库",
        columns=4,
    )
    write_docs(generated)
    print(f"generated_crops={len(generated)}")
    print(f"inventory={len(collect_inventory())}")
    print(f"preview={PREVIEW}")


if __name__ == "__main__":
    main()
