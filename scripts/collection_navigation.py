"""Index the captured pages of a collection by their existing feature and page IDs."""
from hashlib import sha256


def page_key(feature, device, page):
    return "/".join((feature, device, page))


def scene_for_page(feature, device, page_id, system):
    scenes = [s for s in feature["scenes"] if device in s["start"]]
    initial = feature.get("initialView", {})
    if initial.get("device") == device and initial.get("page") == page_id:
        return initial["scene"]
    if system == "@face" or feature["pages"][page_id].get("facePanel"):
        return "face-navigation"
    keys = {page_id, system} - {None}
    while keys:
        for scene in scenes:
            if any(d == device and k in keys for d, k, _ in scene["keys"]):
                return scene["id"]
        for scene in scenes:
            if keys.intersection(scene.get("phonePageIndex", [])) or scene["start"][device] in keys:
                return scene["id"]
        parent = feature["pages"].get(page_id, {}).get("parent")
        page_id = parent.get(device) if isinstance(parent, dict) else parent
        keys = {page_id} if page_id in feature["pages"] else set()
    if not scenes:
        raise ValueError(f"页面没有对应设备场景 {feature['id']}/{device}")
    return scenes[0]["id"]


def build_directory(config, features, common_media):
    by_id = {f["id"]: f for f in features}
    rows, aliases, shared = [], {}, {}
    groups = config["groups"]
    labels = {g["id"]: g["label"] for g in groups}
    if len(labels) != len(groups) or config["default"] not in labels:
        raise ValueError("合集入口标识冲突或缺少默认入口")
    owners = {by_id[g["home"]["feature"]]["appName"]: g["id"] for g in groups}
    if len(owners) != len(groups):
        raise ValueError("每个合集入口需要独立的设备或 App")
    home_models = {g["home"]["feature"] for g in groups}
    for f in sorted(features, key=lambda model: model["id"] not in home_models):
        group = owners[f["appName"]]
        systems = {v: k for k, v in f.get("watchScreens", {}).items()}
        for pid, p in f["pages"].items():
            for device in (("phone", "watch") if p["device"] == "both" else (p["device"],)):
                key = page_key(f["id"], device, pid)
                if p.get("aliasOf"):
                    aliases[key] = page_key(f["id"], device, p["aliasOf"])
                    continue
                system = systems.get(pid)
                target = system or pid
                cap = p.get("capture", {})
                common = device == "watch" and (system or p.get("facePanel") or cap.get("launcherRows"))
                if common:
                    ref = cap["content"]
                    data = f["media"].get(ref) or common_media[ref]
                    signature = (group, system or pid, sha256(data.encode()).digest())
                    if signature in shared:
                        aliases[key] = shared[signature]
                    else:
                        shared[signature] = key
                if system:
                    aliases[page_key(f["id"], device, system)] = aliases.get(key, key)
                if device == "phone" and pid == f.get("phoneHome"):
                    aliases[page_key(f["id"], device, "@home")] = key
                if key in aliases:
                    continue
                scene_id = scene_for_page(f, device, pid, system)
                section = "表盘与应用列表" if common else f["name"]
                title = p["title"]
                # Identically titled screens can occur under different parent pages.
                trail = [title]
                parent = p.get("parent")
                while parent:
                    if isinstance(parent, dict):
                        parent = parent.get(device)
                    ancestor = f["pages"].get(parent)
                    if not ancestor:
                        break
                    if ancestor["title"] != trail[0]:
                        trail.insert(0, ancestor["title"])
                    parent = ancestor.get("parent")
                rows.append(dict(key=key, group=group, section=section, title=title,
                                 path=" › ".join([labels[group], section, *trail]),
                                 feature=f["id"], device=device, page=target, scene=scene_id))
    known = {row["key"] for row in rows}

    def resolve(ref):
        key = page_key(ref["feature"], ref["device"], ref["page"])
        key = aliases.get(key, key)
        if key not in known:
            raise ValueError(f"合集入口或连接指向未编目的页面 {key}")
        return key

    return dict(default=config["default"], groups=[dict(id=g["id"], label=g["label"], home=resolve(g["home"]))
                for g in groups], pages=rows, aliases=aliases, links=[
                    {"from": resolve(link["from"]), "to": resolve(link["to"]), "label": link["label"]}
                    for link in config.get("links", [])])
