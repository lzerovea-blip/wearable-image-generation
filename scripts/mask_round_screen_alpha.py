#!/usr/bin/env python3
"""Apply a circular alpha mask to a round wearable screen PNG."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def parse_pair(value: str, *, name: str) -> tuple[float, float]:
    try:
        left, right = value.split(",", 1)
        return float(left), float(right)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{name} must be formatted as x,y") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set pixels outside a circular round-screen boundary to alpha=0."
    )
    parser.add_argument("--input", required=True, help="Input PNG from imagegen or a normalized frame.")
    parser.add_argument("--out", required=True, help="Output PNG with transparent round-screen exterior.")
    parser.add_argument(
        "--mode",
        choices=("inscribed-circle",),
        default="inscribed-circle",
        help="Use the largest circle inscribed in the image canvas. Defaults to inscribed-circle.",
    )
    parser.add_argument(
        "--center",
        type=lambda value: parse_pair(value, name="center"),
        help="Optional circle center as x,y. Defaults to the image center.",
    )
    parser.add_argument(
        "--radius",
        type=float,
        help="Optional circle radius in pixels. Defaults to min(width, height) / 2.",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=0,
        help="Pixels to subtract from the radius when the generated circle touches the canvas edge.",
    )
    return parser.parse_args()


def make_circle_mask(
    size: tuple[int, int],
    center: tuple[float, float],
    radius: float,
    *,
    scale: int = 4,
) -> Image.Image:
    width, height = size
    mask = Image.new("L", (width * scale, height * scale), 0)
    draw = ImageDraw.Draw(mask)
    cx, cy = center
    box = (
        (cx - radius) * scale,
        (cy - radius) * scale,
        (cx + radius) * scale,
        (cy + radius) * scale,
    )
    draw.ellipse(box, fill=255)
    return mask.resize(size, Image.Resampling.LANCZOS)


def corner_alpha_is_zero(image: Image.Image) -> bool:
    alpha = image.getchannel("A")
    width, height = image.size
    corners = (
        alpha.getpixel((0, 0)),
        alpha.getpixel((width - 1, 0)),
        alpha.getpixel((0, height - 1)),
        alpha.getpixel((width - 1, height - 1)),
    )
    return all(value == 0 for value in corners)


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    out_path = Path(args.out)

    try:
        image = Image.open(input_path).convert("RGBA")
        width, height = image.size
        center = args.center or ((width - 1) / 2, (height - 1) / 2)
        radius = args.radius if args.radius is not None else min(width, height) / 2
        radius = radius - args.padding
        if radius <= 0:
            raise ValueError("circle radius must be positive after padding")

        circle_alpha = make_circle_mask(image.size, center, radius)
        original_alpha = image.getchannel("A")
        masked_alpha = Image.new("L", image.size, 0)
        masked_alpha = Image.composite(original_alpha, masked_alpha, circle_alpha)
        image.putalpha(masked_alpha)

        if not corner_alpha_is_zero(image):
            raise ValueError("corner alpha check failed; expected all four corners to be 0")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(out_path, format="PNG")
    except Exception as exc:
        print(f"mask_round_screen_alpha failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {out_path} with transparent round-screen exterior ({width}x{height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
