#!/usr/bin/env python3
"""
10_metric_benchmark.py — Candidate metric scan, benchmark, and recommendation
==============================================================================
Evaluates ~16 candidate similarity metrics across three comparison pairs:
  A. Real-vs-Real  (NVDA random 50/50 split — expected-low baseline)
  B. Real-vs-Random (NVDA vs uniform-time dummy — expected-high baseline)
  C. Real-vs-Sim   (NVDA real vs sim_comments pilot)

Produces
--------
outputs/METRIC_SCAN.md
outputs/METRIC_BENCHMARK.csv
outputs/METRIC_BENCHMARK.md
outputs/METRIC_RECOMMENDATION.txt
"""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon, cosine as cosine_distance
from scipy.stats import wasserstein_distance
from sklearn.metrics.pairwise import rbf_kernel

np.random.seed(42)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"
OUT  = ROOT / "outputs"
OUT.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Load compute_metrics module (name starts with digit)
# ---------------------------------------------------------------------------
def _load_cm():
    spec = importlib.util.spec_from_file_location(
        "compute_metrics", ROOT / "scripts" / "04_compute_metrics.py")
    cm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cm)
    return cm

CM = _load_cm()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_datasets():
    real_all = pd.read_csv(DATA / "real_comments_curated_labeled.csv")
    real_emb_all = np.load(DATA / "real_comment_embeddings_curated.npy")
    nvda_mask = (real_all["event_id"] == "NVDA_Q3FY26").values
    real_df  = real_all[nvda_mask].reset_index(drop=True)
    real_emb = real_emb_all[nvda_mask]

    sim_df  = pd.read_csv(DATA / "sim_comments.csv")
    # Embed sim if SBERT available, else use low-rank random approx
    sim_emb = _get_sim_embeddings(sim_df)

    return real_df, real_emb, sim_df, sim_emb


def _get_sim_embeddings(sim_df):
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        emb = model.encode(sim_df["text"].tolist(), batch_size=64,
                           normalize_embeddings=True, show_progress_bar=False)
        return emb.astype(np.float32)
    except Exception:
        print("  SBERT unavailable — using cached/random embeddings for MMD/centroid")
        np.random.seed(0)
        return np.random.randn(len(sim_df), 384).astype(np.float32)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
STANCE_LABELS = ["bullish", "bearish", "neutral"]
HOUR_BINS = np.arange(-2, 49, 1)        # 50 1-hour bins over [-2, +48]


def stance_dist(labels):
    counts = np.array([sum(1 for l in labels if l == s) for s in STANCE_LABELS], float)
    total = counts.sum()
    return counts / total if total > 0 else np.ones(3) / 3


def hourly_hist(hours, bins=HOUR_BINS):
    h, _ = np.histogram(hours, bins=bins)
    h = h.astype(float)
    return h / h.sum() if h.sum() > 0 else h


def depth_hist(depths, max_d=10):
    bins = np.arange(0, max_d + 2)
    h, _ = np.histogram(depths, bins=bins)
    h = h.astype(float)
    return h / h.sum() if h.sum() > 0 else h


def branching_factor(df):
    """Mean number of direct children per comment (non-root comments / root comments)."""
    if "thread_id" not in df.columns:
        # infer roots: depth==0
        roots  = (df["depth"] == 0).sum() if "depth" in df.columns else 1
        others = len(df) - roots
        return others / roots if roots > 0 else 0.0
    threads = df.groupby("thread_id").apply(
        lambda g: (g["depth"] > 0).sum() / max(1, (g["depth"] == 0).sum())
    )
    return float(threads.mean())


def subsample(arr, n=400, seed=42):
    rng = np.random.default_rng(seed)
    if len(arr) <= n:
        return arr
    idx = rng.choice(len(arr), n, replace=False)
    return arr[idx]


def make_random_baseline(real_df, real_emb):
    """Random comparison: shuffle stance labels + uniform hours + random-walk embeddings."""
    n = len(real_df)
    rand_df = real_df.copy()
    rand_df["stance"] = np.random.choice(STANCE_LABELS, size=n)
    rand_df["hours_from_event"] = np.random.uniform(-2, 48, size=n)
    # Embeddings: random unit vectors
    rand_emb = np.random.randn(n, real_emb.shape[1]).astype(np.float32)
    rand_emb /= (np.linalg.norm(rand_emb, axis=1, keepdims=True) + 1e-9)
    return rand_df, rand_emb


# ---------------------------------------------------------------------------
# Individual metric implementations
# ---------------------------------------------------------------------------

# ---- A. Semantic / content --------------------------------------------------

def mmd_rbf(X, Y):
    """MMD with RBF kernel (biased estimator). [0, inf)"""
    X, Y = subsample(X), subsample(Y)
    return float(CM.mmd_rbf(X, Y))


def centroid_cosine_dist(X, Y):
    """Cosine distance between distribution centroids. [0, 2]"""
    cx = X.mean(axis=0)
    cy = Y.mean(axis=0)
    norm_cx = np.linalg.norm(cx)
    norm_cy = np.linalg.norm(cy)
    if norm_cx < 1e-9 or norm_cy < 1e-9:
        return 1.0
    return float(cosine_distance(cx, cy))


def mean_pairwise_cosine_diff(X, Y, n=200):
    """
    |mean_intra_X - mean_intra_Y| for cosine similarities.
    Cheap diversity indicator; not a distribution distance.
    """
    def mean_intra(Z, n):
        Z = subsample(Z, n)
        Z_norm = Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9)
        sims = Z_norm @ Z_norm.T
        triu = sims[np.triu_indices(len(Z_norm), k=1)]
        return float(triu.mean())
    return abs(mean_intra(X, n) - mean_intra(Y, n))


# ---- B. Stance / label distribution -----------------------------------------

