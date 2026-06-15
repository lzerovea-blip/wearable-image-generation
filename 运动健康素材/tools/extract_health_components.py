from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


WORKSPACE = Path(__file__).resolve().parents[1]
APP_DIR = WORKSPACE / "华为运动健康app"
WEARABLE_DIR = WORKSPACE / "华为穿戴"
COMPONENT_ROOT = WORKSPACE / "官方设计规范" / "组件资源"
APP_OUT = COMPONENT_ROOT / "运动健康App截图组件"
WEARABLE_OUT = COMPONENT_ROOT / "穿戴截图组件"
VERSION_DIR = COMPONENT_ROOT / "索引版本"
MANIFEST_PATH = COMPONENT_ROOT / "组件资源索引_manifest.json"
VERSION = "v20260611_001"
TODAY = date.today().isoformat()

TYPES = ["卡片", "按钮", "图标", "导航", "列表", "图表", "弹窗", "状态提示", "其他控件"]
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass
class Component:
    name: str
    kind: str
    source_end: str
    source_image: Path
    output_path: Path
    bbox: tuple[int, int, int, int]
    note: str


def rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE))


def slug(text: str, max_len: int = 36) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "_", text, flags=re.UNICODE).strip("_")
    return text[:max_len] or "未命名"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_files(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS)


def ensure_dirs() -> None:
    for base in (APP_OUT, WEARABLE_OUT):
        for kind in TYPES:
            (base / kind).mkdir(parents=True, exist_ok=True)
    VERSION_DIR.mkdir(parents=True, exist_ok=True)


def crop_save(img: Image.Image, bbox: tuple[int, int, int, int], out: Path) -> bool:
    w, h = img.size
    x1, y1, x2, y2 = bbox
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 - x1 < 32 or y2 - y1 < 32:
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    img.crop((x1, y1, x2, y2)).save(out, "PNG")
    return True


def is_light_component(arr: np.ndarray) -> np.ndarray:
    rgb = arr[:, :, :3].astype(np.int16)
    return (rgb[:, :, 0] > 235) & (rgb[:, :, 1] > 235) & (rgb[:, :, 2] > 235)


def row_segments(mask: np.ndarray, min_height: int, max_segments: int = 8) -> list[tuple[int, int]]:
    coverage = mask.mean(axis=1)
    active = coverage > 0.50
    segments: list[tuple[int, int]] = []
    start = None
    for i, value in enumerate(active):
        if value and start is None:
            start = i
        elif not value and start is not None:
            if i - start >= min_height:
                segments.append((start, i))
            start = None
    if start is not None and len(active) - start >= min_height:
        segments.append((start, len(active)))

    merged: list[tuple[int, int]] = []
    for seg in segments:
        if merged and seg[0] - merged[-1][1] < 16:
            merged[-1] = (merged[-1][0], seg[1])
        else:
            merged.append(seg)
    return merged[:max_segments]


def classify_app_segment(y1: int, y2: int, width: int, height: int) -> tuple[str, str]:
    seg_h = y2 - y1
    if y1 < 220:
        return "导航", "标题栏"
    if y2 > height - 220 and height <= 2400:
        return "导航", "底部页签"
    if seg_h < 90:
        return "按钮", "操作按钮"
    if seg_h > width * 0.55:
        return "图表", "数据图表区域"
    if seg_h > 220:
        return "卡片", "信息卡片"
    return "列表", "列表项"


