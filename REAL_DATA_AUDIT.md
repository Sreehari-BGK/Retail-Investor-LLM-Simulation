# REAL_DATA_AUDIT.md
Generated: 2026-03-19 (this session)
Purpose: Line-by-line audit of what was actually collected, queried, and computed.

---

## 1. What was actually collected

### Real Reddit data

| Event ID       | Ticker | Filing date (SEC) | Event time used     | n comments | Posts | Subreddits |
|----------------|--------|-------------------|---------------------|-----------|-------|------------|
| NVDA_Q3FY26    | NVDA   | 2025-11-19        | 2025-11-19T21:00Z   | 2641      | 13    | stocks, wallstreetbets |
| META_Q3_2025   | META   | 2025-10-29        | 2025-10-29T21:00Z   | 1444      | 16    | stocks, wallstreetbets |
| AAPL_Q4FY25    | AAPL   | 2025-10-30        | 2025-10-30T21:00Z   | 392       | 4     | stocks only |
| **TOTAL**      |        |                   |                     | **4477**  | **33**|            |

All comments are within the window -24h to +48h relative to event_time.
Event window confirmed by `hours_from_event` column in data/processed/real_comments_labeled.csv.

Files:
- `data/raw/real_reddit_NVDA_Q3FY26.csv` — 2641 rows, raw
- `data/raw/real_reddit_META_Q3_2025.csv` — 1444 rows, raw
- `data/raw/real_reddit_AAPL_Q4FY25.csv` — 392 rows, raw
- `data/raw/collection_log.json` — machine-readable summary
- `data/processed/real_comments.csv` — 4477 rows, merged, no stance labels
- `data/processed/real_comments_labeled.csv` — 4477 rows, with provisional stance labels
- `data/processed/real_comment_embeddings.npy` — shape (4477, 384), float32, L2-normalised

---

## 2. What sources were actually queried

### SEC EDGAR (queried in this session)

All queries made via Python `requests` with User-Agent header `academic-research llm-investor-sim krizc@student.uq.edu.au`.

| URL actually fetched | Purpose | HTTP status |
|---|---|---|
| https://data.sec.gov/submissions/CIK0001045810.json | NVDA 8-K filings list | 200 |
| https://data.sec.gov/submissions/CIK0001326801.json | META 8-K filings list | 200 |
| https://data.sec.gov/submissions/CIK0000320193.json | AAPL 8-K filings list | 200 |
| https://www.sec.gov/Archives/edgar/data/1045810/000104581025000228/0001045810-25-000228-index.htm | NVDA 8-K index (Item 2.02 confirmed) | 200 |
| https://www.sec.gov/Archives/edgar/data/1326801/000162828025047114/0001628280-25-047114-index.htm | META 8-K index (Item 2.02 confirmed) | 200 |
| https://www.sec.gov/Archives/edgar/data/320193/000032019325000077/0000320193-25-000077-index.htm | AAPL 8-K index (Item 2.02 confirmed) | 200 |
| https://www.sec.gov/Archives/edgar/data/1045810/000104581025000228/q3fy26pr.htm | NVDA press release (call time: 2pm PT / 5pm ET confirmed) | 200 |
| https://www.sec.gov/Archives/edgar/data/1326801/000162828025047114/meta-09302025xexhibit991.htm | META press release (call time: 1:30pm PT / 4:30pm ET confirmed) | 200 |
| https://www.sec.gov/Archives/edgar/data/320193/000032019325000077/a8-kex991q4202509272025.htm | AAPL press release (call time: 2pm PT / 5pm ET confirmed) | 200 |

All three 8-K filings confirmed as "Item 2.02: Results of Operations and Financial Condition" — the standard SEC item for quarterly earnings releases.

Event time used in analysis: 21:00 UTC (4pm ET / market close) on the filing date.
Rationale: This is the standard after-hours release convention. The conference calls all started at 4:30-5pm ET; press releases are released at or before call start.
The exact intraday minute of release was NOT retrievable from SEC EDGAR (filing records date only, not time-of-day).

### Reddit (queried in this session)

API used: Reddit public JSON API (no OAuth), endpoint `https://www.reddit.com/r/{sub}/search.json`
Parameters: `sort=new, restrict_sr=on, limit=100, t=year` — then locally filtered to event window.
User-Agent: `academic-research-bot/0.1 (UQ student project, non-commercial research)`