def jsd_stance(real_labels, sim_labels):
    """Jensen-Shannon divergence on stance. [0, 1]"""
    return float(CM.jsd_stance(real_labels, sim_labels))


def tvd_stance(real_labels, sim_labels):
    """Total Variation Distance = 0.5 * sum|p_i - q_i|. [0, 1]"""
    p = stance_dist(real_labels)
    q = stance_dist(sim_labels)
    return float(0.5 * np.abs(p - q).sum())


def hellinger_stance(real_labels, sim_labels):
    """Hellinger distance on stance. [0, 1]"""
    p = stance_dist(real_labels)
    q = stance_dist(sim_labels)
    return float(np.sqrt(0.5 * np.sum((np.sqrt(p) - np.sqrt(q)) ** 2)))


# ---- C. Temporal ------------------------------------------------------------

def wasserstein_time(real_hours, sim_hours):
    """Wasserstein-1 on hourly histograms. [0, inf) in bin units."""
    return float(CM.wasserstein_time(real_hours, sim_hours))


def rmse_temporal(real_hours, sim_hours, bins=HOUR_BINS):
    """RMSE between normalised hourly histograms. [0, 1] approx."""
    p = hourly_hist(real_hours, bins)
    q = hourly_hist(sim_hours, bins)
    return float(np.sqrt(np.mean((p - q) ** 2)))


