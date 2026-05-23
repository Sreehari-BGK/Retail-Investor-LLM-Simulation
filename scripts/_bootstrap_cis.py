#!/usr/bin/env python3
"""Bootstrap CIs - fast version with precomputed gamma + dot-product MMD."""
import sys, io, os, json, importlib.util, warnings, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

OUT = os.path.join('outputs', 'proposal_support')
os.makedirs(OUT, exist_ok=True)

N_BOOT = 1000
REAL_SUB = 300  # subsample size of real corpus per iteration (enough for stable MMD)
RNG = np.random.default_rng(42)

spec = importlib.util.spec_from_file_location('metrics', 'scripts/04_compute_metrics.py')
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)

real_all = pd.read_csv('data/processed/real_comments_curated_labeled.csv')
real = real_all[real_all['event_id'] == 'NVDA_Q3FY26'].reset_index(drop=True)
real_emb = np.load('outputs/real_emb_cache_nvda_minilm.npy').astype(np.float32)
assert len(real_emb) == len(real)
print(f'Real NVDA: {len(real)}, emb shape {real_emb.shape}')

from sentence_transformers import SentenceTransformer
sbert = SentenceTransformer('all-MiniLM-L6-v2')
def embed(texts):
    return sbert.encode(list(texts), batch_size=64, normalize_embeddings=True,
                        show_progress_bar=False, convert_to_numpy=True).astype(np.float32)


# ---------- Fast MMD with precomputed gamma, dot-product trick ----------
def precompute_gamma(X, n_sample=1000):
    """Median-heuristic gamma via dot-product trick on a subsample."""
    n = len(X)
    if n > n_sample:
        idx = RNG.choice(n, n_sample, replace=False)
        Z = X[idx]
    else:
        Z = X
    dot = Z @ Z.T
    sq = np.einsum('ij,ij->i', Z, Z)
    sq_dists = sq[:, None] + sq[None, :] - 2.0 * dot
    iu = np.triu_indices(len(Z), k=1)
    median_sq = float(np.median(sq_dists[iu]))
    return 1.0 / max(median_sq, 1e-12)

def mmd_fast(X, Y, gamma):
    """MMD^2 with RBF kernel, memory-safe via dot-product trick."""
    XX = X @ X.T
    YY = Y @ Y.T
    XY = X @ Y.T
    x_sq = np.einsum('ij,ij->i', X, X)
    y_sq = np.einsum('ij,ij->i', Y, Y)
    Kxx = np.exp(-gamma * (x_sq[:, None] + x_sq[None, :] - 2 * XX))
    Kyy = np.exp(-gamma * (y_sq[:, None] + y_sq[None, :] - 2 * YY))
    Kxy = np.exp(-gamma * (x_sq[:, None] + y_sq[None, :] - 2 * XY))
    m = len(X); n = len(Y)
    np.fill_diagonal(Kxx, 0); np.fill_diagonal(Kyy, 0)
    return float(Kxx.sum()/(m*(m-1)) + Kyy.sum()/(n*(n-1)) - 2*Kxy.sum()/(m*n))

# Precompute gamma once on real corpus; use across all pairs
GAMMA = precompute_gamma(real_emb, n_sample=1000)
print(f'Precomputed gamma = {GAMMA:.5f}')

# ---------- Pairs ----------
PAIRS = [{'pair_name': 'real_vs_real_splithalf_NVDA', 'kind': 'splithalf'}]

template = pd.read_csv('data/processed/sim_comments.csv')
template = template[template['event_id'] == 'NVDA_Q3FY26'].reset_index(drop=True)
PAIRS.append({'pair_name': 'real_vs_template_sim', 'sim_df': template, 'kind': 'sim'})

