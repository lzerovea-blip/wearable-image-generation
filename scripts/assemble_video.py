#!/usr/bin/env python3
"""Assemble image frames into a validated MP4 video."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble PNG/JPG frames into an MP4 video using ffmpeg."
    )
    parser.add_argument("--frames", required=True, help="Directory containing frames.")
    parser.add_argument("--out", required=True, help="Output MP4 path.")
    parser.add_argument(
        "--duration",
        type=float,
        default=4.0,
        help="Total video duration in seconds. Defaults to 4.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=12,
        help="Output video frame rate. Defaults to 12.",
    )
    parser.add_argument(
        "--normalize-to",
        default="first",
        help=(
            "Resize frames before MP4 assembly. Use 'first' to match the first frame "
            "(default), 'none' to require exact sizes, or WIDTHxHEIGHT."
        ),
    )
    parser.add_argument(
        "--background",
        default="0,0,0",
        help=(
            "RGB background used when flattening transparent frames for MP4, "
            "formatted as R,G,B. Defaults to black."
        ),
    )
    return parser.parse_args()


def find_ffmpeg() -> tuple[str, str]:
    path = shutil.which("ffmpeg")
    if path:
        return path, "PATH"

    try:
        import imageio_ffmpeg
    except Exception as exc:  # pragma: no cover - message is surfaced to CLI users
        raise ValueError(
            "视频编码器不可用：未找到 PATH 中的 ffmpeg，也无法导入 imageio_ffmpeg"
        ) from exc

    path = imageio_ffmpeg.get_ffmpeg_exe()
    if not path:
        raise ValueError("视频编码器不可用：imageio_ffmpeg 未返回 ffmpeg 可执行文件")
    return path, "imageio-ffmpeg"


def find_frames(frames_dir: Path) -> list[Path]:
    if not frames_dir.is_dir():
        raise ValueError(f"frames directory does not exist: {frames_dir}")

    frames = [
        path
        for path in sorted(frames_dir.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if len(frames) < 3:
        raise ValueError("video requires at least 3 PNG/JPG frames")
    return frames


def parse_target_size(value: str, first_size: tuple[int, int]) -> tuple[int, int] | None:
    if value == "none":
        return None
    if value == "first":
        return first_size

    parts = value.lower().split("x", 1)
    if len(parts) != 2:
        raise ValueError("--normalize-to must be 'first', 'none', or WIDTHxHEIGHT")
    try:
        width, height = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise ValueError("--normalize-to width and height must be integers") from exc
    if width <= 0 or height <= 0:
        raise ValueError("--normalize-to width and height must be positive")
    return (width, height)


def parse_background(value: str) -> tuple[int, int, int]:
    parts = value.split(",")
    if len(parts) != 3:
        raise ValueError("--background must be formatted as R,G,B")
    try:
        color = tuple(int(part.strip()) for part in parts)
    except ValueError as exc:
        raise ValueError("--background values must be integers") from exc
    if any(channel < 0 or channel > 255 for channel in color):
        raise ValueError("--background values must be between 0 and 255")
    return color  # type: ignore[return-value]


def even_size(size: tuple[int, int]) -> tuple[int, int]:
    width, height = size
    return (width if width % 2 == 0 else width - 1, height if height % 2 == 0 else height - 1)


def load_and_prepare_frames(
    paths: list[Path],
    normalize_to: str,
    background: tuple[int, int, int],
) -> tuple[list[Image.Image], tuple[int, int]]:
    images: list[Image.Image] = []
    expected_size: tuple[int, int] | None = None
    target_size: tuple[int, int] | None = None

    for path in paths:
        try:
            image = Image.open(path).convert("RGBA")
        except Exception as exc:  # pragma: no cover - message is surfaced to CLI users
            raise ValueError(f"failed to read frame {path}: {exc}") from exc

        if expected_size is None:
            expected_size = image.size
            target_size = parse_target_size(normalize_to, image.size)
        elif image.size != expected_size:
            if target_size is None:
                raise ValueError(
                    f"frame size mismatch: {path} is {image.size}, expected {expected_size}"
                )

        if target_size is not None and image.size != target_size:
            image = image.resize(target_size, Image.Resampling.LANCZOS)

        flattened = Image.new("RGBA", image.size, (*background, 255))
        flattened.alpha_composite(image)
        flattened = flattened.convert("RGB")

        output_size = even_size(flattened.size)
        if output_size[0] <= 0 or output_size[1] <= 0:
            raise ValueError(f"invalid frame size after even-size adjustment: {flattened.size}")
        if output_size != flattened.size:
            flattened = flattened.crop((0, 0, output_size[0], output_size[1]))
        images.append(flattened)

    if not images:
        raise ValueError("no frames loaded")
    return images, images[0].size


def write_concat_inputs(images: list[Image.Image], tmp_dir: Path, total_seconds: float) -> Path:
    frame_duration = total_seconds / len(images)
    concat_path = tmp_dir / "frames.txt"
    lines: list[str] = []

    for index, image in enumerate(images):
        frame_path = tmp_dir / f"frame_{index:06d}.png"
        image.save(frame_path, format="PNG")
        lines.append(f"file '{frame_path.as_posix()}'\n")
        lines.append(f"duration {frame_duration:.8f}\n")

    # ffmpeg concat demuxer requires the final file to be repeated for its duration.
    lines.append(f"file '{(tmp_dir / f'frame_{len(images) - 1:06d}.png').as_posix()}'\n")
    concat_path.write_text("".join(lines), encoding="utf-8")
    return concat_path


def run_ffmpeg(
    ffmpeg: str,
    concat_path: Path,
    out_path: Path,
    *,
    duration: float,
    fps: int,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-t",
        f"{duration:.8f}",
        "-vf",
        f"fps={fps},format=yuv420p",
        "-c:v",
        "libx264",
        "-movflags",
        "+faststart",
        str(out_path),
    ]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown ffmpeg error"
        raise ValueError(f"ffmpeg failed: {message}")


def probe_video(ffmpeg: str, out_path: Path) -> None:
    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise ValueError(f"output MP4 is missing or empty: {out_path}")

    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(out_path)],
        text=True,
        capture_output=True,
    )
    probe_text = f"{result.stdout}\n{result.stderr}"
    if "Video:" not in probe_text:
        raise ValueError("output MP4 does not contain a readable video stream")


def main() -> int:
    args = parse_args()
    frames_dir = Path(args.frames)
    out_path = Path(args.out)

    try:
        if args.duration < 3 or args.duration > 5:
            raise ValueError("duration must be between 3 and 5 seconds")
        if args.fps < 1 or args.fps > 60:
            raise ValueError("fps must be between 1 and 60")

        ffmpeg, ffmpeg_source = find_ffmpeg()
        background = parse_background(args.background)
        frame_paths = find_frames(frames_dir)
        images, target_size = load_and_prepare_frames(
            frame_paths, args.normalize_to, background
        )

        with tempfile.TemporaryDirectory(prefix="assemble-video-") as tmp:
            concat_path = write_concat_inputs(images, Path(tmp), args.duration)
            run_ffmpeg(ffmpeg, concat_path, out_path, duration=args.duration, fps=args.fps)
        probe_video(ffmpeg, out_path)
    except Exception as exc:
        print(f"assemble_video failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Wrote {out_path} from {len(frame_paths)} frames at "
        f"{target_size[0]}x{target_size[1]}, {args.fps} fps, "
        f"{args.duration:g}s, encoder={ffmpeg_source}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
