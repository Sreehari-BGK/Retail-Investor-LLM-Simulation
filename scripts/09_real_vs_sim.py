#!/usr/bin/env python3
"""
09_real_vs_sim.py — Real vs simulated comparison metrics
=========================================================
Compares sim_comments.csv (NVDA_Q3FY26 pilot simulation) against
real_comments_curated_labeled.csv (NVDA_Q3FY26 real Reddit data).

Metrics (from 04_compute_metrics.py)
--------------------------------------
  JSD stance       : stance distribution similarity
  Wasserstein time : temporal posting-volume profile similarity
  MMD semantic     : embedding-space similarity (SBERT)

Outputs
-------
outputs/real_vs_sim_metrics.json
outputs/real_vs_sim_summary.png
"""

import importlib.util
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

ROOT    = Path(__file__).resolve().parent.parent
DATA    = ROOT / "data" / "processed"
OUT     = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

EVENT_ID = "NVDA_Q3FY26"


def _load_metrics_module():
    """Dynamically import 04_compute_metrics.py (name starts with digit)."""
    spec = importlib.util.spec_from_file_location(
        "compute_metrics",
        ROOT / "scripts" / "04_compute_metrics.py"
    )
    cm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cm)
    return cm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_real_data():
    """Load real NVDA_Q3FY26 curated labeled comments."""
    path = DATA / "real_comments_curated_labeled.csv"
    df = pd.read_csv(path)
    nvda = df[df["event_id"] == EVENT_ID].copy()
    print(f"  Real NVDA rows: {len(nvda)}")
    return nvda


def load_sim_data():
    """Load simulated NVDA_Q3FY26 comments."""
    path = DATA / "sim_comments.csv"
    df = pd.read_csv(path)
    print(f"  Sim NVDA rows: {len(df)}")
    return df


def load_real_embeddings(real_df: pd.DataFrame) -> np.ndarray:
    """Load pre-computed SBERT embeddings for real NVDA comments."""
    emb_path = DATA / "real_comment_embeddings_curated.npy"
    all_emb  = np.load(emb_path)
    all_real = pd.read_csv(DATA / "real_comments_curated_labeled.csv")
    nvda_mask = (all_real["event_id"] == EVENT_ID).values
    emb = all_emb[nvda_mask]
    print(f"  Real embeddings shape: {emb.shape}")
    return emb