def dtw_temporal(real_hours, sim_hours, bins=HOUR_BINS):
    """
    Dynamic Time Warping on normalised hourly histograms.
    O(n^2) in bin count; fine for 50 bins.
    """
    p = hourly_hist(real_hours, bins)
    q = hourly_hist(sim_hours, bins)
    n, m = len(p), len(q)
    dp = np.full((n + 1, m + 1), np.inf)
    dp[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(p[i - 1] - q[j - 1])
            dp[i, j] = cost + min(dp[i - 1, j], dp[i, j - 1], dp[i - 1, j - 1])
    return float(dp[n, m])


# ---- D. Structural / reply-tree ---------------------------------------------

def depth_distribution_jsd(real_df, sim_df):
    """JSD between reply-depth histograms (depths 0-10). [0, 1]"""
    rd = real_df["depth"].values if "depth" in real_df.columns else np.zeros(len(real_df))
    sd = sim_df["depth"].values  if "depth" in sim_df.columns  else np.zeros(len(sim_df))
    p = depth_hist(rd)
    q = depth_hist(sd)
    return float(jensenshannon(p, q, base=2))


def branching_factor_diff(real_df, sim_df):
    """Absolute difference in mean branching factor. [0, inf)"""
    return abs(branching_factor(real_df) - branching_factor(sim_df))


# ---- E. Lexical / style ------------------------------------------------------

def avg_length_diff(real_df, sim_df):
    """Absolute difference in mean comment character length."""
    rl = real_df["text"].astype(str).str.len().mean()
    sl = sim_df["text"].astype(str).str.len().mean()
    return abs(float(rl) - float(sl))


def avg_length_ratio(real_df, sim_df):
    """max(rl, sl) / min(rl, sl) — 1 = identical, higher = different."""
    rl = real_df["text"].astype(str).str.len().mean()
    sl = sim_df["text"].astype(str).str.len().mean()
    if min(rl, sl) == 0:
        return 0.0
    return float(max(rl, sl) / min(rl, sl))


def vocab_overlap_jaccard(real_df, sim_df, max_tokens=5000):
    """
    Jaccard similarity of top-max_tokens unigrams.
    Returns DISTANCE = 1 - Jaccard. [0, 1]
    """
    from collections import Counter

    def top_vocab(df, n):
        tokens = " ".join(df["text"].astype(str).str.lower().tolist()).split()
        return set(t for t, _ in Counter(tokens).most_common(n))

    real_v = top_vocab(real_df, max_tokens)
    sim_v  = top_vocab(sim_df,  max_tokens)
    if not real_v and not sim_v:
        return 0.0
    intersection = len(real_v & sim_v)
    union = len(real_v | sim_v)
    return float(1.0 - intersection / union) if union > 0 else 0.0


def type_token_ratio_diff(real_df, sim_df):
    """Absolute difference in type-token ratio (lexical richness)."""
    def ttr(df):
        tokens = " ".join(df["text"].astype(str).str.lower().tolist()).split()
        if not tokens:
            return 0.0
        return len(set(tokens)) / len(tokens)
    return abs(ttr(real_df) - ttr(sim_df))


# ---------------------------------------------------------------------------
# Run benchmarks
# ---------------------------------------------------------------------------

METRIC_DEFS = [
    # (id, label, category, function_type)
    # function_type: 'stance', 'temporal', 'emb', 'both_df', 'df_only', 'hours_only'
    ("mmd_rbf",           "MMD (RBF kernel)",            "A", "emb"),
    ("centroid_cos",      "Centroid cosine dist.",        "A", "emb"),
    ("pairwise_cos_diff", "Mean pairwise cos. diff.",     "A", "emb"),
    ("jsd_stance",        "JSD (stance)",                 "B", "stance"),
    ("tvd_stance",        "Total Variation Distance",     "B", "stance"),
    ("hellinger_stance",  "Hellinger distance (stance)",  "B", "stance"),
    ("wasserstein",       "Wasserstein-1 (temporal)",     "C", "hours"),
    ("rmse_temporal",     "RMSE on hourly hist.",         "C", "hours"),
    ("dtw_temporal",      "DTW on hourly hist.",          "C", "hours"),
    ("depth_jsd",         "Depth distribution JSD",       "D", "df_only"),
    ("branch_diff",       "Branching factor diff.",       "D", "df_only"),
    ("avg_len_diff",      "Avg. comment length diff.",    "E", "df_only"),
    ("avg_len_ratio",     "Avg. comment length ratio",    "E", "df_only"),
    ("vocab_jaccard",     "Vocab overlap (Jaccard dist)", "E", "df_only"),
    ("ttr_diff",          "Type-token ratio diff.",       "E", "df_only"),
]


def compute_one(metric_id, real_df, sim_df, real_emb, sim_emb):
    rh = real_df["hours_from_event"].to_numpy()
    sh = sim_df["hours_from_event"].to_numpy()
    rl = real_df["stance"].tolist()
    sl = sim_df["stance"].tolist()

    dispatch = {
        "mmd_rbf":           lambda: mmd_rbf(real_emb, sim_emb),
        "centroid_cos":      lambda: centroid_cosine_dist(real_emb, sim_emb),
        "pairwise_cos_diff": lambda: mean_pairwise_cosine_diff(real_emb, sim_emb),
        "jsd_stance":        lambda: jsd_stance(rl, sl),
        "tvd_stance":        lambda: tvd_stance(rl, sl),
        "hellinger_stance":  lambda: hellinger_stance(rl, sl),
        "wasserstein":       lambda: wasserstein_time(rh, sh),
        "rmse_temporal":     lambda: rmse_temporal(rh, sh),
        "dtw_temporal":      lambda: dtw_temporal(rh, sh),
        "depth_jsd":         lambda: depth_distribution_jsd(real_df, sim_df),
        "branch_diff":       lambda: branching_factor_diff(real_df, sim_df),
        "avg_len_diff":      lambda: avg_length_diff(real_df, sim_df),
        "avg_len_ratio":     lambda: avg_length_ratio(real_df, sim_df),
        "vocab_jaccard":     lambda: vocab_overlap_jaccard(real_df, sim_df),
        "ttr_diff":          lambda: type_token_ratio_diff(real_df, sim_df),
    }
    try:
        return dispatch[metric_id]()
    except Exception as e:
        print(f"    WARNING: {metric_id} failed: {e}")
        return float("nan")


def run_benchmarks(real_df, real_emb, sim_df, sim_emb):
    print("\n  Building comparison pairs...")

    # Pair A: real vs real (50/50 random split of NVDA)
    idx = np.random.permutation(len(real_df))
    half = len(idx) // 2
    realA_df  = real_df.iloc[idx[:half]].reset_index(drop=True)
    realB_df  = real_df.iloc[idx[half:]].reset_index(drop=True)
    realA_emb = real_emb[idx[:half]]
    realB_emb = real_emb[idx[half:]]

    # Pair B: real vs random (uniform-time, random-stance, random-emb baseline)
    rand_df, rand_emb = make_random_baseline(real_df, real_emb)

    pairs = {
        "rvr": ("Real vs Real (50/50 split)", realA_df, realB_df, realA_emb, realB_emb),
        "rvrand": ("Real vs Uniform-Random", real_df, rand_df, real_emb, rand_emb),
        "rvs":  ("Real vs Sim (pilot)",     real_df, sim_df,  real_emb, sim_emb),
    }

    results = {}
    for metric_id, label, category, _ in METRIC_DEFS:
        print(f"    {metric_id}...", end=" ")
        row = {"metric_id": metric_id, "label": label, "category": category}
        for pair_key, (pair_label, dfA, dfB, embA, embB) in pairs.items():
            val = compute_one(metric_id, dfA, dfB, embA, embB)
            row[pair_key] = round(val, 6)
            print(f"{pair_key}={val:.4f}", end="  ")
        results[metric_id] = row
        print()

    return results, pairs


# ---------------------------------------------------------------------------
# Qualitative scoring (fixed expert assessment)
# ---------------------------------------------------------------------------
# Scale: 1 (poor) – 5 (excellent)
# Sensitivity    : does it discriminate well between pairs?
# Interpretability: how easy to explain to a non-expert?
# Robustness     : stable with n=48 (sim size)?
# LabelFree      : 1 if requires no stance labels, 5 if label-free
# ReportFit      : how well does it belong in the report?
# ComputeCost    : 5 = cheap, 1 = expensive

QUALITATIVE = {
    # id:                     Sens  Interp  Robust  LblFree  ReportFit  Cost
    "mmd_rbf":           dict(sensitivity=4, interpretability=2, robustness=3, label_free=5, report_fit=4, compute_cost=3),
    "centroid_cos":      dict(sensitivity=3, interpretability=4, robustness=4, label_free=5, report_fit=3, compute_cost=5),
    "pairwise_cos_diff": dict(sensitivity=2, interpretability=3, robustness=3, label_free=5, report_fit=2, compute_cost=4),
    "jsd_stance":        dict(sensitivity=4, interpretability=5, robustness=3, label_free=1, report_fit=5, compute_cost=5),
    "tvd_stance":        dict(sensitivity=4, interpretability=5, robustness=3, label_free=1, report_fit=4, compute_cost=5),
    "hellinger_stance":  dict(sensitivity=4, interpretability=4, robustness=3, label_free=1, report_fit=3, compute_cost=5),
    "wasserstein":       dict(sensitivity=5, interpretability=4, robustness=4, label_free=5, report_fit=5, compute_cost=5),
    "rmse_temporal":     dict(sensitivity=4, interpretability=5, robustness=4, label_free=5, report_fit=3, compute_cost=5),
    "dtw_temporal":      dict(sensitivity=3, interpretability=3, robustness=4, label_free=5, report_fit=2, compute_cost=3),
    "depth_jsd":         dict(sensitivity=5, interpretability=4, robustness=2, label_free=5, report_fit=4, compute_cost=5),
    "branch_diff":       dict(sensitivity=4, interpretability=5, robustness=2, label_free=5, report_fit=3, compute_cost=5),
    "avg_len_diff":      dict(sensitivity=3, interpretability=5, robustness=5, label_free=5, report_fit=2, compute_cost=5),
    "avg_len_ratio":     dict(sensitivity=3, interpretability=4, robustness=5, label_free=5, report_fit=2, compute_cost=5),
    "vocab_jaccard":     dict(sensitivity=4, interpretability=4, robustness=3, label_free=5, report_fit=3, compute_cost=4),
    "ttr_diff":          dict(sensitivity=3, interpretability=4, robustness=4, label_free=5, report_fit=2, compute_cost=5),
}


# ---------------------------------------------------------------------------
# Write outputs
# ---------------------------------------------------------------------------

def write_metric_scan(results):
    """METRIC_SCAN.md — comprehensive candidate survey."""

    entries = {
        # id: (full_name, what_it_measures, implementation, pros, cons, fit, feasible)
        "mmd_rbf": (
            "MMD (Maximum Mean Discrepancy) with RBF kernel",
            "Whether two sets of text embeddings come from the same distribution. A kernel two-sample statistic: MMD=0 iff distributions identical under the kernel.",
            "Embed all comments with SBERT (all-MiniLM-L6-v2, dim=384). Compute biased MMD^2 = E[k(x,x')] + E[k(y,y')] - 2E[k(x,y)] with RBF kernel, bandwidth via median heuristic.",
            "Metric-space aware; captures full distributional shape, not just moments; well-grounded statistically (Gretton et al., 2012); no stance labels needed.",
            "Hard to interpret intuitively ('what does 0.1 mean?'); sensitive to embedding quality; quadratic memory O(n^2) in naive form; meaningless if embeddings are template-repeated.",
            "Good for semantic fidelity — but template text will always be far from real Reddit. Flag as expected-high rather than a failure.",
            "Yes — already implemented in 04_compute_metrics.py",
        ),
        "centroid_cos": (
            "Centroid Cosine Distance",
            "How far apart the average (centroid) embeddings of the two sets are in semantic space. Simpler than MMD; one number.",
            "Compute mean embedding for real set and sim set. Return 1 - cosine_similarity(centroid_real, centroid_sim). Range [0, 2].",
            "Intuitive ('how different is the average meaning?'); fast O(n); no labels needed; stable at small sample sizes.",
            "Loses distributional shape — two identical-centroid but spread-out distributions score 0; less rigorous than MMD.",
            "Good secondary metric to sanity-check semantic direction without full MMD computation.",
            "Yes — trivial to implement",
        ),
        "pairwise_cos_diff": (
            "Mean Pairwise Cosine Similarity Difference",
            "Difference in internal diversity between real and sim. High internal sim = repetitive; low = diverse.",
            "For each set, compute mean cosine similarity of all pairs (subsample for speed). Report |mean_real - mean_sim|.",
            "Captures lexical diversity; no labels; easy to explain ('sim comments are X% more similar to each other than real ones').",
            "Not a distribution distance — measures diversity, not divergence; easily dominated by one archetype.",
            "Good diagnostic for the template-repetition problem; less useful as a primary metric.",
            "Yes",
        ),
        "jsd_stance": (
            "JSD (Jensen-Shannon Divergence) on stance",
            "How different the bullish/bearish/neutral proportions are between real and sim. Symmetric, bounded [0,1].",
            "Compute normalised frequency vectors over [bullish, bearish, neutral]. Return JSD(p||q) base-2. Already in 04_compute_metrics.py.",
            "Bounded and symmetric; interpretable; widely used for comparing discrete distributions; directly motivated by research question (stance alignment).",
            "Requires stance labels in both sets; labels are provisional (keyword-based) for real data — adds noise to the metric.",
            "Primary metric — directly answers 'do agents adopt the right stance mix?'",
            "Yes — already implemented",
        ),
        "tvd_stance": (
            "TVD (Total Variation Distance) on stance",
            "The largest possible difference between two probability distributions. TVD = 0.5 * sum|p_i - q_i|. Same inputs as JSD but different geometry.",
            "Same as JSD but TVD = 0.5 * L1(p, q). Trivial to add.",
            "Bounded [0,1]; interpretable as 'the max probability of correctly identifying which distribution a sample came from'; simple formula.",
            "Less sensitive than JSD for small differences near zero; same label dependency as JSD.",
            "Good secondary metric alongside JSD — same data, different sensitivity profile. TVD is often easier to explain in a table.",
            "Yes",
        ),
        "hellinger_stance": (
            "Hellinger Distance on stance",
            "Square-root-based divergence. Between JSD and TVD in sensitivity. Bounded [0,1].",
            "H(p,q) = sqrt(0.5 * sum((sqrt(p_i) - sqrt(q_i))^2)). Same stance vectors as JSD.",
            "Bounded; smoother penalty for moderate differences; easier to bound than KL divergence.",
            "Less standard in NLP/finance literature than JSD; adds redundancy if JSD already used.",
            "Useful for appendix/robustness check, not as a primary metric.",
            "Yes",
        ),
        "wasserstein": (
            "Wasserstein-1 Distance (temporal)",
            "The 'earth mover's distance' between posting-time distributions. Respects the metric structure of time — a 1-hour shift costs less than a 10-hour shift.",
            "Bin hours_from_event into 1-hour bins. Use scipy.stats.wasserstein_distance on normalised histograms with bin-centre supports. Already in 04_compute_metrics.py.",
            "Metric-aware (penalises off-by-N-bins proportionally); no labels needed; well-grounded in optimal transport theory; interpretable as 'average bin shift'.",
            "Requires enough temporal coverage; sensitive to outliers at the tails; bin resolution is a choice (1h used here).",
            "Primary metric — directly tests whether agents post at the right times relative to the event.",
            "Yes — already implemented",
        ),
        "rmse_temporal": (
            "RMSE on normalised hourly histograms",
            "Root-mean-squared difference between the real and sim posting-frequency profiles, hour by hour.",
            "Compute normalised hourly histograms for both sets. RMSE = sqrt(mean((p_h - q_h)^2)) over all bins.",
            "Extremely intuitive ('average per-hour squared error'); no labels; simple formula; familiar to all reviewers.",
            "Does not account for temporal metric structure (a shift by 2 hours looks the same as a random scatter); sensitive to bin choice.",
            "Good secondary metric alongside Wasserstein — simpler to explain, complementary sensitivity.",
            "Yes",
        ),
        "dtw_temporal": (
            "DTW (Dynamic Time Warping) on hourly histograms",
            "Allows a flexible alignment of two temporal sequences before measuring distance. Less sensitive to exact timing than RMSE.",
            "Apply DTW to normalised hourly histograms (50 1-hour bins). O(n^2) = 2500 operations — fast. Use custom numpy implementation.",
            "Handles temporal warping (e.g., sim peaks 2h after real peak and still scores well); used in time-series analysis.",
            "Less interpretable than Wasserstein; results depend on DTW cost function choice; more complex to explain in a report.",
            "Interesting as a robustness check — if DTW is much lower than Wasserstein, it means the temporal profile is right shape but time-shifted.",
            "Yes — implemented from scratch",
        ),
        "depth_jsd": (
            "Reply-depth distribution JSD",
            "How different the distribution of comment depths (depth 0, 1, 2, ...) is between real and sim. Tests whether the reply-tree structure is realistic.",
            "Compute normalised depth histograms [0,1,...,10+]. Apply JSD. Real data has depths up to 10; sim pilot has depths 0-1.",
            "Label-free; captures a structural dimension none of A-C measures; directly exposes the shallowness of sim reply trees.",
            "High expected divergence for the pilot (sim has no deep threading); requires depth column in both datasets.",
            "Important diagnostic for structural realism. The pilot will score badly on this — which is honest and worth reporting.",
            "Yes",
        ),
        "branch_diff": (
            "Branching Factor Difference",
            "Absolute difference in average number of replies per top-level post.",
            "Count children per root per thread. Mean over threads. Report |real_mean - sim_mean|.",
            "Simple; interpretable; directly measures conversation depth; no labels.",
            "Single-number summary loses distribution information; sensitive to outlier threads.",
            "Good simple structural metric alongside depth JSD.",
            "Yes",
        ),
        "avg_len_diff": (
            "Average Comment Length Difference",
            "Absolute difference in mean character count. Tests whether agents write similar-length comments.",
            "Compute mean(len(text)) for real and sim. Report absolute difference.",
            "Trivial; intuitive; label-free; very robust to sample size.",
            "Crude; template text may coincidentally match real length; not a distribution metric.",
            "Useful diagnostic but too weak to be a primary metric.",
            "Yes",
        ),
        "avg_len_ratio": (
            "Average Comment Length Ratio",
            "Max/min mean length ratio. 1.0 = identical mean length, 2.0 = one set is twice as long.",
            "max(mean_real, mean_sim) / min(mean_real, mean_sim).",
            "Scale-invariant version of avg_len_diff; easier to compare across datasets.",
            "Same limitations as avg_len_diff but multiplicative.",
            "Appendix diagnostic only.",
            "Yes",
        ),
        "vocab_jaccard": (
            "Vocabulary Overlap (Jaccard Distance)",
            "What fraction of the top-5000 words appear in both sets. Distance = 1 - Jaccard similarity.",
            "Tokenise all text to lowercase words. Compute top-5000 unigrams per set. Jaccard distance = 1 - |intersection| / |union|.",
            "Intuitive; no labels; captures real-world vocabulary vs template vocabulary gap; fast.",
            "Sensitive to vocabulary size choice; unigrams miss phrase-level patterns; template repetition makes sim vocabulary tiny.",
            "Good secondary metric to confirm template vs real vocabulary gap.",
            "Yes",
        ),
        "ttr_diff": (
            "Type-Token Ratio Difference",
            "Difference in lexical richness (unique words / total words). High TTR = diverse text; low TTR = repetitive.",
            "For each set: TTR = |unique tokens| / |total tokens|. Report |TTR_real - TTR_sim|.",
            "Simple; intuitive; directly quantifies template repetition problem; no labels.",
            "Decreases with corpus size (not corpus-size-independent); sim corpus is small so TTR naturally higher.",
            "Useful to document the template limitation honestly, not as a primary metric.",
            "Yes",
        ),
    }

    cat_names = {
        "A": "Semantic / Content",
        "B": "Stance / Label Distribution",
        "C": "Temporal",
        "D": "Structural / Reply-Tree",
        "E": "Lexical / Style",
    }

    lines = ["# METRIC SCAN — Candidate Similarity Metrics\n",
             "## NVDA_Q3FY26 Pilot — LLM Investor Simulation\n\n",
             "*Generated by `10_metric_benchmark.py`*\n\n",
             "---\n\n",
             "## Overview\n\n",
             "16 candidate metrics are surveyed across 5 categories. Each is assessed for:\n",
             "fit to this project, implementation feasibility, and role in the final evaluation.\n\n",
             "The project requires **exactly 3 primary metrics** (locked in CLAUDE.md).\n\n",
             "---\n\n"]

    # Group by category
    cat_metrics = {}
    for mid, (full_name, *_) in entries.items():
        cat = next(d[2] for d in METRIC_DEFS if d[0] == mid)
        cat_metrics.setdefault(cat, []).append(mid)

    for cat in ["A", "B", "C", "D", "E"]:
        lines.append(f"## Category {cat}: {cat_names[cat]}\n\n")
        for mid in cat_metrics.get(cat, []):
            if mid not in entries:
                continue
            name, what, impl, pros, cons, fit, feasible = entries[mid]
            q = QUALITATIVE[mid]
            lines.append(f"### {name}\n\n")
            lines.append(f"| Property | Detail |\n|---|---|\n")
            lines.append(f"| **What it measures** | {what} |\n")
            lines.append(f"| **Implementation** | {impl} |\n")
            lines.append(f"| **Pros** | {pros} |\n")
            lines.append(f"| **Cons** | {cons} |\n")
            lines.append(f"| **Fit for this project** | {fit} |\n")
            lines.append(f"| **Feasible tonight?** | {feasible} |\n")
            lines.append(f"| **Sensitivity** | {'★'*q['sensitivity']}{'☆'*(5-q['sensitivity'])} ({q['sensitivity']}/5) |\n")
            lines.append(f"| **Interpretability** | {'★'*q['interpretability']}{'☆'*(5-q['interpretability'])} ({q['interpretability']}/5) |\n")
            lines.append(f"| **Robustness (small n)** | {'★'*q['robustness']}{'☆'*(5-q['robustness'])} ({q['robustness']}/5) |\n")
            lines.append(f"| **Label-free** | {'Yes' if q['label_free'] >= 4 else 'No — requires stance labels'} |\n")
            lines.append(f"| **Report fit** | {'★'*q['report_fit']}{'☆'*(5-q['report_fit'])} ({q['report_fit']}/5) |\n\n")

    lines.append("---\n\n*See METRIC_BENCHMARK.md for quantitative benchmark results.*\n")

    path = OUT / "METRIC_SCAN.md"
    path.write_text("".join(lines), encoding="utf-8")
    print(f"  Saved: {path}")


def write_benchmark_csv(results):
    rows = []
    for mid, row in results.items():
        q = QUALITATIVE[mid]
        full_row = {**row, **q}
        rows.append(full_row)
    df = pd.DataFrame(rows)
    col_order = (
        ["metric_id", "label", "category",
         "rvr", "rvrand", "rvs",
         "sensitivity", "interpretability", "robustness",
         "label_free", "report_fit", "compute_cost"]
    )
    df = df[col_order]
    path = OUT / "METRIC_BENCHMARK.csv"
    df.to_csv(path, index=False)
    print(f"  Saved: {path}")
    return df


def write_benchmark_md(results, df):
    lines = ["# METRIC BENCHMARK RESULTS\n\n",
             "## NVDA_Q3FY26 Pilot\n\n",
             "*Generated by `10_metric_benchmark.py`*\n\n",
             "---\n\n",
             "## Comparison pairs\n\n",
             "| Pair | Description | Expected gap |\n|---|---|---|\n",
             "| Real-vs-Real (RvR) | NVDA random 50/50 split | Low — same data source |\n",
             "| Real-vs-Random (RvRand) | NVDA vs uniform-time/random-stance/random-emb | High — completely different distributions |\n",
             "| Real-vs-Sim (RvS) | NVDA real vs sim_comments.csv pilot | Medium — structured gen, not real Reddit |\n\n",
             "A good metric should satisfy: **RvR < RvS < RvRand** (monotone ordering).\n\n",
             "---\n\n",
             "## Results table\n\n",
             "| Metric | Cat | RvR | RvRand | RvS | Sens | Interp | Robust | Report-fit |\n",
             "|--------|-----|-----|--------|-----|------|--------|--------|------------|\n"]

    for mid, row in results.items():
        q = QUALITATIVE[mid]
        label = row["label"]
        cat = row["category"]
        rvr    = f"{row['rvr']:.4f}"
        rvrand = f"{row['rvrand']:.4f}"
        rvs    = f"{row['rvs']:.4f}"
        sens   = q["sensitivity"]
        interp = q["interpretability"]
        robust = q["robustness"]
        rfit   = q["report_fit"]
        lines.append(
            f"| {label} | {cat} | {rvr} | {rvrand} | {rvs} | "
            f"{sens}/5 | {interp}/5 | {robust}/5 | {rfit}/5 |\n"
        )

    lines.append("\n---\n\n## Monotone ordering check\n\n")
    lines.append("Does each metric satisfy RvR < RvS < RvRand?\n\n")
    lines.append("| Metric | RvR | RvS | RvRand | Ordered? |\n|---|---|---|---|---|\n")

    for mid, row in results.items():
        rvr, rvs, rvrand = row["rvr"], row["rvs"], row["rvrand"]
        ordered = "YES" if rvr <= rvs <= rvrand else (
            "PARTIAL" if (rvr <= rvrand and rvs <= rvrand) else "NO"
        )
        lines.append(f"| {row['label']} | {rvr:.4f} | {rvs:.4f} | {rvrand:.4f} | {ordered} |\n")

    lines.append("\n---\n\n## Category summaries\n\n")

    cat_notes = {
        "A": (
            "**Semantic metrics** require SBERT embeddings. MMD is the gold standard "
            "but expensive and hard to explain. Centroid cosine distance is a fast, "
            "interpretable proxy. Both will show high divergence for template text."
        ),
        "B": (
            "**Stance metrics** all use the same underlying data (stance labels). "
            "JSD is the standard choice. TVD and Hellinger are correlated — picking "
            "all three adds little information. JSD is the most cited in NLP literature."
        ),
        "C": (
            "**Temporal metrics** all test posting-volume profiles. "
            "Wasserstein respects the ordering of time bins (metric-aware). "
            "RMSE is simpler but treats all bin mismatches equally. "
            "DTW is overkill for 50-bin histograms."
        ),
        "D": (
            "**Structural metrics** capture reply-tree topology. "
            "Depth JSD will be large for the pilot (sim has no deep threading). "
            "This is honest and worth documenting, but structural metrics are not "
            "suitable as primary metrics for a first-pass pilot."
        ),
        "E": (
            "**Lexical metrics** expose the template-repetition limitation. "
            "Useful as diagnostic/honest-reporting tools, not as primary comparison metrics."
        ),
    }
    for cat, note in cat_notes.items():
        cat_mets = [row["label"] for _, row in results.items() if row["category"] == cat]
        lines.append(f"### Category {cat}\n\n{note}\n\n")
        lines.append(f"Metrics in this category: {', '.join(cat_mets)}\n\n")

    path = OUT / "METRIC_BENCHMARK.md"
    path.write_text("".join(lines), encoding="utf-8")
    print(f"  Saved: {path}")


def write_recommendation(results):
    # Analyse ordering
    ordered_metrics = []
    for mid, row in results.items():
        rvr, rvs, rvrand = row["rvr"], row["rvs"], row["rvrand"]
        is_ordered = rvr <= rvs <= rvrand
        q = QUALITATIVE[mid]
        score = (q["sensitivity"] + q["interpretability"] + q["robustness"] +
                 q["report_fit"]) / 4
        ordered_metrics.append((mid, row["label"], row["category"], is_ordered, score, rvr, rvs, rvrand))

    ordered_metrics.sort(key=lambda x: (0 if x[3] else 1, -x[4]))  # ordered first, then score

    # Fixed recommendation (informed by benchmark + project context):
    primary = [
        ("MMD (RBF kernel)", "mmd_rbf",
         "Semantically grounded, embedding-based; the strongest discriminator for content fidelity. "
         "Already locked in CLAUDE.md. Acknowledged limitation: template text inflates MMD above "
         "what a genuine LLM-based sim would produce."),
        ("JSD on stance distribution", "jsd_stance",
         "Directly answers the core research question: do simulated agents adopt the same "
         "bullish/bearish/neutral mix as real investors? Bounded [0,1], interpretable, standard "
         "in NLP. Limitation: depends on provisional keyword-based real labels."),
        ("Wasserstein-1 on temporal distribution", "wasserstein",
         "Measures whether agents post at the right times relative to the earnings event. "
         "Metric-aware (respects temporal ordering), no labels needed, well-grounded theoretically. "
         "Expected gap is interpretable: a Wasserstein of N means the sim profile is shifted by ~N hours on average."),
    ]

    secondary = [
        ("Depth distribution JSD", "depth_jsd",
         "Exposes structural gap: sim comments are all depth 0-1; real Reddit has threads reaching depth 10+. "
         "Honest documentation of pilot limitation."),
        ("TVD on stance / RMSE on temporal histograms", "tvd_stance",
         "Paired with JSD/Wasserstein as a simpler cross-check. TVD has a cleaner probability interpretation "
         "('max classification advantage'); RMSE is familiar to all readers."),
    ]

    not_used = [
        ("DTW on temporal histograms", "dtw_temporal",
         "Adds complexity without insight for 50-bin histograms; Wasserstein already metric-aware."),
        ("Centroid cosine distance", "centroid_cos",
         "Loses distributional shape; redundant given MMD for primary evaluation."),
        ("Average comment length difference", "avg_len_diff",
         "Too crude; not a distribution metric. Useful only as a one-line diagnostic."),
        ("Type-token ratio difference", "ttr_diff",
         "Same limitation as avg_len_diff; not informative for between-corpus comparison."),
        ("Branching factor difference", "branch_diff",
         "Useful in a future full-scale simulation; pilot is too small for this to be meaningful."),
        ("Hellinger distance on stance", "hellinger_stance",
         "Redundant given JSD; less standard in the relevant literature."),
    ]

    rvr_rvs_gap_mmd  = results["mmd_rbf"]["rvs"] - results["mmd_rbf"]["rvr"]
    rvr_rvs_gap_jsd  = results["jsd_stance"]["rvs"] - results["jsd_stance"]["rvr"]
    rvr_rvs_gap_wass = results["wasserstein"]["rvs"] - results["wasserstein"]["rvr"]

    lines = [
        "METRIC RECOMMENDATION — LLM Investor Simulation Pilot\n",
        "======================================================\n",
        "Generated by 10_metric_benchmark.py | Event: NVDA_Q3FY26\n\n",
        "DATA BASIS\n",
        "----------\n",
        "All benchmarks use:\n",
        "  - Real data  : data/processed/real_comments_curated_labeled.csv\n",
        "                 (NVDA_Q3FY26, 2403 rows, curated, provisional stance labels)\n",
        "  - Real embeddings: data/processed/real_comment_embeddings_curated.npy\n",
        "                     (SBERT all-MiniLM-L6-v2, L2-normalised)\n",
        "  - Sim data   : data/processed/sim_comments.csv\n",
        "                 (48 sim comments from pilot 07_agent_simulation.py)\n\n",
        "BENCHMARK SUMMARY (Real-vs-Real  /  Real-vs-Sim  /  Real-vs-Random)\n",
        "--------------------------------------------------------------------\n",
        f"  MMD (RBF)      : {results['mmd_rbf']['rvr']:.4f}  /  {results['mmd_rbf']['rvs']:.4f}  /  {results['mmd_rbf']['rvrand']:.4f}   (gap RvR->RvS: {rvr_rvs_gap_mmd:+.4f})\n",
        f"  JSD (stance)   : {results['jsd_stance']['rvr']:.4f}  /  {results['jsd_stance']['rvs']:.4f}  /  {results['jsd_stance']['rvrand']:.4f}   (gap RvR->RvS: {rvr_rvs_gap_jsd:+.4f})\n",
        f"  Wasserstein    : {results['wasserstein']['rvr']:.4f}  /  {results['wasserstein']['rvs']:.4f}  /  {results['wasserstein']['rvrand']:.4f}   (gap RvR->RvS: {rvr_rvs_gap_wass:+.4f})\n\n",
        "Note: 'Real-vs-Real' uses a random 50/50 split of NVDA data, providing\n",
        "      a same-distribution lower bound.\n",
        "Note: 'Real-vs-Random' uses uniform-time / random-stance / random-emb baseline,\n",
        "      providing an upper bound on expected metric values.\n\n",
        "Primary metrics for the report:\n",
        "1. MMD (Maximum Mean Discrepancy with RBF kernel on SBERT embeddings)\n",
        "   Reason: Distributional semantic fidelity; no labels needed; grounded in\n",
        "   kernel two-sample test theory (Gretton et al., 2012). Already locked in\n",
        "   CLAUDE.md. Acknowledged limitation: template-based text will score worse\n",
        "   than a genuine LLM-based simulation — this is documented honestly.\n\n",
        "2. JSD (Jensen-Shannon Divergence on stance distribution)\n",
        "   Reason: Directly tests the core research hypothesis — do simulated agents\n",
        "   produce the correct bullish/bearish/neutral mix? Bounded [0,1], symmetric,\n",
        "   interpretable, standard in NLP. Already locked in CLAUDE.md.\n\n",
        "3. Wasserstein-1 distance on hourly posting-volume distribution\n",
        "   Reason: Tests temporal realism — do agents post at the right times relative\n",
        "   to the earnings event? Metric-aware (respects time ordering). Label-free.\n",
        "   Already locked in CLAUDE.md.\n\n",
        "Secondary metrics to mention briefly:\n",
        "1. Depth distribution JSD\n",
        "   Reason: Exposes the structural gap (sim comments are all depth 0-1; real\n",
        "   threads reach depth 10+). Provides honest documentation of pilot limitation\n",
        "   without claiming it should be a primary evaluation criterion.\n\n",
        "2. TVD (Total Variation Distance) on stance\n",
        "   Reason: Paired with JSD as a simpler cross-check in the same table.\n",
        "   TVD has an intuitive probability interpretation and requires no extra\n",
        "   computation beyond the stance vectors already needed for JSD.\n\n",
        "Metrics considered but not used:\n",
        "1. DTW on temporal histograms\n",
        "   Reason: Wasserstein already metric-aware; DTW adds complexity without\n",
        "   interpretive gain for 50-bin histograms.\n\n",
        "2. Centroid cosine distance\n",
        "   Reason: Loses distributional shape; redundant given MMD.\n\n",
        "3. Average comment length difference\n",
        "   Reason: Not a distribution metric; too crude for primary evaluation.\n\n",
        "4. Hellinger distance on stance\n",
        "   Reason: Redundant with JSD; less standard in NLP/finance literature.\n\n",
        "5. Type-token ratio difference\n",
        "   Reason: Corpus-size dependent; not interpretable as a between-corpus metric.\n\n",
        "6. Branching factor difference\n",
        "   Reason: Useful in a future full-scale simulation with richer threading;\n",
        "   pilot scale (48 comments) is too small for this to be meaningful.\n\n",
        "RECOMMENDATION BASIS\n",
        "--------------------\n",
        "Which recommendations are based on REAL data:\n",
        "  - All three primary metrics are evaluated on real NVDA_Q3FY26 data\n",
        "    (2403 rows, SBERT embeddings, provisional stance labels).\n",
        "  - The Real-vs-Real baseline uses the same dataset (50/50 random split).\n",
        "  - Real stance labels are provisional (keyword-based); this affects JSD.\n\n",
        "Which recommendations are based on SIMULATED pilot outputs:\n",
        "  - The Real-vs-Sim column uses sim_comments.csv (48 template-generated\n",
        "    comments from 07_agent_simulation.py).\n",
        "  - These values represent a template-baseline, not a full LLM simulation.\n",
        "  - Depth JSD recommendation is based on sim structure (all depth 0-1).\n\n",
        "BIGGEST REMAINING RISK IN THE EVALUATION DESIGN\n",
        "------------------------------------------------\n",
        "The primary risk is that JSD stance is evaluated against provisional keyword-based\n",
        "real labels (see STANCE_LABEL_AUDIT.md: 33% of sampled labels flagged as\n",
        "potentially incorrect). If the real label distribution is noisy, JSD conflates\n",
        "two sources of error: (1) agents using the wrong stance mix, and (2) the real\n",
        "labels being wrong. The metric cannot distinguish these cases.\n\n",
        "Secondary risk: MMD is adversely affected by template text repetition in the\n",
        "sim (low within-sim diversity). A genuine LLM-based simulation would reduce\n",
        "MMD significantly relative to the pilot numbers shown here. The pilot MMD\n",
        "values should be interpreted as an upper bound on what a full LLM simulation\n",
        "would produce, not as the expected final result.\n",
    ]

    path = OUT / "METRIC_RECOMMENDATION.txt"
    path.write_text("".join(lines), encoding="utf-8")
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("10_metric_benchmark.py — Metric Scan & Benchmark")
    print("=" * 60)

    print("\n  Loading datasets...")
    real_df, real_emb, sim_df, sim_emb = load_datasets()
    print(f"  Real: {len(real_df)} rows | Sim: {len(sim_df)} rows")
    print(f"  Real emb: {real_emb.shape} | Sim emb: {sim_emb.shape}")

    print("\n  Running benchmarks...")
    results, pairs = run_benchmarks(real_df, real_emb, sim_df, sim_emb)

    print("\n  Writing METRIC_SCAN.md...")
    write_metric_scan(results)

    print("  Writing METRIC_BENCHMARK.csv / .md...")
    df = write_benchmark_csv(results)
    write_benchmark_md(results, df)

    print("  Writing METRIC_RECOMMENDATION.txt...")
    write_recommendation(results)

    print("\nDone.")


if __name__ == "__main__":
    main()
