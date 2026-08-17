"""
Fetches live LeetCode stats for devanshhhh09 and patches index.html.
Runs inside GitHub Actions — no secrets needed (LeetCode's GraphQL API is public).
"""

import re
import sys
import requests

# ── CONFIG ────────────────────────────────────────────────────────────────────
USERNAME   = "devanshhhh09"
HTML_FILE  = "index.html"
# ──────────────────────────────────────────────────────────────────────────────

LEETCODE_GRAPHQL = "https://leetcode.com/graphql"

QUERY = """
query getUserProfile($username: String!) {
  matchedUser(username: $username) {
    submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
  }
}
"""

def fetch_stats():
    headers = {
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {
        "query": QUERY,
        "variables": {"username": USERNAME}
    }
    resp = requests.post(LEETCODE_GRAPHQL, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    user = data.get("data", {}).get("matchedUser")
    if not user:
        print(f"ERROR: LeetCode user '{USERNAME}' not found or API changed.")
        sys.exit(1)

    counts = {}
    for item in user["submitStatsGlobal"]["acSubmissionNum"]:
        counts[item["difficulty"]] = item["count"]

    total  = counts.get("All",    0)
    easy   = counts.get("Easy",   0)
    medium = counts.get("Medium", 0)
    hard   = counts.get("Hard",   0)

    print(f"  Fetched from LeetCode API:")
    print(f"    Total:  {total}")
    print(f"    Easy:   {easy}")
    print(f"    Medium: {medium}")
    print(f"    Hard:   {hard}")

    return {"total": total, "easy": easy, "medium": medium, "hard": hard}


def fetch_acceptance():
    url = f"https://leetcode-stats-api.herokuapp.com/{USERNAME}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        d = resp.json()
        rate = d.get("acceptanceRate", None)
        if rate is not None:
            result = round(float(rate), 1)
            print(f"    Acceptance: {result}%")
            return result
    except Exception as e:
        print(f"  Acceptance rate fetch failed (non-critical): {e}")
    return None


def patch_html(stats, acceptance):
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    original = html

    # ── Easy ──────────────────────────────────────────────────────────────────
    pattern = r'(<span class="lc-num easy">)\d+(<\/span>)'
    match = re.search(pattern, html)
    if match:
        print(f"  Easy: found '{match.group(0)}' → replacing with {stats['easy']}")
        html = re.sub(pattern, rf'\g<1>{stats["easy"]}\2', html)
    else:
        print("  WARNING: Easy pattern not found in HTML")

    # ── Medium ────────────────────────────────────────────────────────────────
    pattern = r'(<span class="lc-num medium">)\d+(<\/span>)'
    match = re.search(pattern, html)
    if match:
        print(f"  Medium: found '{match.group(0)}' → replacing with {stats['medium']}")
        html = re.sub(pattern, rf'\g<1>{stats["medium"]}\2', html)
    else:
        print("  WARNING: Medium pattern not found in HTML")

    # ── Hard ──────────────────────────────────────────────────────────────────
    pattern = r'(<span class="lc-num hard">)\d+(<\/span>)'
    match = re.search(pattern, html)
    if match:
        print(f"  Hard: found '{match.group(0)}' → replacing with {stats['hard']}")
        html = re.sub(pattern, rf'\g<1>{stats["hard"]}\2', html)
    else:
        print("  WARNING: Hard pattern not found in HTML")

    # ── Total (data-lc-total attribute — drives typewriter + about section) ────
    pattern = r'(<span class="mv" data-lc-total>)\d+(<\/span>)'
    match = re.search(pattern, html)
    if match:
        print(f"  Total: found → replacing with {stats['total']}")
        html = re.sub(pattern, rf'\g<1>{stats["total"]}\2', html)
    else:
        print("  WARNING: Total problems pattern not found in HTML")

    # ── About section inline count ────────────────────────────────────────────
    pattern = r'(<span data-lc-about>)\d+(<\/span>)'
    match = re.search(pattern, html)
    if match:
        print(f"  About text: found → replacing with {stats['total']}")
        html = re.sub(pattern, rf'\g<1>{stats["total"]}\2', html)
    else:
        print("  WARNING: About section count pattern not found in HTML")

    # ── Fact chip count ───────────────────────────────────────────────────────
    pattern = r'(<span data-lc-chip>)\d+(<\/span>)'
    match = re.search(pattern, html)
    if match:
        print(f"  Fact chip: found → replacing with {stats['total']}")
        html = re.sub(pattern, rf'\g<1>{stats["total"]}\2', html)
    else:
        print("  WARNING: Fact chip pattern not found in HTML")

    # ── Skills subtitle count ─────────────────────────────────────────────────
    pattern = r'(<span data-lc-sub>)\d+(<\/span>)'
    match = re.search(pattern, html)
    if match:
        print(f"  Skills subtitle: found → replacing with {stats['total']}")
        html = re.sub(pattern, rf'\g<1>{stats["total"]}\2', html)
    else:
        print("  WARNING: Skills subtitle pattern not found in HTML")

    # ── Acceptance rate ───────────────────────────────────────────────────────
    if acceptance is not None:
        pattern = r'(<span class="metric-value">)[\d.]+%(<\/span>\s*<span class="metric-label">Acceptance Rate)'
        match = re.search(pattern, html)
        if match:
            print(f"  Acceptance: found → replacing with {acceptance}%")
            html = re.sub(pattern, rf'\g<1>{acceptance}%\2', html)
        else:
            print("  WARNING: Acceptance rate pattern not found in HTML")

    # ── Goal line ─────────────────────────────────────────────────────────────
    pattern = r'(Goal:\s*<span>)\d+\+(\s*problems)'
    match = re.search(pattern, html)
    if match:
        goal = stats["total"] + 50  # always shows ~50 ahead as the next milestone
        print(f"  Goal line: updating to {goal}+")
        html = re.sub(pattern, rf'\g<1>{goal}+\2', html)

    # ── Write back ────────────────────────────────────────────────────────────
    if html == original:
        print("\nNo changes detected — stats already up to date in HTML.")
    else:
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n✅ index.html updated successfully.")


def patch_readme(stats, acceptance):
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            readme = f.read()
    except FileNotFoundError:
        print("  README.md not found — skipping.")
        return

    original = readme

    # Replace everything between LC_STATS_START and LC_STATS_END
    acceptance_str = f"{acceptance}%" if acceptance else "N/A"
    new_block = f"""<!-- LC_STATS_START -->
<div align="center">

<table>
<tr>
<td align="center">✅ <b>Total Solved</b></td>
<td align="center"><b>{stats['total']}</b></td>
</tr>
<tr>
<td align="center">🟢 <b>Easy</b></td>
<td align="center">{stats['easy']}</td>
</tr>
<tr>
<td align="center">🟡 <b>Medium</b></td>
<td align="center">{stats['medium']}</td>
</tr>
<tr>
<td align="center">🔴 <b>Hard</b></td>
<td align="center">{stats['hard']}</td>
</tr>
<tr>
<td align="center">📊 <b>Acceptance Rate</b></td>
<td align="center">{acceptance_str}</td>
</tr>
<tr>
<td align="center">💻 <b>Language</b></td>
<td align="center">C++</td>
</tr>
<tr>
<td align="center">🎯 <b>Goal</b></td>
<td align="center">250+ by December 2026</td>
</tr>
</table>

</div>
<!-- LC_STATS_END -->"""

    readme = re.sub(
        r'<!-- LC_STATS_START -->.*?<!-- LC_STATS_END -->',
        new_block,
        readme,
        flags=re.DOTALL
    )

    # ── Google & Amazon Readiness block ──────────────────────────────────────
    ready_block = f"""<!-- LC_READY_START -->
```
Distributed Systems  ████████████████████  Architected in Production (PoliceOSINT)
Programming (C++)    ████████████████░░░░  {stats['total']}+ LeetCode · Daily Practice
Algorithms & DSA     ██████████████░░░░░░  Arrays, Trees, HashMaps · Building Graphs & DP
AI Integration       ████████████████████  Groq/Llama-3.3-70b in Production
System Design        ████████████░░░░░░░░  Learning · PoliceOSINT as foundation
```
<!-- LC_READY_END -->"""
    readme = re.sub(
        r'<!-- LC_READY_START -->.*?<!-- LC_READY_END -->',
        ready_block,
        readme,
        flags=re.DOTALL
    )
    print(f"  Readiness block: updated to {stats['total']}+")

    # ── Typing SVG URL ────────────────────────────────────────────────────────
    typing_line = f"<!-- LC_TYPING_START -->[![Typing SVG](https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&weight=600&size=16&duration=3000&pause=1000&color=4285F4&center=true&vCenter=true&repeat=true&width=600&lines=Building+PoliceOSINT+for+Gurugram+Police;DSA+in+C%2B%2B+%7C+{stats['total']}%2B+LeetCode+Solved;Targeting+Google+%26+Amazon+SWE+Roles)](https://git.io/typing-svg)<!-- LC_TYPING_END -->"
    readme = re.sub(
        r'<!-- LC_TYPING_START -->.*?<!-- LC_TYPING_END -->',
        typing_line,
        readme,
        flags=re.DOTALL
    )
    print(f"  Typing SVG: updated to {stats['total']}+")

    if readme == original:
        print("  README: No changes.")
    else:
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(readme)
        print(f"  ✅ README.md updated.")


def main():
    print(f"Fetching LeetCode stats for @{USERNAME}...")
    stats      = fetch_stats()
    acceptance = fetch_acceptance()
    print(f"\nPatching {HTML_FILE}...")
    patch_html(stats, acceptance)
    print(f"\nPatching README.md...")
    patch_readme(stats, acceptance)


if __name__ == "__main__":
    main()
