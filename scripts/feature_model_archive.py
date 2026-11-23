"""Validate recorded device paths and archive a reproducible feature demo."""
from datetime import datetime
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

DEFAULT_ARCHIVE = Path.home() / "Documents" / "穿戴功能模型备份"
FONT = "运动健康素材/官方设计规范/华为字体/HarmonyOS-Sans.zip"
FONT_DIR = "HarmonyOS Sans/HarmonyOS_Sans_SC/"
CHUNK = 1024 * 1024


def owned_file(root, name):
    if not isinstance(name, str) or not name:
        raise ValueError("素材路径为空")
    rel = Path(name)
    path = (root / rel).resolve()
    if rel.is_absolute() or ".." in rel.parts or not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"请将引用的素材放在功能工作目录内：{name}")
    return path


def feature_images(feature):
    images = set()
    if feature.get("icon") and not feature["icon"].startswith("@"):
        images.add(feature["icon"])
    for page in feature["pages"].values():
        if "cover" in page:
            images.add(page["cover"])
        capture = page.get("capture", {})
        images.update(capture[k] for k in ("header", "content", "footer") if k in capture)
    return sorted(images)


def inspect_model(feature_path, feature):
    path = feature_path.with_name("model.json")
    if not path.exists():
        return "待联机", {}, []
    model = json.loads(path.read_text())
    if model.get("feature") != feature["id"]:
        raise ValueError(f"{path} 的 feature 与功能 ID 不一致")
    steps = model.get("steps", [])
    devices = model.get("devices", {})
    observed = set()
    files = {"model.json": path}
    # A companion device may be parked on its home page. Verify the devices
    # that actually have key frames in this scene.
    required = {(s["id"], k[0]) for s in feature["scenes"] for k in s["keys"]}
    pending = []
    for row in steps:
        key = (row["scene"], row["device"])
        if key[0] not in {s["id"] for s in feature["scenes"]} or key[1] not in devices:
            raise ValueError(f"未识别的场景或设备 {key}")
        status = row["source"]
        if status not in {"live", "reference", "pending"} or not all(row.get(k) for k in ("from", "action", "to")):
            raise ValueError(f"操作记录不完整 {key}")
        evidence = row.get("files", [])
        if status != "pending" and not evidence:
            raise ValueError(f"{key} 缺少截图或录屏")
        for name in evidence:
            files[name] = owned_file(path.parent, name)
        if status == "live":
            if not row.get("observedAt") or not devices[key[1]].get("model"):
                raise ValueError(f"{key} 缺少观测时间或设备型号")
            observed.add(key)
        else:
            pending.append(f"{key[1]} · {row['from']} → {row['action']} → {row['to']}")
    complete = bool(steps and required <= observed and not pending and model.get("reviewed") is True)
    return ("联机已核对" if complete else "待联机补采"), files, pending


def font_archive(root):
    data = BytesIO()
    with ZipFile(root / FONT) as source, ZipFile(data, "w") as dest:
        for name in ("HarmonyOS_Sans_SC_Regular.ttf", "LICENSE.txt"):
            key = FONT_DIR + name
            dest.writestr(source.getinfo(key), source.read(key))
    return data.getvalue()


def digest_stream(stream, output=None):
    h = sha256()
    for chunk in iter(lambda: stream.read(CHUNK), b""):
        h.update(chunk)
        if output is not None:
            output.write(chunk)
    return h.hexdigest()


def verify(path):
    with ZipFile(path) as z:
        manifest = json.loads(z.read("manifest.json"))
        hashes = manifest["sha256"]
        if sorted(z.namelist()) != sorted([*hashes, "manifest.json"]):
            raise ValueError("备份文件清单不一致")
        for name, expected in hashes.items():
            with z.open(name) as stream:
                if digest_stream(stream) != expected:
                    raise ValueError(f"备份校验失败 {name}")
    return hashes


def archive(root, feature_paths, states, delivery, archive_dir, collection=None):
    members = {f"demo/{n}": delivery / n for n in ("index.html", "generation-report.md")}
    ids = []
    has_baseline = False
    has_watch_face = False
    for path, (status, evidence, pending) in zip(feature_paths, states):
        feature = json.loads(path.read_text())
        has_watch_face |= feature.get("watchProfile") == "watch6" and bool(feature.get("watchScreens"))
        fid = feature["id"]
        ids.append(fid)
        inputs = {"feature.json": path, **evidence}
        baseline = feature.get("baselineFiles", [])
        if baseline:
            has_baseline = True
            for name in baseline:
                inputs[name] = owned_file(path.parent, name)
        for name in feature_images(feature):
            inputs[name] = owned_file(path.parent, name)
        for name, src in inputs.items():
            members[f"features/{fid}/{name}"] = src
    template = root / "assets/interactive-demo"
    renderer = [template / name for name in ("style.css", "demo.js", "template.html")]
    renderer += list((template / "media").glob("*.webp"))
    if collection and "navigation" in collection:
        renderer.append(template / "directory.js")
        if has_watch_face:
            renderer.append(template / "watch6-case/original.png")
            renderer.extend(p for p in (template / "watch6-launcher").iterdir() if p.is_file())
    if has_watch_face:
        folder = template / "watch6-face"
        renderer += [folder / "navigation.json", folder / "evidence.json", *folder.glob("*.webp")]
    renderer += [root / "scripts" / name for name in ("generate_interactive_demo.py", "feature_model_archive.py", "capture_policy.py", "collection_navigation.py", "demo_styles.py")]
    if has_baseline:
        renderer.append(root / "scripts/health_ui_baseline.py")
        renderer.append(root / "scripts/record_phone_page.py")
        renderer.append(root / "assets/health-baseline/compare.html")
    for path in renderer:
        members["skill/" + path.relative_to(root).as_posix()] = path
    members["skill/" + FONT] = font_archive(root)
    if collection:
        spec = dict(collection, features=[fid + "/feature.json" for fid in ids])
        members["features/collection.json"] = json.dumps(spec, ensure_ascii=False, indent=2).encode()
    group = collection["id"] if collection else ids[0] if len(ids) == 1 else "多功能演示"
    folder = Path(archive_dir) / group
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder) as tmp:
        staged = Path(tmp) / "version.zip"
        hashes = {}
        with ZipFile(staged, "w", compression=ZIP_DEFLATED, compresslevel=5) as z:
            for name, src in sorted(members.items()):
                with (BytesIO(src) if isinstance(src, bytes) else src.open("rb")) as inp, z.open(name, "w", force_zip64=True) as out:
                    hashes[name] = digest_stream(inp, out)
            manifest = {"archivedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
                        "features": dict(zip(ids, (s[0] for s in states))), "sha256": hashes}
            z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        version = sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:20]
        target = folder / f"{group}-{version}.zip"
        verify(staged)
        try:
            os.link(staged, target)
        except FileExistsError:
            if verify(target) != hashes:
                raise ValueError(f"已有备份校验失败，请检查 {target}")
    return target

