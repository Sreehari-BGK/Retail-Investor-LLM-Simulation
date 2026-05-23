"""
curate_and_freeze.py
Curates the real pilot dataset, reruns metrics, audits stance labels,
and produces all freeze outputs.

Reads:  data/processed/real_comments.csv
        data/processed/real_comments_labeled.csv
        data/processed/real_comment_embeddings.npy

Writes: data/processed/real_comments_curated.csv
        data/processed/real_comments_curated_labeled.csv
        outputs/CURATION_LOG.md
        outputs/REAL_PILOT_SUMMARY.md
        outputs/real_sanity_check_curated.json
        outputs/real_sanity_A_curated.png
        outputs/real_sanity_B_curated.png
        outputs/real_temporal_distribution_curated.png
        outputs/real_stance_distribution_curated.png
        outputs/STANCE_LABEL_AUDIT.md
        outputs/FINAL_DATA_STATUS.txt
"""

import sys, io, json, importlib.util, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

# ── load metrics module ────────────────────────────────────────────────────────
_spec = importlib.util.spec_from_file_location(
    'metrics', 'scripts/04_compute_metrics.py')
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
jsd_stance      = _mod.jsd_stance
wasserstein_time = _mod.wasserstein_time
mmd_rbf          = _mod.mmd_rbf

# ═══════════════════════════════════════════════════════════════════════════════
# 1. CURATION RULES
# ═══════════════════════════════════════════════════════════════════════════════

# Each entry: (thread_id, event_id, decision, reason)
# decision: 'remove' | 'marginal' | 'relevant'
THREAD_DECISIONS = [
    # ── NVDA_Q3FY26 ────────────────────────────────────────────────────────────
    # RELEVANT — directly about NVDA Q3 FY2026 earnings
    ('1p1ked6', 'NVDA_Q3FY26', 'relevant',
     'Title: "NVDA Quarterly Revenue $57 billion (up 62% YoY)" — earnings post'),
    ('1p1kd0p', 'NVDA_Q3FY26', 'relevant',
     'Title: "Nvidia shares rise on stronger than expected revenue" — earnings news'),
    ('1p1pyaw', 'NVDA_Q3FY26', 'relevant',
     'Title: "Burry\'s Recent Tweets: Week of Nvidia Q3 Earnings" — earnings-week context'),
    ('1p1kake', 'NVDA_Q3FY26', 'relevant',
     'Title: "Nvidia Beat Earnings And Raise Guidance" — earnings reaction'),
    ('1p1k9ic', 'NVDA_Q3FY26', 'relevant',
     'Title: "NVDA Earnings with the Double Beat" — earnings numbers'),
    ('1p1gh2w', 'NVDA_Q3FY26', 'relevant',
     'Title: "(NVDA) NVIDIA Q3 2026 Earnings Call | Live Transcript" — official call thread'),
    # MARGINAL — NVDA-adjacent but not directly about Q3 earnings results
    ('1p37j7u', 'NVDA_Q3FY26', 'marginal',
     'Title: "Trump team internally floats idea of selling Nvidia H200 Chips to China" — chip policy, not earnings results; NVDA-adjacent'),
    ('1p1no2c', 'NVDA_Q3FY26', 'marginal',
     'Title: "Why the bubble narrative is missing the point" — NVDA valuation commentary; earnings-week context'),
    ('1p1jbwk', 'NVDA_Q3FY26', 'marginal',
     'Title: "Fork in the road" — general market/NVDA sentiment; ambiguous earnings link; large thread (n=396)'),
    # REMOVE — clearly off-topic
    ('1p36q7u', 'NVDA_Q3FY26', 'remove',
     'Title: "Anatomy of a tenbagger: why the Red Queen hypothesis..." — general investing thesis; no NVDA earnings mention'),
    ('1p2fpnz', 'NVDA_Q3FY26', 'remove',
     'Title: "Fixed that meme from earlier" — meme post; no earnings content'),
    ('1p1zbmk', 'NVDA_Q3FY26', 'remove',
     'Title: "(WMT) Walmart Q3 2026 Earnings Call | Live Transcript" — WRONG COMPANY: Walmart'),
    ('1p13lj6', 'NVDA_Q3FY26', 'remove',
     'Title: "(TGT) Target Q3 2026 Earnings Call | Live Transcript" — WRONG COMPANY: Target'),

    # ── META_Q3_2025 ───────────────────────────────────────────────────────────
    # RELEVANT — directly about META Q3 2025 earnings
    ('1ojfjyr', 'META_Q3_2025', 'relevant',
     'Title: "Meta reports earnings, sees profits hit by one time tax charge" — earnings news'),
    ('1ojqk3q', 'META_Q3_2025', 'relevant',
     'Title: "What is this Meta tax issue?" — META earnings tax discussion'),
    ('1ojvqv2', 'META_Q3_2025', 'relevant',
     'Title: "Meta to acknowledge a devaluation of their Deferred Tax Assets" — META earnings, DTA'),
    ('1ojfizn', 'META_Q3_2025', 'relevant',
     'Title: "Meta stock sinks after tax hit weighs on earnings" — earnings reaction'),
    # REMOVE — wrong company or off-topic
    ('1ojkjhb', 'META_Q3_2025', 'remove',
     'Title: "Apple to split in 2026??" — WRONG COMPANY: Apple (also appears in AAPL event)'),
    ('1ojag2j', 'META_Q3_2025', 'remove',
     'Title: "Absolutely everything you need to know about MSFT earnings" — WRONG COMPANY: Microsoft'),
    ('1okx9vg', 'META_Q3_2025', 'remove',
     'Title: "Something about Kenvue $KVUE" — WRONG COMPANY: Kenvue'),
    ('1okaep4', 'META_Q3_2025', 'remove',
     'Title: "Reddit releases their Q3 earnings" — WRONG COMPANY: Reddit (RDDT)'),
    ('1ojffro', 'META_Q3_2025', 'remove',
     'Title: "ServiceNow tops estimates, approves 5-for-1 stock split" — WRONG COMPANY: ServiceNow'),
    ('1ojfcc2', 'META_Q3_2025', 'remove',
     'Title: "Chipotle cuts same-store sales forecast" — WRONG COMPANY: Chipotle'),
    ('1ojf9mj', 'META_Q3_2025', 'remove',
     'Title: "Alphabet tops $100 billion quarterly revenue for first time" — WRONG COMPANY: Alphabet'),
    ('1oko5wp', 'META_Q3_2025', 'remove',
     'Title: "In a survey of 10k teens, <1% listed Reddit as their favorite social" — off-topic: RDDT survey'),
    ('1ojdtli', 'META_Q3_2025', 'remove',
     'Title: "Lumentum $LITEs it up: Key Supplier of NVIDIA Optics" — WRONG COMPANY: Lumentum/NVDA'),
    ('1okbxi0', 'META_Q3_2025', 'remove',
     'Title: "Thank you $AMZN" — WRONG COMPANY: Amazon'),
    ('1okar62', 'META_Q3_2025', 'remove',
     'Title: "RDDT announces Q3 Earnings Beat" — WRONG COMPANY: Reddit (RDDT)'),

    # ── AAPL_Q4FY25 ────────────────────────────────────────────────────────────
    # RELEVANT
    ('1okb9l1', 'AAPL_Q4FY25', 'relevant',
     'Title: "Apple earnings strong beat and ecosystem domination" — directly AAPL Q4 earnings'),
    # MARGINAL
    ('1ojkjhb', 'AAPL_Q4FY25', 'marginal',
     'Title: "Apple to split in 2026??" — Apple topic but not about Q4 FY2025 earnings results'),
    ('1okpz3y', 'AAPL_Q4FY25', 'marginal',
     'Title: "r/Stocks Daily Discussion & Fundamentals Friday Oct 31, 2025" — megathread; mixed content; day of AAPL post-earnings but not exclusively AAPL'),
    # REMOVE
    ('1oky7mz', 'AAPL_Q4FY25', 'remove',
     'Title: "Seagate : -7,60%, why ??" — WRONG COMPANY: Seagate'),
]


