#!/usr/bin/env python3
"""Render deterministic vertical slide transition frames between two UI screens."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw


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
    parser.add_argument(
        "--nav-centers",
        help="Optional Swiper dot centers for an overlay, for example '1180,540;1180,590;1180,640'.",
    )
    parser.add_argument(
        "--nav-clear-box",
        help="Optional tight redraw box for the navigation overlay, as 'x,y,w,h'.",
    )
    parser.add_argument(
        "--nav-active-from",
        type=int,
        default=0,
        help="Active nav index before the page switch. Defaults to 0.",
    )
    parser.add_argument(
        "--nav-active-to",
        type=int,
        help="Active nav index after the page switch. Defaults to the last center.",
    )
    parser.add_argument(
        "--nav-switch-progress",
        type=float,
        default=0.5,
        help="Progress where the active nav focus switches. Defaults to 0.5.",
    )
    parser.add_argument(
        "--nav-fade-window",
        type=float,
        default=0.3,
        help="Progress width used to cross-fade active nav focus. Defaults to 0.3.",
    )
    parser.add_argument(
        "--nav-dot-radius",
        type=float,
        default=4,
        help="Inactive nav dot radius in pixels. Defaults to 4.",
    )
    parser.add_argument(
        "--nav-focus-size",
        default="8x22",
        help="Active nav focus pill size, as WIDTHxHEIGHT. Defaults to 8x22.",
    )
    parser.add_argument(
        "--nav-active-color",
        default="#007DFF",
        help="Active nav focus color. Defaults to #007DFF.",
    )
    parser.add_argument(
        "--nav-inactive-color",
        default="#C7CCD8A0",
        help="Inactive nav dot color. Defaults to #C7CCD8A0.",
    )
    parser.add_argument(
        "--nav-background-color",
        help="Optional background color for the nav redraw box. Defaults to sampled frame background.",
    )
    return parser.parse_args()


def parse_pair_list(value: str) -> list[tuple[float, float]]:
    pairs: list[tuple[float, float]] = []
    for item in value.split(";"):
        item = item.strip()
        if not item:
            continue
        parts = item.split(",", 1)
        if len(parts) != 2:
            raise ValueError("--nav-centers must look like 'x,y;x,y;...'")
        pairs.append((float(parts[0]), float(parts[1])))
    if len(pairs) < 2:
        raise ValueError("--nav-centers requires at least 2 points")
    return pairs


def parse_box(value: str) -> tuple[int, int, int, int]:
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("--nav-clear-box must look like 'x,y,w,h'")
    x, y, width, height = parts
    if width <= 0 or height <= 0:
        raise ValueError("--nav-clear-box width and height must be positive")
    return x, y, width, height


def parse_size(value: str) -> tuple[float, float]:
    parts = value.lower().split("x", 1)
    if len(parts) != 2:
        raise ValueError("--nav-focus-size must look like WIDTHxHEIGHT")
    width, height = float(parts[0]), float(parts[1])
    if width <= 0 or height <= 0:
        raise ValueError("--nav-focus-size width and height must be positive")
    return width, height


def parse_color(value: str) -> tuple[int, int, int, int]:
    return ImageColor.getcolor(value, "RGBA")


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


def sampled_background(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x, y, width, height = box
    samples: list[tuple[int, int, int, int]] = []
    for px in range(max(0, x - 2), min(image.width, x + width + 2)):
        for py in (max(0, y - 2), min(image.height - 1, y + height + 1)):
            samples.append(image.getpixel((px, py)))
    for py in range(max(0, y - 2), min(image.height, y + height + 2)):
        for px in (max(0, x - 2), min(image.width - 1, x + width + 1)):
            samples.append(image.getpixel((px, py)))
    if not samples:
        return (0, 0, 0, 0)
    channels = []
    for channel in range(4):
        ordered = sorted(sample[channel] for sample in samples)
        channels.append(ordered[len(ordered) // 2])
    return tuple(channels)  # type: ignore[return-value]


def active_focus_alphas(progress: float, switch_progress: float, fade_window: float) -> tuple[int, int]:
    if fade_window <= 0:
        return (0, 255) if progress >= switch_progress else (255, 0)

    start = max(0.0, switch_progress - fade_window / 2)
    end = min(1.0, switch_progress + fade_window / 2)
    if progress <= start:
        return 255, 0
    if progress >= end:
        return 0, 255
    ratio = (progress - start) / max(end - start, 1e-6)
    return round(255 * (1 - ratio)), round(255 * ratio)


def with_alpha(color: tuple[int, int, int, int], alpha: int) -> tuple[int, int, int, int]:
    return color[0], color[1], color[2], round(color[3] * max(0, min(alpha, 255)) / 255)


def draw_nav_overlay(
    frame: Image.Image,
    *,
    progress: float,
    centers: list[tuple[float, float]],
    clear_box: tuple[int, int, int, int],
    active_from: int,
    active_to: int,
    switch_progress: float,
    fade_window: float,
    dot_radius: float,
    focus_size: tuple[float, float],
    active_color: tuple[int, int, int, int],
    inactive_color: tuple[int, int, int, int],
    background_color: tuple[int, int, int, int] | None,
) -> Image.Image:
    output = frame.copy()
    draw = ImageDraw.Draw(output, "RGBA")
    x, y, width, height = clear_box
    fill = background_color if background_color is not None else sampled_background(output, clear_box)
    draw.rectangle((x, y, x + width, y + height), fill=fill)

    for cx, cy in centers:
        draw.ellipse(
            (cx - dot_radius, cy - dot_radius, cx + dot_radius, cy + dot_radius),
            fill=inactive_color,
        )

    from_alpha, to_alpha = active_focus_alphas(progress, switch_progress, fade_window)
    focus_width, focus_height = focus_size
    radius = min(focus_width, focus_height) / 2
    for active_index, alpha in ((active_from, from_alpha), (active_to, to_alpha)):
        if alpha <= 0:
            continue
        cx, cy = centers[active_index]
        draw.rounded_rectangle(
            (
                cx - focus_width / 2,
                cy - focus_height / 2,
                cx + focus_width / 2,
                cy + focus_height / 2,
            ),
            radius=radius,
            fill=with_alpha(active_color, alpha),
        )
    return output


def render_frame(
    first: Image.Image,
    final: Image.Image,
    progress: float,
    *,
    mask: Image.Image | None,
    nav_options: dict[str, object] | None,
) -> Image.Image:
    width, height = first.size
    canvas = Image.new("RGBA", first.size, (0, 0, 0, 0))
    first_y = round(-progress * height)
    final_y = round((1 - progress) * height)
    paste_with_alpha(canvas, first, (0, first_y))
    paste_with_alpha(canvas, final, (0, final_y))
    if nav_options is not None:
        canvas = draw_nav_overlay(canvas, progress=progress, **nav_options)
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

        nav_options: dict[str, object] | None = None
        if args.nav_centers or args.nav_clear_box:
            if not args.nav_centers or not args.nav_clear_box:
                raise ValueError("--nav-centers and --nav-clear-box must be provided together")
            centers = parse_pair_list(args.nav_centers)
            active_to = args.nav_active_to if args.nav_active_to is not None else len(centers) - 1
            if args.nav_active_from < 0 or args.nav_active_from >= len(centers):
                raise ValueError("--nav-active-from is outside the nav centers range")
            if active_to < 0 or active_to >= len(centers):
                raise ValueError("--nav-active-to is outside the nav centers range")
            if args.nav_switch_progress < 0 or args.nav_switch_progress > 1:
                raise ValueError("--nav-switch-progress must be between 0 and 1")
            if args.nav_fade_window < 0 or args.nav_fade_window > 1:
                raise ValueError("--nav-fade-window must be between 0 and 1")
            nav_options = {
                "centers": centers,
                "clear_box": parse_box(args.nav_clear_box),
                "active_from": args.nav_active_from,
                "active_to": active_to,
                "switch_progress": args.nav_switch_progress,
                "fade_window": args.nav_fade_window,
                "dot_radius": args.nav_dot_radius,
                "focus_size": parse_size(args.nav_focus_size),
                "active_color": parse_color(args.nav_active_color),
                "inactive_color": parse_color(args.nav_inactive_color),
                "background_color": (
                    parse_color(args.nav_background_color)
                    if args.nav_background_color
                    else None
                ),
            }

        mask = circle_mask(first.size) if args.round_mask else None
        out_dir.mkdir(parents=True, exist_ok=True)
        for index in range(args.frame_count):
            progress = index / (args.frame_count - 1)
            frame = render_frame(first, final, progress, mask=mask, nav_options=nav_options)
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
