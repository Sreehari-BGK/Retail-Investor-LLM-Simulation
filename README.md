# LLM Investor Simulation — Pilot Pipeline

Pilot implementation for the UQ "Simulating the World" project.
Validates data collection, embedding, and similarity metrics before running full simulation.

## Project structure

```
llm-investor-sim/
  data/
    raw/          ← raw PRAW output (one CSV per event)
    processed/    ← merged, filtered, embedded data
  scripts/
    00_make_synthetic_data.py   ← generate synthetic data (no API needed)
    01_collect_reddit.py        ← collect real Reddit data via PRAW
    02_prepare_event_windows.py ← merge + filter raw files
    03_embed_comments.py        ← SBERT embeddings
    04_compute_metrics.py       ← MMD / JSD / Wasserstein functions
    05_sanity_checks.py         ← pilot validation experiment
    06_explore_data.py          ← EDA figures for report
  outputs/                      ← plots and results
  requirements.txt
  README.md
```

## Quick start (no Reddit API credentials needed)

```bash
cd llm-investor-sim
pip install -r requirements.txt

# Generate synthetic pilot data
python scripts/00_make_synthetic_data.py

# Embed with Sentence-BERT
python scripts/03_embed_comments.py

# Run sanity checks
python scripts/05_sanity_checks.py

# EDA figures
python scripts/06_explore_data.py
```

## With real Reddit data

1. Create a Reddit app at https://www.reddit.com/prefs/apps (script type)
2. Set credentials:
   ```bash
   export REDDIT_CLIENT_ID=your_id
   export REDDIT_CLIENT_SECRET=your_secret
   export REDDIT_USER_AGENT=llm-investor-sim/0.1
   ```
3. Run:
   ```bash
   python scripts/01_collect_reddit.py
   python scripts/02_prepare_event_windows.py
   python scripts/03_embed_comments.py
   python scripts/05_sanity_checks.py
   python scripts/06_explore_data.py
   ```

## Pilot events

| Event ID      | Ticker | Release time (UTC)  | Source            |
|---------------|--------|---------------------|-------------------|
| AAPL_Q4_2023  | AAPL   | 2023-11-02 17:00    | Apple IR / SEC 8-K |
| NVDA_Q3_2023  | NVDA   | 2023-11-21 16:30    | Nvidia IR / Nasdaq |
| META_Q3_2023  | META   | 2023-10-25 17:00    | Meta IR / SEC 8-K  |

Event timestamps sourced from SEC EDGAR 8-K filings and the Nasdaq earnings calendar.

## Similarity metrics

| Metric              | What it measures              | Range      | Reference              |
|---------------------|-------------------------------|------------|------------------------|
| MMD (RBF kernel)    | Semantic / content similarity | ≥ 0        | Gretton et al. (2012)  |
| JSD (stance)        | Stance distribution           | [0, 1]     | Lin (1991)             |
| Wasserstein-1 (time)| Temporal profile similarity   | ≥ 0        | Villani (2009)         |

## Sanity check logic

| Test            | What changes            | Expected effect                  |
|-----------------|-------------------------|----------------------------------|
| A: Real vs Real | Nothing (split-half)    | Smallest distances (baseline)    |
| B: Real vs Shuf | Timestamps shuffled     | Wasserstein increases            |
| C: Real vs Sim  | Naive simulation        | All metrics larger than Test A   |
