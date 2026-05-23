#!/usr/bin/env python3
"""Build stance-validation sample of 100 random NVDA comments for manual annotation."""
import sys, io, os, importlib.util, warnings
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np

OUT = os.path.join('outputs', 'proposal_support')
os.makedirs(OUT, exist_ok=True)

SEED = 20260421
SAMPLE_N = 100

# Load heuristic labeler
spec = importlib.util.spec_from_file_location('stance', 'scripts/label_stance_rulebased.py')
stance_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stance_mod)

# Load curated NVDA data
df = pd.read_csv('data/processed/real_comments_curated_labeled.csv')
nvda = df[df['event_id'] == 'NVDA_Q3FY26'].copy().reset_index(drop=True)
print(f'NVDA curated: {len(nvda)}')

# Fixed-seed random sample
rng = np.random.default_rng(SEED)
idx = rng.choice(len(nvda), size=SAMPLE_N, replace=False)
sample = nvda.iloc[idx].copy().reset_index(drop=True)

# Prefill keyword label (regenerate from labeler to be sure)
sample['keyword_label'] = sample['text'].fillna('').apply(stance_mod.label_text)
sample['human_label'] = ''  # to be filled manually

out = sample[['comment_id', 'text', 'human_label', 'keyword_label']]
out.to_csv(f'{OUT}/stance_validation_sample.csv', index=False)
print(f'Wrote {len(out)} rows -> {OUT}/stance_validation_sample.csv')
print(f'Keyword label dist: {sample["keyword_label"].value_counts().to_dict()}')
print(f'Seed: {SEED}')
