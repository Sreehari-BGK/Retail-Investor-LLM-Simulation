#!/usr/bin/env python3
"""Top-level vs replies robustness check for the over-grounding headline.

Outputs:
  outputs/seminar_support/top_level_vs_replies_robustness.csv
  outputs/seminar_support/top_level_grounding_comparison.png
Plus a JSON dump of the recomputed metrics for the MD writer.
"""
import sys, io, os, importlib.util, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import warnings; warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = os.path.join('outputs', 'seminar_support')
os.makedirs(OUT, exist_ok=True)

# ---- load curated NVDA + helpers ----
cur = pd.read_csv('data/processed/real_comments_curated_labeled.csv')
nv = cur[cur['event_id'] == 'NVDA_Q3FY26'].copy().reset_index(drop=True)

# top-level rule: parent_id starts with 't3_' (Reddit "link" prefix)
def classify(row):
    pid = row['parent_id']
    cid = row['comment_id']; tid = row['thread_id']
    if cid == tid:
        return 'post_row'
    if pd.isna(pid):
        return 'unknown'
    s = str(pid)
    if s.startswith('t3_'):
        return 'top_level'
    if s.startswith('t1_'):
        return 'reply'
    return 'other'

nv['class'] = nv.apply(classify, axis=1)
print('NVDA class counts:')
print(nv['class'].value_counts())
print()

# ---- grounding evaluator + stance metric + MMD ----
spec_g = importlib.util.spec_from_file_location('grnd', 'scripts/12_eval_grounding.py')
g_mod = importlib.util.module_from_spec(spec_g); spec_g.loader.exec_module(g_mod)
spec_m = importlib.util.spec_from_file_location('metrics', 'scripts/04_compute_metrics.py')
m_mod = importlib.util.module_from_spec(spec_m); spec_m.loader.exec_module(m_mod)

# ---- load real embedding cache (row-aligned to curated NVDA) ----
real_emb_path = 'outputs/real_emb_cache_nvda_minilm.npy'
real_emb = np.load(real_emb_path).astype(np.float32)
assert len(real_emb) == len(nv), f'cache mismatch: {len(real_emb)} vs {len(nv)}'

# ---- load best LLM finalist (Qwen3.5-2B P2_V1 tau=1.1 seed=123) ----
best_csv = 'runs/finalist_qwen_qwen3_5_2b_P2_V1_t1.1_s123/prompt_exp_P2_V1_comments.csv'
best = pd.read_csv(best_csv)
print(f'Best LLM run: {len(best)} comments')

# Embed best run's text with same SBERT
from sentence_transformers import SentenceTransformer
sbert = SentenceTransformer('all-MiniLM-L6-v2')
print('Embedding best LLM run...')
sim_emb = sbert.encode(best['text'].fillna('').tolist(),
                       batch_size=64, normalize_embeddings=True,
                       show_progress_bar=False, convert_to_numpy=True).astype(np.float32)

# ---- fast MMD with precomputed gamma (median heuristic on full real corpus) ----
def precompute_gamma(X, n_sample=1000, seed=42):
    rng = np.random.default_rng(seed)
    n = len(X)
    if n > n_sample:
        idx = rng.choice(n, n_sample, replace=False)
        Z = X[idx]
    else:
        Z = X
    dot = Z @ Z.T
    sq = np.einsum('ij,ij->i', Z, Z)
    sq_dists = sq[:, None] + sq[None, :] - 2.0 * dot
    iu = np.triu_indices(len(Z), k=1)
    median_sq = float(np.median(sq_dists[iu]))
    return 1.0 / max(median_sq, 1e-12)

GAMMA = precompute_gamma(real_emb)
print(f'Precomputed gamma = {GAMMA:.5f}')

def mmd_fast(X, Y, gamma):
    XX = X @ X.T; YY = Y @ Y.T; XY = X @ Y.T
    xsq = np.einsum('ij,ij->i', X, X)
    ysq = np.einsum('ij,ij->i', Y, Y)
    Kxx = np.exp(-gamma*(xsq[:,None] + xsq[None,:] - 2*XX))
    Kyy = np.exp(-gamma*(ysq[:,None] + ysq[None,:] - 2*YY))
    Kxy = np.exp(-gamma*(xsq[:,None] + ysq[None,:] - 2*XY))
    m = len(X); n = len(Y)
    np.fill_diagonal(Kxx, 0); np.fill_diagonal(Kyy, 0)
    return float(Kxx.sum()/(m*(m-1)) + Kyy.sum()/(n*(n-1)) - 2*Kxy.sum()/(m*n))

# ---- subset definitions for NVDA ----
subsets = {
    'all':       nv,
    'top_level': nv[nv['class'] == 'top_level'].reset_index(),
    'replies':   nv[nv['class'] == 'reply'].reset_index(),
    'post_rows': nv[nv['class'] == 'post_row'].reset_index(),
}

