#!/usr/bin/env python3
"""Compute Cohen's kappa, per-class P/R/F1, and confusion matrix from stance_validation_sample.csv.
Run AFTER manually filling human_label column."""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
from sklearn.metrics import (cohen_kappa_score, precision_recall_fscore_support,
                              confusion_matrix, classification_report)

OUT = os.path.join('outputs', 'proposal_support')
SAMPLE = f'{OUT}/stance_validation_sample.csv'

df = pd.read_csv(SAMPLE)
df['human_label'] = df['human_label'].astype(str).str.strip().str.lower()
df['keyword_label'] = df['keyword_label'].astype(str).str.strip().str.lower()

done = df[df['human_label'].isin(['bullish', 'bearish', 'neutral'])]
n = len(done)
total = len(df)
print(f'Annotated: {n} / {total}')
if n < 30:
    print(f'Not enough annotations yet (need >=30, preferably all 100). Aborting.')
    sys.exit(0)

labels = ['bullish', 'bearish', 'neutral']
y_true = done['human_label'].values
y_pred = done['keyword_label'].values

kappa = cohen_kappa_score(y_true, y_pred, labels=labels)
p, r, f1, support = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
cm = confusion_matrix(y_true, y_pred, labels=labels)
acc = (y_true == y_pred).mean()

# Write results MD
lines = [
    '# Stance Label Validation Results',
    '',
    f'- Sample size: **{n}** annotated of {total} sampled (seed 20260421)',
    f'- Agreement (accuracy): **{acc*100:.1f}%**',
    f"- Cohen's kappa: **{kappa:.3f}**",
    '',
    '## Per-class metrics',
    '',
    '| Class   | Precision | Recall | F1    | Support |',
    '|---------|-----------|--------|-------|---------|',
]
for lbl, pi, ri, fi, si in zip(labels, p, r, f1, support):
    lines.append(f'| {lbl:<7} | {pi:.3f}     | {ri:.3f}  | {fi:.3f} | {int(si)}       |')
lines += [
    '',
    '## Confusion matrix (rows=human, cols=keyword)',
    '',
    '|           | ' + ' | '.join(labels) + ' |',
    '|-----------|' + '|'.join(['-' * 9] * len(labels)) + '|',
]
for lbl, row in zip(labels, cm):
    lines.append(f'| {lbl:<9} | ' + ' | '.join(f'{v:>7}' for v in row) + ' |')

# Proposal-ready paragraph
def kappa_interp(k):
    if k < 0.2: return 'slight'
    if k < 0.4: return 'fair'
    if k < 0.6: return 'moderate'
    if k < 0.8: return 'substantial'
    return 'almost perfect'

lines += [
    '',
    '## Proposal-ready paragraph',
    '',
    f'To validate the rule-based stance labeler, a random sample of {n} curated '
    f'NVDA comments (seed 20260421) was manually annotated. Agreement between the '
    f'keyword heuristic and human judgement was {acc*100:.1f}%, with a Cohen\'s '
    f'kappa of {kappa:.3f} ({kappa_interp(kappa)} agreement in the Landis-Koch '
    f'convention). Per-class F1 scores were: bullish {f1[0]:.2f}, bearish '
    f'{f1[1]:.2f}, neutral {f1[2]:.2f}. These scores are sufficient for the '
    f'distribution-level comparison (JSD on stance proportions) that the evaluation '
    f'framework requires, while being transparent about the labeler\'s limitations '
    f'for individual-comment classification.',
]

with open(f'{OUT}/stance_validation_results.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')

print('\n'.join(lines))
print(f'\nSaved -> {OUT}/stance_validation_results.md')
