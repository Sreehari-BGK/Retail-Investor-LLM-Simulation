#!/usr/bin/env python3
"""
12_eval_grounding.py — Financial grounding fidelity metric
============================================================
Measures whether generated comments reference actual earnings facts,
not just produce investor-sounding text. This is the project's novel
metric contribution — generic social simulation papers don't test this.

Usage:
    # Evaluate real data (baseline)
    python scripts/12_eval_grounding.py --input data/processed/real_comments_curated.csv --label real

    # Evaluate template sim
    python scripts/12_eval_grounding.py --input data/processed/sim_comments.csv --label template

    # Evaluate Qwen one-shot
    python scripts/12_eval_grounding.py --input data/processed/sim_comments_qwen_oneshot.csv --label qwen_oneshot

Outputs:
    outputs/grounding_{label}.json
    outputs/grounding_comparison.csv  (appends)
"""

import argparse
import json
import re
import csv
from pathlib import Path
from collections import Counter

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# ── NVDA Q3 FY2026 grounding facts ────────────────────────────────────────
# Source: real data headline comment + SEC filing
# IMPORTANT: verify these against your actual SEC/earnings data
NVDA_FACTS = {
    "revenue": {
        "keywords": [r"\brevenue\b", r"\b57\b", "57 billion", "$57", "57b",
                     r"\bsales\b", "top line", "top-line"],
        "growth_keywords": ["62%", "62 percent", r"\byoy\b", "year over year", "year-over-year"],
    },
    "earnings": {
        "keywords": [r"\beps\b", "earnings per share", r"\bearnings\b", r"\bprofit\b",
                     "net income", "bottom line"],
    },
    "guidance": {
        "keywords": [r"\bguidance\b", r"\boutlook\b", r"\bq4\b", "next quarter",
                     r"\bforecast\b", r"\braised\b", r"\bguide\b", "guided higher",
                     "raised guidance"],
    },
    "product": {
        "keywords": [r"\bblackwell\b", r"\bgpu\b", r"\bchips?\b", "ai chip",
                     "data center", "datacenter", r"\bh100\b", r"\bh200\b",
                     r"\bb100\b", r"\bb200\b", r"\bhopper\b"],
    },
    "valuation": {
        "keywords": [r"\bpe\b", r"\bp/e\b", r"\bvaluation\b", r"\bovervalued\b",
                     r"\bundervalued\b", r"\bmultiple\b", "market cap", r"\btrillion\b",
                     "forward pe", "price to earnings"],
    },
    "price_action": {
        "keywords": ["after hours", "after-hours", r"\bah\b", r"\bdip\b",
                     "sold off", "premarket", "pre-market"],
    },
}

# Directional truth for NVDA Q3 FY2026
DIRECTION_TRUTH = {
    "beat": True,     # Revenue and EPS beat expectations
    "guidance_raised": True,  # Q4 guidance raised
}


def _match_keyword(kw: str, text_lower: str) -> bool:
    """Match a keyword — supports both plain substring and regex patterns."""
    if kw.startswith(r"\b"):
        return bool(re.search(kw, text_lower))
    else:
        return kw in text_lower


def check_fact_categories(text: str) -> dict:
    """Check which fact categories are mentioned in the comment."""
    text_lower = text.lower()
    mentions = {}
    for category, info in NVDA_FACTS.items():
        found = any(_match_keyword(kw, text_lower) for kw in info["keywords"])
        mentions[category] = found
        # Also check growth keywords for revenue
        if category == "revenue" and "growth_keywords" in info:
            if any(_match_keyword(kw, text_lower) for kw in info["growth_keywords"]):
                mentions[category] = True
    return mentions


def check_directional_correctness(text: str) -> str | None:
    """Check if directional claims (beat/miss, raised/lowered) are correct."""
    text_lower = text.lower()
    claims = []

    # Beat/miss
    beat_words = ["beat", "beats", "topped", "exceeded", "crushed", "smashed",
                  "blowout", "strong quarter", "better than expected"]
    miss_words = ["missed", "miss", "fell short", "disappointed", "weak", "below"]

    if any(w in text_lower for w in beat_words):
        claims.append("correct" if DIRECTION_TRUTH["beat"] else "incorrect")
    if any(w in text_lower for w in miss_words):
        claims.append("incorrect" if DIRECTION_TRUTH["beat"] else "correct")

    # Guidance
    raised_words = ["raised guidance", "guided up", "guidance above", "strong guidance",
                    "raised", "guide higher", "guidance beat"]
    lowered_words = ["lowered guidance", "guided down", "weak guidance",
                     "guidance below", "guidance miss", "cut guidance"]

    if any(w in text_lower for w in raised_words):
        claims.append("correct" if DIRECTION_TRUTH["guidance_raised"] else "incorrect")
    if any(w in text_lower for w in lowered_words):
        claims.append("incorrect" if DIRECTION_TRUTH["guidance_raised"] else "correct")

    if not claims:
        return None
    return "incorrect" if "incorrect" in claims else "correct"


