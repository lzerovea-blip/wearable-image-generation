#!/usr/bin/env python3
"""Resize or cover-crop an image to exactly match a reference image size."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize an image to the exact pixel size of a reference image."
    )
    parser.add_argument("--input", required=True, help="Image to normalize.")
    parser.add_argument("--reference", required=True, help="Reference image with target size.")
    parser.add_argument("--out", required=True, help="Output image path.")
    parser.add_argument(
        "--mode",
        choices=("resize", "cover"),
        default="resize",
        help="resize scales exactly; cover preserves aspect then center-crops. Defaults to resize.",
    )
    return parser.parse_args()


def cover_crop(image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    target_width, target_height = target_size
    scale = max(target_width / image.width, target_height / image.height)
    scaled_size = (round(image.width * scale), round(image.height * scale))
    scaled = image.resize(scaled_size, Image.Resampling.LANCZOS)
    left = max(0, (scaled.width - target_width) // 2)
    top = max(0, (scaled.height - target_height) // 2)
    return scaled.crop((left, top, left + target_width, top + target_height))


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    reference_path = Path(args.reference)
    out_path = Path(args.out)

    try:
        image = Image.open(input_path).convert("RGBA")
        reference = Image.open(reference_path)
        target_size = reference.size
        if args.mode == "cover":
            normalized = cover_crop(image, target_size)
        else:
            normalized = image.resize(target_size, Image.Resampling.LANCZOS)

        if normalized.size != target_size:
            raise ValueError(f"normalized size {normalized.size} != reference size {target_size}")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        normalized.save(out_path)
    except Exception as exc:
        print(f"normalize_to_reference failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {out_path} at {target_size[0]}x{target_size[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