Total search API calls: ~24 (4 queries × 2 subreddits × 3 events)
Total comment fetch calls: ~33 (one per post found in window)
All calls made with 1.2s delay between requests.

### Bloomberg Terminal: NOT queried.
### Nasdaq earnings calendar: NOT queried (SEC EDGAR used instead).
### Capital IQ: NOT queried.
### Pushshift / Arctic Shift: NOT queried.

---

## 3. What code actually ran

All scripts run from `c:/SBK/University/SEM 3/Project/Codez/llm-investor-sim/`

| Script / command | Status | Output |
|---|---|---|
| `scripts/collect_real_reddit.py` | SUCCESS | 4477 rows across 3 raw CSVs |
| `scripts/label_stance_rulebased.py` | SUCCESS | real_comments_labeled.csv |
| `python -c "SentenceTransformer(...).encode(...)"` | SUCCESS | real_comment_embeddings.npy (4477, 384) |
| Sanity checks (inline python -c) | SUCCESS | real_sanity_check_corrected.json |
| Plotting (inline python -c) | SUCCESS | 4 PNG files in outputs/ |

---

## 4. Sanity check results — REAL DATA

### Test A: Real vs Real (split-half, random_state=42)

| Event | n | JSD stance | Wasserstein time | MMD semantic |
|---|---|---|---|---|
| NVDA_Q3FY26 | 2641 | 0.017561 | 0.389938 | 0.000614 |
| META_Q3_2025 | 1444 | 0.033222 | 1.095568 | 0.000910 |
| AAPL_Q4FY25 | 392 | 0.039120 | 0.775510 | 0.003659 |

Interpretation: All values are small, indicating the two halves of each event's real data are similar. MMD values are near zero (mean field collapse of biased estimator at this scale — the distributions are very close).

### Test B: Real vs Uniform Random Timestamps

Original Test B implementation (row shuffle) was a bug — shuffling rows preserves the marginal histogram, so Wasserstein is mathematically identical. Fixed to compare against truly random uniform hours in [-24, 48].

| Event | WD Real vs Real | WD Real vs Uniform | Increased | Delta |
|---|---|---|---|---|
| NVDA_Q3FY26 | 0.3899 | 11.6769 | YES | +11.29 |
| META_Q3_2025 | 1.0956 | 6.1717 | YES | +5.08 |
| AAPL_Q4FY25 | 0.7755 | 12.8622 | YES | +12.09 |

Interpretation: All three events show strongly non-uniform temporal distributions. The real Reddit data clusters around specific hours after the announcement (visible in `outputs/real_temporal_distribution.png`). Wasserstein correctly detects this — real-vs-real is much smaller than real-vs-uniform.

---

## 5. What remains synthetic or provisional

### Synthetic data (from previous session — SEPARATE from real data)
- `data/processed/comments.csv` — 300 rows, ENTIRELY SYNTHETIC. 15 hardcoded template sentences × 3 events.
- `data/processed/comment_embeddings.npy` — embeddings of synthetic text
- `data/processed/comments_with_index.csv` — same synthetic rows

These files have NOT been deleted. They are separate from the real data pipeline. Do not mix these files with the real data files.

### Provisional: stance labels
- Method: keyword counting (see `scripts/label_stance_rulebased.py`)
- Bullish keywords: 30 regex patterns (buy, bull, long, calls, beat, strong, etc.)
- Bearish keywords: 30 regex patterns (sell, bear, short, puts, miss, weak, etc.)
- Assignment rule: bullish if bull_count > bear_count; bearish if bear_count > bull_count; neutral otherwise
- Result: 64.2% neutral, 21.5% bullish, 14.3% bearish
- Known limitations: does not handle negation ("not bullish"), sarcasm, or context
- NOT validated against human annotations
- NOT a trained classifier

### Provisional: event time precision
- Event time set to 21:00 UTC on the SEC filing date (4pm ET)
- Exact intraday minute not confirmed; press releases released at or before the start of each conference call
- Call times confirmed from press releases: NVDA 22:00 UTC, META 21:30 UTC, AAPL 22:00 UTC
- All event windows (-24h to +48h) are large enough that ±1 hour precision in event_time does not materially affect results

### Not yet done (simulation side)
- LLM agent simulation: NOT run
- No sim_agent rows exist in any dataset
- Agent prompts: NOT written
- Comparison between real data and agent simulation: NOT computed

