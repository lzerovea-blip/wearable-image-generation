"""Build a self-contained wearable / phone demo from one or more feature files."""
import argparse
import base64
from collections import Counter
import hashlib
from datetime import datetime
from io import BytesIO
import json
import math
from pathlib import Path
import re
import tempfile
from zipfile import BadZipFile, ZipFile

from feature_model_archive import DEFAULT_ARCHIVE, archive, feature_images, inspect_model, owned_file
from capture_policy import check_screen_sources
from collection_navigation import build_directory
from demo_styles import compile_styles, validate_elements

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "assets/interactive-demo"
EXAMPLE = TEMPLATE / "examples/readiness/feature.json"
SYSTEM = {"watch": {"@face", "@launcher", "@minus", "@cards"}, "phone": {"@home", "@summary"}}
SLOTS = {"launcher": "watch", "minus": "watch", "cards": "watch", "summary": "phone"}
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def label(obj, key):
    value = obj.get(key) if isinstance(obj, dict) else None
    require(isinstance(value, str) and value.strip(), f"需要非空文本字段 {key}")
    return value


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9-]*", value), f"无效 ID {value!r}")


def image_url(path):
    require(path.suffix.lower() in MIME and path.is_file(), f"找不到支持的本地图片 {path}")
    return "data:" + MIME[path.suffix.lower()] + ";base64," + base64.b64encode(path.read_bytes()).decode()