def build_decision_maps():
    remove_set  = set()
    marginal_set = set()
    relevant_set = set()
    reasons = {}
    for tid, eid, decision, reason in THREAD_DECISIONS:
        key = (tid, eid)
        reasons[key] = reason
        if decision == 'remove':
            remove_set.add(key)
        elif decision == 'marginal':
            marginal_set.add(key)
        else:
            relevant_set.add(key)
    return remove_set, marginal_set, relevant_set, reasons


def apply_relevance(df, remove_set, marginal_set, relevant_set):
    """Add relevance column; return curated (non-removed) df."""
    def flag(row):
        key = (row['thread_id'], row['event_id'])
        if key in remove_set:
            return 'remove'
        if key in marginal_set:
            return 'marginal'
        if key in relevant_set:
            return 'relevant'
        return 'unclassified'  # safety net

    df = df.copy()
    df['relevance'] = df.apply(flag, axis=1)
    curated = df[df['relevance'] != 'remove'].copy()
    return df, curated


# ═══════════════════════════════════════════════════════════════════════════════
# 2. LOAD DATA
# ═══════════════════════════════════════════════════════════════════════════════
print('Loading data...')
raw     = pd.read_csv('data/processed/real_comments.csv')
labeled = pd.read_csv('data/processed/real_comments_labeled.csv')
emb_all = np.load('data/processed/real_comment_embeddings.npy')
assert len(raw) == len(emb_all) == len(labeled), 'Row count mismatch!'
print(f'  raw: {len(raw)} rows, embeddings: {emb_all.shape}')

remove_set, marginal_set, relevant_set, reasons = build_decision_maps()

raw_flagged,  curated_raw     = apply_relevance(raw,     remove_set, marginal_set, relevant_set)
lab_flagged,  curated_labeled = apply_relevance(labeled, remove_set, marginal_set, relevant_set)

