"""Remove a measured notification strip from display images of a recorded phone UI."""
import argparse
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image

from feature_model_archive import owned_file


def clean_images(feature_path, screen_width, box):
    root = feature_path.parent
    feature = json.loads(feature_path.read_text())
    displays = set()
    for page in feature["pages"].values():
        capture = page.get("capture")
        if page["device"] == "phone" and capture:
            displays.add(owned_file(root, capture.get("header", capture["content"])))
    evidence = set()
    model_path = root / "model.json"
    if model_path.exists():
        model = json.loads(model_path.read_text())
        evidence = {owned_file(root, name) for step in model["steps"] for name in step["files"]}
    if displays & evidence:
        raise ValueError("请先为展示图建立单独副本，保留证据图原件")
    count = 0
    for path in sorted(displays):
        with Image.open(path) as source:
            fmt = source.format
            if fmt not in ("PNG", "WEBP"):
                raise ValueError(f"无损展示图需要 PNG 或 WebP：{path}")
            image = source.copy()
        left, top, right, bottom = (round(v * image.width / screen_width) for v in box)
        if not 0 < left < right < image.width or not 0 <= top < bottom <= image.height:
            raise ValueError(f"选区超出状态栏展示图：{path}")
        edges = Image.new(image.mode, (2, bottom - top))
        edges.paste(image.crop((left - 1, top, left, bottom)), (0, 0))
        edges.paste(image.crop((right, top, right + 1, bottom)), (1, 0))
        fill = edges.resize((right - left, bottom - top), Image.Resampling.BILINEAR)
        if image.crop((left, top, right, bottom)).tobytes() == fill.tobytes():
            continue
        image.paste(fill, (left, top))
        with NamedTemporaryFile(dir=path.parent, delete=False) as temp:
            tmp = Path(temp.name)
        try:
            image.save(tmp, format=fmt, **({"lossless": True, "exact": True} if fmt == "WEBP" else {}))
            tmp.chmod(path.stat().st_mode & 0o777)
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
        count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feature", type=Path)
    parser.add_argument("--screen-width", required=True, type=int)
    parser.add_argument("--box", required=True, nargs=4, type=int, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"))
    args = parser.parse_args()
    if args.screen_width <= 0:
        parser.error("screen-width 必须为正数")
    print(f"更新 {clean_images(args.feature, args.screen_width, args.box)} 张展示图")