# helper: stance counts
def stance_dist(df):
    if 'stance' not in df.columns:
        return {}
    vc = df['stance'].value_counts()
    total = vc.sum()
    return {
        'bullish_n': int(vc.get('bullish', 0)),
        'bearish_n': int(vc.get('bearish', 0)),
        'neutral_n': int(vc.get('neutral', 0)),
        'bullish_pct': round(100*vc.get('bullish', 0)/total, 1) if total else 0,
        'bearish_pct': round(100*vc.get('bearish', 0)/total, 1) if total else 0,
        'neutral_pct': round(100*vc.get('neutral', 0)/total, 1) if total else 0,
    }

# compute everything
results = []
for name, sub in subsets.items():
    n = len(sub)
    if n == 0:
        continue
    g = g_mod.evaluate_corpus(sub, text_col='text')['grounding']
    st = stance_dist(sub)
    row = {'subset': name, 'n': n, **g, **st}
    results.append(row)
print('\nNVDA subset metrics:')
for r in results:
    print(f'  {r["subset"]:10s}  n={r["n"]:>5}  grounded={r["grounded_pct"]:.1f}%  ungrounded={r["ungrounded_pct"]:.1f}%  bullish={r["bullish_pct"]:.1f}%  bearish={r["bearish_pct"]:.1f}%  neutral={r["neutral_pct"]:.1f}%')

# best LLM grounding/stance for direct comparison
g_llm = g_mod.evaluate_corpus(best, text_col='text')['grounding']
st_llm = stance_dist(best)
print(f'\nBest LLM: n=108  grounded={g_llm["grounded_pct"]:.1f}%  ungrounded={g_llm["ungrounded_pct"]:.1f}%  '
      f'bullish={st_llm["bullish_pct"]:.1f}% bearish={st_llm["bearish_pct"]:.1f}% neutral={st_llm["neutral_pct"]:.1f}%')

# ---- recompute JSD and MMD against top-level NVDA ----
# top-level mask (preserve original positional index of nv for embedding cache lookup)
tl_idx = np.array(nv.index[nv['class'] == 'top_level'])
print(f'\nTop-level indices: {len(tl_idx)}')

real_stances_tl = nv.loc[tl_idx, 'stance'].tolist()
sim_stances = best['stance'].tolist()
jsd_tl = m_mod.jsd_stance(real_stances_tl, sim_stances)

# Also JSD against all curated NVDA (sanity)
jsd_all = m_mod.jsd_stance(nv['stance'].tolist(), sim_stances)

# MMD: real_emb is row-aligned to nv (post-reset_index); use the same positional indices
real_emb_tl = real_emb[tl_idx]
mmd_tl = mmd_fast(real_emb_tl, sim_emb, GAMMA)
mmd_all = mmd_fast(real_emb, sim_emb, GAMMA)

# Replies-only for completeness
reply_idx = np.array(nv.index[nv['class'] == 'reply'])
real_emb_rep = real_emb[reply_idx]
real_stances_rep = nv.loc[reply_idx, 'stance'].tolist()
jsd_rep = m_mod.jsd_stance(real_stances_rep, sim_stances)
mmd_rep = mmd_fast(real_emb_rep, sim_emb, GAMMA)

print(f'\nJSD (best LLM vs real subset):  all={jsd_all:.4f}  top_level={jsd_tl:.4f}  replies={jsd_rep:.4f}')
print(f'MMD (best LLM vs real subset):  all={mmd_all:.4f}  top_level={mmd_tl:.4f}  replies={mmd_rep:.4f}')

# ---- AAPL and META: counts only (priority is NVDA) ----
def class_counts(event_id):
    sub = cur[cur['event_id'] == event_id].copy()
    sub['class'] = sub.apply(classify, axis=1)
    vc = sub['class'].value_counts().to_dict()
    g = g_mod.evaluate_corpus(sub, text_col='text')['grounding']
    out = {
        'event_id': event_id, 'n': len(sub),
        'top_level_n': vc.get('top_level', 0),
        'replies_n': vc.get('reply', 0),
        'post_row_n': vc.get('post_row', 0),
        'other_n': vc.get('other', 0) + vc.get('unknown', 0),
        'grounded_pct_all': g['grounded_pct'],
        'ungrounded_pct_all': g['ungrounded_pct'],
    }
    # top-level only
    tl_sub = sub[sub['class'] == 'top_level']
    if len(tl_sub):
        g_tl = g_mod.evaluate_corpus(tl_sub, text_col='text')['grounding']
        out['grounded_pct_top_level'] = g_tl['grounded_pct']
        out['ungrounded_pct_top_level'] = g_tl['ungrounded_pct']
    return out

aapl_meta = [class_counts('AAPL_Q4FY25'), class_counts('META_Q3_2025')]

# ---- write CSV ----
csv_rows = []
for r in results:
    csv_rows.append({
        'event': 'NVDA_Q3FY26',
        'subset': r['subset'],
        'n': r['n'],
        'grounded_pct': r['grounded_pct'],
        'weakly_grounded_pct': r['weakly_grounded_pct'],
        'ungrounded_pct': r['ungrounded_pct'],
        'bullish_pct': r['bullish_pct'],
        'bearish_pct': r['bearish_pct'],
        'neutral_pct': r['neutral_pct'],
        'jsd_vs_best_llm': {'all': round(jsd_all,4),
                            'top_level': round(jsd_tl,4),
                            'replies': round(jsd_rep,4),
                            'post_rows': None}.get(r['subset']),
        'mmd_vs_best_llm': {'all': round(mmd_all,5),
                            'top_level': round(mmd_tl,5),
                            'replies': round(mmd_rep,5),
                            'post_rows': None}.get(r['subset']),
    })
