"""
06_explore_data.py
Basic exploratory data analysis — produces summary tables and figures
that can be included in the revised draft's Data section.

Run:
    python 06_explore_data.py

Outputs (all in outputs/):
    eda_summary.txt              — text statistics
    eda_temporal_distribution.png
    eda_stance_distribution.png
    eda_score_distribution.png
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV_PATH = "data/processed/comments.csv"
INDEX_CSV = "data/processed/comments_with_index.csv"


def load():
    path = INDEX_CSV if os.path.exists(INDEX_CSV) else CSV_PATH
    if not os.path.exists(path):
        print("ERROR: No processed data found. Run 00_make_synthetic_data.py first.")
        sys.exit(1)
    return pd.read_csv(path)


def print_summary(df, f=None):
    lines = []
    lines.append("=" * 60)
    lines.append("DATASET SUMMARY")
    lines.append("=" * 60)
    lines.append(f"Total comments         : {len(df)}")
    lines.append(f"Events                 : {df['event_id'].nunique()}")
    lines.append(f"Subreddits             : {df['subreddit'].nunique()}")
    lines.append(f"Source types           : {dict(df['source_type'].value_counts())}")
    lines.append("")
    lines.append("Per-event comment counts:")
    lines.append(df.groupby(["event_id", "source_type"]).size()
                 .unstack(fill_value=0).to_string())
    lines.append("")
    lines.append("Stance distribution (real only):")
    real = df[df["source_type"] == "real"]
    lines.append(real["stance"].value_counts(normalize=True)
                 .mul(100).round(1).to_string() + " %")
    lines.append("")
    lines.append("Temporal range (hours from event):")
    lines.append(f"  min : {df['hours_from_event'].min():.1f}")
    lines.append(f"  max : {df['hours_from_event'].max():.1f}")
    lines.append(f"  mean: {df['hours_from_event'].mean():.1f}")
    lines.append(f"  std : {df['hours_from_event'].std():.1f}")
    lines.append("=" * 60)

    text = "\n".join(lines)
    print(text)
    if f:
        f.write(text + "\n")


def plot_temporal(df):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for ax, source_type, title in zip(
        axes,
        ["real", "sim_naive"],
        ["Real Reddit Comments", "Naive Simulation (Baseline)"],
    ):
        subset = df[df["source_type"] == source_type]
        if len(subset) == 0:
            ax.set_title(title + " — no data")
            continue
        bins = np.arange(-24, 49, 1)
        ax.hist(subset["hours_from_event"], bins=bins,
                color="#4878CF" if source_type == "real" else "#D65F5F",
                alpha=0.7, edgecolor="white", linewidth=0.3)
        ax.axvline(0, color="black", linestyle="--", linewidth=1.2,
                   label="Event time")
        ax.set_xlabel("Hours from earnings announcement")
        ax.set_ylabel("Comment count")
        ax.set_title(title)
        ax.legend()

    fig.suptitle("Temporal Distribution of Comments Around Earnings Announcement",
                 fontsize=12)
    plt.tight_layout()
    out = "outputs/eda_temporal_distribution.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


def plot_stance(df):
    real = df[df["source_type"] == "real"]
    sim = df[df["source_type"] == "sim_naive"]

    labels = ["bullish", "bearish", "neutral"]

    def proportions(subset):
        counts = subset["stance"].value_counts()
        total = max(counts.sum(), 1)
        return [counts.get(l, 0) / total for l in labels]

    x = np.arange(len(labels))
    w = 0.35
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(x - w / 2, proportions(real), w, label="Real", color="#4878CF", alpha=0.8)
    if len(sim) > 0:
        ax.bar(x + w / 2, proportions(sim), w, label="Naive Sim",
               color="#D65F5F", alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Proportion")
    ax.set_title("Stance Distribution: Real vs Naive Simulation")
    ax.legend()
    plt.tight_layout()
    out = "outputs/eda_stance_distribution.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


def plot_score(df):
    real = df[df["source_type"] == "real"]
    fig, ax = plt.subplots(figsize=(7, 4))
    scores = real["score"].clip(0, 200)
    ax.hist(scores, bins=30, color="#6ACC65", alpha=0.8, edgecolor="white")
    ax.set_xlabel("Comment score (upvotes, clipped at 200)")
    ax.set_ylabel("Count")
    ax.set_title("Score Distribution — Real Reddit Comments")
    plt.tight_layout()
    out = "outputs/eda_score_distribution.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


def main():
    os.makedirs("outputs", exist_ok=True)
    df = load()

    with open("outputs/eda_summary.txt", "w") as f:
        print_summary(df, f)

    plot_temporal(df)
    plot_stance(df)
    plot_score(df)

    print("\nAll EDA outputs saved to outputs/")


if __name__ == "__main__":
    main()