for sim_path, label in [
    ('runs/qwen35_2b_seed42_promptgrid_nvda/prompt_exp_P2_V1_comments.csv',
        'real_vs_qwen35_2b_seed42_P2V1_best_MMD'),
    ('runs/qwen25_3b_seed42_promptgrid_nvda/prompt_exp_P0_V0_comments.csv',
        'real_vs_qwen25_3b_seed42_P0V0_best_JSD'),
    ('runs/qwen35_2b_seed42_promptgrid_nvda/prompt_exp_all_comments.csv',
        'real_vs_qwen35_2b_seed42_all81'),
    ('runs/qwen35_2b_temp07_seed42_promptgrid_nvda/prompt_exp_P2_V1_comments.csv',
        'real_vs_qwen35_2b_t0p7_seed42_P2V1'),
]:
    if os.path.exists(sim_path):
        PAIRS.append({'pair_name': label, 'sim_df': pd.read_csv(sim_path), 'kind': 'sim'})


# ---------- Bootstrap functions ----------
real_stances = real['stance'].values
real_hours = real['hours_from_event'].values

def bs_splithalf(n_iter):
    jsds, wds, mmds = [], [], []
    n = len(real)
    for i in range(n_iter):
        idx = RNG.permutation(n)
        a = idx[:REAL_SUB]
        b = idx[REAL_SUB:REAL_SUB*2]
        jsds.append(metrics.jsd_stance(real_stances[a].tolist(), real_stances[b].tolist()))
        wds.append(metrics.wasserstein_time(real_hours[a].tolist(), real_hours[b].tolist()))
        mmds.append(mmd_fast(real_emb[a], real_emb[b], GAMMA))
    return np.array(jsds), np.array(wds), np.array(mmds)

def bs_real_vs_sim(sim_df, n_iter):
    sim_stances = sim_df['stance'].values
    sim_hours = sim_df['hours_from_event'].values
    sim_emb = embed(sim_df['text'].fillna('').tolist())
    n_real = len(real); n_sim = len(sim_df)
    jsds, wds, mmds = [], [], []
    for i in range(n_iter):
        r_idx = RNG.choice(n_real, size=REAL_SUB, replace=True)
        s_idx = RNG.choice(n_sim, size=n_sim, replace=True)
        jsds.append(metrics.jsd_stance(real_stances[r_idx].tolist(), sim_stances[s_idx].tolist()))
        wds.append(metrics.wasserstein_time(real_hours[r_idx].tolist(), sim_hours[s_idx].tolist()))
        mmds.append(mmd_fast(real_emb[r_idx], sim_emb[s_idx], GAMMA))
    return np.array(jsds), np.array(wds), np.array(mmds)


def summarize(arr):
    return {
        'mean': float(np.mean(arr)),
        'median': float(np.median(arr)),
        'ci_low': float(np.quantile(arr, 0.025)),
        'ci_high': float(np.quantile(arr, 0.975)),
        'std': float(np.std(arr)),
    }


rows = []
for p in PAIRS:
    print(f'\n[{p["pair_name"]}]')
    t0 = time.time()
    if p['kind'] == 'splithalf':
        jsds, wds, mmds = bs_splithalf(N_BOOT)
    else:
        jsds, wds, mmds = bs_real_vs_sim(p['sim_df'], N_BOOT)
    for m, arr in [('jsd_stance', jsds), ('wasserstein_time', wds), ('mmd_semantic', mmds)]:
        s = summarize(arr)
        rows.append({'pair_name': p['pair_name'], 'metric': m, **s, 'n_boot': N_BOOT, 'real_subsample': REAL_SUB})
        print(f'  {m:18s} mean={s["mean"]:.4f}  95% CI [{s["ci_low"]:.4f}, {s["ci_high"]:.4f}]')
    print(f'  elapsed {time.time()-t0:.1f}s')

df = pd.DataFrame(rows).round(4)
df.to_csv(f'{OUT}/bootstrap_metrics.csv', index=False)
print(f'\nSaved -> {OUT}/bootstrap_metrics.csv')
