#!/usr/bin/env python3
"""Render geometry-locked Swiper focus frames from a reference crop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw


def parse_pair_list(value: str) -> list[tuple[float, float]]:
    pairs: list[tuple[float, float]] = []
    for item in value.split(";"):
        item = item.strip()
        if not item:
            continue
        parts = item.split(",", 1)
        if len(parts) != 2:
            raise ValueError("--centers must look like 'x,y;x,y;...'")
        pairs.append((float(parts[0]), float(parts[1])))
    if len(pairs) < 2:
        raise ValueError("--centers requires at least 2 points")
    return pairs


def parse_int_sequence(value: str, count: int) -> list[int]:
    indexes = [int(item.strip()) for item in value.split(",") if item.strip()]
    if len(indexes) < 3:
        raise ValueError("--active-sequence requires at least 3 indexes")
    for index in indexes:
        if index < 0 or index >= count:
            raise ValueError(f"active index {index} is outside 0..{count - 1}")
    return indexes


def parse_box(value: str) -> tuple[int, int, int, int]:
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("--clear-box must look like 'x,y,w,h'")
    x, y, width, height = parts
    if width <= 0 or height <= 0:
        raise ValueError("--clear-box width and height must be positive")
    return x, y, width, height


def parse_size(value: str) -> tuple[float, float]:
    parts = value.lower().split("x", 1)
    if len(parts) != 2:
        raise ValueError("--focus-size must look like WIDTHxHEIGHT")
    width, height = float(parts[0]), float(parts[1])
    if width <= 0 or height <= 0:
        raise ValueError("--focus-size width and height must be positive")
    return width, height


def parse_color(value: str) -> tuple[int, int, int, int]:
    return ImageColor.getcolor(value, "RGBA")


def sampled_background(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x, y, width, height = box
    samples: list[tuple[int, int, int, int]] = []
    for px in range(max(0, x - 1), min(image.width, x + width + 1)):
        for py in (max(0, y - 1), min(image.height - 1, y + height)):
            samples.append(image.getpixel((px, py)))
    for py in range(max(0, y - 1), min(image.height, y + height + 1)):
        for px in (max(0, x - 1), min(image.width - 1, x + width)):
            samples.append(image.getpixel((px, py)))
    if not samples:
        return (255, 255, 255, 255)
    channels = []
    for channel in range(4):
        ordered = sorted(sample[channel] for sample in samples)
        channels.append(ordered[len(ordered) // 2])
    return tuple(channels)  # type: ignore[return-value]


def draw_frame(
    base: Image.Image,
    clear_box: tuple[int, int, int, int],
    centers: list[tuple[float, float]],
    active_index: int,
    dot_radius: float,
    focus_size: tuple[float, float],
    inactive_color: tuple[int, int, int, int],
    active_color: tuple[int, int, int, int],
    background_color: tuple[int, int, int, int],
) -> Image.Image:
    frame = base.copy()
    draw = ImageDraw.Draw(frame)
    x, y, width, height = clear_box
    draw.rectangle((x, y, x + width, y + height), fill=background_color)

    for cx, cy in centers:
        draw.ellipse(
            (cx - dot_radius, cy - dot_radius, cx + dot_radius, cy + dot_radius),
            fill=inactive_color,
        )

    cx, cy = centers[active_index]
    focus_width, focus_height = focus_size
    radius = min(focus_width, focus_height) / 2
    draw.rounded_rectangle(
        (
            cx - focus_width / 2,
            cy - focus_height / 2,
            cx + focus_width / 2,
            cy + focus_height / 2,
        ),
        radius=radius,
        fill=active_color,
    )
    return frame


def frame_name(position: int, total: int) -> str:
    if position == 1:
        suffix = "first"
    elif position == total:
        suffix = "final"
    else:
        suffix = "middle"
    return f"{position:03d}-{suffix}.png"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy a reference component crop into multiple frames and only redraw "
            "a measured Swiper focus state inside a tight clear box."
        )
    )
    parser.add_argument("--input", required=True, help="Reference crop used as the frame base.")
    parser.add_argument("--out", required=True, help="Output frames directory.")
    parser.add_argument("--centers", required=True, help="Dot centers, for example '20,8;20,18;20,28'.")
    parser.add_argument("--active-sequence", required=True, help="Comma-separated active indexes.")
    parser.add_argument("--clear-box", required=True, help="Tight redraw box, as 'x,y,w,h'.")
    parser.add_argument("--dot-radius", type=float, required=True, help="Inactive dot radius in pixels.")
    parser.add_argument("--focus-size", required=True, help="Active focus pill size, as WIDTHxHEIGHT.")
    parser.add_argument("--active-color", default="#007DFF", help="Active focus color.")
    parser.add_argument("--inactive-color", default="#C7CCD8", help="Inactive dot color.")
    parser.add_argument("--background-color", help="Optional redraw background color.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        base = Image.open(args.input).convert("RGBA")
        centers = parse_pair_list(args.centers)
        sequence = parse_int_sequence(args.active_sequence, len(centers))
        clear_box = parse_box(args.clear_box)
        focus_size = parse_size(args.focus_size)
        active_color = parse_color(args.active_color)
        inactive_color = parse_color(args.inactive_color)
        background_color = (
            parse_color(args.background_color)
            if args.background_color
            else sampled_background(base, clear_box)
        )

        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        for existing in out_dir.glob("*.png"):
            existing.unlink()

        for position, active_index in enumerate(sequence, start=1):
            frame = draw_frame(
                base,
                clear_box,
                centers,
                active_index,
                args.dot_radius,
                focus_size,
                inactive_color,
                active_color,
                background_color,
            )
            if frame.size != base.size:
                raise ValueError(f"frame size {frame.size} drifted from reference {base.size}")
            frame.save(out_dir / frame_name(position, len(sequence)))
    except Exception as exc:
        print(f"render_swiper_focus_frames failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {len(sequence)} frames to {args.out} at {base.width}x{base.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
