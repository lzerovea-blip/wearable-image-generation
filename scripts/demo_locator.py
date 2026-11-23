"""Resolve a published page to its editable source and navigation neighbors."""
import json
import re

from collection_navigation import build_directory, page_key
from generate_interactive_demo import ROOT, TEMPLATE, prepare_features, read_collection


def display_path(path):
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def locate(project, query):
    config, paths = read_collection(project)
    features, shared = prepare_features(paths)
    nav = build_directory(config["navigation"], features, shared)
    rows = {r["key"]: r for r in nav["pages"]}
    aliases = nav["aliases"]
    def resolve(fid, device, pid):
        key = page_key(fid, device, pid)
        return aliases.get(key, key)
    query = query.strip()
    # The clipboard includes the full human path and the stable ID on separate lines.
    key = query.splitlines()[-1]
    key = aliases.get(key, key)
    if key not in rows:
        parts = [s.strip().casefold() for s in re.split(r"\s*(?:→|›|>|/)\s*", query) if s.strip()]
        pattern = ".*".join(map(re.escape, parts))
        matches = [r for r in rows.values() if re.search(pattern, r["path"].casefold())
                   or r["key"].split("/")[-1] == query or any(
                       a.rsplit("/", 1)[-1] == query and k == r["key"] for a, k in aliases.items())]
        if len(parts) > 1:
            exact_leaf = [r for r in matches if r["title"].casefold() == parts[-1]]
            matches = exact_leaf or matches
        if len(matches) != 1:
            return {"matches": [{"key": r["key"], "path": r["path"]} for r in matches]}
        key = matches[0]["key"]
    row = rows[key]
    models = {f["id"]: f for f in features}
    files = dict(zip(models, paths))
    fid, device, pid = key.split("/")
    f, source = models[fid], files[fid]
    page = f["pages"][pid]
    cap = page.get("capture", {})
    sysdir = TEMPLATE / "watch6-face"
    system = pid not in json.loads(source.read_text())["pages"]
    model_file = sysdir / "evidence.json" if system else source.with_name("model.json")
    base = sysdir if system else source.parent
    evidence = json.loads(model_file.read_text())
    refs = list(evidence.get("frameEvidence", {}).get(pid, {}).get("sources", {}))
    if system:
        # Shared panels may keep a redacted render plus only the raw frame's digest.
        refs = []
    elif not refs and "采集索引.json" in f.get("baselineFiles", []):
        refs = json.loads((base / "采集索引.json").read_text()).get("evidence", {}).get(pid, [])
    elif not refs:
        live = {s for step in evidence.get("steps", []) if step["source"] == "live" for s in step.get("files", [])}
        refs = [cap[z] for z in ("header", "content", "footer") if cap.get(z) in live]
    outgoing, incoming = [], []
    def edge(start, label, dest, **details):
        record = {"from": start, "action": label, "to": dest, **details}
        if start == key and record not in outgoing:
            outgoing.append(record)
        if dest == key and record not in incoming:
            incoming.append(record)
    for model in features:
        owner = model["id"]
        for name, item in model["pages"].items():
            capture = item.get("capture", {})
            for d in (("phone", "watch") if item["device"] == "both" else (item["device"],)):
                start = resolve(owner, d, name)
                if start not in rows:
                    continue
                def link(label, dest, other=owner, **meta):
                    if dest:
                        target_device = models.get(other, {}).get("pages", {}).get(dest, {}).get("device", d)
                        end = "@back" if dest == "@back" else resolve(other, d if target_device == "both" else target_device, dest)
                        edge(start, label, end, **meta)
                for spot in capture.get("hotspots", []):
                    dest = spot.get("openFeature", {})
                    if dest.get("id") in models:
                        link(spot["label"], dest["page"], dest["id"], fallback=spot["page"])
                    else:
                        link(spot["label"], spot["page"], spot.get("feature", owner))
                    for route, target in spot.get("rememberRoutes", {}).items():
                        link("入口记忆 · " + route, target)
                for action in capture.get("replay", {}).get("actions", []) + item.get("watchFlow", {}).get("actions", []):
                    link(action["label"], action["page"], action.get("related", owner))
                for direction, dest in (capture.get("swipe") or item.get("watchFlow", {}).get("swipe", {})).items():
                    link("swipe." + direction, dest)
                for name_ in ("action", "coverAction", "after"):
                    action = item.get(name_, {})
                    link(action.get("label", name_), action.get("page"))
                parent = item.get("parent")
                if name not in model.get("watchScreens", {}).values() and name != model.get("phoneHome"):
                    link("初始定位的上级", parent.get(d) if isinstance(parent, dict) else parent)
        for menu in model.get("watchLists", []):
            for item in menu["rows"]:
                for choice in (item, item.get("secondary", {})):
                    if choice.get("page"):
                        edge(resolve(owner, "watch", item["location"]), choice["label"], resolve(owner, "watch", choice["page"]))
        if model.get("watchScreens"):
            home = model.get("watchReplayEntry") or model.get("entries", {}).get("launcher", {}).get("page")
            if home:
                edge(resolve(owner, "watch", "@launcher"), model["name"], resolve(owner, "watch", home))
            edge(resolve(owner, "watch", "@face"), "按下表冠", resolve(owner, "watch", "@launcher"))
    for route in nav["links"]:
        edge(route["from"], route["label"], route["to"])
    mode = "实机页面"
    for group in f.get("watchScrollGroups", []):
        if pid in (group if isinstance(group, list) else group["pages"]):
            mode = "连续长页" if isinstance(group, list) else "整屏吸附"
    if any(pid in menu["anchors"] for menu in f.get("watchLists", [])) or cap.get("launcherRows"):
        mode = "滚动列表"
    theme = config.get("styles", {})
    sections = {src: f["pages"][src].get("capture", {}) for src in cap.get("scrollSources", [pid])}
    def spots(field):
        return [dict(spot, sourcePage=src) for src, segment in sections.items() for spot in segment.get(field, [])]
    style_file = json.loads(project.read_text()).get("stylesFile")
    return {**row, "sourcePage": pid, "aliases": [a for a, target in aliases.items() if target == key],
            "featureFile": display_path(sysdir / "navigation.json" if system else source),
            "evidenceFile": display_path(model_file), "originals": [display_path(base / p) for p in refs],
            "sourceHashes": ({r["archivedFrame"]: r["sourceFrameSHA256"] for r in evidence["pages"] if r["page"] == pid}
                             if system else evidence.get("frameEvidence", {}).get(pid, {}).get("sources", {})),
            "renders": {z: display_path(base / cap[z]) for z in ("header", "content", "footer") if z in cap},
            "mode": mode, "scrollSources": cap.get("scrollSources", []),
            "hotspots": spots("hotspots"), "pendingHotspots": spots("pendingHotspots"),
            "elements": spots("elements"), "styleFile": display_path(project.parent / style_file if style_file else project),
            "styles": {
                "global": theme.get("global", {}), "device": theme.get("devices", {}).get(device, {}),
                "feature": theme.get("features", {}).get(fid, {}), "page": theme.get("pages", {}).get(key, {})},
            "back": "实际点入或从目录选择后，返回来源界面与滚动位置。直接作为开场时使用 parent 与系统导航。",
            "outgoing": outgoing, "incoming": incoming}
