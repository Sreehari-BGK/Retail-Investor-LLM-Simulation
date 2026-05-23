"""
04_compute_metrics.py
Core similarity metrics for comparing real vs simulated investor comment distributions.

Metrics
-------
1. MMD (Maximum Mean Discrepancy) with RBF kernel
   — Semantic/content similarity via SBERT embeddings
   — A kernel two-sample statistic: MMD=0 iff distributions are identical under the kernel.
   — Uses median heuristic for bandwidth selection (Gretton et al., 2012).

2. JSD (Jensen-Shannon Divergence) on stance distributions
   — Measures similarity of bullish/bearish/neutral proportions.
   — JSD ∈ [0, 1] (base-2 bits); 0 = identical, 1 = maximally different.
   — Symmetric, bounded: preferable to KL for finite samples.

3. Wasserstein-1 distance on temporal (hourly) distributions
   — Compares posting-volume profiles over the event window.
   — Optimal-transport distance that respects the metric structure of time.
   — Computed via scipy.stats.wasserstein_distance on histogram supports.

References
----------
- Gretton et al. (2012). A Kernel Two-Sample Test. JMLR 13, 723–773.
- Lin (1991). Divergence measures based on the Shannon entropy. IEEE Trans. Inf. Theory.
- Villani (2009). Optimal Transport: Old and New. Springer.
"""

import numpy as np
from collections import Counter
from scipy.spatial.distance import jensenshannon
from scipy.stats import wasserstein_distance
from sklearn.metrics.pairwise import rbf_kernel


# ---------------------------------------------------------------------------
# Stance similarity — JSD
# ---------------------------------------------------------------------------

STANCE_LABELS = ["bullish", "bearish", "neutral"]


def label_distribution(labels, label_order=STANCE_LABELS):
    """Normalised frequency vector over label_order."""
    counts = np.array([Counter(labels).get(lab, 0) for lab in label_order],
                      dtype=float)
    total = counts.sum()
    if total == 0:
        return np.ones(len(label_order)) / len(label_order)  # uniform fallback
    return counts / total


def jsd_stance(real_labels, sim_labels, label_order=STANCE_LABELS) -> float:
    """
    Jensen-Shannon divergence between real and simulated stance distributions.
    Returns a value in [0, 1] (base-2). Lower = more similar.
    """
    p = label_distribution(real_labels, label_order)
    q = label_distribution(sim_labels, label_order)
    return float(jensenshannon(p, q, base=2))


# ---------------------------------------------------------------------------
# Temporal similarity — Wasserstein distance on hourly histograms
# ---------------------------------------------------------------------------

def binned_time_distribution(hours_from_event,
                              start_h: float = -24,
                              end_h: float = 48,
                              bin_size: float = 1.0):
    """
    Bin hours_from_event values into a normalised histogram.
    Returns (hist, bin_centres) where hist sums to 1.
    """
    bins = np.arange(start_h, end_h + bin_size, bin_size)
    hist, _ = np.histogram(hours_from_event, bins=bins)
    hist = hist.astype(float)
    if hist.sum() > 0:
        hist /= hist.sum()
    # bin centres as integer support for Wasserstein
    bin_centres = np.arange(len(hist))
    return hist, bin_centres


def wasserstein_time(real_hours, sim_hours,
                     start_h: float = -24,
                     end_h: float = 48,
                     bin_size: float = 1.0) -> float:
    """
    Wasserstein-1 distance between real and simulated temporal distributions.
    Uses normalised hourly histograms as discrete probability measures.
    Lower = more similar posting-volume profiles.
    """
    p, support = binned_time_distribution(real_hours, start_h, end_h, bin_size)
    q, _ = binned_time_distribution(sim_hours, start_h, end_h, bin_size)
    return float(wasserstein_distance(support, support,
                                      u_weights=p, v_weights=q))


# ---------------------------------------------------------------------------
# Semantic similarity — MMD with RBF kernel
# ---------------------------------------------------------------------------

def _median_bandwidth(X: np.ndarray, Y: np.ndarray) -> float:
    """Median heuristic for RBF bandwidth (Gretton et al., 2012)."""
    Z = np.vstack([X, Y])
    # Squared pairwise distances — sample up to 2000 points for speed
    if len(Z) > 2000:
        idx = np.random.choice(len(Z), 2000, replace=False)
        Z = Z[idx]
    dists_sq = np.sum((Z[:, None, :] - Z[None, :, :]) ** 2, axis=-1)
    nonzero = dists_sq[dists_sq > 0]
    median_sq = float(np.median(nonzero)) if len(nonzero) > 0 else 1.0
    return 1.0 / (2.0 * median_sq)


def mmd_rbf(X: np.ndarray, Y: np.ndarray, gamma: float = None) -> float:
    """
    Maximum Mean Discrepancy with RBF kernel.
    MMD^2 = E[k(x,x')] + E[k(y,y')] - 2*E[k(x,y)]
    where k(u,v) = exp(-gamma * ||u-v||^2).

    Positive values indicate distributional divergence.
    Near-zero values indicate the two sets are likely from the same distribution.

    Parameters
    ----------
    X : array (n, d)  — real embeddings
    Y : array (m, d)  — simulated embeddings
    gamma : float     — RBF bandwidth; if None, uses median heuristic

    Returns float (biased estimator of MMD^2).
    """
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)

    if gamma is None:
        gamma = _median_bandwidth(X, Y)

    Kxx = rbf_kernel(X, X, gamma=gamma)
    Kyy = rbf_kernel(Y, Y, gamma=gamma)
    Kxy = rbf_kernel(X, Y, gamma=gamma)

    return float(Kxx.mean() + Kyy.mean() - 2.0 * Kxy.mean())


# ---------------------------------------------------------------------------
# Convenience: compute all metrics at once
# ---------------------------------------------------------------------------

def compute_all_metrics(real_df, sim_df, real_emb, sim_emb) -> dict:
    """
    Parameters
    ----------
    real_df  : DataFrame with columns [stance, hours_from_event]
    sim_df   : DataFrame with columns [stance, hours_from_event]
    real_emb : np.ndarray (n, d)
    sim_emb  : np.ndarray (m, d)

    Returns dict with keys: jsd_stance, wasserstein_time, mmd_semantic
    """
    return {
        "jsd_stance": jsd_stance(
            real_df["stance"].tolist(),
            sim_df["stance"].tolist(),
        ),
        "wasserstein_time": wasserstein_time(
            real_df["hours_from_event"].to_numpy(),
            sim_df["hours_from_event"].to_numpy(),
        ),
        "mmd_semantic": mmd_rbf(real_emb, sim_emb),
    }


if __name__ == "__main__":
    # Quick self-test with random data
    import pandas as pd

    np.random.seed(0)
    n = 100

    real_df = pd.DataFrame({
        "stance": np.random.choice(["bullish", "bearish", "neutral"],
                                   size=n, p=[0.5, 0.3, 0.2]),
        "hours_from_event": np.random.normal(4, 6, size=n).clip(-24, 48),
    })
    sim_df = pd.DataFrame({
        "stance": np.random.choice(["bullish", "bearish", "neutral"],
                                   size=n, p=[0.5, 0.3, 0.2]),
        "hours_from_event": np.random.normal(4, 6, size=n).clip(-24, 48),
    })
    real_emb = np.random.randn(n, 64)
    sim_emb = real_emb + np.random.randn(n, 64) * 0.1  # close distributions

    metrics = compute_all_metrics(real_df, sim_df, real_emb, sim_emb)
    print("Self-test metrics (similar distributions, expect small values):")
    for k, v in metrics.items():
        print(f"  {k}: {v:.6f}")
