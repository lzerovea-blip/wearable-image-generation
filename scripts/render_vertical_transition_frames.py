#!/usr/bin/env python3
"""Render deterministic vertical slide transition frames between two UI screens."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a visible vertical slide transition: the first screen moves upward "
            "and the final screen enters from the bottom."
        )
    )
    parser.add_argument("--first", required=True, help="First/home frame PNG.")
    parser.add_argument("--final", required=True, help="Final/detail frame PNG.")
    parser.add_argument("--out", required=True, help="Output frames directory.")
    parser.add_argument(
        "--frame-count",
        type=int,
        default=9,
        help="Number of frames to render. Use 8-12 for swipe animations. Defaults to 9.",
    )
    parser.add_argument(
        "--round-mask",
        action="store_true",
        help="Apply an inscribed circular alpha mask to every output frame.",
    )
    return parser.parse_args()


def circle_mask(size: tuple[int, int], *, scale: int = 4) -> Image.Image:
    width, height = size
    mask = Image.new("L", (width * scale, height * scale), 0)
    draw = ImageDraw.Draw(mask)
    radius = min(width, height) / 2
    center = ((width - 1) / 2, (height - 1) / 2)
    box = (
        (center[0] - radius) * scale,
        (center[1] - radius) * scale,
        (center[0] + radius) * scale,
        (center[1] + radius) * scale,
    )
    draw.ellipse(box, fill=255)
    return mask.resize(size, Image.Resampling.LANCZOS)


def apply_mask(image: Image.Image, mask: Image.Image) -> Image.Image:
    output = image.convert("RGBA")
    original_alpha = output.getchannel("A")
    masked_alpha = Image.new("L", output.size, 0)
    masked_alpha = Image.composite(original_alpha, masked_alpha, mask)
    output.putalpha(masked_alpha)
    return output


def paste_with_alpha(canvas: Image.Image, source: Image.Image, xy: tuple[int, int]) -> None:
    canvas.alpha_composite(source, dest=xy)


def render_frame(
    first: Image.Image,
    final: Image.Image,
    progress: float,
    *,
    mask: Image.Image | None,
) -> Image.Image:
    width, height = first.size
    canvas = Image.new("RGBA", first.size, (0, 0, 0, 0))
    first_y = round(-progress * height)
    final_y = round((1 - progress) * height)
    paste_with_alpha(canvas, first, (0, first_y))
    paste_with_alpha(canvas, final, (0, final_y))
    if mask is not None:
        canvas = apply_mask(canvas, mask)
    return canvas


def main() -> int:
    args = parse_args()
    first_path = Path(args.first)
    final_path = Path(args.final)
    out_dir = Path(args.out)

    try:
        if args.frame_count < 3:
            raise ValueError("--frame-count must be at least 3")
        first = Image.open(first_path).convert("RGBA")
        final = Image.open(final_path).convert("RGBA")
        if first.size != final.size:
            raise ValueError(f"frame size mismatch: first {first.size}, final {final.size}")

        mask = circle_mask(first.size) if args.round_mask else None
        out_dir.mkdir(parents=True, exist_ok=True)
        for index in range(args.frame_count):
            progress = index / (args.frame_count - 1)
            frame = render_frame(first, final, progress, mask=mask)
            if index == 0:
                name = "001-first.png"
            elif index == args.frame_count - 1:
                name = f"{args.frame_count:03d}-final.png"
            else:
                name = f"{index + 1:03d}-slide.png"
            frame.save(out_dir / name, format="PNG")
    except Exception as exc:
        print(f"render_vertical_transition_frames failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.frame_count} vertical slide frames to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
