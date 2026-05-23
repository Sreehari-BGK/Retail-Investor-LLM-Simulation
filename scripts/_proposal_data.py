#!/usr/bin/env python3
"""Generate all proposal-support CSVs and figures."""
import sys, io, os, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = os.path.join('outputs', 'proposal_support')
os.makedirs(OUT, exist_ok=True)

raw_all = pd.read_csv('data/processed/real_comments_labeled.csv')
cur_all = pd.read_csv('data/processed/real_comments_curated_labeled.csv')

EVENTS = ['NVDA_Q3FY26', 'AAPL_Q4FY25', 'META_Q3_2025']
LABELS = {'NVDA_Q3FY26': 'NVDA', 'AAPL_Q4FY25': 'AAPL', 'META_Q3_2025': 'META'}
COLORS = {'NVDA_Q3FY26': '#76b900', 'AAPL_Q4FY25': '#555555', 'META_Q3_2025': '#0082FB'}
ROLES = {'NVDA_Q3FY26': 'primary benchmark', 'AAPL_Q4FY25': 'secondary supporting',
         'META_Q3_2025': 'exploratory / stress-test'}
INTERP = {
    'NVDA_Q3FY26': 'High retention (91%) with diverse thread coverage; strongest benchmark with 2403 curated comments.',
    'AAPL_Q4FY25': 'Very high retention (98%) but small corpus; clean data but limited statistical power.',
    'META_Q3_2025': 'Severe curation loss (76%) due to wrong-company thread contamination; unsuitable as primary benchmark.',
}

# ============ TASK 1: event_summary.csv ============
rows = []
for eid in EVENTS:
    r = raw_all[raw_all['event_id'] == eid]
    c = cur_all[cur_all['event_id'] == eid]
    raw_n, cur_n = len(r), len(c)
    rem = raw_n - cur_n
    rows.append({
        'event': eid, 'raw_comments': raw_n, 'curated_comments': cur_n,
        'removed_comments': rem, 'retention_pct': round(100 * cur_n / raw_n, 1),
        'removal_pct': round(100 * rem / raw_n, 1),
        'benchmark_role': ROLES[eid], 'interpretation': INTERP[eid],
    })
pd.DataFrame(rows).to_csv(f'{OUT}/event_summary.csv', index=False)
print('[1] event_summary.csv')

# ============ TASK 2: removal_reasons_by_event.csv ============
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('curate', 'scripts/curate_and_freeze.py')
_cmod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_cmod)
THREAD_DECISIONS = _cmod.THREAD_DECISIONS

def classify_reason(reason):
    r = reason.lower()
    if 'wrong company' in r or 'wrong ticker' in r:
        return 'wrong company / wrong ticker'
    if 'off-topic' in r or 'meta-discussion' in r:
        return 'meme / off-topic'
    if 'general market' in r or 'not about' in r or 'tangential' in r or 'not directly' in r:
        return 'generic macro / market chatter'
    if 'outside' in r or 'window' in r:
        return 'outside event window'
    if 'deleted' in r or 'removed' in r or 'unavailable' in r:
        return 'deleted / removed / unavailable'
    return 'other (off-topic / unrelated)'

removal_rows = []
for thread_id, event_id, decision, reason in THREAD_DECISIONS:
    if decision == 'remove':
        n = len(raw_all[(raw_all['event_id'] == event_id) & (raw_all['thread_id'] == thread_id)])
        removal_rows.append({
            'event': event_id, 'removal_reason': classify_reason(reason),
            'reason_detail': reason, 'comment_count': n,
        })

rr_df = pd.DataFrame(removal_rows)
agg_rows = []
for eid in EVENTS:
    subset = rr_df[rr_df['event'] == eid]
    raw_n = len(raw_all[raw_all['event_id'] == eid])
    total_removed = subset['comment_count'].sum()
    for reason, grp in subset.groupby('removal_reason'):
        cnt = grp['comment_count'].sum()
        agg_rows.append({
            'event': eid, 'removal_reason': reason, 'count': cnt,
            'pct_of_removed': round(100 * cnt / max(total_removed, 1), 1),
            'pct_of_raw': round(100 * cnt / max(raw_n, 1), 1),
        })
pd.DataFrame(agg_rows).to_csv(f'{OUT}/removal_reasons_by_event.csv', index=False)
print('[2] removal_reasons_by_event.csv')

# ============ TASK 3: comment_length_stats.csv ============
def token_approx(words):
    return (words * 1.3).astype(int)

