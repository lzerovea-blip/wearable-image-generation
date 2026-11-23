"""Capture one visible Huawei phone page under a stable ID for a later baseline."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from datetime import datetime
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("page", help="前后版本共用的页面 ID")
    parser.add_argument("--out", required=True, type=Path, help="本次新版本采集目录")
    parser.add_argument("--package", choices=["com.huawei.health", "com.huawei.study.hiresearch"], default="com.huawei.health")
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", help="多设备连接时指定手机")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,95}", args.page):
        parser.error("请使用小写字母、数字、连字符组成的页面 ID")
    command = [args.adb] + (["-s", args.serial] if args.serial else [])

    def adb(*words):
        return subprocess.check_output([*command, *words], timeout=30)

    def foreground():
        text = adb("shell", "dumpsys", "activity", "activities").decode()
        result = re.search(r"(?:mResumedActivity|topResumedActivity):[^\n]*?\bu\d+\s+([^\s}]+/[^\s}]+)", text)
        if not result or result[1].split("/")[0] != args.package:
            raise ValueError("请先在手机上进入目标 App 的对应页面")
        return result[1]

    try:
        activity = foreground()
        package = adb("shell", "dumpsys", "package", args.package).decode()
        version = re.search(r"\bversionName=([^\s]+)", package)
        code = re.search(r"\bversionCode=(\d+)", package)
        if not version or not code:
            raise ValueError("无法读取当前 App 版本")
        dump = adb("exec-out", "uiautomator", "dump", "/dev/tty")
        start, end = dump.index(b"<hierarchy"), dump.index(b"</hierarchy>") + len(b"</hierarchy>")
        xml = dump[start:end]
        ET.fromstring(xml)
        screen = adb("exec-out", "screencap", "-p")
        if not screen.startswith(b"\x89PNG\r\n\x1a\n") or foreground() != activity:
            raise ValueError("采集过程中前台页面发生变化，请在画面稳定后重新采集")
        at = datetime.now().astimezone()
        folder = args.out / args.page
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        target = folder / at.strftime("%Y%m%dT%H%M%S%f%z")
        data = {"page": args.page, "observedAt": at.isoformat(), "package": args.package,
                "appVersion": version[1], "versionCode": int(code[1]), "activity": activity,
                "model": adb("shell", "getprop", "ro.product.model").decode().strip(),
                "sha256": {k: hashlib.sha256(v).hexdigest() for k, v in [("screen.png", screen), ("controls.xml", xml)]}}
        with tempfile.TemporaryDirectory(dir=folder) as tmp:
            stage = Path(tmp) / "capture"
            stage.mkdir(mode=0o700)
            (stage / "screen.png").write_bytes(screen)
            (stage / "controls.xml").write_bytes(xml)
            (stage / "capture.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.rename(stage, target)
        print(target)
    except (ValueError, OSError, ET.ParseError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"采集失败。{exc}\n")


if __name__ == "__main__":
    main()
