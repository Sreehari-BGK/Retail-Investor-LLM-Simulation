#!/usr/bin/env python3
"""Extract thread-level inventory for seminar support pack."""
import sys, io, os, importlib.util
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
os.makedirs('outputs/seminar_support', exist_ok=True)

# Extract THREAD_DECISIONS without executing the whole script (it has side effects)
src = open('scripts/curate_and_freeze.py', encoding='utf-8').read()
bracket_start = src.index('[', src.index('THREAD_DECISIONS = ['))
depth = 0
end = None
for i, ch in enumerate(src[bracket_start:], bracket_start):
    if ch == '[':
        depth += 1
    elif ch == ']':
        depth -= 1
        if depth == 0:
            end = i + 1
            break
import ast
list_src = src[bracket_start:end]
decisions = ast.literal_eval(list_src)
dec_map = {(tid, eid): (dec, reason) for tid, eid, dec, reason in decisions}

cur_all = pd.read_csv('data/processed/real_comments_curated_labeled.csv')

rows_out = []
for f, eid in [
    ('data/raw/real_reddit_NVDA_Q3FY26.csv', 'NVDA_Q3FY26'),
    ('data/raw/real_reddit_AAPL_Q4FY25.csv', 'AAPL_Q4FY25'),
    ('data/raw/real_reddit_META_Q3_2025.csv', 'META_Q3_2025'),
]:
    raw = pd.read_csv(f)
    for tid, grp in raw.groupby('thread_id'):
        post_row = grp[grp['comment_id'] == tid]
        if len(post_row):
            title = str(post_row.iloc[0]['text']).split('\n')[0].strip()[:300]
        else:
            title = '(post row not found)'
        subreddit = str(grp.iloc[0]['subreddit'])
        raw_n = len(grp)
        cur_n = len(cur_all[(cur_all['event_id']==eid) & (cur_all['thread_id']==tid)])
        dec, reason = dec_map.get((tid, eid), ('unclassified', ''))
        rows_out.append({
            'event_id': eid, 'subreddit': subreddit, 'thread_id': tid,
            'title': title, 'raw_n': raw_n, 'curated_n': cur_n,
            'decision': dec, 'reason': reason,
        })

out = pd.DataFrame(rows_out)
out.to_csv('outputs/seminar_support/_threads_inventory.csv', index=False)
print(f'Wrote {len(out)} rows -> outputs/seminar_support/_threads_inventory.csv')
for eid in out['event_id'].unique():
    sub = out[out['event_id']==eid]
    print(f'  {eid}: {len(sub)} threads, decisions: {sub["decision"].value_counts().to_dict()}')