len_rows = []
for eid in EVENTS:
    c = cur_all[cur_all['event_id'] == eid]
    texts = c['text'].fillna('')
    chars = texts.str.len()
    words = texts.str.split().str.len().fillna(0).astype(int)
    tokens = token_approx(words)
    len_rows.append({
        'event': eid, 'n_comments': len(c),
        'mean_tokens': round(float(tokens.mean()), 1),
        'median_tokens': int(tokens.median()),
        'std_tokens': round(float(tokens.std()), 1),
        'min_tokens': int(tokens.min()),
        'max_tokens': int(tokens.max()),
        'p25_tokens': int(tokens.quantile(0.25)),
        'p75_tokens': int(tokens.quantile(0.75)),
        'p90_tokens': int(tokens.quantile(0.90)),
        'mean_chars': round(float(chars.mean()), 1),
        'median_chars': int(chars.median()),
        'pct_le100': round(float((tokens <= 100).mean() * 100), 1),
        'pct_le150': round(float((tokens <= 150).mean() * 100), 1),
        'pct_le200': round(float((tokens <= 200).mean() * 100), 1),
    })
pd.DataFrame(len_rows).to_csv(f'{OUT}/comment_length_stats.csv', index=False)

all_texts = cur_all['text'].fillna('')
all_words = all_texts.str.split().str.len().fillna(0).astype(int)
all_tokens = token_approx(all_words)
all_chars = all_texts.str.len()
pd.DataFrame([{
    'n_comments': len(cur_all),
    'mean_tokens': round(float(all_tokens.mean()), 1),
    'median_tokens': int(all_tokens.median()),
    'std_tokens': round(float(all_tokens.std()), 1),
    'min_tokens': int(all_tokens.min()),
    'max_tokens': int(all_tokens.max()),
    'p25_tokens': int(all_tokens.quantile(0.25)),
    'p75_tokens': int(all_tokens.quantile(0.75)),
    'p90_tokens': int(all_tokens.quantile(0.90)),
    'mean_chars': round(float(all_chars.mean()), 1),
    'median_chars': int(all_chars.median()),
    'pct_le100': round(float((all_tokens <= 100).mean() * 100), 1),
    'pct_le150': round(float((all_tokens <= 150).mean() * 100), 1),
    'pct_le200': round(float((all_tokens <= 200).mean() * 100), 1),
}]).to_csv(f'{OUT}/comment_length_overall.csv', index=False)
print('[3] comment_length CSVs')

# ============ TASK 4: comment-length figures ============
fig, ax = plt.subplots(figsize=(8, 4))
for eid in EVENTS:
    c = cur_all[cur_all['event_id'] == eid]
    words = c['text'].fillna('').str.split().str.len().fillna(0).astype(int)
    tokens = token_approx(words)
    ax.hist(tokens, bins=np.arange(0, 210, 5), alpha=0.5,
            label=LABELS[eid], color=COLORS[eid], edgecolor='white', linewidth=0.3)
ax.axvline(150, color='red', linestyle='--', linewidth=1.2, label='150-token cap')
ax.set_xlabel('Approximate token count')
ax.set_ylabel('Number of comments')
ax.set_title('Distribution of Real Comment Lengths (Curated Benchmark)')
ax.legend()
ax.set_xlim(0, 210)
plt.tight_layout()
fig.savefig(f'{OUT}/comment_length_histogram.png', dpi=150)
plt.close()

fig, ax = plt.subplots(figsize=(6, 4))
data = []
labels = []
for eid in EVENTS:
    c = cur_all[cur_all['event_id'] == eid]
    words = c['text'].fillna('').str.split().str.len().fillna(0).astype(int)
    data.append(token_approx(words).values)
    labels.append(LABELS[eid])
bp = ax.boxplot(data, labels=labels, patch_artist=True, showfliers=False)
for patch, eid in zip(bp['boxes'], EVENTS):
    patch.set_facecolor(COLORS[eid])
    patch.set_alpha(0.6)
ax.axhline(150, color='red', linestyle='--', linewidth=1, label='150-token cap')
ax.set_ylabel('Approximate token count')
ax.set_title('Comment Length by Event (outliers hidden)')
ax.legend()
plt.tight_layout()
fig.savefig(f'{OUT}/comment_length_boxplot.png', dpi=150)
plt.close()

# Cumulative coverage plot
fig, ax = plt.subplots(figsize=(7, 4))
for eid in EVENTS:
    c = cur_all[cur_all['event_id'] == eid]
    words = c['text'].fillna('').str.split().str.len().fillna(0).astype(int)
    tokens = token_approx(words)
    sorted_t = np.sort(tokens)
    cdf = np.arange(1, len(sorted_t) + 1) / len(sorted_t)
    ax.plot(sorted_t, cdf, label=LABELS[eid], color=COLORS[eid], linewidth=1.5)
for cap in [100, 150, 200]:
    ax.axvline(cap, color='gray', linestyle=':', linewidth=0.8, alpha=0.7)
    ax.text(cap + 2, 0.5, f'{cap}', fontsize=8, color='gray')
