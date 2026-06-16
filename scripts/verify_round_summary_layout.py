#!/usr/bin/env python3
"""Verify round wearable summary-card boxes stay inside the circular safe area."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image


def parse_boxes(value: str) -> list[tuple[float, float, float, float]]:
    boxes: list[tuple[float, float, float, float]] = []
    for item in value.split(";"):
        item = item.strip()
        if not item:
            continue
        parts = [float(part.strip()) for part in item.split(",")]
        if len(parts) != 4:
            raise ValueError("--boxes must look like 'x,y,w,h;x,y,w,h;...'")
        x, y, width, height = parts
        if width <= 0 or height <= 0:
            raise ValueError("box width and height must be positive")
        boxes.append((x, y, width, height))
    if not boxes:
        raise ValueError("--boxes requires at least one box")
    return boxes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check measured summary-card boxes against an inscribed circular screen. "
            "Use this after imagegen creates a round wearable detail final frame."
        )
    )
    parser.add_argument("--image", required=True, help="Round wearable PNG frame to check.")
    parser.add_argument(
        "--boxes",
        required=True,
        help="Measured summary item/card boxes as 'x,y,w,h;x,y,w,h;x,y,w,h'.",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=3,
        help="Expected number of summary boxes. Defaults to 3.",
    )
    parser.add_argument(
        "--reference-vp",
        type=float,
        default=466,
        help="Reference wearable screenshot size in vp used to convert vp to pixels. Defaults to 466.",
    )
    parser.add_argument(
        "--safe-bottom-vp",
        type=float,
        default=6,
        help="Bottom safety distance in vp. Defaults to 6.",
    )
    parser.add_argument(
        "--safe-top-vp",
        type=float,
        default=20,
        help="Top safety distance in vp used for total-height checks. Defaults to 20.",
    )
    parser.add_argument(
        "--extra-bottom-px",
        type=float,
        default=0,
        help="Extra pixel safety distance added to the bottom vp safety. Defaults to 0.",
    )
    parser.add_argument(
        "--max-total-height-ratio",
        type=float,
        default=1.0,
        help="Maximum summary stack height as a ratio of top/bottom safe area. Defaults to 1.0.",
    )
    return parser.parse_args()


def circle_bottom_y(width: int, height: int, x: float) -> float:
    radius = min(width, height) / 2
    center_x = (width - 1) / 2
    center_y = (height - 1) / 2
    dx = x - center_x
    if abs(dx) > radius:
        return -math.inf
    return center_y + math.sqrt(max(0, radius * radius - dx * dx))


def min_bottom_y_for_box(width: int, height: int, x1: float, x2: float) -> float:
    samples = [
        x1,
        x2,
        (x1 + x2) / 2,
        x1 + (x2 - x1) * 0.25,
        x1 + (x2 - x1) * 0.75,
    ]
    return min(circle_bottom_y(width, height, x) for x in samples)


def verify(image: Image.Image, boxes: list[tuple[float, float, float, float]], args: argparse.Namespace) -> list[str]:
    width, height = image.size
    scale = min(width, height) / args.reference_vp
    bottom_safe_px = args.safe_bottom_vp * scale + args.extra_bottom_px
    top_safe_px = args.safe_top_vp * scale
    failures: list[str] = []

    if args.expected_count > 0 and len(boxes) != args.expected_count:
        failures.append(f"expected {args.expected_count} summary boxes, got {len(boxes)}")

    stack_top = min(y for _, y, _, _ in boxes)
    stack_bottom = max(y + box_height for _, y, _, box_height in boxes)
    max_stack_height = (min(width, height) - top_safe_px - bottom_safe_px) * args.max_total_height_ratio
    stack_height = stack_bottom - stack_top
    if stack_height > max_stack_height:
        failures.append(
            f"summary stack height {stack_height:.1f}px exceeds allowed {max_stack_height:.1f}px"
        )

    for index, (x, y, box_width, box_height) in enumerate(boxes, start=1):
        x1, x2 = x, x + box_width
        y2 = y + box_height
        allowed_bottom = min_bottom_y_for_box(width, height, x1, x2) - bottom_safe_px
        if y2 > allowed_bottom:
            failures.append(
                f"box {index} bottom {y2:.1f}px exceeds circular safe bottom "
                f"{allowed_bottom:.1f}px by {y2 - allowed_bottom:.1f}px"
            )

    return failures


def main() -> int:
    args = parse_args()
    try:
        image = Image.open(Path(args.image)).convert("RGBA")
        boxes = parse_boxes(args.boxes)
        failures = verify(image, boxes, args)
    except Exception as exc:
        print(f"verify_round_summary_layout failed: {exc}", file=sys.stderr)
        return 1

    if failures:
        print("Round summary layout check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(
        f"Round summary layout check passed: {len(boxes)} boxes inside circular safe area "
        f"for {image.width}x{image.height}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
