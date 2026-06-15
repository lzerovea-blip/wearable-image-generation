from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import date
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
OFFICIAL_DIR = WORKSPACE / "官方设计规范"
DOWNLOAD_DIR = OFFICIAL_DIR / "下载记录"
MANIFEST_PATH = DOWNLOAD_DIR / "官方设计资源manifest.json"
TODAY = date.today().isoformat()


DESTINATION_RULES = {
    "HarmonyOS+应用图标.zip": ("Icon资源", "HarmonyOS 应用图标", "Icon资源", "P0"),
    "HarmonyOS+服务组件库.zip": ("组件资源", "HarmonyOS 服务组件库", "组件资源", "P0"),
    "手机折叠屏平板.zip": ("组件资源", "手机折叠屏平板", "组件资源", "P0"),
    "手机折叠屏平板 (1).zip": ("下载记录/重复资源", "手机折叠屏平板 (1)", "重复资源", "P2"),
    "穿戴.zip": ("组件资源", "穿戴", "组件资源", "P0"),
    "智慧屏.zip": ("组件资源", "智慧屏", "组件资源", "P1"),
    "启动页设计资源.zip": ("模板资源", "启动页设计资源", "模板资源", "P0"),
    "实况窗设计资源.zip": ("组件资源", "实况窗设计资源", "组件资源", "P0"),
    "使用华为账号登录.zip": ("组件资源", "使用华为账号登录", "组件资源", "P1"),
    "元服务静默登录默认头像.zip": ("视觉资源", "元服务静默登录默认头像", "视觉资源", "P1"),
    "产品机框-手机.zip": ("模板资源/产品机框", "产品机框-手机", "模板资源", "P1"),
    "产品机框-穿戴.zip": ("模板资源/产品机框", "产品机框-穿戴", "模板资源", "P0"),
    "产品机框-电脑.zip": ("模板资源/产品机框", "产品机框-电脑", "模板资源", "P2"),
    "产品机框-智慧屏.zip": ("模板资源/产品机框", "产品机框-智慧屏", "模板资源", "P2"),
}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_member_path(name: str) -> Path | None:
    member = Path(name)
    if member.is_absolute() or ".." in member.parts:
        return None
    return member


def classify_zip(zip_path: Path) -> tuple[str, str, str, str]:
    if zip_path.name in DESTINATION_RULES:
        return DESTINATION_RULES[zip_path.name]
    if zip_path.name.startswith("0000000000011111111."):
        return ("组件资源", "设备连接流程", "组件资源", "P1")
    return ("组件资源", zip_path.stem, "组件资源", "P1")


def extract_zip(zip_path: Path, destination_root: Path) -> list[str]:
    extracted: list[str] = []
    with zipfile.ZipFile(zip_path, metadata_encoding="gbk") as zf:
        for info in zf.infolist():
            member_path = safe_member_path(info.filename)
            if member_path is None:
                continue
            target = destination_root / member_path
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted.append(str(target.relative_to(WORKSPACE)))
    return extracted


def main() -> None:
    manifest = []
    for zip_path in sorted(DOWNLOAD_DIR.glob("*.zip")):
        dest_folder, resource_name, resource_type, priority = classify_zip(zip_path)
        destination_root = OFFICIAL_DIR / dest_folder
        extracted_files = extract_zip(zip_path, destination_root)
        manifest.append(
            {
                "resource_name": resource_name,
                "resource_type": resource_type,
                "source_zip": str(zip_path.relative_to(WORKSPACE)),
                "destination_root": str(destination_root.relative_to(WORKSPACE)),
                "file_count": len(extracted_files),
                "sample_files": extracted_files[:8],
                "sha256": file_sha256(zip_path),
                "status": "已解压" if extracted_files else "未发现文件",
                "priority": priority,
                "registered_date": TODAY,
                "source_link": "https://developer.huawei.com/consumer/cn/design/devstart/",
                "notes": "原始 zip 保留在下载记录；中文文件名按 GBK 元数据解码。",
            }
        )

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(MANIFEST_PATH.relative_to(WORKSPACE)), "packages": len(manifest)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
