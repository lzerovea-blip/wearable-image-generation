#!/usr/bin/env python3
"""Assemble image frames into a validated animated GIF."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble PNG/JPG frames into an animated GIF."
    )
    parser.add_argument("--frames", required=True, help="Directory containing frames.")
    parser.add_argument("--out", required=True, help="Output GIF path.")
    parser.add_argument(
        "--duration",
        type=float,
        default=4.0,
        help="Total animation duration in seconds. Defaults to 4.",
    )
    return parser.parse_args()


def find_frames(frames_dir: Path) -> list[Path]:
    if not frames_dir.is_dir():
        raise ValueError(f"frames directory does not exist: {frames_dir}")

    frames = [
        path
        for path in sorted(frames_dir.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if len(frames) < 3:
        raise ValueError("animation requires at least 3 PNG/JPG frames")
    return frames


def load_frames(paths: list[Path]) -> list[Image.Image]:
    images: list[Image.Image] = []
    expected_size: tuple[int, int] | None = None

    for path in paths:
        try:
            image = Image.open(path).convert("RGBA")
        except Exception as exc:  # pragma: no cover - message is surfaced to CLI users
            raise ValueError(f"failed to read frame {path}: {exc}") from exc

        if expected_size is None:
            expected_size = image.size
        elif image.size != expected_size:
            raise ValueError(
                f"frame size mismatch: {path} is {image.size}, expected {expected_size}"
            )
        images.append(image)

    return images


def save_gif(images: list[Image.Image], out_path: Path, total_seconds: float) -> None:
    if total_seconds < 3 or total_seconds > 5:
        raise ValueError("duration must be between 3 and 5 seconds")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame_duration_ms = max(1, round(total_seconds * 1000 / len(images)))
    first, rest = images[0], images[1:]
    first.save(
        out_path,
        save_all=True,
        append_images=rest,
        duration=frame_duration_ms,
        loop=0,
        disposal=2,
        optimize=False,
    )


def validate_gif(path: Path) -> None:
    with Image.open(path) as image:
        frame_count = getattr(image, "n_frames", 1)
        if frame_count < 3:
            raise ValueError(f"output is not a valid multi-frame GIF: {frame_count} frame")


def main() -> int:
    args = parse_args()
    frames_dir = Path(args.frames)
    out_path = Path(args.out)

    try:
        frame_paths = find_frames(frames_dir)
        images = load_frames(frame_paths)
        save_gif(images, out_path, args.duration)
        validate_gif(out_path)
    except Exception as exc:
        print(f"assemble_animation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {out_path} from {len(frame_paths)} frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
