#!/usr/bin/env python3
"""Fetch public GitHub contribution-calendar data and save it as JSON."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("GH_PROFILE_USER", "").strip()
if not USERNAME:
    raise SystemExit("GH_PROFILE_USER is required.")

URL = f"https://github.com/users/{USERNAME}/contributions"
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"


def fetch_days() -> list[dict[str, object]]:
    response = requests.get(
        URL,
        headers={
            "User-Agent": "github-profile-contribution-heatmap/1.0",
            "Accept": "text/html,application/xhtml+xml",
        },
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    cells = soup.select("td.ContributionCalendar-day[data-date]")

    if not cells:
        print(
            "No contribution-calendar cells were found. "
            "GitHub may have changed its HTML markup.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    days: list[dict[str, object]] = []

    for cell in cells:
        date = cell.get("data-date")
        if not date:
            continue

        count = 0
        cell_id = cell.get("id")
        tooltip = soup.find("tool-tip", attrs={"for": cell_id}) if cell_id else None
        tooltip_text = tooltip.get_text(" ", strip=True) if tooltip else ""

        match = re.search(r"([\d,]+)\s+contribution", tooltip_text, re.IGNORECASE)
        if match:
            count = int(match.group(1).replace(",", ""))

        days.append({"date": date, "count": count})

    days.sort(key=lambda item: str(item["date"]))
    return days


def calculate_stats(days: list[dict[str, object]]) -> dict[str, object]:
    total = sum(int(day["count"]) for day in days)
    active_days = sum(1 for day in days if int(day["count"]) > 0)
    best_day = max(days, key=lambda day: int(day["count"]))

    longest = 0
    current_run = 0
    for day in days:
        if int(day["count"]) > 0:
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 0

    index = len(days) - 1
    if index >= 0 and int(days[index]["count"]) == 0:
        index -= 1

    current = 0
    while index >= 0 and int(days[index]["count"]) > 0:
        current += 1
        index -= 1

    return {
        "username": USERNAME,
        "generated_at": dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "range": {
            "start": days[0]["date"],
            "end": days[-1]["date"],
        },
        "total_contributions": total,
        "active_days": active_days,
        "current_streak": current,
        "longest_streak": longest,
        "best_day": best_day,
        "days": days,
    }


def main() -> None:
    days = fetch_days()
    data = calculate_stats(days)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(
        f"Wrote {OUTPUT}: {data['total_contributions']} contributions, "
        f"current streak {data['current_streak']} days."
    )


if __name__ == "__main__":
    main()
