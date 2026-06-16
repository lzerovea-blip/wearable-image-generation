#!/usr/bin/env python3
"""Verify geometry-locked Swiper frames against a reference crop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageChops


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def parse_box(value: str) -> tuple[int, int, int, int]:
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("--clear-box must look like 'x,y,w,h'")
    x, y, width, height = parts
    if width <= 0 or height <= 0:
        raise ValueError("--clear-box width and height must be positive")
    return x, y, width, height


def find_frames(frames_dir: Path) -> list[Path]:
    frames = [
        path
        for path in sorted(frames_dir.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if len(frames) < 3:
        raise ValueError("verification requires at least 3 frames")
    return frames


def mask_clear_box(image: Image.Image, clear_box: tuple[int, int, int, int]) -> Image.Image:
    masked = image.copy()
    x, y, width, height = clear_box
    masked.paste((0, 0, 0, 0), (x, y, x + width, y + height))
    return masked


def differs_outside_clear_box(
    reference: Image.Image,
    frame: Image.Image,
    clear_box: tuple[int, int, int, int],
) -> bool:
    reference_masked = mask_clear_box(reference, clear_box)
    frame_masked = mask_clear_box(frame, clear_box)
    return ImageChops.difference(reference_masked, frame_masked).getbbox() is not None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check that Swiper component frames match the reference size and do not "
            "change pixels outside the measured focus redraw box."
        )
    )
    parser.add_argument("--reference", required=True, help="Reference component crop.")
    parser.add_argument("--frames", required=True, help="Directory containing frames.")
    parser.add_argument("--clear-box", required=True, help="Allowed redraw box, as 'x,y,w,h'.")
    parser.add_argument("--expected-count", type=int, help="Expected number of frames.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        reference = Image.open(args.reference).convert("RGBA")
        clear_box = parse_box(args.clear_box)
        frame_paths = find_frames(Path(args.frames))

        if args.expected_count is not None and len(frame_paths) != args.expected_count:
            raise ValueError(
                f"frame count {len(frame_paths)} != expected {args.expected_count}"
            )

        for path in frame_paths:
            frame = Image.open(path).convert("RGBA")
            if frame.size != reference.size:
                raise ValueError(
                    f"{path} size {frame.size} != reference size {reference.size}"
                )
            if differs_outside_clear_box(reference, frame, clear_box):
                raise ValueError(f"{path} changed pixels outside clear-box {clear_box}")
    except Exception as exc:
        print(f"verify_swiper_geometry failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Verified {len(frame_paths)} frames at {reference.width}x{reference.height}; "
        f"only clear-box {clear_box} changed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
