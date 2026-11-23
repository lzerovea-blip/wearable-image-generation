"""Check the evidence or explicit user approval for each screen in a demo."""
import hashlib
import json
from pathlib import Path
from feature_model_archive import owned_file


def check_screen_sources(path, feature, model):
    frames = model.get("frameEvidence", {})
    approvals = model.get("pageApprovals", {})
    recorded = {name for step in model.get("steps", []) if step.get("source") == "live"
                for name in step.get("files", [])}
    hashes = {}
    baseline_images, baseline_sources = {}, {}
    if {"采集索引.json", "baseline.json"} <= set(feature.get("baselineFiles", [])):
        index = json.loads(owned_file(path.parent, "采集索引.json").read_text())
        baseline = json.loads(owned_file(path.parent, "baseline.json").read_text())
        if baseline.get("feature") == feature["id"]:
            baseline_sources = index.get("evidence", {})
            baseline_images = baseline.get("pages", {})

    def digest(name):
        if name not in hashes:
            hashes[name] = hashlib.sha256(owned_file(path.parent, name).read_bytes()).hexdigest()
        return hashes[name]

    def approved(page):
        consent = approvals.get(page, {})
        return all(isinstance(consent.get(key), str) and consent[key].strip()
                   for key in ("approvedAt", "userStatement", "description"))

    for page, item in feature["pages"].items():
        source_description = item.get("provenance", "")
        elements = item.get("capture", {}).get("elements", [])
        if elements:
            allowed = approvals.get(page, {}).get("elements", [])
            if not approved(page) or not isinstance(allowed, list) or not all(el["id"] in allowed for el in elements):
                raise ValueError(f"{page} 的可编辑文字层缺少逐项页面授权")
            item["provenance"] = "实机底图 · 已授权修改 " + approvals[page]["description"]
        elif approved(page):
            item["provenance"] = "经用户授权 · " + approvals[page]["description"]
            continue
        cap = item.get("capture", {})
        displayed = {cap[k] for k in ("header", "content", "footer") if cap.get(k)}
        row = frames.get(page, {})
        refs = row.get("sources", {})
        renders = row.get("renders", {})
        if not row and page in baseline_sources and page in baseline_images:
            refs = {name: digest(name) for name in baseline_sources[page]}
            renders = {cap[zone]: checksum for zone, checksum in baseline_images[page]["images"].items()
                       if zone in cap}
        # A live capture may be displayed directly without a separate rendering.
        if not row and displayed and displayed <= recorded:
            refs = renders = {name: digest(name) for name in displayed}
        image_evidence = any(Path(name).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov")
                             for name in refs)
        alternative = any(word in source_description for word in ("参考", "示例", "复原", "模拟"))
        if (not displayed or alternative or item.get("watchFlow") or cap.get("bindings") or not image_evidence
                or not set(refs) <= recorded or set(renders) != displayed):
            raise ValueError(f"{feature['name']} / {page} 缺少逐页实机画面证据或该页的用户授权")
        for files in (refs, renders):
            for name, expected in files.items():
                if digest(name) != expected:
                    raise ValueError(f"{feature['name']} / {page} 的证据或展示图发生变化：{name}")

    # System screens may also have a renderer fallback behind a reserved ID.
    recorded_system = set(feature.get("watchScreens", {}))
    if feature.get("phoneHome"):
        recorded_system.add("@home")
    system = {"@home", "@summary", "@launcher", "@face", "@minus", "@cards"}
    def visit(value):
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str) and value in system and value not in recorded_system and not approved(value):
            raise ValueError(f"{feature['name']} / {value} 需要系统实机图或该页的用户授权")
    for section in ("pages", "scenes", "initialView", "entries"):
        visit(feature.get(section))