---

## 6. Known data quality issues

1. **AAPL_Q4FY25 underrepresented**: Only 392 comments from 4 posts in r/stocks only. r/wallstreetbets returned 0 posts for AAPL during this window. This may be because AAPL earnings had lower WSB interest than NVDA/META, or because the search queries did not match WSB post titles. The AAPL window (Oct 29 - Nov 1, 2025) overlaps heavily with META's window (Oct 28 - Oct 31, 2025).

2. **Off-topic posts in META collection**: Some posts found via "Meta earnings Q3" query in r/stocks are not about META specifically (e.g., "Apple to split in 2026??", "Chipotle cuts same-store sales forecast", "ServiceNow tops estimates"). These were returned by Reddit's search algorithm because they appeared in the same subreddit during the same time window. They inflate the META row count. No ticker-relevance filter was applied post-collection. This is a limitation.

3. **NVDA off-topic posts**: "Anatomy of a tenbagger" (1p36q7u) and "Trump team internally floats idea of selling Nvidia chips" (1p37j7u) may not be directly about the Q3 earnings results. They appeared in WSB during the window.

4. **Comments from threads only superficially matching queries**: Reddit search returns posts matching the query at the title level; deep comments in those threads may discuss unrelated topics. No per-comment relevance filter was applied.

5. **Test B bug (historical)**: The original Test B in `scripts/05_sanity_checks.py` used `df.sample(frac=1)` to shuffle rows, then passed the result to `wasserstein_time()`. Because Wasserstein measures the marginal distribution of hours (via histogram), shuffling row order produces an identical histogram and thus identical distance. This is a methodological error. The corrected version compares against uniform random hours drawn from `Uniform(-24, 48)`.

---

## 7. Numeric results — complete table

### All metric values from real data

| Event | Test | JSD stance | Wasserstein time | MMD semantic |
|---|---|---|---|---|
| NVDA_Q3FY26 | A: Real vs Real | 0.017561 | 0.389938 | 0.000614 |
| NVDA_Q3FY26 | B: Real vs Uniform | — | 11.676900 | — |
| META_Q3_2025 | A: Real vs Real | 0.033222 | 1.095568 | 0.000910 |
| META_Q3_2025 | B: Real vs Uniform | — | 6.171700 | — |
| AAPL_Q4FY25 | A: Real vs Real | 0.039120 | 0.775510 | 0.003659 |
| AAPL_Q4FY25 | B: Real vs Uniform | — | 12.862200 | — |

### Synthetic data results (previous session, separate pipeline)

| Test | JSD stance | Wasserstein time | MMD semantic |
|---|---|---|---|
| A: Synth vs Synth | 0.109956 | 2.466667 | 0.010109 |
| B: Synth vs Shuffled (buggy) | 0.109956 | 2.466667 | 0.010109 |
| C: Synth vs Naive Sim | 0.138640 | 8.919444 | 0.232859 |

These synthetic numbers must NOT be reported as real data results.

---

## 8. Output files from this session

| File | Description | Real or Synthetic |
|---|---|---|
| data/raw/real_reddit_NVDA_Q3FY26.csv | Raw collected Reddit data | REAL |
| data/raw/real_reddit_META_Q3_2025.csv | Raw collected Reddit data | REAL |
| data/raw/real_reddit_AAPL_Q4FY25.csv | Raw collected Reddit data | REAL |
| data/raw/collection_log.json | Collection metadata | REAL |
| data/processed/real_comments.csv | Merged, unlabeled | REAL |
| data/processed/real_comments_labeled.csv | Labeled (provisional) | REAL |
| data/processed/real_comment_embeddings.npy | SBERT embeddings | REAL |
| outputs/real_temporal_distribution.png | Temporal histogram per event | REAL |
| outputs/real_stance_distribution.png | Stance bar charts per event | REAL (provisional labels) |
| outputs/real_sanity_A_metrics.png | Test A metric bars | REAL |
| outputs/real_sanity_B_wasserstein.png | Test B comparison | REAL |
| outputs/real_sanity_check_corrected.json | All metric values | REAL |
| data/processed/comments.csv | 300 synthetic rows | SYNTHETIC — do not mix |
| data/processed/comment_embeddings.npy | Synthetic embeddings | SYNTHETIC — do not mix |