ax.axvline(150, color='red', linestyle='--', linewidth=1.2)
ax.set_xlabel('Token count')
ax.set_ylabel('Cumulative fraction of comments')
ax.set_title('Cumulative Coverage: What Fraction of Real Comments Fit Under N Tokens?')
ax.set_xlim(0, 300)
ax.legend()
plt.tight_layout()
fig.savefig(f'{OUT}/comment_length_cumulative.png', dpi=150)
plt.close()
print('[4] comment-length figures')

# ============ TASK 5: stance bar chart ============
fig, ax = plt.subplots(figsize=(7, 4))
x = np.arange(3)
width = 0.25
stances = ['bullish', 'bearish', 'neutral']
for i, eid in enumerate(EVENTS):
    c = cur_all[cur_all['event_id'] == eid]
    total = len(c)
    pcts = [100 * (c['stance'] == s).sum() / total for s in stances]
    ax.bar(x + i * width, pcts, width, label=LABELS[eid], color=COLORS[eid], alpha=0.75)
ax.set_xticks(x + width)
ax.set_xticklabels([s.title() for s in stances])
ax.set_ylabel('Percentage of comments')
ax.set_title('Stance Distribution in Real Curated Comments')
ax.legend()
plt.tight_layout()
fig.savefig(f'{OUT}/stance_distribution_grouped.png', dpi=150)
plt.close()

pd.DataFrame([{
    'event': eid, 'stance': s,
    'count': (cur_all[cur_all['event_id'] == eid]['stance'] == s).sum(),
    'pct': round(100 * (cur_all[cur_all['event_id'] == eid]['stance'] == s).sum()
                 / len(cur_all[cur_all['event_id'] == eid]), 1),
} for eid in EVENTS for s in stances]).to_csv(f'{OUT}/real_stance_distribution.csv', index=False)
print('[5] stance CSV + chart')

# ============ TASK 6: temporal activity ============
temporal_rows = []
for eid in EVENTS:
    h = cur_all[cur_all['event_id'] == eid]['hours_from_event'].dropna()
    bins = list(range(-24, 49))
    counts, edges = np.histogram(h, bins=bins)
    for i in range(len(counts)):
        temporal_rows.append({
            'event': eid, 'hour_start': int(edges[i]),
            'hour_end': int(edges[i + 1]), 'count': int(counts[i]),
        })
pd.DataFrame(temporal_rows).to_csv(f'{OUT}/temporal_activity_by_event.csv', index=False)

# Summary
temporal_summary = []
for eid in EVENTS:
    h = cur_all[cur_all['event_id'] == eid]['hours_from_event'].dropna()
    total = len(h)
    pre = ((h >= -24) & (h < 0)).sum()
    early = ((h >= 0) & (h <= 6)).sum()
    mid = ((h > 6) & (h <= 24)).sum()
    late = ((h > 24) & (h <= 48)).sum()
    hist_counts = np.histogram(h, bins=range(-24, 49))[0]
    peak = int(hist_counts.argmax()) - 24
    temporal_summary.append({
        'event': eid, 'total': total,
        'pre_event_pct': round(100 * pre / total, 1),
        'early_0_6h_pct': round(100 * early / total, 1),
        'mid_6_24h_pct': round(100 * mid / total, 1),
        'late_24_48h_pct': round(100 * late / total, 1),
        'peak_activity_hour': peak,
    })
pd.DataFrame(temporal_summary).to_csv(f'{OUT}/temporal_activity_summary.csv', index=False)

# Timeline plots
fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
for ax, eid in zip(axes, EVENTS):
    h = cur_all[cur_all['event_id'] == eid]['hours_from_event'].dropna()
    bins = list(range(-24, 49))
    counts, edges = np.histogram(h, bins=bins)
    centers = [(edges[i] + edges[i + 1]) / 2 for i in range(len(counts))]
    ax.bar(centers, counts, width=0.9, color=COLORS[eid], alpha=0.7, edgecolor='white', linewidth=0.3)
    ax.axvline(0, color='red', linestyle='--', linewidth=1, alpha=0.8)
    ax.set_ylabel('Comments')
    ax.set_title(f'{LABELS[eid]} - Hourly Comment Activity Around Earnings')
    ax.text(0.5, ax.get_ylim()[1] * 0.85, 'Earnings release', color='red', fontsize=8, ha='left')
axes[-1].set_xlabel('Hours from earnings release')
plt.tight_layout()
fig.savefig(f'{OUT}/temporal_timeline_all_events.png', dpi=150)
plt.close()
print('[6] temporal CSVs + timeline')

print('\nALL DATA + FIGURES COMPLETE')
