from __future__ import annotations

import hashlib
import json
from pathlib import Path

from openpyxl import load_workbook


WORKSPACE = Path(__file__).resolve().parents[1]
COMPONENT_ROOT = WORKSPACE / "官方设计规范" / "组件资源"
MANIFEST_PATH = COMPONENT_ROOT / "组件资源索引_manifest.json"
INDEX_PATH = COMPONENT_ROOT / "组件资源索引.xlsx"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    components = manifest["components"]
    source_images = manifest["source_manifest"]

    missing_component_files = [
        str(WORKSPACE / item["image_path"]) for item in components if not (WORKSPACE / item["image_path"]).exists()
    ]
    changed_sources = [
        item["source"]
        for item in source_images
        if not (WORKSPACE / item["source"]).exists()
        or sha256(WORKSPACE / item["source"]) != item["sha256"]
    ]

    workbook = load_workbook(INDEX_PATH, read_only=True, data_only=False)
    required_sheets = ["组件索引", "版本说明", "变更记录"]
    missing_sheets = [sheet for sheet in required_sheets if sheet not in workbook.sheetnames]

    component_sheet = workbook["组件索引"]
    version_sheet = workbook["版本说明"]
    change_sheet = workbook["变更记录"]

    rows = list(component_sheet.iter_rows(values_only=True))
    headers = list(rows[0])
    data_rows = len(rows) - 1
    version_value = version_sheet["B1"].value
    snapshot_path = COMPONENT_ROOT / "索引版本" / f"组件资源索引_{manifest['version']}.xlsx"

    report = {
        "version": manifest["version"],
        "source_count": len(source_images),
        "component_count_manifest": len(components),
        "component_count_excel": data_rows,
        "missing_component_files": len(missing_component_files),
        "changed_or_missing_sources": len(changed_sources),
        "missing_sheets": missing_sheets,
        "headers": headers,
        "version_sheet_value": version_value,
        "change_log_rows": max(0, len(list(change_sheet.iter_rows(values_only=True))) - 1),
        "snapshot_exists": snapshot_path.exists(),
    }

    if (
        missing_component_files
        or changed_sources
        or missing_sheets
        or data_rows != len(components)
        or version_value != manifest["version"]
        or not snapshot_path.exists()
    ):
        report["sample_missing_component_files"] = missing_component_files[:5]
        report["sample_changed_sources"] = changed_sources[:5]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