# Align embeddings to curated index
curated_idx = curated_raw.index.to_numpy()
emb_curated = emb_all[curated_idx]
assert len(curated_raw) == len(emb_curated)

print(f'  curated: {len(curated_raw)} rows  ({len(raw)-len(curated_raw)} removed)')

# Save curated files (originals untouched)
curated_raw.to_csv('data/processed/real_comments_curated.csv', index=False)
curated_labeled.to_csv('data/processed/real_comments_curated_labeled.csv', index=False)
np.save('data/processed/real_comment_embeddings_curated.npy', emb_curated)
print('  Saved: real_comments_curated.csv, real_comments_curated_labeled.csv, embeddings_curated.npy')


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CURATION LOG
# ═══════════════════════════════════════════════════════════════════════════════
print('\nWriting CURATION_LOG.md ...')

lines = ['# CURATION_LOG.md', f'Generated: 2026-03-19', '',
         '## Summary', '']

orig_total = len(raw)
cur_total  = len(curated_raw)
removed_total = orig_total - cur_total

lines += [f'| | Rows |', f'|---|---|',
          f'| Original (real_comments.csv) | {orig_total} |',
          f'| After curation | {cur_total} |',
          f'| Removed | {removed_total} |', '']

for eid in raw['event_id'].unique():
    orig_n = len(raw[raw['event_id'] == eid])
    cur_n  = len(curated_raw[curated_raw['event_id'] == eid])
    rem_n  = orig_n - cur_n
    marg_n = len(curated_raw[(curated_raw['event_id']==eid) & (curated_raw['relevance']=='marginal')])
    rel_n  = len(curated_raw[(curated_raw['event_id']==eid) & (curated_raw['relevance']=='relevant')])
    lines += [f'| {eid} | {orig_n} original | {cur_n} after | {rem_n} removed | {rel_n} relevant | {marg_n} marginal |']

lines += ['', '## Filtering Rules', '',
          '### Rule 1: Wrong company (REMOVE)',
          'Posts whose titles are about a company other than the target ticker are removed.',
          'Identified by reading thread titles and matching against target ticker.',
          '',
          '### Rule 2: Clearly off-topic (REMOVE)',
          'Posts with no identifiable connection to the target company or its earnings (memes, general thesis posts).',
          '',
          '### Rule 3: Company-adjacent but not earnings-focused (MARGINAL)',
          'Posts about the target company during the event window, but discussing policy/macro/valuation rather than earnings results directly. Kept in curated dataset with relevance=marginal.',
          '',
          '### Rule 4: Mixed-content megathreads (MARGINAL)',
          'Daily discussion megathreads covering many topics. Kept but flagged as marginal.',
          '',
          '## Removed Posts by Event', '']

for eid in raw['event_id'].unique():
    lines.append(f'### {eid}')
    removes = [(tid, eid2, r) for (tid, eid2), decision, r
               in [(k, d, reasons[k]) for k, d in
                   [(k, 'remove') for k in remove_set if k[1]==eid] +
                   [(k, 'marginal') for k in marginal_set if k[1]==eid]]
               if decision == 'remove']
    # Flatten: just get removed thread IDs for this event
    removed_tids = [tid for (tid, eid2) in remove_set if eid2 == eid]
    for tid in removed_tids:
        n = len(raw[(raw['event_id']==eid) & (raw['thread_id']==tid)])
        reason = reasons.get((tid, eid), 'no reason recorded')
        lines.append(f'- `{tid}` (n={n}) REMOVED — {reason}')
    marginal_tids = [tid for (tid, eid2) in marginal_set if eid2 == eid]
    for tid in marginal_tids:
        n = len(raw[(raw['event_id']==eid) & (raw['thread_id']==tid)])
        reason = reasons.get((tid, eid), 'no reason recorded')
        lines.append(f'- `{tid}` (n={n}) MARGINAL — {reason}')
    lines.append('')

lines += ['## What Remains Uncertain', '',
          '- NVDA thread `1p1jbwk` ("Fork in the road"): n=396 comments. Generic market sentiment post during NVDA earnings week. May contain NVDA earnings discussion or may not. Kept as marginal.',
          '- NVDA thread `1p1no2c` ("Why the bubble narrative is missing the point"): n=287. NVDA valuation debate. Relevant to investor reaction but not specifically about Q3 numbers.',
          '- NVDA thread `1p37j7u` ("Trump team/H200 Chips"): n=89. China chip export policy, not earnings. Kept as marginal since it reflects investor sentiment about NVDA in the earnings window.',
          '- AAPL thread `1okpz3y` ("r/Stocks Daily Discussion"): n=293. Mixed megathread. Kept marginal; some comments inside may be AAPL earnings discussion.',
          '- AAPL thread `1ojkjhb` ("Apple to split in 2026??"): n=16. Apple topic but not Q4 FY2025 earnings. Kept marginal.',
          '- Comment-level relevance: No per-comment relevance filter was applied. Comments within kept threads may individually be off-topic.',
          '- Stance labels: Still provisional keyword-based. See STANCE_LABEL_AUDIT.md.',
          ]

