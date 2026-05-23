"""
05_sanity_checks.py
Three-part pilot validation experiment.

Purpose
-------
Before running the full simulation, we validate that the proposed similarity
metrics behave in the expected direction using real data alone:

  Test A — Real vs Real
    Split real comments into two random halves. Metrics should be relatively
    small, indicating the distributions are similar (same data source).

  Test B — Real vs Shuffled Timestamps
    Keep comments identical but randomly permute their hours_from_event values
    in one half. The temporal Wasserstein distance should increase noticeably
    while stance JSD and semantic MMD remain unchanged.

  Test C — Real vs Naive Simulation
    Compare real comments against a naive synthetic baseline (generic prompts,
    no archetypes, no agent interaction). All three metrics should be larger
    than in Test A, confirming the metrics can discriminate closer vs more
    distant distributions.

Expected ordering (lower = more similar):
    Test A ≤ Tests B/C   (for the respective metric)

Run:
    python 05_sanity_checks.py

Dependencies:
    Run 00_make_synthetic_data.py (or 02_prepare_event_windows.py) and
    03_embed_comments.py first.
"""

import sys
import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Allow running from the scripts/ directory or the project root
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _scripts_dir)
# Rename 04_compute_metrics module — import via importlib since name starts with digit
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "compute_metrics",
    os.path.join(_scripts_dir, "04_compute_metrics.py"),
)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
jsd_stance = _mod.jsd_stance
wasserstein_time = _mod.wasserstein_time
mmd_rbf = _mod.mmd_rbf

INDEX_CSV = "data/processed/comments_with_index.csv"
EMB_NPY = "data/processed/comment_embeddings.npy"
FALLBACK_CSV = "data/processed/comments.csv"
RANDOM_STATE = 42


def load_data():
    # Prefer the index CSV produced by 03_embed_comments.py; fall back to raw
    csv_path = INDEX_CSV if os.path.exists(INDEX_CSV) else FALLBACK_CSV
    if not os.path.exists(csv_path):
        print("ERROR: No processed CSV found. Run 00_make_synthetic_data.py first.")
        sys.exit(1)

    df = pd.read_csv(csv_path)

    if os.path.exists(EMB_NPY):
        emb = np.load(EMB_NPY)
        print(f"Loaded embeddings: {emb.shape}")
    else:
        print("WARNING: No embeddings found. MMD will use random placeholders.")
        print("         Run 03_embed_comments.py to get real SBERT embeddings.")
        emb = np.random.randn(len(df), 384).astype(np.float32)
        # Normalise rows to unit sphere (mirrors what SBERT produces)
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        emb = emb / np.where(norms == 0, 1, norms)

    assert len(df) == len(emb), (
        f"Row count mismatch: CSV has {len(df)}, embeddings have {len(emb)}"
    )
    return df, emb


