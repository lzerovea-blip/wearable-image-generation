"""Freeze a phone UI model and compare versions by stable page and action IDs."""
import argparse
import base64
import hashlib
import html
import json
from io import BytesIO
from pathlib import Path

from PIL import Image

from feature_model_archive import owned_file


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def image_evidence(image_path):
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        h = hashlib.sha256()
        h.update(str(image.size).encode())
        h.update(image.tobytes())
        image.thumbnail((200, 1800), Image.Resampling.LANCZOS)
        preview = BytesIO()
        image.save(preview, "WEBP", quality=75)
        return h.hexdigest(), base64.b64encode(preview.getvalue()).decode("ascii")


def snapshot(path):
    feature = read(path)
    root = path.parent
    model = read(root / "model.json")
    inventory = read(root / "inventory.json")
    pages = {}
    for key, page in feature["pages"].items():
        capture = page.get("capture", {})
        actions = {}
        for spot in capture.get("hotspots", []):
            action = spot.get("baselineId", spot["label"])
            if action in actions:
                raise ValueError(f"重复的操作标识 {key}/{action}")
            actions[action] = {k: v for k,v in spot.items() if k != "baselineId"}
        for direction, destination in capture.get("swipe", {}).items():
            swipe = {"page": destination}
            if direction in capture.get("swipeAreas", {}):
                swipe["area"] = capture["swipeAreas"][direction]
            actions["swipe-" + direction] = swipe
        if "after" in page:
            actions["@after"] = page["after"]
        images, previews = {}, {}
        for zone in ("header", "content", "footer"):
            if zone in capture:
                images[zone], previews[zone] = image_evidence(owned_file(root, capture[zone]))
        meta = inventory["pages"].get(key, {})
        pages[key] = {"title": page["title"], "module": meta.get("module", ""),
                      "parent": page["parent"], "actions": actions, "images": images, "previews": previews,
                      "captureBoundary": meta.get("captureBoundary", ""), "scrollEvidence": meta.get("scrollEvidence", ""),
                      "controls": sorted(meta.get("controls", [])), "pending": sorted(meta.get("pending", []))}
    navigation = {"home": feature.get("phoneHome"), "initial": feature.get("initialView"),
                  "modules": {s["id"]: {k: s[k] for k in ("title", "start", "keys", "phonePageIndex") if k in s}
                              for s in feature["scenes"]}}
    return {"schema": 1, "feature": feature["id"], "device": model["devices"]["phone"], "navigation": navigation,
            "scope": inventory["scope"], "capturedAt": inventory["capturedAt"], "pages": pages}


def comparison(a, b):
    if not (a["schema"] == b["schema"] == 1 and a["feature"] == b["feature"]):
        raise ValueError("请选择同一功能、同一基线格式的两个版本")
    if a["scope"] != b["scope"]:
        raise ValueError("比较范围不同，请先选择相同的标签、设备范围和排除项")
    changes = []
    def change(kind, page, field, old, new):
        changes.append({"kind": kind, "page": page, "field": field, "before": old, "after": new})
    for field in sorted(set(a.get("navigation", {})) | set(b.get("navigation", {}))):
        old, new = a.get("navigation", {}).get(field), b.get("navigation", {}).get(field)
        if old != new:
            change("导航变化", "@navigation", field, old, new)
    for key in sorted(set(a["pages"]) | set(b["pages"])):
        left = a["pages"].get(key)
        right = b["pages"].get(key)
        if left is None or right is None:
            change("新采到页面" if left is None else "新版未采到页面", key, "title",
                   left and left["title"], right and right["title"])
            continue
        for field in ("module", "title", "parent", "controls", "pending", "captureBoundary", "scrollEvidence"):
            if left.get(field) != right.get(field):
                kind = "核对范围" if field in ("pending", "captureBoundary", "scrollEvidence") else "页面结构"
                change(kind, key, field, left.get(field), right.get(field))
        for action in sorted(set(left["actions"]) | set(right["actions"])):
            old = left["actions"].get(action)
            new = right["actions"].get(action)
            if old != new:
                kind = "新增操作" if old is None else "未采到操作" if new is None else "操作变化"
                if old and new and {k:v for k,v in old.items() if k != "box"} == {k:v for k,v in new.items() if k != "box"}:
                    kind = "入口位置"
                change(kind, key, action, old, new)
        for zone in sorted(set(left["images"]) | set(right["images"])):
            old = left["images"].get(zone)
            new = right["images"].get(zone)
            if old != new:
                change("画面待复核", key, zone, old, new)
    return {"feature": a["feature"], "before": a["device"], "after": b["device"], "changes": changes}


def html_report(result):
    def escape(value):
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
        return html.escape(text)
    rows = []
    for change in result["changes"]:
        rows.append("<tr>" + "".join("<td><pre>" + escape(change[k]) + "</pre></td>"
                                     for k in ("kind", "page", "field", "before", "after")) + "</tr>")
    versions = [escape(result[k].get("appVersion", "")) for k in ("before", "after")]
    return """<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>运动健康版本差异</title>
<style>body{font:15px system-ui;margin:3vw;color:#193934}table{border-collapse:collapse;width:100%}
td,th{text-align:left;vertical-align:top;border-bottom:1px solid #c7d4ce;padding:.7em}
pre{white-space:pre-wrap;overflow-wrap:anywhere;margin:0;max-width:32em}</style>
<h1>运动健康版本差异</h1>""" + f"<p>{versions[0]} → {versions[1]}，共 {len(rows)} 处差异。</p>" + \
        "<p>画面变化可能来自日期、用户数据或在线内容。新版未采到的页面需要结合采集范围核对。</p>" + \
        "<table><tr><th>分类</th><th>页面</th><th>项目</th><th>基线</th><th>新版</th></tr>" + "".join(rows) + "</table></html>"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="command", required=True)
    take = actions.add_parser("snapshot")
    take.add_argument("feature", type=Path)
    diff = actions.add_parser("compare")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    viewer = actions.add_parser("viewer")
    viewer.add_argument("baseline", type=Path)
    for cmd in (take, diff, viewer):
        cmd.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f"输出已存在，请为此次结果指定新文件 {args.out}")
    if args.command == "viewer":
        template = Path(__file__).resolve().parents[1] / "assets/health-baseline/compare.html"
        payload = json.dumps(read(args.baseline), ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(template.read_text(encoding="utf-8").replace("@@BASELINE@@", payload), encoding="utf-8")
        print(args.out)
        return
    value = snapshot(args.feature) if args.command == "snapshot" else comparison(read(args.before), read(args.after))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.command == "compare" and args.out.suffix.lower() == ".html":
        args.out.write_text(html_report(value), encoding="utf-8")
    else:
        write(args.out, value)
    print(args.out)


if __name__ == "__main__":
    main()
