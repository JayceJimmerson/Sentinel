"""
Sentinel
Fetches asteroid close-approach data from NASA NeoWs and uses Claude
to generate a plain-English risk narrative and 1-10 risk score for each object.

Usage:
  python sentinel.py                        # next 7 days, within 5M km
  python sentinel.py --days 30              # next 30 days (chains NASA calls)
  python sentinel.py --days 14 --max-distance 2000000
  python sentinel.py --days 7 --start 2026-05-01
"""

import argparse
import os
import re
import sys
import time
from datetime import date, timedelta

import requests
import anthropic
from dotenv import load_dotenv
import db

# ── Configuration ─────────────────────────────────────────────────────────────

load_dotenv()

NASA_API_KEY      = os.getenv("NASA_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

NASA_NEO_URL  = "https://api.nasa.gov/neo/rest/v1/feed"
CLAUDE_MODEL  = "claude-haiku-4-5-20251001"
OUTPUT_DIR    = os.path.join(os.path.dirname(__file__), "outputs")

# NASA enforces a maximum 7-day window per request
NASA_MAX_WINDOW = 7


# ── CLI arguments ──────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sentinel")
    parser.add_argument(
        "--days", type=int, default=7,
        help="Number of days to fetch (default: 7, any positive int supported)",
    )
    parser.add_argument(
        "--start", type=date.fromisoformat, default=date.today(),
        metavar="YYYY-MM-DD",
        help="Start date (default: today)",
    )
    parser.add_argument(
        "--max-distance", type=float, default=5_000_000,
        metavar="KM",
        help="Only include objects whose miss distance is within this many km (default: 5,000,000)",
    )
    return parser.parse_args()


# ── NASA NeoWs ────────────────────────────────────────────────────────────────

def _fetch_chunk(start: date, end: date, max_distance_km: float) -> list[dict]:
    """Single NASA API call (max 7-day window)."""
    params = {
        "start_date": start.isoformat(),
        "end_date":   end.isoformat(),
        "api_key":    NASA_API_KEY,
    }
    response = requests.get(NASA_NEO_URL, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    asteroids = []
    for day_objects in data["near_earth_objects"].values():
        for obj in day_objects:
            approach = obj["close_approach_data"][0]
            miss_km  = float(approach["miss_distance"]["kilometers"])

            if miss_km > max_distance_km:
                continue

            asteroids.append({
                "name":             obj["name"],
                "nasa_id":          obj["id"],
                "hazardous":        obj["is_potentially_hazardous_asteroid"],
                "diameter_min_m":   obj["estimated_diameter"]["meters"]["estimated_diameter_min"],
                "diameter_max_m":   obj["estimated_diameter"]["meters"]["estimated_diameter_max"],
                "approach_date":    approach["close_approach_date"],
                "velocity_kph":     float(approach["relative_velocity"]["kilometers_per_hour"]),
                "miss_distance_km": miss_km,
                "orbiting_body":    approach["orbiting_body"],
            })

    return asteroids


def fetch_neos(start: date, end: date, max_distance_km: float) -> list[dict]:
    """Chain 7-day chunks to cover any date range. Returns all results sorted by miss distance."""
    seen_ids: set[str] = set()
    all_asteroids: list[dict] = []

    chunk_start = start
    total_days  = (end - start).days + 1
    chunk_num   = 0

    while chunk_start <= end:
        chunk_end = min(chunk_start + timedelta(days=NASA_MAX_WINDOW - 1), end)
        chunk_num += 1
        chunks_total = -(-total_days // NASA_MAX_WINDOW)  # ceiling division
        print(
            f"  Fetching NASA data chunk {chunk_num}/{chunks_total}: {chunk_start} → {chunk_end}…",
            end="\r", flush=True,
        )

        for asteroid in _fetch_chunk(chunk_start, chunk_end, max_distance_km):
            if asteroid["nasa_id"] not in seen_ids:
                seen_ids.add(asteroid["nasa_id"])
                all_asteroids.append(asteroid)

        chunk_start = chunk_end + timedelta(days=1)

    print(" " * 80, end="\r")  # clear progress line
    return sorted(all_asteroids, key=lambda a: a["miss_distance_km"])


# ── Claude ────────────────────────────────────────────────────────────────────

def build_prompt(asteroid: dict) -> str:
    hazard_flag = "YES — flagged as potentially hazardous" if asteroid["hazardous"] else "No"
    return f"""You are a space science communicator analyzing near-Earth asteroid data.

Given the data below, do two things:

1. Write a concise 2–3 sentence plain-English risk narrative for a general audience.
   Be factual, calm, and avoid sensationalism.

2. On a new line, output a risk score using EXACTLY this format:
   RISK_SCORE: <number from 1 to 10>

   Score guide:
   1–2  = negligible (very distant, tiny, slow)
   3–4  = low (distant or small, no real concern)
   5–6  = moderate (closer approach or larger object, worth noting)
   7–8  = elevated (combination of close, fast, and/or large)
   9–10 = high (very close, large, and/or fast — genuinely notable)

   Base your score on the COMBINATION of miss distance, velocity, and diameter together,
   not just NASA's binary hazard flag.

Asteroid data:
  Name:              {asteroid['name']}
  Close approach:    {asteroid['approach_date']}
  Miss distance:     {asteroid['miss_distance_km']:,.0f} km
  Relative velocity: {asteroid['velocity_kph']:,.0f} km/h
  Est. diameter:     {asteroid['diameter_min_m']:.1f} – {asteroid['diameter_max_m']:.1f} metres
  Potentially hazardous (NASA): {hazard_flag}
  Orbiting body:     {asteroid['orbiting_body']}

Write the narrative and score now:"""


def _call_claude(client: anthropic.Anthropic, prompt: str) -> str:
    """Call Claude with retry on 429 (rate limit) and 529 (overload)."""
    for attempt in range(4):
        try:
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text.strip()
        except Exception as e:
            msg = str(e)
            is_rate_limit = "429" in msg
            is_overloaded = "529" in msg or "overloaded" in msg.lower()
            if (is_rate_limit or is_overloaded) and attempt < 3:
                match = re.search(r'retry.*?(\d+(?:\.\d+)?)s', msg, re.IGNORECASE)
                wait  = float(match.group(1)) if match else 30 * (attempt + 1)
                reason = "Rate limited" if is_rate_limit else "Server overloaded"
                print(f"\n  {reason} — waiting {wait:.0f}s before retry…", flush=True)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Claude failed after 4 attempts")


def generate_assessment(client: anthropic.Anthropic, asteroid: dict) -> dict:
    """Return {"narrative": str, "score": int} for one asteroid."""
    raw = _call_claude(client, build_prompt(asteroid))

    # Extract score line, then remove it from the narrative text
    score_match = re.search(r'RISK_SCORE:\s*(\d+)', raw, re.IGNORECASE)
    score = int(score_match.group(1)) if score_match else 0
    score = max(1, min(10, score))  # clamp to 1–10

    narrative = re.sub(r'\n?RISK_SCORE:\s*\d+', '', raw, flags=re.IGNORECASE).strip()

    return {"narrative": narrative, "score": score}


def score_bar(score: int) -> str:
    """Visual bar for the risk score, e.g. ████░░░░░░ 4/10"""
    filled = "█" * score
    empty  = "░" * (10 - score)
    return f"{filled}{empty} {score}/10"


# ── Markdown output ───────────────────────────────────────────────────────────

def build_markdown(
    start: date,
    end: date,
    max_distance_km: float,
    asteroids: list[dict],
    assessments: list[dict],
) -> str:
    lines = []
    lines.append("# Sentinel Report")
    lines.append(f"\n**Date range:** {start} → {end}  ")
    lines.append(f"**Objects within {max_distance_km:,.0f} km:** {len(asteroids)}  ")
    lines.append(f"**Generated:** {date.today()}  ")
    lines.append(f"**Model:** {CLAUDE_MODEL}  ")
    lines.append(f"**Sorted by:** miss distance (closest first)\n")
    lines.append("---\n")

    for i, (asteroid, assessment) in enumerate(zip(asteroids, assessments), start=1):
        hazard_badge = " 🚨 **POTENTIALLY HAZARDOUS**" if asteroid["hazardous"] else ""
        score        = assessment["score"]
        score_emoji  = "🔴" if score >= 7 else "🟡" if score >= 4 else "🟢"

        lines.append(f"## {i}. {asteroid['name']}{hazard_badge}\n")
        lines.append("| Field | Value |")
        lines.append("|---|---|")
        lines.append(f"| Approach date | {asteroid['approach_date']} |")
        lines.append(f"| Miss distance | {asteroid['miss_distance_km']:,.0f} km |")
        lines.append(f"| Velocity | {asteroid['velocity_kph']:,.0f} km/h |")
        lines.append(f"| Est. diameter | {asteroid['diameter_min_m']:.1f} – {asteroid['diameter_max_m']:.1f} m |")
        lines.append(f"| Orbiting body | {asteroid['orbiting_body']} |")
        lines.append(f"| NASA hazard flag | {'Yes' if asteroid['hazardous'] else 'No'} |")
        lines.append(f"| **Claude risk score** | {score_emoji} **{score_bar(score)}** |\n")
        lines.append("### Claude Risk Assessment\n")
        lines.append(assessment["narrative"])
        lines.append("\n---\n")

    return "\n".join(lines)


def save_report(
    start: date,
    end: date,
    max_distance_km: float,
    asteroids: list[dict],
    assessments: list[dict],
) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"sentinel_report_{start}_to_{end}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    content  = build_markdown(start, end, max_distance_km, asteroids, assessments)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    missing = [
        name for name, val in [("NASA_API_KEY", NASA_API_KEY), ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY)]
        if not val or val.endswith("_here")
    ]
    if missing:
        print(f"Error: missing or placeholder value(s) in .env: {', '.join(missing)}")
        sys.exit(1)

    db.init_db()

    start_date = args.start
    end_date   = start_date + timedelta(days=args.days - 1)

    print(f"Fetching NEO data: {start_date} → {end_date} (within {args.max_distance:,.0f} km)…")
    asteroids = fetch_neos(start_date, end_date, args.max_distance)

    if not asteroids:
        print(f"No asteroids found within {args.max_distance:,.0f} km in that window.")
        sys.exit(0)

    print(f"Found {len(asteroids)} object(s). Generating Claude assessments…")

    client      = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    assessments = []
    for i, asteroid in enumerate(asteroids, start=1):
        print(f"  [{i}/{len(asteroids)}] {asteroid['name']}…", end="\r", flush=True)
        assessments.append(generate_assessment(client, asteroid))
    print(" " * 80, end="\r")

    filepath  = save_report(start_date, end_date, args.max_distance, asteroids, assessments)
    report_id = db.save_report(
        str(start_date), str(end_date), args.max_distance,
        CLAUDE_MODEL, asteroids, assessments,
    )
    print(f"Report saved → {filepath}")
    print(f"Database updated (report #{report_id})")


if __name__ == "__main__":
    main()
