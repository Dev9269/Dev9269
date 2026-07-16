import json
import re
import os
from datetime import datetime, timezone
from urllib.request import urlopen

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_FILE = os.path.join(REPO_ROOT, "profile-views.json")
README_FILE = os.path.join(REPO_ROOT, "README.md")
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
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"history": []}


def save_history(data):
    with open(DATA_FILE, "w") as f:
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


def update_readme(monthly_summary, total_views):
    with open(README_FILE, encoding="utf-8") as f:
        content = f.read()

    rows = ""
    for month_key in sorted(monthly_summary.keys(), reverse=True):
        m = monthly_summary[month_key]
        rows += f"| {month_key} | {m['first']} | {m['peak']} | {m['last']} | {m['last'] - m['first']} |\n"

    monthly_section = f"""
<details>
<summary><b>📊 Monthly Profile Views</b> (Total: {total_views})</summary>
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

    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    count = fetch_view_count()
    if count is None:
        print("Failed to fetch view count")
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data = load_history()

    if data["history"] and data["history"][-1]["date"] == today:
        data["history"][-1]["count"] = count
        print(f"Updated today's count to {count}")
    else:
        data["history"].append({"date": today, "count": count})
        print(f"Added new entry: {today} -> {count}")

    save_history(data)

    monthly = get_monthly_summary(data["history"])
    total = data["history"][-1]["count"] if data["history"] else 0
    update_readme(monthly, total)

    print(f"Total views: {total}")


if __name__ == "__main__":
    main()