def classify_grounding(fact_mentions: dict, text: str) -> str:
    """Classify grounding level: grounded / weakly_grounded / ungrounded."""
    categories_hit = sum(1 for v in fact_mentions.values() if v)

    # Check for specific numbers
    numbers = re.findall(r'\$?\d+\.?\d*[bBmMtT%]?', text)
    has_numbers = len(numbers) > 0

    if categories_hit >= 3 or (categories_hit >= 2 and has_numbers):
        return "grounded"
    elif categories_hit >= 1:
        return "weakly_grounded"
    else:
        return "ungrounded"


def evaluate_corpus(df: pd.DataFrame, text_col: str = "text") -> dict:
    """Evaluate financial grounding for entire corpus."""
    n = len(df)
    grounding_levels = Counter()
    directional = Counter()
    category_counts = Counter()
    fact_mention_count = 0
    number_count = 0

    for _, row in df.iterrows():
        text = str(row.get(text_col, ""))

        facts = check_fact_categories(text)
        direction = check_directional_correctness(text)
        grounding = classify_grounding(facts, text)

        grounding_levels[grounding] += 1
        if direction:
            directional[direction] += 1

        for cat, found in facts.items():
            if found:
                category_counts[cat] += 1

        if any(facts.values()):
            fact_mention_count += 1
        if re.search(r'\d+\.?\d*', text):
            number_count += 1

    summary = {
        "n": n,
        "grounding": {
            "grounded_pct": round(grounding_levels.get("grounded", 0) / n * 100, 1),
            "weakly_grounded_pct": round(grounding_levels.get("weakly_grounded", 0) / n * 100, 1),
            "ungrounded_pct": round(grounding_levels.get("ungrounded", 0) / n * 100, 1),
        },
        "fact_mention_rate_pct": round(fact_mention_count / n * 100, 1),
        "any_number_rate_pct": round(number_count / n * 100, 1),
        "category_rates": {
            cat: round(cnt / n * 100, 1)
            for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1])
        },
        "directional": {
            "correct": directional.get("correct", 0),
            "incorrect": directional.get("incorrect", 0),
            "no_claim": n - sum(directional.values()),
            "accuracy_pct": round(
                directional.get("correct", 0) / max(1, sum(directional.values())) * 100, 1
            ) if sum(directional.values()) > 0 else None,
        },
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description="Evaluate financial grounding")
    parser.add_argument("--input", required=True, help="CSV file to evaluate")
    parser.add_argument("--label", required=True, help="Label for this evaluation")
    parser.add_argument("--text-col", default="text", help="Column containing comment text")
    parser.add_argument("--ticker-filter", default="NVDA", help="Filter to this ticker (or 'all')")
    args = parser.parse_args()

    out_dir = ROOT / "outputs"
    out_dir.mkdir(exist_ok=True)

    print(f"Loading {args.input}...")
    df = pd.read_csv(args.input)
    print(f"  Total rows: {len(df)}")

    if args.ticker_filter != "all" and "ticker" in df.columns:
        df = df[df["ticker"] == args.ticker_filter]
        print(f"  After {args.ticker_filter} filter: {len(df)}")

    summary = evaluate_corpus(df, text_col=args.text_col)
    summary["label"] = args.label

    # Print
    print(f"\n{'='*60}")
    print(f"  FINANCIAL GROUNDING: {args.label}")
    print(f"{'='*60}")
    print(f"  N = {summary['n']}")
    print(f"\n  Grounding levels:")
    for level in ["grounded_pct", "weakly_grounded_pct", "ungrounded_pct"]:
        print(f"    {level:<25} {summary['grounding'][level]:>5.1f}%")
    print(f"\n  Fact mention rate:  {summary['fact_mention_rate_pct']}%")
    print(f"  Any number rate:    {summary['any_number_rate_pct']}%")
    print(f"\n  Category rates:")
    for cat, rate in summary["category_rates"].items():
        print(f"    {cat:<20} {rate:>5.1f}%")
    d = summary["directional"]
    print(f"\n  Directional claims:")
    print(f"    Correct:   {d['correct']}")
    print(f"    Incorrect: {d['incorrect']}")
    print(f"    No claim:  {d['no_claim']}")
    if d["accuracy_pct"] is not None:
        print(f"    Accuracy:  {d['accuracy_pct']}%")

    # Save JSON
    json_path = out_dir / f"grounding_{args.label}.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Saved: {json_path}")

    # Append to comparison CSV
    csv_path = out_dir / "grounding_comparison.csv"
    write_header = not csv_path.exists()
    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["label", "n", "grounded_pct", "weakly_grounded_pct",
                           "ungrounded_pct", "fact_mention_rate_pct",
                           "any_number_rate_pct", "directional_accuracy_pct"])
        g = summary["grounding"]
        writer.writerow([
            args.label, summary["n"],
            g["grounded_pct"], g["weakly_grounded_pct"], g["ungrounded_pct"],
            summary["fact_mention_rate_pct"],
            summary["any_number_rate_pct"],
            summary["directional"]["accuracy_pct"] or "N/A",
        ])
    print(f"  Appended to: {csv_path}")


if __name__ == "__main__":
    main()
