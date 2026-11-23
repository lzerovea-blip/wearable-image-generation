"""Locate, rebuild, package and restore the bundled WATCH 6 collection."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from demo_locator import locate
from feature_model_archive import digest_stream, inspect_model
from generate_interactive_demo import ROOT, build, read_collection

PROJECT = ROOT / "projects/watch6-health/collection.json"
DELIVERY = Path("outputs/20261119-WATCH6与手机全功能合集")
DOCUMENTS = ("generation-report.md", "index.html")
MANIFEST = "package-manifest.json"


def digest(path):
    with path.open("rb") as stream:
        return digest_stream(stream)


def render(project, out):
    config, paths = read_collection(project)
    states = [inspect_model(p, json.loads(p.read_text())) for p in paths]
    return build(paths, out, states, config)


@contextmanager
def publishing(folder):
    # Serialize replacements of the report and HTML. Build and validate before taking the lock.
    lock = folder / ".demo-publish.lock"
    with lock.open("x") as handle:
        handle.write(str(os.getpid()))
    try:
        yield
    finally:
        lock.unlink()


def publish(project, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        staged = Path(tmp) / "candidate"
        render(project, staged)
        if not out.exists():
            staged.rename(out)
            return
        with publishing(out):
            if not all((out / n).is_file() for n in DOCUMENTS):
                raise ValueError(f"目标目录已有其他内容，请指定现有合集或新目录 {out}")
            if digest(staged / "index.html") == digest(out / "index.html"):
                return
            version = hashlib.sha256("".join(digest(out / n) for n in DOCUMENTS).encode()).hexdigest()[:20]
            backup = out / "versions" / version
            if not backup.is_dir():
                saved = Path(tmp) / "previous"
                saved.mkdir()
                for name in DOCUMENTS:
                    shutil.copy2(out / name, saved / name)
                backup.parent.mkdir(exist_ok=True)
                saved.rename(backup)
            if any(digest(backup / n) != digest(out / n) for n in DOCUMENTS):
                raise ValueError("已有历史版本与当前交付不同")
            replaced = []
            try:
                for name in DOCUMENTS:
                    os.replace(staged / name, out / name)
                    replaced.append(name)
            except BaseException:
                for name in replaced:
                    restored = Path(tmp) / name
                    shutil.copy2(backup / name, restored)
                    os.replace(restored, out / name)
                raise


def package(folder):
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder) as tmp:
        tmp = Path(tmp)
        if digest(render(PROJECT, tmp / "check")) != digest(ROOT / DELIVERY / "index.html"):
            raise ValueError("当前 HTML 与源模型不同，请先 build")
        files = [ROOT / "SKILL.md", *(ROOT / DELIVERY / n for n in DOCUMENTS)]
        for part in ("agents", "references", "scripts", "assets", "projects/watch6-health", "运动健康素材"):
            files.extend(p for p in (ROOT / part).rglob("*") if p.is_file() and not p.is_symlink()
                         and not any(x.startswith(".") or x == "__pycache__" for x in p.relative_to(ROOT).parts))
        archive = tmp / "skill.zip"
        hashes = {}
        with ZipFile(archive, "w", ZIP_DEFLATED, compresslevel=3) as z:
            for path in sorted(files):
                name = unicodedata.normalize("NFC", path.relative_to(ROOT).as_posix())
                if name in hashes:
                    raise ValueError(f"包内路径冲突 {name}")
                with path.open("rb") as inp, z.open("wearable-image-generation/" + name, "w", force_zip64=True) as out:
                    hashes[name] = digest_stream(inp, out)
            manifest = json.dumps(hashes, ensure_ascii=False, sort_keys=True, indent=2).encode()
            z.writestr("wearable-image-generation/" + MANIFEST, manifest)
        dest = folder / ("wearable-image-generation-" + hashlib.sha256(manifest).hexdigest()[:16] + ".zip")
        if dest.exists():
            if read_package(dest) != hashes:
                raise ValueError(f"已有同名开发包内容不同 {dest}")
        else:
            os.link(archive, dest)
        return dest


def read_package(archive, root=None):
    prefix = "wearable-image-generation/"
    with ZipFile(archive) as z:
        hashes = json.loads(z.read(prefix + MANIFEST))
        if sorted(z.namelist()) != sorted(prefix + n for n in [*hashes, MANIFEST]):
            raise ValueError("开发包清单不一致")
        for name, expected in hashes.items():
            if Path(name).is_absolute() or ".." in Path(name).parts or "\\" in name:
                raise ValueError(f"开发包内路径无效 {name}")
            with z.open(prefix + name) as stream:
                if root is None:
                    actual = digest_stream(stream)
                else:
                    target = root / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open("xb") as out:
                        actual = digest_stream(stream, out)
            if actual != expected:
                raise ValueError(f"文件校验失败 {name}")
    return hashes


def verify(archive, dest):
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        root = dest or temp / "wearable-image-generation"
        root.mkdir(parents=True, exist_ok=False)
        hashes = read_package(archive, root)
        out = temp / "rebuilt"
        subprocess.run([sys.executable, "-E", "-B", str(root / "scripts/demo_project.py"),
                        "build", "--out", str(out)], cwd=root, check=True)
        expected = hashes[(DELIVERY / "index.html").as_posix()]
        if digest(out / "index.html") != expected:
            raise ValueError("独立重建的 HTML 与包内版本不同")
        print(f"{len(hashes)} 个文件通过 SHA-256 校验。离线重建 HTML {expected}")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--project", type=Path, default=PROJECT, help="指定其他合集 collection.json")
    commands = cli.add_subparsers(dest="action", required=True)
    commands.add_parser("locate", help="按路径、稳定 ID 或旧 ID 查源文件和跳转").add_argument("query")
    commands.add_parser("build", help="从模型原位重建并保留上一版本").add_argument("--out", type=Path)
    commands.add_parser("package", help="备份完整可离线开发的 skill").add_argument("--out", type=Path, default=ROOT / "outputs/开发包")
    check = commands.add_parser("verify", help="逐文件校验并从解包副本独立重建")
    check.add_argument("archive", type=Path)
    check.add_argument("--extract-to", type=Path, help="保留解出的 skill 到一个新目录")
    args = cli.parse_args()
    try:
        project = args.project.resolve()
        if args.action == "locate":
            result = locate(project, args.query)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if "matches" in result:
                return 2
        elif args.action == "build":
            if not args.out and project != PROJECT:
                raise ValueError("其他合集请指定自己的 --out")
            out = (args.out or ROOT / DELIVERY).resolve()
            publish(project, out)
            print(out / "index.html", flush=True)
        elif args.action == "package":
            if project != PROJECT:
                raise ValueError("可迁移开发包对应本 skill 内置的合集")
            print(package(args.out.resolve()))
        else:
            verify(args.archive, args.extract_to.resolve() if args.extract_to else None)
    except (ValueError, KeyError, TypeError, OSError, BadZipFile, subprocess.CalledProcessError) as exc:
        cli.exit(1, f"操作失败 {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