def run_sanity_checks(df, emb):
    results = {}

    # -----------------------------------------------------------------------
    # Split real vs naive sim
    # -----------------------------------------------------------------------
    real_mask = df["source_type"] == "real"
    sim_mask = df["source_type"] == "sim_naive"

    real_idx = np.where(real_mask)[0]
    sim_idx = np.where(sim_mask)[0]

    if len(real_idx) < 10:
        print("ERROR: Fewer than 10 real comments found. Check your data.")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Test A — Real vs Real (split-half)
    # -----------------------------------------------------------------------
    a_idx, b_idx = train_test_split(real_idx, test_size=0.5,
                                    random_state=RANDOM_STATE)

    jsd_rr = jsd_stance(df.iloc[a_idx]["stance"].tolist(),
                        df.iloc[b_idx]["stance"].tolist())
    wd_rr = wasserstein_time(df.iloc[a_idx]["hours_from_event"].to_numpy(),
                             df.iloc[b_idx]["hours_from_event"].to_numpy())
    mmd_rr = mmd_rbf(emb[a_idx], emb[b_idx])

    results["A_real_vs_real"] = {
        "jsd_stance": jsd_rr,
        "wasserstein_time": wd_rr,
        "mmd_semantic": mmd_rr,
    }
    print("\n--- Test A: Real vs Real (split-half) ---")
    print(f"  JSD stance      : {jsd_rr:.6f}")
    print(f"  Wasserstein time: {wd_rr:.6f}")
    print(f"  MMD semantic    : {mmd_rr:.6f}")

    # -----------------------------------------------------------------------
    # Test B — Real vs Shuffled timestamps
    # -----------------------------------------------------------------------
    shuffled_hours = (
        df.iloc[b_idx]["hours_from_event"]
        .sample(frac=1, random_state=RANDOM_STATE)
        .to_numpy()
    )
    wd_shuf = wasserstein_time(df.iloc[a_idx]["hours_from_event"].to_numpy(),
                               shuffled_hours)

    results["B_real_vs_shuffled"] = {
        "jsd_stance": jsd_rr,       # unchanged — same comments, same stances
        "wasserstein_time": wd_shuf,
        "mmd_semantic": mmd_rr,     # unchanged — same embeddings
    }
    print("\n--- Test B: Real vs Shuffled Timestamps ---")
    print(f"  JSD stance      : {jsd_rr:.6f}  (unchanged - stances not shuffled)")
    print(f"  Wasserstein time: {wd_shuf:.6f}  (expect > Test A)")
    print(f"  MMD semantic    : {mmd_rr:.6f}  (unchanged - text not shuffled)")

    # -----------------------------------------------------------------------
    # Test C — Real vs Naive Simulation
    # -----------------------------------------------------------------------
    if len(sim_idx) == 0:
        print("\n--- Test C: skipped - no sim_naive rows in dataset ---")
    else:
        jsd_rs = jsd_stance(df.iloc[real_idx]["stance"].tolist(),
                            df.iloc[sim_idx]["stance"].tolist())
        wd_rs = wasserstein_time(df.iloc[real_idx]["hours_from_event"].to_numpy(),
                                 df.iloc[sim_idx]["hours_from_event"].to_numpy())
        mmd_rs = mmd_rbf(emb[real_idx], emb[sim_idx])

        results["C_real_vs_naive_sim"] = {
            "jsd_stance": jsd_rs,
            "wasserstein_time": wd_rs,
            "mmd_semantic": mmd_rs,
        }
        print("\n--- Test C: Real vs Naive Simulation ---")
        print(f"  JSD stance      : {jsd_rs:.6f}  (expect >= Test A)")
        print(f"  Wasserstein time: {wd_rs:.6f}  (expect >= Test A)")
        print(f"  MMD semantic    : {mmd_rs:.6f}  (expect >= Test A)")

    return results


def plot_results(results):
    os.makedirs("outputs", exist_ok=True)

    labels = list(results.keys())
    metrics = ["jsd_stance", "wasserstein_time", "mmd_semantic"]
    metric_labels = ["JSD Stance", "Wasserstein Time", "MMD Semantic"]
    colors = ["#4878CF", "#6ACC65", "#D65F5F"]

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, metric, mlabel, color in zip(axes, metrics, metric_labels, colors):
        values = [results[l].get(metric, 0.0) for l in labels]
        bars = ax.bar(range(len(labels)), values, color=color, alpha=0.8)
        ax.set_title(mlabel)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(
            [l.replace("_", "\n") for l in labels],
            fontsize=7
        )
        ax.set_ylabel("Distance (lower = more similar)")
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.001,
                    f"{val:.4f}", ha="center", va="bottom", fontsize=8)

    fig.suptitle("Pilot Sanity Checks - Metric Validation", fontsize=13)
    plt.tight_layout()
    out_path = "outputs/sanity_check_results.png"
    plt.savefig(out_path, dpi=150)
    print(f"\nPlot saved to {out_path}")


def main():
    df, emb = load_data()

    print(f"\nDataset summary:")
    print(df["source_type"].value_counts().to_string())
    print(df.groupby("event_id").size().to_string())

    results = run_sanity_checks(df, emb)
    plot_results(results)

    print("\n--- Summary ---")
    print("Expected pattern for valid metrics:")
    print("  Wasserstein(B) > Wasserstein(A)  - shuffled timeline should be worse")
    if "C_real_vs_naive_sim" in results:
        print("  MMD(C) > MMD(A)                  - naive sim should be more distant")
        print("  JSD(C) >= JSD(A)                 - naive sim stance may differ")


if __name__ == "__main__":
    main()
