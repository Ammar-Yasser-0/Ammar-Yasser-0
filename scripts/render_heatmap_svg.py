#!/usr/bin/env python3
"""Render contribution JSON as a self-contained animated SVG."""

from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "data" / "contributions.json"
OUTPUT = ROOT / "contrib-heatmap.svg"

CELL = 12
GAP = 3
STEP = CELL + GAP
PADDING = 22
LEFT_LABEL = 30
TOP_LABEL = 20
TITLE_BAR = 30

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
BACKGROUND_TOP = "#0d1420"
BACKGROUND_BOTTOM = "#0a0e14"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#58a6ff"
GREEN = "#39d353"
GOLD = "#d29922"


def contribution_level(count: int, maximum: int) -> int:
    if count <= 0 or maximum <= 0:
        return 0

    ratio = count / maximum
    if ratio <= 0.25:
        return 1
    if ratio <= 0.50:
        return 2
    if ratio <= 0.75:
        return 3
    return 4


def build_grid(days: list[dict[str, object]]) -> list[list[dict[str, object] | None]]:
    first_date = dt.date.fromisoformat(str(days[0]["date"]))
    leading_blanks = (first_date.weekday() + 1) % 7  # Sunday is row zero.

    grid: list[list[dict[str, object] | None]] = []
    column: list[dict[str, object] | None] = [None] * leading_blanks

    for day in days:
        date = dt.date.fromisoformat(str(day["date"]))
        weekday = (date.weekday() + 1) % 7

        while len(column) < weekday:
            column.append(None)

        column.append(day)

        if len(column) == 7:
            grid.append(column)
            column = []

    if column:
        column.extend([None] * (7 - len(column)))
        grid.append(column)

    return grid