with open('outputs/CURATION_LOG.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('  Saved: outputs/CURATION_LOG.md')


# ═══════════════════════════════════════════════════════════════════════════════
# 4. REAL PILOT SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
print('Writing REAL_PILOT_SUMMARY.md ...')

def pilot_lines(df, label):
    lines = [f'### {label}', '']
    for eid in df['event_id'].unique():
        e = df[df['event_id']==eid]
        lines.append(f'**{eid}**')
        lines.append(f'- Total rows: {len(e)}')
        for sub, g in e.groupby('subreddit'):
            lines.append(f'- {sub}: {len(g)} rows')
        for rel, g in e.groupby('relevance'):
            lines.append(f'- relevance={rel}: {len(g)} rows')
        lines.append('')
    return lines

event_meta = {
    'NVDA_Q3FY26': {
        'ticker': 'NVDA',
        'event_time': '2025-11-19T21:00:00Z (4pm ET)',
        'sec_8k': '0001045810-25-000228',
        'sec_url': 'https://www.sec.gov/Archives/edgar/data/1045810/000104581025000228/0001045810-25-000228-index.htm',
        'item': '2.02 Results of Operations and Financial Condition',
        'call_time': '2pm PT / 5pm ET (22:00 UTC) confirmed from press release q3fy26pr.htm',
        'period': 'Q3 FY2026 (quarter ended ~Oct 2025)',
    },
    'META_Q3_2025': {
        'ticker': 'META',
        'event_time': '2025-10-29T21:00:00Z (4pm ET)',
        'sec_8k': '0001628280-25-047114',
        'sec_url': 'https://www.sec.gov/Archives/edgar/data/1326801/000162828025047114/0001628280-25-047114-index.htm',
        'item': '2.02 Results of Operations and Financial Condition',
        'call_time': '1:30pm PT / 4:30pm ET (21:30 UTC) confirmed from press release meta-09302025xexhibit991.htm',
        'period': 'Q3 2025 (quarter ended Sep 30, 2025)',
    },
    'AAPL_Q4FY25': {
        'ticker': 'AAPL',
        'event_time': '2025-10-30T21:00:00Z (4pm ET)',
        'sec_8k': '0000320193-25-000077',
        'sec_url': 'https://www.sec.gov/Archives/edgar/data/320193/000032019325000077/0000320193-25-000077-index.htm',
        'item': '2.02 Results of Operations and Financial Condition',
        'call_time': '2pm PT / 5pm ET (22:00 UTC) confirmed from press release a8-kex991q4202509272025.htm',
        'period': 'Q4 FY2025 (quarter ended Sep 27, 2025)',
    },
}

plines = ['# REAL_PILOT_SUMMARY.md', 'Generated: 2026-03-19', '', '## Events', '']
for eid, meta in event_meta.items():
    plines += [
        f'### {eid}',
        f'- Ticker: {meta["ticker"]}',
        f'- Period: {meta["period"]}',
        f'- Event time used: {meta["event_time"]}',
        f'- SEC 8-K accession: {meta["sec_8k"]}',
        f'- SEC 8-K index (verified, HTTP 200): {meta["sec_url"]}',
        f'- 8-K item confirmed: {meta["item"]}',
        f'- Conference call time: {meta["call_time"]}',
        '',
    ]

plines += ['## Row Counts', '', '### Uncurated (original collection)', '']
for eid in raw['event_id'].unique():
    e = raw[raw['event_id']==eid]
    plines.append(f'- {eid}: {len(e)} rows')
    for sub, g in e.groupby('subreddit'):
        plines.append(f'  - {sub}: {len(g)}')

plines += ['', '### Curated', '']
for eid in curated_raw['event_id'].unique():
    e = curated_raw[curated_raw['event_id']==eid]
    plines.append(f'- {eid}: {len(e)} rows total')
    for sub, g in e.groupby('subreddit'):
        plines.append(f'  - {sub}: {len(g)}')
    for rel, g in e.groupby('relevance'):
        plines.append(f'  - relevance={rel}: {len(g)}')

plines += ['', '## What Was Verified from SEC / Press Releases', '',
           '- All three 8-K filings fetched from data.sec.gov (HTTP 200)',
           '- All three confirmed as Item 2.02: Results of Operations and Financial Condition',
           '- Conference call times confirmed from Exhibit 99.1 press release HTML documents',
           '- Exact intraday release minute NOT in SEC EDGAR records (date only)',
           '- Event time set to 21:00 UTC (4pm ET) as conservative market-close proxy',
           '',
           '## Remaining Limitations', '',
           '- AAPL_Q4FY25 has only 74 clearly relevant comments (thread 1okb9l1)',
           '- 309 AAPL rows are marginal (megathread + Apple split post)',
           '- META_Q3_2025 reduced from 1444 to 344 rows after removing wrong-company threads',
           '- Some marginal NVDA threads (n=772 total) may dilute signal',
           '- No per-comment relevance filter applied',
           '- Stance labels are provisional keyword-based (see STANCE_LABEL_AUDIT.md)',
           '- Reddit collection used public JSON API; rate-limited, no guarantee of completeness',
           '- wallstreetbets returned 0 posts for AAPL (only r/stocks data for AAPL)',
           ]

with open('outputs/REAL_PILOT_SUMMARY.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(plines))
print('  Saved: outputs/REAL_PILOT_SUMMARY.md')


# ═══════════════════════════════════════════════════════════════════════════════
# 5. METRICS ON CURATED DATA (+ side-by-side with uncurated)
# ═══════════════════════════════════════════════════════════════════════════════
print('\nRunning metrics on curated data ...')

rng = np.random.default_rng(42)

def run_sanity(df, emb, label):
    results = {}
    for eid in df['event_id'].unique():
        mask = df['event_id'] == eid
        edf  = df[mask].reset_index(drop=True)
        eidx = np.where(mask)[0]
        eemb = emb[eidx]
        n = len(edf)
        if n < 20:
            results[eid] = {'n': n, 'skipped': True}
            continue

        a_idx, b_idx = train_test_split(np.arange(n), test_size=0.5, random_state=42)

        jsd = jsd_stance(edf.iloc[a_idx]['stance'].tolist(),
                         edf.iloc[b_idx]['stance'].tolist())
        wd  = wasserstein_time(edf.iloc[a_idx]['hours_from_event'].to_numpy(),
                               edf.iloc[b_idx]['hours_from_event'].to_numpy())
        mmd = mmd_rbf(eemb[a_idx], eemb[b_idx])

        unif = rng.uniform(-24, 48, size=len(b_idx))
        wd_u = wasserstein_time(edf.iloc[a_idx]['hours_from_event'].to_numpy(), unif)

        results[eid] = {
            'n': n, 'skipped': False,
            'A_RvR':        {'jsd': jsd,  'wd': wd,  'mmd': mmd},
            'B_vs_uniform': {'wd': wd_u,  'increased': wd_u > wd},
        }
        print(f'  [{label}] {eid} n={n}: JSD={jsd:.4f} WD={wd:.4f} MMD={mmd:.6f} | WD_unif={wd_u:.4f}')
    return results

# Need stance column in curated_raw for metrics
curated_for_metrics = curated_labeled.copy()

results_curated   = run_sanity(curated_for_metrics,  emb_curated,  'curated')
results_uncurated = run_sanity(labeled,               emb_all,      'original')

# Merge for output
combined = {}
for eid in raw['event_id'].unique():
    combined[eid] = {
        'original':  results_uncurated.get(eid, {}),
        'curated':   results_curated.get(eid, {}),
    }

with open('outputs/real_sanity_check_curated.json', 'w') as f:
    json.dump(combined, f, indent=2, default=str)
print('  Saved: outputs/real_sanity_check_curated.json')


# ═══════════════════════════════════════════════════════════════════════════════
# 6. PLOTS
# ═══════════════════════════════════════════════════════════════════════════════
print('\nPlotting ...')
events = list(raw['event_id'].unique())
colors = {'NVDA_Q3FY26': '#76b900', 'META_Q3_2025': '#0082FB', 'AAPL_Q4FY25': '#555555'}
rel_alpha = {'relevant': 0.85, 'marginal': 0.45}
rel_hatch = {'relevant': '', 'marginal': '//'}

# Temporal distribution curated
fig, axes = plt.subplots(1, 3, figsize=(14, 4))
bins = np.arange(-24, 49, 1)
for ax, eid in zip(axes, events):
    edf = curated_for_metrics[curated_for_metrics['event_id'] == eid]
    for rel in ['relevant', 'marginal']:
        sub = edf[edf['relevance'] == rel]
        if len(sub):
            ax.hist(sub['hours_from_event'], bins=bins,
                    color=colors.get(eid, 'blue'),
                    alpha=rel_alpha[rel], hatch=rel_hatch[rel],
                    edgecolor='white', linewidth=0.3,
                    label=f'{rel} (n={len(sub)})', stacked=False)
    ax.axvline(0, color='red', linestyle='--', linewidth=1.5, label='Event time')
    ax.set_title(eid.replace('_', ' '), fontsize=9)
    ax.set_xlabel('Hours from earnings release')
    ax.set_ylabel('Count')
    ax.legend(fontsize=7)
fig.suptitle('Curated Real Data: Temporal Distribution (solid=relevant, hatch=marginal)', fontsize=10)
plt.tight_layout()
plt.savefig('outputs/real_temporal_distribution_curated.png', dpi=150)
plt.close()

# Stance distribution curated
fig, axes = plt.subplots(1, 3, figsize=(12, 4))
stance_colors = {'bullish': '#2ecc71', 'bearish': '#e74c3c', 'neutral': '#95a5a6'}
for ax, eid in zip(axes, events):
    edf = curated_for_metrics[curated_for_metrics['event_id'] == eid]
    x = np.arange(3)
    labels_s = ['bullish', 'bearish', 'neutral']
    for rel, offset, width in [('relevant', -0.2, 0.35), ('marginal', 0.2, 0.35)]:
        sub = edf[edf['relevance'] == rel]
        if not len(sub): continue
        total = max(len(sub), 1)
        vals = [sub[sub['stance']==l].shape[0]/total for l in labels_s]
        bars = ax.bar(x + offset, vals, width,
                      color=[stance_colors[l] for l in labels_s],
                      alpha=rel_alpha[rel], label=rel)
    ax.set_xticks(x); ax.set_xticklabels(labels_s)
    ax.set_title(eid.replace('_', ' '), fontsize=9)
    ax.set_ylabel('Proportion')
    ax.legend(fontsize=7)
    ax.annotate('PROVISIONAL\nrule-based', xy=(0.5, 0.85), xycoords='axes fraction',
                ha='center', fontsize=7, color='gray', style='italic')
fig.suptitle('Curated Real Data: Stance Distribution (left=relevant, right=marginal)', fontsize=10)
plt.tight_layout()
plt.savefig('outputs/real_stance_distribution_curated.png', dpi=150)
plt.close()

# Test A bar chart curated vs original
fig, axes = plt.subplots(1, 3, figsize=(13, 4))
metric_keys = [('jsd', 'JSD Stance'), ('wd', 'Wasserstein Time'), ('mmd', 'MMD Semantic')]
col_pairs = [('#4878CF', '#A0BBE0'), ('#6ACC65', '#B5E3B0'), ('#D65F5F', '#EBB0B0')]
for ax, (mk, mlabel), (c_cur, c_orig) in zip(axes, metric_keys, col_pairs):
    x = np.arange(len(events))
    w = 0.3
    vals_cur  = [combined[e]['curated'].get('A_RvR', {}).get(mk, 0) for e in events]
    vals_orig = [combined[e]['original'].get('A_RvR', {}).get(mk, 0) for e in events]
    ax.bar(x - w/2, vals_cur,  w, label='Curated',   color=c_cur,  alpha=0.9)
    ax.bar(x + w/2, vals_orig, w, label='Uncurated', color=c_orig, alpha=0.9)
    ax.set_title(f'Test A: {mlabel}', fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([e.replace('_', '\n') for e in events], fontsize=7)
    ax.set_ylabel('Distance')
    ax.legend(fontsize=7)
fig.suptitle('Test A Real vs Real — Curated vs Uncurated', fontsize=10)
plt.tight_layout()
plt.savefig('outputs/real_sanity_A_curated.png', dpi=150)
plt.close()

# Test B bar chart
fig, ax = plt.subplots(figsize=(9, 4))
x = np.arange(len(events))
w = 0.22
vals_rr_cur  = [combined[e]['curated'].get('A_RvR', {}).get('wd', 0) for e in events]
vals_ru_cur  = [combined[e]['curated'].get('B_vs_uniform', {}).get('wd', 0) for e in events]
vals_rr_orig = [combined[e]['original'].get('A_RvR', {}).get('wd', 0) for e in events]
vals_ru_orig = [combined[e]['original'].get('B_vs_uniform', {}).get('wd', 0) for e in events]
ax.bar(x - 1.5*w, vals_rr_cur,  w, label='Curated: RvR',     color='#4878CF', alpha=0.9)
ax.bar(x - 0.5*w, vals_ru_cur,  w, label='Curated: vs Unif', color='#D65F5F', alpha=0.9)
ax.bar(x + 0.5*w, vals_rr_orig, w, label='Orig: RvR',        color='#A0BBE0', alpha=0.9)
ax.bar(x + 1.5*w, vals_ru_orig, w, label='Orig: vs Unif',    color='#EBB0B0', alpha=0.9)
ax.set_xticks(x); ax.set_xticklabels(events, fontsize=9)
ax.set_ylabel('Wasserstein Distance')
ax.set_title('Test B: Temporal — Real vs Real vs Uniform (Curated vs Uncurated)')
ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig('outputs/real_sanity_B_curated.png', dpi=150)
plt.close()
print('  Plots saved.')


# ═══════════════════════════════════════════════════════════════════════════════
# 7. STANCE LABEL AUDIT (sample 60 comments)
# ═══════════════════════════════════════════════════════════════════════════════
print('\nRunning stance label audit ...')

sample_rows = []
for eid in curated_for_metrics['event_id'].unique():
    e = curated_for_metrics[curated_for_metrics['event_id']==eid]
    n_sample = min(20, len(e))
    s = e.sample(n=n_sample, random_state=99)
    sample_rows.append(s)
sample_df = pd.concat(sample_rows).reset_index(drop=True)

# Heuristic inspection: flag likely errors
def inspect_label(row):
    text = str(row['text']).lower()
    label = row['stance']
    flags = []

    # Negation patterns
    neg_bull = any(p in text for p in ['not bullish', "not bull", 'not buying', "don't buy",
                                        "didn't buy", 'no longer hold', 'stopped holding'])
    neg_bear = any(p in text for p in ['not bearish', 'not bear', 'not selling', "don't sell"])
    if neg_bull and label == 'bullish': flags.append('NEGATION: "not bullish"-type phrase but labeled bullish')
    if neg_bear and label == 'bearish': flags.append('NEGATION: "not bearish"-type phrase but labeled bearish')

    # Sarcasm indicators
    sarc = any(p in text for p in ['lol', 'lmao', 'haha', 'sure', '/s', '...', 'genius',
                                    'totally', 'definitely', 'obviously', 'great job'])
    if sarc: flags.append('POSSIBLE SARCASM: hedging/irony markers present')

    # Mixed stance: both bull and bear keywords
    bull_hit = any(p in text for p in ['bull', 'buy', 'long', 'calls', 'beat', 'gain', 'rise'])
    bear_hit = any(p in text for p in ['bear', 'sell', 'short', 'puts', 'miss', 'drop', 'crash'])
    if bull_hit and bear_hit: flags.append('MIXED: both bullish and bearish keywords present')

    # Very short text
    if len(str(row['text'])) < 25: flags.append('SHORT TEXT: label may be unreliable')

    # Question-only
    if text.strip().endswith('?') and label != 'neutral':
        flags.append('QUESTION: text ends in "?" but not neutral')

    return flags

sample_df['flags'] = sample_df.apply(inspect_label, axis=1)
sample_df['has_flag'] = sample_df['flags'].apply(lambda x: len(x) > 0)

total = len(sample_df)
flagged = sample_df['has_flag'].sum()
flag_rate = flagged / total

alines = ['# STANCE_LABEL_AUDIT.md',
          'Generated: 2026-03-19',
          '',
          '## Method',
          '',
          'This is a ROUGH LABEL QUALITY CHECK, not a validated classifier evaluation.',
          'Labels are produced by a keyword-counting heuristic (scripts/label_stance_rulebased.py).',
          'No ground truth annotations exist.',
          '',
          f'Sample: {total} comments ({total//len(curated_for_metrics["event_id"].unique())} per event where possible)',
          'Inspection: heuristic flag rules applied to each sampled comment.',
          'Flags are NOT definitive errors — they are signals that the label may be wrong.',
          '',
          '## Distribution in Sample', '']

for eid in sample_df['event_id'].unique():
    sub = sample_df[sample_df['event_id']==eid]
    alines.append(f'**{eid}** (n={len(sub)}):')
    for lbl, g in sub.groupby('stance'):
        alines.append(f'  - {lbl}: {len(g)}')

alines += ['', '## Flag Summary', '',
           f'Total sampled: {total}',
           f'With at least one flag: {flagged} ({flag_rate*100:.1f}%)',
           f'Clean (no flags): {total-flagged} ({(1-flag_rate)*100:.1f}%)',
           '']

flag_types = {}
for flags in sample_df['flags']:
    for f in flags:
        ft = f.split(':')[0]
        flag_types[ft] = flag_types.get(ft, 0) + 1
alines.append('Flag type counts:')
for ft, cnt in sorted(flag_types.items(), key=lambda x: -x[1]):
    alines.append(f'  - {ft}: {cnt}')

alines += ['', '## Sampled Comments with Flags', '']
flagged_df = sample_df[sample_df['has_flag']].copy()
for _, row in flagged_df.iterrows():
    text_short = str(row['text'])[:150].replace('\n', ' ')
    alines.append(f'**[{row["event_id"]}]** stance={row["stance"]}')
    alines.append(f'  text: {text_short}')
    for f in row['flags']:
        alines.append(f'  FLAG: {f}')
    alines.append('')

alines += ['## Main Failure Modes', '',
           '1. **Negation not handled**: "not bullish", "not buying anymore" still count as bullish keywords.',
           '2. **Sarcasm**: Reddit uses heavy irony. "Wow great quarter" could be bearish sarcasm.',
           '3. **Mixed stance**: A comment discussing both bulls and bears gets arbitrary tie-break.',
           '4. **Short texts**: <30 char comments are hard to classify reliably.',
           '5. **Context-dependent neutral**: Many comments asking questions (neutral) may use one sentiment word incidentally.',
           '6. **Domain slang**: "to the moon" (bullish slang) not in keyword list; "bag holder" (bearish) not in list.',
           '',
           '## Estimated Rough Accuracy',
           '',
           f'No ground truth exists. Based on flag inspection: ~{100-int(flag_rate*100)}% of labels appear '
           f'plausible (no obvious flag). This is not a precision/recall estimate.',
           'Treat stance distributions as directional indicators only, not precise measurements.',
           '',
           '## What Should Replace This',
           '',
           '- Apply a zero-shot NLI stance classifier (e.g., facebook/bart-large-mnli) to all comments',
           '- Or: manually annotate a 200-comment gold set and measure keyword-label agreement',
           '- Report Cohen\'s kappa or percent agreement against the gold set',
           ]

with open('outputs/STANCE_LABEL_AUDIT.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(alines))
print(f'  Saved: outputs/STANCE_LABEL_AUDIT.md  (flagged {flagged}/{total} = {flag_rate*100:.1f}%)')


# ═══════════════════════════════════════════════════════════════════════════════
# 8. FINAL DATA STATUS
# ═══════════════════════════════════════════════════════════════════════════════
print('\nWriting FINAL_DATA_STATUS.txt ...')

cur_rel = curated_for_metrics[curated_for_metrics['relevance']=='relevant']
cur_mar = curated_for_metrics[curated_for_metrics['relevance']=='marginal']

status_lines = [
    'FINAL_DATA_STATUS.txt',
    'Generated: 2026-03-19',
    '=' * 60,
    '',
    'WHAT IS REAL',
    '------------',
    f'  data/processed/real_comments.csv              {len(raw)} rows — real Reddit comments collected via public JSON API',
    f'  data/processed/real_comments_labeled.csv      {len(labeled)} rows — same + provisional stance labels',
    f'  data/processed/real_comment_embeddings.npy    shape ({len(emb_all)}, 384) — SBERT embeddings of real text',
    f'  data/raw/real_reddit_NVDA_Q3FY26.csv          2641 rows',
    f'  data/raw/real_reddit_META_Q3_2025.csv         1444 rows',
    f'  data/raw/real_reddit_AAPL_Q4FY25.csv          392 rows',
    f'  data/raw/collection_log.json                  collection metadata',
    '',
    'WHAT IS SYNTHETIC (DO NOT MIX WITH REAL)',
    '-----------------------------------------',
    '  data/processed/comments.csv                   300 rows — 15 hardcoded template sentences',
    '  data/processed/comment_embeddings.npy         (300, 384) — embeddings of synthetic text',
    '  data/processed/comments_with_index.csv        same 300 synthetic rows',
    '',
    'WHAT IS CURATED',
    '---------------',
    f'  data/processed/real_comments_curated.csv          {len(curated_raw)} rows — real data with off-topic threads removed + relevance flag',
    f'  data/processed/real_comments_curated_labeled.csv  {len(curated_labeled)} rows — same + stance labels',
    f'  data/processed/real_comment_embeddings_curated.npy ({len(emb_curated)}, 384)',
    '',
    f'  Curated breakdown:',
    f'    relevant: {len(cur_rel)} rows',
    f'    marginal: {len(cur_mar)} rows',
    f'    removed:  {len(raw)-len(curated_raw)} rows',
    '',
    '  Per event (curated):',
]
for eid in curated_for_metrics['event_id'].unique():
    e = curated_for_metrics[curated_for_metrics['event_id']==eid]
    rel_n = len(e[e['relevance']=='relevant'])
    mar_n = len(e[e['relevance']=='marginal'])
    status_lines.append(f'    {eid}: {len(e)} total  ({rel_n} relevant, {mar_n} marginal)')

status_lines += [
    '',
    'WHAT IS STILL PROVISIONAL',
    '--------------------------',
    '  Stance labels: keyword-based rule (see scripts/label_stance_rulebased.py)',
    '  Method: count bullish/bearish keywords; assign majority; neutral if tie',
    '  NOT a trained classifier. NOT validated against human annotations.',
    f'  Rough flag rate from audit: ~{flag_rate*100:.0f}% of sampled comments have a potential labeling issue',
    '  Distribution: 64.2% neutral, 21.5% bullish, 14.3% bearish (full uncurated set)',
    '',
    '  Event times: set to 21:00 UTC (4pm ET) on SEC filing date',
    '  Exact intraday release minute not available from SEC EDGAR',
    '  Conference call times confirmed from press releases; event_time ± ~1h uncertainty',
    '',
    '  Comment relevance: thread-level only; no per-comment filter applied',
    '  Some comments in kept threads may be off-topic',
    '',
    'WHETHER DATA SECTION IS SUBMISSION-SAFE',
    '-----------------------------------------',
    '  YES, with the following required disclosures in the report:',
    '',
    '  1. State clearly that real_comments_curated.csv is the primary analysis dataset',
    '  2. State that off-topic threads were removed using thread-title inspection',
    '     (exact IDs and counts in outputs/CURATION_LOG.md)',
    '  3. State that stance labels are provisional keyword-based; not validated',
    '  4. State that AAPL has significantly fewer relevant comments (74 clearly relevant)',
    '  5. Do NOT claim SEC EDGAR provided intraday release times (only dates were available)',
    '  6. Do NOT mix synthetic data (300-row comments.csv) with real data in any figure or table',
    '  7. Do NOT claim the marginal rows (n={}) are directly about earnings events'.format(len(cur_mar)),
    '',
    'NOT YET DONE (SIMULATION SIDE)',
    '--------------------------------',
    '  LLM agent simulation: NOT run',
    '  No sim_agent rows exist in any dataset',
    '  Comparison of real vs agent simulation: NOT computed',
    '=' * 60,
]

with open('outputs/FINAL_DATA_STATUS.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(status_lines))
print('  Saved: outputs/FINAL_DATA_STATUS.txt')
print('\nDone. All outputs written.')
