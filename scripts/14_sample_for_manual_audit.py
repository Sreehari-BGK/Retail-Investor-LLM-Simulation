#!/usr/bin/env python3
"""
14_sample_for_manual_audit.py — Pull random samples for human grounding check
==============================================================================
Outputs a simple CSV you can open in Excel/Google Sheets, read each comment,
and write your own grounding label next to the script's label.

Usage:
    python scripts/14_sample_for_manual_audit.py

Outputs:
    outputs/grounding_manual_audit.csv
    
Then YOU fill in the 'human_label' column by reading each comment.
Compare with 'script_label' to see if the grounding rubric is trustworthy.
"""

import random
import json
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Import the grounding functions from our evaluator
import sys
sys.path.insert(0, str(ROOT / "scripts"))
from importlib import import_module

# We'll inline the core logic to avoid import issues
import re

NVDA_FACTS = {
    "revenue": {
        "keywords": [r"\brevenue\b", r"\b57\b", "57 billion", "$57", "57b",
                     r"\bsales\b", "top line", "top-line"],
    },
    "earnings": {
        "keywords": [r"\beps\b", "earnings per share", r"\bearnings\b", r"\bprofit\b",
                     "net income", "bottom line"],
    },
    "guidance": {
        "keywords": [r"\bguidance\b", r"\boutlook\b", r"\bq4\b", "next quarter",
                     r"\bforecast\b", r"\braised\b", r"\bguide\b"],
    },
    "product": {
        "keywords": [r"\bblackwell\b", r"\bgpu\b", r"\bchips?\b", "ai chip",
                     "data center", "datacenter", r"\bh100\b", r"\bh200\b"],
    },
    "valuation": {
        "keywords": [r"\bpe\b", r"\bp/e\b", r"\bvaluation\b", r"\bovervalued\b",
                     r"\bundervalued\b", r"\bmultiple\b", "market cap", r"\btrillion\b"],
    },
    "price_action": {
        "keywords": ["after hours", "after-hours", r"\bah\b", r"\bdip\b",
                     "sold off", "premarket", "pre-market"],
    },
}


def _match_kw(kw, text_lower):
    if kw.startswith(r"\b"):
        return bool(re.search(kw, text_lower))
    return kw in text_lower


def check_facts(text):
    text_lower = text.lower()
    mentions = {}
    for cat, info in NVDA_FACTS.items():
        mentions[cat] = any(_match_kw(kw, text_lower) for kw in info["keywords"])
    return mentions


def script_grounding_label(text):
    facts = check_facts(text)
    cats_hit = sum(1 for v in facts.values() if v)
    has_numbers = len(re.findall(r'\$?\d+\.?\d*[bBmMtT%]?', text)) > 0
    if cats_hit >= 3 or (cats_hit >= 2 and has_numbers):
        return "grounded"
    elif cats_hit >= 1:
        return "weakly_grounded"
    else:
        return "ungrounded"


def main():
    random.seed(42)
    out_dir = ROOT / "outputs"

    # Load real NVDA comments
    real_df = pd.read_csv(ROOT / "data" / "processed" / "real_comments_curated.csv")
    real_nvda = real_df[real_df["ticker"] == "NVDA"].copy()

    # Load template sim comments
    sim_df = pd.read_csv(ROOT / "data" / "processed" / "sim_comments.csv")

    # Sample 20 from each
    real_sample = real_nvda.sample(n=min(20, len(real_nvda)), random_state=42)
    sim_sample = sim_df.sample(n=min(20, len(sim_df)), random_state=42)

    rows = []
    for _, r in real_sample.iterrows():
        text = str(r["text"])
        rows.append({
            "source": "real",
            "comment_id": r.get("comment_id", ""),
            "text": text[:500],  # truncate for readability
            "script_label": script_grounding_label(text),
            "human_label": "",  # YOU FILL THIS IN
            "notes": "",        # YOUR NOTES
        })

    for _, r in sim_sample.iterrows():
        text = str(r["text"])
        rows.append({
            "source": "template",
            "comment_id": r.get("comment_id", ""),
            "text": text[:500],
            "script_label": script_grounding_label(text),
            "human_label": "",
            "notes": "",
        })

    # Shuffle so you're not biased by seeing all real then all template
    random.shuffle(rows)

    audit_df = pd.DataFrame(rows)
    out_path = out_dir / "grounding_manual_audit.csv"
    audit_df.to_csv(out_path, index=False)

    print(f"Saved {len(audit_df)} comments to {out_path}")
    print(f"  Real:     {sum(1 for r in rows if r['source']=='real')}")
    print(f"  Template: {sum(1 for r in rows if r['source']=='template')}")
    print()
    print("INSTRUCTIONS:")
    print("  1. Open this CSV in Excel or Google Sheets")
    print("  2. Read each comment in the 'text' column")
    print("  3. In 'human_label', write: grounded / weakly_grounded / ungrounded")
    print("     - grounded = references specific NVDA earnings facts or numbers")
    print("     - weakly_grounded = mentions earnings/NVDA themes but no specifics")
    print("     - ungrounded = generic investor opinion, no event connection")
    print("  4. Compare human_label vs script_label")
    print("  5. If >70% agree, the rubric is usable. If not, fix the keywords.")


if __name__ == "__main__":
    main()