def render(data: dict[str, object]) -> str:
    days = list(data["days"])
    grid = build_grid(days)
    max_count = max(int(day["count"]) for day in days)

    columns = len(grid)
    grid_width = columns * STEP
    grid_height = 7 * STEP
    width = PADDING + LEFT_LABEL + grid_width + PADDING
    stats_height = 88
    height = TITLE_BAR + TOP_LABEL + grid_height + stats_height + PADDING

    grid_left = PADDING + LEFT_LABEL
    grid_top = TITLE_BAR + TOP_LABEL

    month_labels: list[tuple[int, str]] = []
    seen_months: set[tuple[int, int]] = set()

    for column_index, column in enumerate(grid):
        for cell in column:
            if cell is None:
                continue

            date = dt.date.fromisoformat(str(cell["date"]))
            month_key = (date.year, date.month)

            if month_key not in seen_months and date.day <= 7:
                seen_months.add(month_key)
                month_labels.append((column_index, date.strftime("%b")))
            break

    css = """
@keyframes reveal {
  from { opacity: 0; transform: translateY(-7px); }
  to   { opacity: 1; transform: translateY(0); }
}
.cell {
  opacity: 0;
  animation: reveal 0.42s cubic-bezier(.2,.8,.2,1) both;
}
@media (prefers-reduced-motion: reduce) {
  .cell { opacity: 1; animation: none; }
}
""".strip()

    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" '
            'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" '
            'role="img" aria-labelledby="title description">'
        ),
        f"<title id=\"title\">{html.escape(str(data['username']))}'s GitHub contribution heatmap</title>",
        (
            f'<desc id="description">{int(data["total_contributions"]):,} contributions '
            f'from {html.escape(str(data["range"]["start"]))} '
            f'to {html.escape(str(data["range"]["end"]))}.</desc>'
        ),
        f"<style>{css}</style>",
        "<defs>",
        '<linearGradient id="background" x1="0" y1="0" x2="0" y2="1">',
        f'<stop offset="0" stop-color="{BACKGROUND_TOP}"/>',
        f'<stop offset="1" stop-color="{BACKGROUND_BOTTOM}"/>',
        "</linearGradient>",
        "</defs>",
        f'<rect width="{width}" height="{height}" rx="12" fill="url(#background)"/>',
        (
            f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" '
            f'rx="12" fill="none" stroke="{BORDER}"/>'
        ),
        (
            f'<line x1="0" y1="{TITLE_BAR}" x2="{width}" y2="{TITLE_BAR}" '
            f'stroke="{BORDER}"/>'
        ),
    ]

    for index, color in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        parts.append(
            f'<circle cx="{PADDING + index * 16}" cy="{TITLE_BAR / 2}" '
            f'r="5" fill="{color}"/>'
        )

    username = html.escape(str(data["username"]))
    parts.append(
        f'<text x="{width / 2}" y="{TITLE_BAR / 2 + 4}" fill="{MUTED}" '
        f'font-size="12" text-anchor="middle">{username}@github: ~/contributions</text>'
    )

    for column_index, label in month_labels:
        x = grid_left + column_index * STEP
        parts.append(
            f'<text x="{x}" y="{TITLE_BAR + 14}" fill="{MUTED}" '
            f'font-size="10">{label}</text>'
        )

    for row_index, weekday_name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = grid_top + row_index * STEP + CELL * 0.78
        parts.append(
            f'<text x="{PADDING}" y="{y:.1f}" fill="{MUTED}" '
            f'font-size="9">{weekday_name}</text>'
        )

    for column_index, column in enumerate(grid):
        x = grid_left + column_index * STEP

        for row_index, cell in enumerate(column):
            if cell is None:
                continue

            count = int(cell["count"])
            level = contribution_level(count, max_count)
            y = grid_top + row_index * STEP
            delay = column_index * 0.018 + row_index * 0.045
            date_text = html.escape(str(cell["date"]))
            noun = "contribution" if count == 1 else "contributions"

            parts.append(
                f'<rect class="cell" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2.5" fill="{PALETTE[level]}" '
                f'style="animation-delay:{delay:.3f}s">'
                f"<title>{date_text}: {count} {noun}</title>"
                "</rect>"
            )

    legend_y = grid_top + grid_height + 6
    legend_x = width - PADDING - (len(PALETTE) * CELL + 54)

    parts.append(
        f'<text x="{legend_x}" y="{legend_y + CELL * 0.8:.1f}" '
        f'fill="{MUTED}" font-size="10" text-anchor="end">Less</text>'
    )

    x = legend_x + 8
    for color in PALETTE:
        parts.append(
            f'<rect x="{x}" y="{legend_y}" width="{CELL - 1}" '
            f'height="{CELL - 1}" rx="2.2" fill="{color}"/>'
        )
        x += CELL

    parts.append(
        f'<text x="{x + 4}" y="{legend_y + CELL * 0.8:.1f}" '
        f'fill="{MUTED}" font-size="10">More</text>'
    )

    separator_y = legend_y + CELL + 14
    parts.append(
        f'<line x1="0" y1="{separator_y}" x2="{width}" y2="{separator_y}" '
        f'stroke="{BORDER}"/>'
    )

    line_one_y = separator_y + 24
    total = int(data["total_contributions"])
    current_streak = int(data["current_streak"])
    longest_streak = int(data["longest_streak"])
    best_day = data["best_day"]

    parts.append(
        f'<text x="{PADDING}" y="{line_one_y}" font-size="13" fill="{GREEN}">'
        f'<tspan font-weight="700">{total:,}</tspan>'
        f'<tspan fill="{MUTED}"> contributions in the last year</tspan>'
        "</text>"
    )
    parts.append(
        f'<text x="{width - PADDING}" y="{line_one_y}" font-size="12" '
        f'fill="{MUTED}" text-anchor="end">'
        f'{html.escape(str(data["range"]["start"]))} &#8594; '
        f'{html.escape(str(data["range"]["end"]))}</text>'
    )

    line_two_y = line_one_y + 24
    parts.append(
        f'<text x="{PADDING}" y="{line_two_y}" font-size="13" fill="{MUTED}">'
        f'current streak <tspan fill="{ACCENT}" font-weight="700">'
        f'{current_streak} days</tspan>'
        f'<tspan> &#183; longest </tspan>'
        f'<tspan fill="{ACCENT}" font-weight="700">{longest_streak} days</tspan>'
        "</text>"
    )
    parts.append(
        f'<text x="{width - PADDING}" y="{line_two_y}" font-size="12" '
        f'fill="{MUTED}" text-anchor="end">best day '
        f'<tspan fill="{GOLD}" font-weight="700">{int(best_day["count"])}</tspan> '
        f'on {html.escape(str(best_day["date"]))}</text>'
    )

    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    if not INPUT.exists():
        raise SystemExit(
            f"{INPUT} does not exist. Run scripts/fetch_contributions.py first."
        )

    data = json.loads(INPUT.read_text(encoding="utf-8"))
    svg = render(data)
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(svg):,} bytes).")


if __name__ == "__main__":
    main()