def app_components(path: Path, global_counter: dict[str, int]) -> list[Component]:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    w, h = img.size
    arr = np.asarray(img)
    stem = slug(path.stem, 22)
    components: list[Component] = []

    def add(kind: str, label: str, bbox: tuple[int, int, int, int], note: str) -> None:
        global_counter[kind] = global_counter.get(kind, 0) + 1
        number = global_counter[kind]
        name = f"{label}_{number:04d}"
        out = APP_OUT / kind / f"app_{kind}_{number:04d}_{slug(label)}.png"
        if crop_save(img, bbox, out):
            components.append(Component(name, kind, "App", path, out, bbox, note))

    visible_h = min(h, 2400)
    add("导航", "标题栏", (0, 0, w, min(190, h)), "自动裁切：顶部标题/状态区域")
    if h <= 2600:
        add("导航", "底部页签", (0, max(0, h - 190), w, h), "自动裁切：底部导航区域")

    content_bottom = h if h > 2600 else max(0, h - 170)
    mask = is_light_component(arr[:content_bottom])
    segments = row_segments(mask, min_height=90 if w > 900 else 60, max_segments=10)
    for y1, y2 in segments:
        if y1 < 120:
            continue
        if h <= 2600 and y2 > h - 170:
            continue
        pad_x = int(w * 0.045)
        kind, label = classify_app_segment(y1, y2, w, h)
        add(kind, label, (pad_x, max(0, y1 - 12), w - pad_x, min(h, y2 + 12)), f"自动识别浅色组件区域；来源 {path.name}")

    if not any(c.kind == "卡片" for c in components):
        add("其他控件", "主内容区域", (int(w * 0.04), 180, int(w * 0.96), min(h, visible_h)), "兜底裁切：未检测到清晰卡片时保留主内容")

    return components


def wearable_components(path: Path, global_counter: dict[str, int]) -> list[Component]:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    w, h = img.size
    stem_text = path.stem
    components: list[Component] = []

    def add(kind: str, label: str, bbox: tuple[int, int, int, int], note: str) -> None:
        global_counter[kind] = global_counter.get(kind, 0) + 1
        number = global_counter[kind]
        name = f"{label}_{number:04d}"
        out = WEARABLE_OUT / kind / f"wearable_{kind}_{number:04d}_{slug(label)}.png"
        if crop_save(img, bbox, out):
            components.append(Component(name, kind, "穿戴", path, out, bbox, note))

    short_name = slug(stem_text, 18)
    add("其他控件", f"{short_name}_完整画面", (0, 0, w, h), "穿戴/宣传图保留完整画面，便于构图参考")

    side = min(w, h)
    if side >= 180:
        cx, cy = w // 2, h // 2
        margin = int(side * 0.04)
        half = side // 2 - margin
        add("卡片", f"{short_name}_中心屏幕", (cx - half, cy - half, cx + half, cy + half), "自动裁切：中心表盘/方屏/主要组件区域")

    if h > w * 1.25:
        add("列表", f"{short_name}_纵向内容", (int(w * 0.08), int(h * 0.12), int(w * 0.92), int(h * 0.88)), "自动裁切：纵向穿戴内容区域")
    elif w > h * 1.25:
        add("图表", f"{short_name}_横向内容", (int(w * 0.08), int(h * 0.08), int(w * 0.92), int(h * 0.92)), "自动裁切：横向功能/图表区域")

    if any(k in stem_text for k in ["高尔夫", "心率", "健康", "地图"]):
        add("图标", f"{short_name}_功能图标语义", (int(w * 0.18), int(h * 0.18), int(w * 0.82), int(h * 0.82)), "自动裁切：功能语义图/图标参考")

    return components


def main() -> None:
    ensure_dirs()
    app_sources = image_files(APP_DIR)
    wearable_sources = image_files(WEARABLE_DIR)
    source_manifest = [
        {
            "source": rel(p),
            "sha256": sha256_file(p),
            "size": ImageOps.exif_transpose(Image.open(p)).size,
        }
        for p in app_sources + wearable_sources
    ]

    counters: dict[str, int] = {}
    components: list[Component] = []
    for path in app_sources:
        components.extend(app_components(path, counters))
    for path in wearable_sources:
        components.extend(wearable_components(path, counters))

    manifest = {
        "version": VERSION,
        "date": TODAY,
        "source_count": len(app_sources) + len(wearable_sources),
        "app_source_count": len(app_sources),
        "wearable_source_count": len(wearable_sources),
        "component_count": len(components),
        "source_manifest": source_manifest,
        "components": [
            {
                "version": c.version if hasattr(c, "version") else VERSION,
                "name": c.name,
                "kind": c.kind,
                "image_path": rel(c.output_path),
                "source_end": c.source_end,
                "source_image": rel(c.source_image),
                "bbox": c.bbox,
                "note": c.note,
            }
            for c in components
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "version": VERSION,
        "sources": manifest["source_count"],
        "components": manifest["component_count"],
        "manifest": rel(MANIFEST_PATH),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