def watch_screen_url(path):
    """Remove the square export matte before a round screen moves through the viewport."""
    from PIL import Image, ImageDraw, ImageFilter
    with Image.open(path) as image:
        w, h = image.size
        if w != h:
            return image_url(path)
        frame = image.convert("RGBA")
    corners = [frame.getpixel((x, y)) for x in (1, w-2) for y in (1, h-2)]
    if not any(a < 16 or min(r,g,b) >= 225 for r,g,b,a in corners):
        return image_url(path)

    def edge_color(start):
        colors = []
        for degree in range(start, start + 180, 2):
            angle = math.radians(degree)
            for radius in (.455, .475):
                x = int(w * (.5 + radius * math.cos(angle)))
                y = int(h * (.5 + radius * math.sin(angle)))
                colors.append(frame.getpixel((x,y))[:3])
        def bucket(color):
            return tuple(v // 16 for v in color)
        tone = Counter(map(bucket, colors)).most_common(1)[0][0]
        samples = [c for c in colors if bucket(c) == tone]
        return tuple(round(sum(channel)/len(samples)) for channel in zip(*samples))

    top, bottom = edge_color(180), edge_color(0)
    ramp = Image.new("RGB", (1,2))
    ramp.putdata([top,bottom])
    display = ramp.resize((w,h), Image.Resampling.BILINEAR)
    mask = Image.new("L", (w,h))
    inset = max(2, round(w*.009))
    ImageDraw.Draw(mask).ellipse((inset,inset,w-1-inset,h-1-inset),fill=255)
    display.paste(frame.convert("RGB"), mask=mask.filter(ImageFilter.GaussianBlur(.6)))
    buf = BytesIO()
    display.save(buf, "WEBP", lossless=True, method=2)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def validate_feature(f):
    identifier(label(f, "id"))
    label(f, "name")
    pages = f["pages"]
    require(isinstance(pages, dict) and pages, "需要功能页面 pages")

    def target(device, page):
        require(isinstance(page, str) and (page in SYSTEM[device] or (
            page in pages and pages[page].get("device") in (device, "both")
        )), f"{device} 页面引用无效 {page!r}")

    def sections(items):
        require(isinstance(items, list), "sections 需要数组")
        for section in items:
            label(section, "title")
            label(section, "text")

    for data in f.get("records", {}).values():
        label(data, "title")
        label(data, "date")
        sections(data["sections"])
        require(data["sections"], "解读结果缺少正文")
    for page, item in pages.items():
        identifier(page)
        label(item, "title")
        if "aliasOf" in item:
            dest = pages.get(item["aliasOf"], {})
            require(item["device"] == dest.get("device") == "watch" and "aliasOf" not in dest,
                    f"腕上旧定位需要指向唯一的有效页面 {page}")
        require(item["device"] in ("watch", "phone", "both"), "设备应为 watch、phone 或 both")
        require("coverAction" not in item or "cover" in item, "热点必须与参考图一起提供")
        sections(item.get("sections", []))
        if "record" in item:
            require(item["record"] in f.get("records", {}), f"缺少共享记录 {item['record']}")
        for device in SYSTEM if item["device"] == "both" else [item["device"]]:
            parent = item["parent"]
            target(device, parent[device] if isinstance(parent, dict) else parent)
            for key in ("action", "coverAction", "after"):
                if key in item:
                    target(device, item[key]["page"])
        for key in ("action", "coverAction"):
            if key in item:
                label(item[key], "label")
        if "coverAction" in item:
            box = item["coverAction"]["box"]
            require(isinstance(box, list) and len(box) == 4 and all(type(x) in (int, float) and 0 <= x <= 100 for x in box)
                    and min(box[2:]) > 0 and box[0]+box[2] <= 100 and box[1]+box[3] <= 100, "热点坐标必须在参考图内")
        if "after" in item:
            require(type(item["after"]["ms"]) is int and item["after"]["ms"] > 0, "等待毫秒数必须为正整数")
        if "watchFlow" in item:
            flow = item["watchFlow"]
            require(item["device"] == "watch" and isinstance(flow, dict), "腕上流程页面需要手表配置")
            for action in flow.get("actions", []):
                label(action, "label")
                if "related" in action:
                    identifier(action["related"])
                elif action["page"] != "@back":
                    target("watch", action["page"])
            for direction, dest in flow.get("swipe", {}).items():
                require(direction in ("up", "down", "left", "right"), "未知滑动方向")
                target("watch", dest)
        if "capture" in item:
            cap = item["capture"]
            label(cap, "content")
            validate_elements(cap)
            if "listBands" in cap:
                require(item["device"] == "watch" and cap["listBands"] and not ({"header", "footer"} & cap.keys()),
                        f"腕上列表切片需要整张腕上截图 {page}")
                previous = 0
                for start, end in cap["listBands"]:
                    require(0 <= previous <= start < end <= 100, f"腕上列表切片越界或重叠 {page}")
                    previous = end
                for spot in cap.get("hotspots", []) + cap.get("pendingHotspots", []):
                    center = spot["box"][1] + spot["box"][3]/2
                    require(any(a <= center < b for a,b in cap["listBands"]), f"列表入口被裁掉 {page}/{spot['label']}")
            if "replay" in cap:
                replay = cap["replay"]
                require(item["device"] == "watch" and isinstance(replay, dict),
                        "截图回放仅用于腕上实机画面")
                label(replay, "description")
                require(isinstance(replay.get("actions"), list) and isinstance(replay.get("pending"), list),
                        "截图回放须声明操作和待采集步骤")
                for action in replay["actions"]:
                    label(action, "label")
                    target("watch", action["page"])
                require(all(isinstance(step, str) and step.strip() for step in replay["pending"]),
                        "待采集步骤须使用非空文本")
            for direction, dest in cap.get("swipe", {}).items():
                require(direction in ("left", "right", "up", "down"), "未知滑动方向")
                for device in SYSTEM if item["device"] == "both" else [item["device"]]:
                    target(device, dest)
            for direction, message in cap.get("pendingSwipes", {}).items():
                require(direction in ("up", "down", "left", "right") and direction not in cap.get("swipe", {})
                        and isinstance(message, str) and message.strip(), "待采集手势与已有路径冲突或缺少说明")
            for spot in cap.get("pendingHotspots", []):
                label(spot, "label")
                box = spot["box"]
                require(spot.get("zone") in ("header", "content", "footer") and spot["zone"] in cap
                        and "page" not in spot and len(box) == 4
                        and all(type(v) in (int, float) and 0 <= v <= 100 for v in box)
                        and 0 < box[2] <= 100-box[0]+.001 and 0 < box[3] <= 100-box[1]+.001,
                        "待采集入口需要位于已采集画面内")
            for direction, area in cap.get("swipeAreas", {}).items():
                require(direction in ("left", "right") and direction in cap.get("swipe", {})
                        and isinstance(area, list) and len(area) == 4
                        and all(type(v) in (int, float) for v in area)
                        and 0 <= area[0] < area[2] <= 100 and 0 <= area[1] < area[3] <= 100,
                        "横滑区域应在对应设备视口内")
            for direction, zone in cap.get("swipeAreaZones", {}).items():
                require(direction in cap.get("swipeAreas", {}) and zone in ("header", "content", "footer") and zone in cap,
                        "横滑区域须引用当前页面已有的截图分区")
            for spot in cap.get("hotspots", []):
                if "openFeature" in spot:
                    link = spot["openFeature"]
                    require(isinstance(link, dict) and spot["page"] != "@back", "跨 App 入口需要本地后备页面")
                    identifier(link["id"])
                    identifier(link["page"])
                if "keepScroll" in spot:
                    require(type(spot["keepScroll"]) is bool, "keepScroll 需要布尔值")
                require(spot["zone"] in cap and spot["zone"] in ("header", "content", "footer"), "热点区域缺失")
                label(spot, "label")
                box = spot["box"]
                require(len(box) == 4 and all(type(v) in (int, float) and 0 <= v <= 100 for v in box)
                        and 0 < box[2] <= 100-box[0]+.001 and 0 < box[3] <= 100-box[1]+.001, "真机热点越界")
                for device in SYSTEM if item["device"] == "both" else [item["device"]]:
                    if spot["page"] != "@back":
                        target(device, spot["page"])
                    if "rememberRoutes" in spot:
                        routes = spot["rememberRoutes"]
                        require(isinstance(routes, dict) and routes and spot["page"] != "@back", "入口记忆需要有效的跳转按钮和页面映射")
                        for entry, destination in routes.items():
                            require(entry in pages and isinstance(destination, str) and destination in pages, "入口记忆须使用本功能页面")
                            target(device, entry)
                            target(device, destination)
    for device in SYSTEM:
        checked = set()
        for start, item in pages.items():
            if item["device"] not in (device, "both"):
                continue
            trail = set()
            current = start
            while current in pages and current not in checked:
                require(current not in trail, f"返回路径形成循环 {device}/{current}")
                trail.add(current)
                parent = pages[current]["parent"]
                current = parent[device] if isinstance(parent, dict) else parent
            checked.update(trail)
    scroll_pages = set()
    for menu in f.get("watchLists", []):
        label(menu, "label")
        rows, anchors = menu["rows"], menu["anchors"]
        require(rows and anchors, "腕上滚动列表缺少行或定位")
        for key, index in anchors.items():
            target("watch", key)
            require(key in pages and key not in scroll_pages and type(index) is int and 0 <= index < len(rows),
                    f"腕上列表定位无效 {key}")
            scroll_pages.add(key)
        for row in rows:
            label(row, "label")
            if "secondary" in row:
                label(row["secondary"], "label")
                if "page" in row["secondary"]:
                    target("watch", row["secondary"]["page"])
            require(row["location"] in anchors, "列表行缺少已登记的位置")
            source = pages.get(row["source"], {})
            require(source.get("device") == "watch" and source.get("capture", {}).get("content"),
                    "列表行须引用腕上实机画面")
            box = row["crop"]
            require(len(box) == 4 and all(type(v) in (int, float) and 0 <= v <= 100 for v in box)
                    and 0 < box[2] <= 100-box[0]+.001 and 0 < box[3] <= 100-box[1]+.001, "列表行裁片越界")
            if row.get("pending"):
                require("page" not in row, "待采集的列表行不能指定跳转")
            else:
                target("watch", row["page"])
    for group in f.get("watchScrollGroups", []):
        paged = isinstance(group, dict)
        if paged:
            require(group.get("mode") == "paged", "未知腕上翻页方式")
            group = group.get("pages")
        require(isinstance(group, list) and len(group) >= 2, "腕上连续阅读需要至少两张截图")
        for i, key in enumerate(group):
            target("watch", key)
            cap = pages[key].get("capture", {})
            require(key not in scroll_pages and "aliasOf" not in pages[key] and cap.get("content") and not ({"header", "footer"} & cap.keys()),
                    f"连续阅读页面须为独立腕上画面 {key}")
            if "scrollSources" in cap:
                sources = cap["scrollSources"]
                require(paged and isinstance(sources, list) and sources and sources[0] == key
                        and len(set(sources)) == len(sources)
                        and all(pages.get(src, {}).get("capture", {}).get("listBands")
                                and (src == key or pages[src].get("aliasOf") == key) for src in sources),
                        f"分页内列表须按顺序引用本页及其已采集的列表切片 {key}")
            if i:
                require(cap.get("swipe", {}).get("down") == group[i-1]
                        and pages[group[i-1]]["capture"].get("swipe", {}).get("up") == key,
                        f"连续阅读缺少双向实机路径 {key}")
            scroll_pages.add(key)
    if "phoneHome" in f:
        home = f["phoneHome"]
        target("phone", home)
        require(home in pages and "capture" in pages[home], "真机首页必须引用可采集的自定义页面")
    if "phoneHomeLabel" in f:
        label(f, "phoneHomeLabel")
    require(f.get("phoneProfile", "pura70") in ("pura70", "mate50"), "未知手机设备底板")
    if "watchScreens" in f:
        require(f.get("watchProfile") == "watch6", "实机圆屏需指定 WATCH 6")
        routes = f["watchScreens"]
        require(isinstance(routes, dict) and "@face" in routes and "@launcher" in routes, "实机圆屏需要表盘和应用列表")
        for system, page in routes.items():
            require(system in SYSTEM["watch"] and page in pages and "capture" in pages[page], "手表系统页需要对应实机截图")
            target("watch", page)
        for row in pages[routes["@launcher"]]["capture"].get("launcherRows", []):
            label(row, "label")
            box = row.get("box")
            require(isinstance(box, list) and len(box) == 4 and all(type(v) in (int, float) and 0 <= v <= 100 for v in box)
                    and 0 < box[2] <= 100-box[0]+.001 and 0 < box[3] <= 100-box[1]+.001, "实机应用列表行越界")
    for device in SYSTEM:
        for page, item in pages.items():
            if item["device"] not in (device, "both"):
                continue
            seen = set()
            step = page
            while step in pages:
                require(step not in seen, f"{device} 返回路径成环 {step}")
                seen.add(step)
                parent = pages[step]["parent"]
                step = parent[device] if isinstance(parent, dict) else parent
    for slot, entry in f["entries"].items():
        require(slot in SLOTS, f"未知入口位置 {slot}")
        label(entry, "label")
        target(SLOTS[slot], entry["page"])
    scenes = f["scenes"]
    require(isinstance(scenes, list) and scenes, "需要至少一个场景")
    seen = set()
    for scene in scenes:
        scene_id = label(scene, "id")
        identifier(scene_id)
        require(scene_id not in seen, f"重复场景 {scene_id}")
        seen.add(scene_id)
        label(scene, "title")
        label(scene, "hint")
        require(scene["start"] and scene["keys"], "场景需要设备起点与关键界面")
        for device, page in scene["start"].items():
            require(device in SYSTEM, f"未知设备 {device}")
            target(device, page)
        for device, page, title in scene["keys"]:
            require(device in scene["start"], f"关键界面缺少设备起点 {device}")
            target(device, page)
            require(isinstance(title, str) and title.strip(), "关键界面需要名称")
        if "phonePageIndex" in scene:
            index = scene["phonePageIndex"]
            require("phone" in scene["start"] and isinstance(index, list), "手机页面目录需要手机场景")
            require(all(isinstance(k, str) and k in pages for k in index) and len(index) == len(set(index)), "页面目录需使用唯一的页面 ID")
            for key in index:
                target("phone", key)
    if "initialView" in f:
        view = f["initialView"]
        scene = next((s for s in scenes if s["id"] == view["scene"]), None)
        require(scene and any(k[:2] == [view["device"], view["page"]] for k in scene["keys"]),
                "初始界面应引用本功能场景内的一张关键图")
    if "watchReplayEntry" in f:
        target("watch", f["watchReplayEntry"])
        require(f.get("watchScreens") and any(
            key[:2] == ["watch", f["watchReplayEntry"]] for scene in scenes for key in scene["keys"]
        ), "截图回放入口需要对应的腕上场景")
    if "sharedPhoneHome" in f:
        identifier(f["sharedPhoneHome"])
        require("phoneHome" in f, "共享首页需要 phoneHome")


def connect_phone_homes(features):
    groups = {}
    for f in features:
        if "sharedPhoneHome" in f:
            groups.setdefault(f["sharedPhoneHome"], []).append(f)
    for members in groups.values():
        if len(members) < 2:
            continue
        links = []
        labels = set()
        for f in members:
            cap = f["pages"][f["phoneHome"]]["capture"]
            for spot in cap.get("hotspots", []):
                name, page = spot["label"], spot["page"]
                require(name not in labels, f"共享首页的入口重复：{name}")
                labels.add(name)
                scene = next((s["id"] for s in f["scenes"] if any(k[:2] == ["phone", page] for k in s["keys"])), None)
                require(scene, f"共享入口 {name} 缺少目标场景")
                initial = f.get("initialView", {})
                if initial.get("device") == "phone" and initial["page"] == page:
                    scene = initial["scene"]
                links.append(dict(spot, feature=f["id"], scene=scene))
        for f in members:
            cap = f["pages"][f["phoneHome"]]["capture"]
            require(all(spot["zone"] in cap for spot in links), "共享首页的分区不一致")
            cap["hotspots"] = links


def add_watch_face_navigation(features):
    watches = [f for f in features if f.get("watchScreens") and f.get("watchProfile") == "watch6"]
    if not watches:
        return {}
    folder = TEMPLATE / "watch6-face"
    profile = json.loads((folder / "navigation.json").read_text())
    evidence = json.loads((folder / "evidence.json").read_text())
    frames = {row["page"]: row for row in evidence["pages"]}
    media = {}
    for key, page in profile["pages"].items():
        name = page["capture"]["content"]
        source = owned_file(folder, name)
        row = frames.get(key, {})
        require(row.get("archivedFrame") == name and row.get("sourceFrameSHA256")
                and row.get("archivedFrameSHA256") == hashlib.sha256(source.read_bytes()).hexdigest()
                and row.get("processing") in ("original", "redacted"),
                f"系统页 {key} 的实机来源或展示图未核实")
        media[name] = watch_screen_url(source)
    for f in watches:
        require(not f["pages"].keys() & profile["pages"].keys(), "表盘导航与功能页面 ID 冲突")
        f["pages"].update(profile["pages"])
        f.setdefault("watchScrollGroups", []).extend(profile.get("watchScrollGroups", []))
        dial = f["pages"][f["watchScreens"]["@face"]]["capture"]
        dial["swipe"] = {**dial.get("swipe", {}), **profile["swipe"]}
        f["scenes"].append(profile["scene"])
        validate_feature(f)
    by_id = {f["id"]: f for f in watches}
    for link in profile.get("links", []):
        dest = by_id.get(link["feature"])
        if not dest:
            continue
        page = link.get("preferredPage") if link.get("preferredPage") in dest["pages"] else link["page"]
        scene = next((s for s in dest["scenes"] if any(
            k[:2] == ["watch", page] for k in s["keys"])), None)
        cap = profile["pages"][link["from"]]["capture"]
        if not scene:
            cap.setdefault("pendingHotspots", []).append({"zone": "content", "label": link["label"], "box": link["box"]})
            continue
        cap["hotspots"].append({key: value for key, value in link.items() if key not in ("from", "preferredPage")} |
                               {"page": page, "zone": "content", "scene": scene["id"]})
    return media


def connect_watch_launchers(features):
    entries = {}
    for f in features:
        if "watchScreens" not in f:
            continue
        first = f["pages"][f["watchScreens"]["@launcher"]]["capture"]
        own = [f["entries"]["launcher"]] if "launcher" in f["entries"] else first.get("hotspots", [])
        for entry in own:
            scene = next((s["id"] for s in f["scenes"] if any(
                key[:2] == ["watch", entry["page"]] for key in s["keys"])), None)
            if scene:
                entries[(f["watchProfile"], entry["label"])] = (f["id"], scene, entry["page"])
    for f in features:
        if "watchScreens" not in f:
            continue
        entry = f["entries"].get("launcher")
        if entry and f["pages"].get(entry["page"], {}).get("parent") == "@launcher":
            # Direct scene links have no previous tap to identify the launcher's scroll position.
            menu = next((key for key, page in f["pages"].items() if key != entry["page"] and any(
                row["label"] == entry["label"] for row in page.get("capture", {}).get("launcherRows", []))), None)
            if menu and menu != f["watchScreens"]["@launcher"]:
                f["pages"][entry["page"]]["parent"] = menu
        for page in f["pages"].values():
            capture = page.get("capture", {})
            for row in capture.get("launcherRows", []):
                target = entries.get((f["watchProfile"], row["label"]))
                if target and not any(s["label"] == row["label"] for s in capture["hotspots"]):
                    spot = dict(row, zone="content", page=target[2])
                    if target[0] != f["id"]:
                        spot.update(feature=target[0], scene=target[1])
                    capture["hotspots"].append(spot)


def load_feature(path):
    try:
        f = json.loads(path.read_text())
        validate_feature(f)
        model = path.with_name("model.json")
        evidence = json.loads(model.read_text()) if model.is_file() else {}
        check_screen_sources(path, f, evidence)
        if evidence:
            devices = evidence.get("devices", {})
            phone = devices.get("phone", {})
            if phone.get("app"):
                f["appName"] = phone["app"]
            elif f.get("watchScreens") and devices.get("watch", {}).get("model"):
                f["appName"] = devices["watch"]["model"]
        icon = f.get("icon", "")
        if icon.startswith("@"):
            require(icon == "@insight-icon", f"未知固定图标 {icon}")
        wrist_frames = {p["capture"]["content"] for p in f["pages"].values()
                        if f.get("watchProfile") == "watch6" and p.get("device") == "watch" and "capture" in p}
        f["media"] = {name: (watch_screen_url if name in wrist_frames else image_url)(path.parent / name)
                      for name in feature_images(f)}
        return f
    except (ValueError, KeyError, AttributeError, TypeError, OSError) as exc:
        raise ValueError(f"{path}: {exc}") from exc


def script_json(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", r"\u003c")


def scrollable_watch_launcher(features):
    folder = TEMPLATE / "watch6-launcher"
    layout = json.loads((folder / "layout.json").read_text())
    apps = {f["id"]: f for f in features if f.get("watchProfile") == "watch6" and f.get("watchScreens")}
    rows = []
    for filename, digest in layout["sources"].items():
        require(hashlib.sha256(owned_file(folder, filename).read_bytes()).hexdigest() == digest,
                f"腕上列表原图校验失败 {filename}")
    for row in layout["rows"]:
        fid = row["feature"]
        if fid not in apps:
            continue
        artwork = owned_file(folder, row["image"])
        require(row["source"] in layout["sources"] and hashlib.sha256(artwork.read_bytes()).hexdigest() == row["sha256"],
                f"腕上列表图标校验失败 {fid}")
        rows.append(dict(feature=fid, label=row["label"], image=image_url(artwork)))
        del apps[fid]
    for fid, feature in apps.items():
        if feature.get("watchReplayEntry") or feature.get("entries", {}).get("launcher"):
            rows.append(dict(feature=fid, label=feature["name"]))
    return {"rows": rows, "anchors": {k: "watch6-" + v for k, v in layout["anchors"].items()}}


def read_collection(path):
    spec = json.loads(path.read_text())
    identifier(spec["id"])
    label(spec, "name")
    require(isinstance(spec.get("features"), list) and spec["features"], "合集须列出功能文件")
    paths = [owned_file(path.parent, item) for item in spec.pop("features")]
    if "stylesFile" in spec:
        require("styles" not in spec, "合集应只指定一个样式来源")
        spec["styles"] = json.loads(owned_file(path.parent, spec.pop("stylesFile")).read_text())
    return spec, paths


def prepare_features(paths):
    features = [load_feature(p) for p in paths]
    require(len({f["id"] for f in features}) == len(features), "功能 ID 重复")
    face_media = add_watch_face_navigation(features)
    connect_phone_homes(features)
    connect_watch_launchers(features)
    by_id = {f["id"]: f for f in features}
    for f in features:
        for page in f["pages"].values():
            for spot in page.get("capture", {}).get("hotspots", []):
                link = spot.get("openFeature")
                if link and link["id"] in by_id:
                    other = by_id[link["id"]]
                    require(any(k[:2] == [page["device"], link["page"]] for s in other["scenes"] for k in s["keys"]),
                            f"跨 App 入口找不到目标关键界面 {link['id']}/{link['page']}")
            for action in page.get("watchFlow", {}).get("actions", []):
                other = by_id.get(action.get("related"))
                if other:
                    require(any(k[1] == action["page"] for s in other["scenes"] for k in s["keys"]),
                            f"跨设备入口找不到目标关键界面 {other['id']}/{action['page']}")
    return features, face_media


def build(paths, out, states=None, collection=None):
    features, face_media = prepare_features(paths)
    media = {p.stem: image_url(p) for p in sorted((TEMPLATE / "media").glob("*.webp"))}
    media.update(face_media)
    font_path = ROOT / "运动健康素材/官方设计规范/华为字体/HarmonyOS-Sans.zip"
    font_dir = "HarmonyOS Sans/HarmonyOS_Sans_SC/"
    with ZipFile(font_path) as archive:
        font = base64.b64encode(archive.read(font_dir + "HarmonyOS_Sans_SC_Regular.ttf")).decode()
        license_text = archive.read(font_dir + "LICENSE.txt").decode("utf-8-sig")
    style = (TEMPLATE / "style.css").read_text().replace("FONT_DATA", font)
    reports = []
    for path, feature in zip(paths, features):
        for name in ("页面清单.html", "版本比较.html"):
            if name in feature.get("baselineFiles", []):
                reports.append({"title": feature["name"] + " · " + Path(name).stem,
                                "html": owned_file(path.parent, name).read_text(encoding="utf-8")})
    data = {"features": features, "media": media, "fontLicense": license_text, "reports": reports}
    scripts = [(TEMPLATE / "demo.js").read_text()]
    if collection and "navigation" in collection:
        data["navigation"] = build_directory(collection["navigation"], features, face_media)
        if "styles" in collection:
            style += "\n" + compile_styles(collection["styles"], features, data["navigation"])
        data["navigation"]["id"] = collection["id"]
        if face_media:
            data["wristLauncher"] = scrollable_watch_launcher(features)
            media["watch6Case"] = image_url(TEMPLATE / "watch6-case/original.png")
        scripts.insert(0, (TEMPLATE / "directory.js").read_text())
    payload = script_json(data)
    sources = {"STYLE": style, "DATA": payload, "SCRIPT": "\n".join(scripts)}
    html = re.sub(r"@@(STYLE|DATA|SCRIPT)@@", lambda m: sources[m[1]], (TEMPLATE / "template.html").read_text())
    report = ["# 交互网页生成报告", "", "交付文件为同目录的 index.html，双击即可离线操作。",
              "", "设备画面和机型按各功能配置展示。WATCH 6 使用实机表盘、应用列表和圆屏截图。",
              "生成器已校验功能 ID、入口、关键界面的目标设备、返回路径及内嵌资源。", ""]
    if data.get("wristLauncher"):
        report.extend(["应用列表以网页滚动容器呈现。图标裁片来源及校验值保存在 watch6-launcher/layout.json。"
                       "点按应用进入实机页面，右滑退出后恢复到列表原位置。", ""])
    if face_media:
        report.extend(["## WATCH 6 表盘导航", "",
                       "表盘上滑进入消息通知，下滑进入控制中心，左滑进入手表卡片，右滑进入小艺建议。",
                       f"共用 {len(face_media)} 张实机界面。位置与私人日程已遮挡，采集记录、展示图和校验值随版本备份。", ""])
    for f in features:
        report.extend(["## " + f["name"], "", *["- " + s["title"] + " · " + s["hint"] for s in f["scenes"]], "",
                       *f.get("references", []), ""])
    if states:
        report.extend(["## 真机建模记录", ""])
        for f, (status, _, pending) in zip(features, states):
            report.extend([f"{f['name']} · {status}", *["- 待实机复核 " + step for step in pending], ""])
    out.parent.mkdir(parents=True, exist_ok=True)
    require(not out.exists(), f"输出目录已存在，请指定新的目录 {out}")
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        staged = Path(tmp) / "demo"
        staged.mkdir()
        (staged / "index.html").write_text(html)
        (staged / "generation-report.md").write_text("\n".join(report))
        staged.rename(out)
    return out / "index.html"


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--feature", action="append", type=Path, help="功能 JSON，可重复指定")
    cli.add_argument("--out", type=Path, help="新的交付目录")
    cli.add_argument("--draft", action="store_true", help="存档尚待联机补采的草稿")
    cli.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE, help="本地版本备份根目录")
    cli.add_argument("--archive-existing", type=Path, help="对现有交付及更新后的验收报告进行备份")
    args = cli.parse_args()
    paths = args.feature or [EXAMPLE]
    try:
        spec = json.loads(paths[0].read_text())
        slug = spec["id"]
        identifier(slug)
        collection = None
        if "features" in spec:
            require(len(paths) == 1 and isinstance(spec["features"], list) and spec["features"], "合集文件须单独传入并列出功能")
            collection, paths = read_collection(paths[0])
        out = args.out or ROOT / "outputs" / (datetime.now().strftime("%Y%m%d-%H%M%S") + "-interactive-demo-" + slug)
        features = [load_feature(path) for path in paths]
        states = [inspect_model(path, f) for path, f in zip(paths, features)]
        for path, (status, _, _) in zip(paths, states):
            if status != "联机已核对" and not args.draft and path.resolve() != EXAMPLE.resolve():
                raise ValueError(f"{path} 尚待真机核对。补齐同目录 model.json 或用 --draft 备份当前进度")
        if args.archive_existing:
            out = args.archive_existing
            if args.out:
                raise ValueError("--out 和 --archive-existing 不能同时指定")
            with tempfile.TemporaryDirectory() as tmp:
                expected = build(paths, Path(tmp) / "check", states, collection)
                if expected.read_bytes() != (out / "index.html").read_bytes():
                    raise ValueError("交付 HTML 与当前功能和模板不同，请指定对应版本的已验收交付")
        else:
            build(paths, out, states, collection)
        print((out / "index.html").resolve(), flush=True)
        print("版本备份 " + str(archive(ROOT, paths, states, out, args.archive_dir, collection).resolve()))
    except (ValueError, KeyError, OSError, TypeError, BadZipFile) as exc:
        cli.exit(1, f"生成失败：{exc}\n")


if __name__ == "__main__":
    main()