def embed_sim_comments(texts: list[str]) -> np.ndarray:
    """Embed sim texts using SBERT (same model as real embeddings)."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("  WARNING: sentence-transformers not found. Using random embeddings for MMD.")
        print("          Install with: pip install sentence-transformers")
        return np.random.randn(len(texts), 384).astype(np.float32)

    print(f"  Embedding {len(texts)} sim comments with SBERT...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = model.encode(texts, batch_size=64, show_progress_bar=False,
                       normalize_embeddings=True)
    print(f"  Sim embeddings shape: {emb.shape}")
    return emb


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(real_df, sim_df, real_emb, sim_emb) -> dict:
    jsd   = jsd_stance(real_df["stance"].tolist(), sim_df["stance"].tolist())
    wass  = wasserstein_time(
        real_df["hours_from_event"].to_numpy(),
        sim_df["hours_from_event"].to_numpy(),
    )
    # Subsample for MMD speed (max 500 per set)
    MAX_MMD = 500
    rx = real_emb if len(real_emb) <= MAX_MMD else real_emb[
        np.random.choice(len(real_emb), MAX_MMD, replace=False)]
    sx = sim_emb  if len(sim_emb)  <= MAX_MMD else sim_emb[
        np.random.choice(len(sim_emb),  MAX_MMD, replace=False)]
    mmd = mmd_rbf(rx, sx)

    return {
        "event_id":          EVENT_ID,
        "n_real":            int(len(real_df)),
        "n_sim":             int(len(sim_df)),
        "jsd_stance":        round(float(jsd),  6),
        "wasserstein_time":  round(float(wass), 6),
        "mmd_semantic":      round(float(mmd),  6),
        "notes": {
            "jsd_range":          "[0, 1] — lower is more similar",
            "wasserstein_range":  "[0, ∞) — lower is more similar (hourly bins)",
            "mmd_range":          "[0, ∞) — lower is more similar; near-zero = same distribution",
            "mmd_subsampled":     f"Subsampled to {MAX_MMD} per set for speed",
            "stance_labels_real": "provisional keyword-based labels (see STANCE_LABEL_AUDIT.md)",
            "stance_labels_sim":  "assigned by rule during simulation",
            "text_generation":    "template-based (not LLM); expect elevated MMD",
        }
    }


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------

def plot_comparison(real_df: pd.DataFrame, sim_df: pd.DataFrame, metrics: dict):
    fig = plt.figure(figsize=(15, 10))
    fig.suptitle(f"Real vs Simulated Comparison — {EVENT_ID}\n"
                 f"(n_real={metrics['n_real']}, n_sim={metrics['n_sim']})",
                 fontsize=13, y=0.98)

    # ---- Panel 1: Stance distribution ----
    ax1 = fig.add_subplot(2, 3, 1)
    stances = ["bullish", "bearish", "neutral"]
    colours = {"bullish": "#4CAF50", "bearish": "#F44336", "neutral": "#9E9E9E"}
    real_pct = [(real_df["stance"] == s).mean() for s in stances]
    sim_pct  = [(sim_df["stance"]  == s).mean() for s in stances]
    x = np.arange(len(stances))
    w = 0.35
    bars1 = ax1.bar(x - w/2, real_pct, w, label="Real",
                    color=[colours[s] for s in stances], alpha=0.7)
    bars2 = ax1.bar(x + w/2, sim_pct,  w, label="Sim",
                    color=[colours[s] for s in stances], alpha=0.4, hatch="//")
    ax1.set_xticks(x); ax1.set_xticklabels(stances, fontsize=9)
    ax1.set_ylabel("Proportion"); ax1.set_title("Stance Distribution")
    ax1.set_ylim(0, 1)
    ax1.legend(fontsize=8)
    ax1.text(0.98, 0.98, f"JSD={metrics['jsd_stance']:.4f}",
             ha="right", va="top", transform=ax1.transAxes,
             fontsize=9, color="#333333",
             bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFFDE7"))

    # ---- Panel 2: Temporal distribution ----
    ax2 = fig.add_subplot(2, 3, 2)
    bins = np.arange(-2, 49, 2)
    ax2.hist(real_df["hours_from_event"], bins=bins, density=True,
             alpha=0.6, color="#2196F3", label="Real")
    ax2.hist(sim_df["hours_from_event"],  bins=bins, density=True,
             alpha=0.6, color="#FF9800", label="Sim")
    ax2.axvline(0, color="black", linestyle="--", alpha=0.5, label="Event time")
    ax2.set_xlabel("Hours from event"); ax2.set_ylabel("Density")
    ax2.set_title("Temporal Distribution")
    ax2.legend(fontsize=8)
    ax2.text(0.98, 0.98, f"W₁={metrics['wasserstein_time']:.2f}h",
             ha="right", va="top", transform=ax2.transAxes,
             fontsize=9, color="#333333",
             bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFFDE7"))

    # ---- Panel 3: Metrics bar chart ----
    ax3 = fig.add_subplot(2, 3, 3)
    metric_names  = ["JSD\n(stance)", "Wasserstein\n(temporal)", "MMD\n(semantic)"]
    metric_values = [metrics["jsd_stance"],
                     metrics["wasserstein_time"],
                     metrics["mmd_semantic"]]
    # Normalise for visibility  (rough scale — display actual values as labels)
    norm_values = [metrics["jsd_stance"],               # already [0,1]
                   metrics["wasserstein_time"] / 50.0,  # normalise to ~[0,1]
                   metrics["mmd_semantic"]]              # rough [0,1]
    bar_colours = ["#9C27B0", "#2196F3", "#FF9800"]
    bars = ax3.bar(metric_names, norm_values, color=bar_colours, alpha=0.75)
    ax3.set_ylim(0, max(max(norm_values) * 1.3, 0.5))
    ax3.set_ylabel("Normalised score (lower = more similar)")
    ax3.set_title("Three Similarity Metrics")
    for bar, val in zip(bars, metric_values):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                 f"{val:.4f}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    # ---- Panel 4: Stance per round (sim) ----
    ax4 = fig.add_subplot(2, 3, 4)
    rounds = sorted(sim_df["round_id"].unique())
    bull_r = [(sim_df[sim_df["round_id"] == r]["stance"] == "bullish").mean() for r in rounds]
    bear_r = [(sim_df[sim_df["round_id"] == r]["stance"] == "bearish").mean() for r in rounds]
    neut_r = [(sim_df[sim_df["round_id"] == r]["stance"] == "neutral").mean() for r in rounds]
    ax4.stackplot(rounds, bull_r, neut_r, bear_r,
                  labels=["bullish", "neutral", "bearish"],
                  colors=["#4CAF50", "#9E9E9E", "#F44336"], alpha=0.75)
    ax4.set_xlabel("Round"); ax4.set_ylabel("Proportion")
    ax4.set_title("Sim: Stance by Round")
    ax4.set_xticks(rounds)
    handles = [mpatches.Patch(color=c, label=l) for l, c in
               [("bullish","#4CAF50"), ("neutral","#9E9E9E"), ("bearish","#F44336")]]
    ax4.legend(handles=handles, fontsize=7, loc="upper right")

    # ---- Panel 5: Comment volume per round (real vs sim) ----
    ax5 = fig.add_subplot(2, 3, 5)
    round_bins = [-2, 0, 6, 12, 24, 48]
    round_lbl  = ["R0\n(-2→0h)", "R1\n(0→6h)", "R2\n(6→12h)", "R3\n(12→24h)", "R4\n(24→48h)"]
    real_vol = np.histogram(real_df["hours_from_event"], bins=round_bins)[0]
    sim_vol  = np.histogram(sim_df["hours_from_event"],  bins=round_bins)[0]
    # Normalise
    real_vol_n = real_vol / real_vol.sum() if real_vol.sum() > 0 else real_vol
    sim_vol_n  = sim_vol  / sim_vol.sum()  if sim_vol.sum()  > 0 else sim_vol
    xr = np.arange(len(round_lbl))
    ax5.bar(xr - 0.2, real_vol_n, 0.4, label="Real", color="#2196F3", alpha=0.7)
    ax5.bar(xr + 0.2, sim_vol_n,  0.4, label="Sim",  color="#FF9800", alpha=0.7)
    ax5.set_xticks(xr); ax5.set_xticklabels(round_lbl, fontsize=8)
    ax5.set_ylabel("Proportion of comments")
    ax5.set_title("Volume Profile by Round")
    ax5.legend(fontsize=8)

    # ---- Panel 6: Text metrics summary box ----
    ax6 = fig.add_subplot(2, 3, 6)
    ax6.axis("off")
    sanity_ref = {"jsd": 0.017, "wass": 0.39, "mmd": 0.001}  # real-vs-real baseline from audit
    summary_text = (
        f"METRIC SUMMARY\n"
        f"{'─'*38}\n"
        f"  JSD (stance)       : {metrics['jsd_stance']:.4f}\n"
        f"  Wasserstein (time) : {metrics['wasserstein_time']:.4f}\n"
        f"  MMD (semantic)     : {metrics['mmd_semantic']:.4f}\n\n"
        f"REFERENCE BASELINE (real-vs-real)\n"
        f"{'─'*38}\n"
        f"  JSD                : {sanity_ref['jsd']:.3f}\n"
        f"  Wasserstein        : {sanity_ref['wass']:.2f}\n"
        f"  MMD                : {sanity_ref['mmd']:.3f}\n\n"
        f"INTERPRETATION\n"
        f"{'─'*38}\n"
        f"  JSD close to real-vs-real →\n"
        f"    stance distribution similar\n"
        f"  High MMD expected →\n"
        f"    template text ≠ real Reddit\n"
        f"  Wasserstein gap →\n"
        f"    sim uses 5 discrete rounds;\n"
        f"    real data is continuous"
    )
    ax6.text(0.05, 0.95, summary_text, ha="left", va="top",
             fontsize=8.5, fontfamily="monospace",
             transform=ax6.transAxes,
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#F5F5F5", alpha=0.8))

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    path = OUT / "real_vs_sim_summary.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("09_real_vs_sim.py — Real vs Sim Comparison")
    print("=" * 60)

    cm = _load_metrics_module()

    print("\n  Loading data...")
    real_df = load_real_data()
    sim_df  = load_sim_data()

    print("\n  Loading real embeddings...")
    real_emb = load_real_embeddings(real_df)

    print("\n  Embedding sim comments...")
    sim_emb = embed_sim_comments(sim_df["text"].tolist())

    print("\n  Computing metrics...")
    jsd  = cm.jsd_stance(real_df["stance"].tolist(), sim_df["stance"].tolist())
    wass = cm.wasserstein_time(
        real_df["hours_from_event"].to_numpy(),
        sim_df["hours_from_event"].to_numpy()
    )

    MAX_MMD = 500
    np.random.seed(42)
    rx = real_emb if len(real_emb) <= MAX_MMD else real_emb[
        np.random.choice(len(real_emb), MAX_MMD, replace=False)]
    sx = sim_emb  if len(sim_emb)  <= MAX_MMD else sim_emb[
        np.random.choice(len(sim_emb),  MAX_MMD, replace=False)]
    mmd = cm.mmd_rbf(rx, sx)

    metrics = {
        "event_id":         EVENT_ID,
        "n_real":           int(len(real_df)),
        "n_sim":            int(len(sim_df)),
        "jsd_stance":       round(float(jsd),  6),
        "wasserstein_time": round(float(wass), 6),
        "mmd_semantic":     round(float(mmd),  6),
        "notes": {
            "jsd_range":          "[0, 1] — lower is more similar",
            "wasserstein_range":  "[0, ∞) — lower is more similar (hourly bins)",
            "mmd_range":          "[0, ∞) — lower is more similar; near-zero = same distribution",
            "mmd_subsampled":     f"Subsampled to {MAX_MMD} per set for speed",
            "real_vs_real_baseline_jsd":        "0.017–0.039 (from sanity check audit)",
            "real_vs_real_baseline_wass":       "0.39–1.10",
            "real_vs_real_baseline_mmd":        "~0.001",
            "stance_labels_real":               "provisional keyword-based (STANCE_LABEL_AUDIT.md)",
            "stance_labels_sim":                "rule-assigned during simulation",
            "text_generation":                  "template-based; expect elevated MMD vs real",
            "temporal_gap_explanation":         "Sim uses 5 discrete rounds; real is continuous stream",
        }
    }

    print(f"\n  Results:")
    print(f"    JSD stance      : {metrics['jsd_stance']:.6f}")
    print(f"    Wasserstein time: {metrics['wasserstein_time']:.6f}")
    print(f"    MMD semantic    : {metrics['mmd_semantic']:.6f}")

    # Save JSON
    json_path = OUT / "real_vs_sim_metrics.json"
    json_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"\n  Saved: {json_path}")

    print("\n  Plotting comparison...")
    plot_comparison(real_df, sim_df, metrics)

    print("\nDone.")


if __name__ == "__main__":
    main()
