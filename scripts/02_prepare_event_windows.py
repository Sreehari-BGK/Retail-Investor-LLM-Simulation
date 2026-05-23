"""
02_prepare_event_windows.py
Merge raw per-event CSVs into a single processed comments.csv.
Filters to the event window, drops near-empty texts, deduplicates.

If using real PRAW data:
    Run after 01_collect_reddit.py

If using synthetic data:
    Run 00_make_synthetic_data.py instead — it writes directly to
    data/processed/comments.csv and you can skip this script.
"""

import os
import glob
import pandas as pd

WINDOW_BEFORE_H = 24
WINDOW_AFTER_H = 48
MIN_TEXT_LEN = 10


def main():
    raw_files = glob.glob("data/raw/reddit_raw_*.csv")
    if not raw_files:
        print("No raw files found in data/raw/. Run 01_collect_reddit.py first,")
        print("or run 00_make_synthetic_data.py for synthetic data.")
        return

    dfs = []
    for f in raw_files:
        df = pd.read_csv(f)
        dfs.append(df)
        print(f"Loaded {len(df)} rows from {f}")

    combined = pd.concat(dfs, ignore_index=True)

    # Filter to event window
    combined = combined[
        (combined["hours_from_event"] >= -WINDOW_BEFORE_H) &
        (combined["hours_from_event"] <= WINDOW_AFTER_H)
    ]

    # Drop rows with missing or very short text
    combined = combined[combined["text"].fillna("").str.len() >= MIN_TEXT_LEN]

    # Deduplicate by comment_id
    combined = combined.drop_duplicates(subset=["comment_id"])

    combined = combined.reset_index(drop=True)

    os.makedirs("data/processed", exist_ok=True)
    out_path = "data/processed/comments.csv"
    combined.to_csv(out_path, index=False)

    print(f"\nSaved {len(combined)} rows to {out_path}")
    print(combined["source_type"].value_counts())
    print(combined.groupby("event_id").size())


if __name__ == "__main__":
    main()