csv_rows.append({
    'event': '(reference)', 'subset': 'best_llm_Qwen3.5-2B_P2V1_t1.1_s123',
    'n': 108,
    'grounded_pct': g_llm['grounded_pct'],
    'weakly_grounded_pct': g_llm['weakly_grounded_pct'],
    'ungrounded_pct': g_llm['ungrounded_pct'],
    'bullish_pct': st_llm['bullish_pct'],
    'bearish_pct': st_llm['bearish_pct'],
    'neutral_pct': st_llm['neutral_pct'],
    'jsd_vs_best_llm': 0.0,
    'mmd_vs_best_llm': 0.0,
})
pd.DataFrame(csv_rows).to_csv(os.path.join(OUT, 'top_level_vs_replies_robustness.csv'), index=False)
print(f'\nWrote {OUT}/top_level_vs_replies_robustness.csv')

# ---- bar chart ----
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

NAVY = '#1F4E79'; ACCENT = '#C00000'; AMBER = '#BF8F00'; GREEN = '#548235'; GREY = '#7F7F7F'

fig, ax = plt.subplots(figsize=(10, 5.5))
labels = ['Real NVDA\nall comments\n(n=2403)',
          f'Real NVDA\ntop-level only\n(n={len(tl_idx)})',
          f'Real NVDA\nreplies only\n(n={len(reply_idx)})',
          'Best LLM\nn=108']
get_g = {r['subset']: r['grounded_pct'] for r in results}
values = [get_g['all'], get_g['top_level'], get_g['replies'], g_llm['grounded_pct']]
colors = [NAVY, NAVY, NAVY, ACCENT]

bars = ax.bar(labels, values, color=colors, edgecolor='white', linewidth=2, width=0.62)
for b, v in zip(bars, values):
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+1.5, f'{v:.1f}%',
            ha='center', fontsize=13, weight='bold',
            color=ACCENT if v > 50 else NAVY)

ax.set_ylabel('Grounded comments (%)', fontsize=12)
ax.set_ylim(0, max(values) + 15)
ax.set_title('Grounding rate — robustness to comment depth (NVDA Q3 FY26)',
             fontsize=14, weight='bold', color=NAVY)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.grid(axis='y', linestyle='--', alpha=0.3)

# Annotation: gap stays large?
gap_top_vs_llm = g_llm['grounded_pct'] - get_g['top_level']
ratio = g_llm['grounded_pct'] / max(get_g['top_level'], 0.001)
fig.text(0.5, 0.01,
         f'Gap between best LLM and top-level real Reddit: {gap_top_vs_llm:+.1f} percentage points  ·  '
         f'LLM still ≈{ratio:.0f}× higher.',
         ha='center', fontsize=11, color=NAVY, style='italic',
         bbox=dict(facecolor='#F2F2F2', edgecolor=NAVY, boxstyle='round,pad=0.5'))

plt.tight_layout(rect=[0, 0.07, 1, 1])
fig.savefig(os.path.join(OUT, 'top_level_grounding_comparison.png'), dpi=200, bbox_inches='tight')
plt.close()
print(f'Wrote {OUT}/top_level_grounding_comparison.png')

# ---- dump JSON for MD writer ----
summary = {
    'nvda': {
        'all':       {**get_g, 'mmd_vs_best_llm': round(mmd_all,5), 'jsd_vs_best_llm': round(jsd_all,4)},
        'top_level': {'grounded_pct': get_g['top_level'], 'mmd_vs_best_llm': round(mmd_tl,5), 'jsd_vs_best_llm': round(jsd_tl,4)},
        'replies':   {'grounded_pct': get_g['replies'],   'mmd_vs_best_llm': round(mmd_rep,5), 'jsd_vs_best_llm': round(jsd_rep,4)},
        'post_rows': {'grounded_pct': get_g.get('post_rows', None)},
        'subset_counts': {r['subset']: r['n'] for r in results},
        'subset_stance': {r['subset']: {'bullish_pct': r['bullish_pct'], 'bearish_pct': r['bearish_pct'], 'neutral_pct': r['neutral_pct']} for r in results},
    },
    'best_llm': {
        'config': 'Qwen3.5-2B + P2_V1 + tau=1.1 + seed=123',
        'n': 108,
        'grounded_pct': g_llm['grounded_pct'],
        'ungrounded_pct': g_llm['ungrounded_pct'],
        'bullish_pct': st_llm['bullish_pct'],
        'bearish_pct': st_llm['bearish_pct'],
        'neutral_pct': st_llm['neutral_pct'],
    },
    'aapl_meta': aapl_meta,
    'gamma': round(GAMMA, 5),
}
with open(os.path.join(OUT, '_robustness_summary.json'), 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=2)
print(f'Wrote {OUT}/_robustness_summary.json')
