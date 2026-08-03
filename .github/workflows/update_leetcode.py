"""
Fetches live LeetCode stats for devanshhhh09 and patches index.html.
Runs inside GitHub Actions — no secrets needed (LeetCode's GraphQL API is public).
"""

import re
import sys
import json
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
  userContestRanking(username: $username) {
    rating
  }
}
"""

ACCEPTANCE_QUERY = """
query getUserSolvedProblems($username: String!) {
  matchedUser(username: $username) {
    problemsSolvedBeatsStats {
      difficulty
      percentage
    }
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

    return {
        "total":  total,
        "easy":   easy,
        "medium": medium,
        "hard":   hard,
    }


def fetch_acceptance():
    """
    Acceptance rate = accepted submissions / total submissions.
    LeetCode doesn't expose this directly in the public API,
    so we compute it from submission stats.
    """
    headers = {
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com",
        "User-Agent": "Mozilla/5.0"
    }

    # Use the public profile stats endpoint
    url = f"https://leetcode-stats-api.herokuapp.com/{USERNAME}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        d = resp.json()
        rate = d.get("acceptanceRate", None)
        if rate is not None:
            return round(float(rate), 1)
    except Exception:
        pass

    # Fallback: return None so we keep whatever's in the HTML
    return None


def patch_html(stats, acceptance):
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    original = html

    # ── Total problems solved ──────────────────────────────────────────────────
    # Targets: <span class="lc-num ...">27</span>  (the total in metric-card)
    # We look for the metric-card that contains "Problems Solved"
    html = re.sub(
        r'(<span class="metric-value"[^>]*>)\d+(<\/span>\s*<span class="metric-label">Problems Solved)',
        rf'\g<1>{stats["total"]}\2',
        html
    )

    # ── Easy count ────────────────────────────────────────────────────────────
    html = re.sub(
        r'(<span class="lc-num easy">)\d+(<\/span>)',
        rf'\g<1>{stats["easy"]}\2',
        html
    )

    # ── Medium count ──────────────────────────────────────────────────────────
    html = re.sub(
        r'(<span class="lc-num medium">)\d+(<\/span>)',
        rf'\g<1>{stats["medium"]}\2',
        html
    )

    # ── Hard count ────────────────────────────────────────────────────────────
    html = re.sub(
        r'(<span class="lc-num hard">)\d+(<\/span>)',
        rf'\g<1>{stats["hard"]}\2',
        html
    )

    # ── Acceptance rate ───────────────────────────────────────────────────────
    if acceptance is not None:
        html = re.sub(
            r'(<span class="metric-value"[^>]*>)[\d.]+(%?<\/span>\s*<span class="metric-label">Acceptance Rate)',
            rf'\g<1>{acceptance}%\2',
            html
        )

    # ── "27+ Problems" goal line  ─────────────────────────────────────────────
    # Updates the "X+ problems solved" display in the lc-goal line
    html = re.sub(
        r'(Goal:\s*<span>)\d+\+(\s*problems)',
        rf'\g<1>{stats["total"] + 1}+\2',  # keep the + notation
        html
    )

    if html == original:
        print("No changes detected — stats are already up to date.")
    else:
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ Portfolio updated:")
        print(f"   Total:    {stats['total']}")
        print(f"   Easy:     {stats['easy']}")
        print(f"   Medium:   {stats['medium']}")
        print(f"   Hard:     {stats['hard']}")
        if acceptance:
            print(f"   Acceptance: {acceptance}%")


def main():
    print(f"Fetching LeetCode stats for @{USERNAME}...")
    stats      = fetch_stats()
    acceptance = fetch_acceptance()
    print(f"Got: total={stats['total']}, easy={stats['easy']}, medium={stats['medium']}, hard={stats['hard']}")
    patch_html(stats, acceptance)


if __name__ == "__main__":
    main()
