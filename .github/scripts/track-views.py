import html
import json
import os
import re
from collections import Counter
from datetime import date, datetime, timezone
from urllib.request import urlopen

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_FILE = os.path.join(REPO_ROOT, "profile-views.json")
PROFILE_VIEWS_FILE = os.path.join(REPO_ROOT, "PROFILE_VIEWS.md")
ACTIVITY_FILE = os.path.join(REPO_ROOT, "activity-log.txt")
ASSETS_DIR = os.path.join(REPO_ROOT, "assets")
BADGE_URL = "https://komarev.com/ghpvc/?username=dev9269"


def fetch_view_count():
    with urlopen(BADGE_URL, timeout=10) as resp:
        svg = resp.read().decode("utf-8")
    match = re.search(r">(\d+)<", svg)
    if match:
        return int(match.group(1))
    return None


def load_history():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"history": []}


def save_history(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_monthly_summary(history):
    months = {}
    for entry in history:
        month_key = entry["date"][:7]
        months.setdefault(
            month_key,
            {"first": entry["count"], "last": entry["count"], "peak": entry["count"]},
        )
        m = months[month_key]
        if entry["count"] < m["first"]:
            m["first"] = entry["count"]
        m["last"] = entry["count"]
        if entry["count"] > m["peak"]:
            m["peak"] = entry["count"]
    return months


def get_activity_summary():
    if not os.path.exists(ACTIVITY_FILE):
        return {"events": 0, "days": 0, "peak": 0, "streak": 0}
    with open(ACTIVITY_FILE, encoding="utf-8", errors="replace") as f:
        text = f.read()
    dates = re.findall(r"\b(\d{4}-\d{2}-\d{2})T", text)
    markers = [int(x) for x in re.findall(r"streak #(\d+)", text)]
    unique = sorted(set(dates))
    per_day = Counter(dates)
    streak = 0
    cursor = date.fromisoformat(unique[-1]) if unique else None
    while cursor and cursor.isoformat() in per_day:
        streak += 1
        cursor = date.fromordinal(cursor.toordinal() - 1)
    return {
        "events": len(dates),
        "days": len(unique),
        "peak": max(markers) if markers else 0,
        "streak": streak,
    }


def badge_svg(label, value, note, accent):
    label = html.escape(str(label))
    value = html.escape(str(value))
    note = html.escape(str(note))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="440" height="64" viewBox="0 0 440 64" role="img" aria-labelledby="t d">
<title id="t">{label}</title><desc id="d">{label} status badge</desc>
<rect width="440" height="64" rx="6" fill="#0D1214" stroke="#1E2A2D" stroke-width="1"/>
<rect x="0" y="0" width="6" height="64" fill="{accent}"/>
<text x="22" y="24" fill="#5F7A70" font-family="JetBrains Mono, Consolas, monospace" font-size="11" letter-spacing="1.5">{label}</text>
<text x="22" y="48" fill="#E7DFD2" font-family="JetBrains Mono, Consolas, monospace" font-size="20" font-weight="700">{value}</text>
<text x="418" y="48" fill="{accent}" font-family="JetBrains Mono, Consolas, monospace" font-size="10" text-anchor="end">{note}</text>
</svg>
'''


def write_badges(total_views, history, activity):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    last_date = history[-1]["date"] if history else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    views_badge = badge_svg(
        "PROFILE VIEWS", f"{total_views:,}", f"LAST LOG {last_date}", "#39FF88"
    )
    streak_badge = badge_svg(
        "ACTIVITY STREAK",
        f'{activity["streak"]}D / #{activity["peak"]}',
        f'{activity["days"]} LOGGED DAYS',
        "#FF4D5E",
    )
    with open(os.path.join(ASSETS_DIR, "views-badge.svg"), "w", encoding="utf-8") as f:
        f.write(views_badge)
    with open(os.path.join(ASSETS_DIR, "streak-badge.svg"), "w", encoding="utf-8") as f:
        f.write(streak_badge)


def update_profile_views(monthly_summary, total_views):
    if os.path.exists(PROFILE_VIEWS_FILE):
        with open(PROFILE_VIEWS_FILE, encoding="utf-8") as f:
            content = f.read()
    else:
        content = "# Profile Analytics\n"

    rows = ""
    for month_key in sorted(monthly_summary.keys(), reverse=True):
        m = monthly_summary[month_key]
        rows += f"| {month_key} | {m['first']} | {m['peak']} | {m['last']} | {m['last'] - m['first']} |\n"

    monthly_section = f"""
<details>
<summary><b>Monthly profile views</b> (Total: {total_views})</summary>
<br>

| Month | Start | Peak | End | Growth |
|-------|-------|------|-----|--------|
{rows}
</details>
"""

    marker_start = "<!-- PROFILE_VIEWS:START -->"
    marker_end = "<!-- PROFILE_VIEWS:END -->"

    new_section = f"{marker_start}\n{monthly_section}\n{marker_end}"

    if marker_start in content:
        pattern = re.compile(
            re.escape(marker_start) + r".*?" + re.escape(marker_end), re.DOTALL
        )
        content = pattern.sub(new_section, content)
    else:
        content += f"\n\n{new_section}"

    with open(PROFILE_VIEWS_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    data = load_history()
    activity = get_activity_summary()
    count = fetch_view_count()
    if count is None:
        print("Failed to fetch view count")
        total = data["history"][-1]["count"] if data["history"] else 0
        write_badges(total, data["history"], activity)
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if data["history"] and data["history"][-1]["date"] == today:
        data["history"][-1]["count"] = count
        print(f"Updated today's count to {count}")
    else:
        data["history"].append({"date": today, "count": count})
        print(f"Added new entry: {today} -> {count}")

    save_history(data)

    monthly = get_monthly_summary(data["history"])
    total = data["history"][-1]["count"] if data["history"] else 0
    update_profile_views(monthly, total)
    write_badges(total, data["history"], activity)

    print(f"Total views: {total}")


if __name__ == "__main__":
    main()
