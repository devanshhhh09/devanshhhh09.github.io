"""
build_resume.py
Reads resume.tex, injects live LeetCode stats, compiles to PDF.
Runs inside GitHub Actions after update_leetcode.py.
Requires: sudo apt-get install -y texlive-latex-extra texlive-fonts-recommended
"""

import re
import os
import sys
import json
import subprocess
import requests

USERNAME = "devanshhhh09"
TEX_TEMPLATE = "resume.tex"
OUTPUT_PDF   = "resume.pdf"

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
    payload = {"query": QUERY, "variables": {"username": USERNAME}}
    resp = requests.post(LEETCODE_GRAPHQL, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    user = data.get("data", {}).get("matchedUser")
    if not user:
        print(f"ERROR: User '{USERNAME}' not found.")
        sys.exit(1)
    counts = {}
    for item in user["submitStatsGlobal"]["acSubmissionNum"]:
        counts[item["difficulty"]] = item["count"]
    return {
        "total":  counts.get("All",    0),
        "easy":   counts.get("Easy",   0),
        "medium": counts.get("Medium", 0),
        "hard":   counts.get("Hard",   0),
    }

def fetch_acceptance():
    headers = {
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com",
        "User-Agent": "Mozilla/5.0"
    }
    query = """
query getUserStats($username: String!) {
  matchedUser(username: $username) {
    submitStats: submitStatsGlobal {
      acSubmissionNum { difficulty count submissions }
      totalSubmissionNum { difficulty count submissions }
    }
  }
}
"""
    try:
        resp = requests.post("https://leetcode.com/graphql",
                             json={"query": query, "variables": {"username": USERNAME}},
                             headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        user = data.get("data", {}).get("matchedUser")
        if not user:
            return 75.6
        ac_total = next((i["submissions"] for i in user["submitStats"]["acSubmissionNum"]    if i["difficulty"] == "All"), 0)
        total    = next((i["submissions"] for i in user["submitStats"]["totalSubmissionNum"] if i["difficulty"] == "All"), 0)
        if total > 0:
            rate = round((ac_total / total) * 100, 2)
            print(f"  Acceptance: {rate}% ({ac_total}/{total})")
            return rate
    except Exception as e:
        print(f"  Acceptance fetch failed: {e}")
    return 75.6

def build_pdf(stats, acceptance):
    # Read template
    with open(TEX_TEMPLATE, "r", encoding="utf-8") as f:
        tex = f.read()

    # Replace placeholders
    tex = tex.replace("%%LC_TOTAL%%",  str(stats["total"]))
    tex = tex.replace("%%LC_EASY%%",   str(stats["easy"]))
    tex = tex.replace("%%LC_MEDIUM%%", str(stats["medium"]))
    tex = tex.replace("%%LC_HARD%%",   str(stats["hard"]))
    tex = tex.replace("%%LC_ACCEPT%%", f"{acceptance}\\%")

    # Write patched tex
    patched_tex = "resume_patched.tex"
    with open(patched_tex, "w", encoding="utf-8") as f:
        f.write(tex)

    print(f"  Stats injected: total={stats['total']}, easy={stats['easy']}, medium={stats['medium']}, hard={stats['hard']}, acceptance={acceptance}%")

    # Compile with pdflatex (run twice for proper layout)
    for i in range(2):
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-jobname=resume", patched_tex],
            capture_output=True, text=True
        )
        if result.returncode != 0 and i == 1:
            print("  pdflatex stderr:", result.stderr[-500:])
            print("  pdflatex stdout:", result.stdout[-500:])
            sys.exit(1)

    # Cleanup aux files
    for ext in [".aux", ".log", ".out", ".fls", ".fdb_latexmk"]:
        try:
            os.remove(f"resume{ext}")
        except FileNotFoundError:
            pass
    try:
        os.remove(patched_tex)
    except FileNotFoundError:
        pass

    print(f"  ✅ resume.pdf compiled successfully.")


def main():
    print(f"Fetching LeetCode stats for @{USERNAME}...")
    stats      = fetch_stats()
    acceptance = fetch_acceptance()
    print(f"\nBuilding resume PDF...")
    build_pdf(stats, acceptance)


if __name__ == "__main__":
    main()
