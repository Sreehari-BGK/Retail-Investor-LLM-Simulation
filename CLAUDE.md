# CLAUDE.md — LLM Investor Simulation (UQ Project)

This file is read automatically by Claude Code at session start.
Keep it up to date as the project evolves.

---

## Finalist run status (as of 2026-05-12)

**The 14 finalist A100 reruns at n=108 are real and complete.** They were executed on Rangpur on 2026-04-25 and have been synced into `runs/finalist_qwen_*/`. Every CSV has 108 rows, every JSONL has `dry_run: false`, and no `[DRY-RUN]` placeholder text appears. The canonical results are:

- `runs/finalist_qwen_*/prompt_exp_*_comments.csv` (14 folders, real text)
- `runs/finalist_qwen_*/prompt_exp_metadata.jsonl` (14 files, `dry_run: false`)
- `outputs/finalist_rerun_results.json` (master metrics)
- `outputs/proposal_support/finalist_results_table.csv` / `.md`

**Best finalist:** Qwen/Qwen3.5-2B + P2_V1 + tau=1.1 + seed=123, MMD=0.0653, JSD=0.4062, Grounded 57.4%, Ungrounded 14.8%. The semantic-first finalist (Qwen3.5-2B + P2_V1) dominates the stance-first finalist (Qwen2.5-3B + P0_V0) on every metric at n=108.

**Do not re-run generation.** Do not overwrite the synced real outputs with `--dry-run`. If you need to verify, read the metadata's `dry_run` flag or check for the `[DRY-RUN]` placeholder substring — both will say "real" on the current files.

**Historical note:** Earlier sessions wrote `REAL_GPU_RUN_AUDIT.md` based on stale local files that still contained dry-run placeholders from April 21 smoke-tests. That audit is now obsolete; see `UPDATED_REAL_GPU_RUN_AUDIT.md` for the corrected state.

---

## Project in one sentence

Simulate retail investor discussions around earnings events using LLM agents,
then evaluate how closely the simulated discussions resemble real Reddit data
using three distribution-similarity metrics.

---

## Course context

- Course: "Simulating the World", Sub-Track 3, University of Queensland
- Revised draft due: Friday 20 March 2026, 4pm (reply-all email)
- All changes in the LaTeX report must be wrapped in `\textcolor{blue}{xxx}`
- Next meeting: Monday 23 March, 11:30am–12:30pm (online)

---

## Run commands (always run from the project root `llm-investor-sim/`)

```bash
# 0. Install dependencies (once)
pip install -r requirements.txt

# 1a. Generate synthetic data (no Reddit API needed)
python scripts/00_make_synthetic_data.py

# 1b. Collect real Reddit data (needs credentials in .env)
python scripts/01_collect_reddit.py

# 2. Merge + filter raw files into processed dataset
python scripts/02_prepare_event_windows.py

# 3. Embed comments with Sentence-BERT
python scripts/03_embed_comments.py

# 4. Run pilot sanity checks (three-way validation)
python scripts/05_sanity_checks.py

# 5. Generate EDA figures for the report
python scripts/06_explore_data.py
```

Full pipeline (synthetic, no API):
```bash
python scripts/00_make_synthetic_data.py && \
python scripts/03_embed_comments.py && \
python scripts/05_sanity_checks.py && \
python scripts/06_explore_data.py
```

---

## Architecture

```
scripts/
  00_make_synthetic_data.py   -- synthetic pilot data (no API)
  01_collect_reddit.py        -- PRAW collection; outputs data/raw/*.csv
  02_prepare_event_windows.py -- merges raw -> data/processed/comments.csv
  03_embed_comments.py        -- SBERT embeddings -> comment_embeddings.npy
  04_compute_metrics.py       -- core metric functions (importable module)
  05_sanity_checks.py         -- 3-part validation: Real/Real, Real/Shuffled, Real/Sim
  06_explore_data.py          -- EDA figures for report

data/raw/      -- one CSV per event from PRAW (reddit_raw_{EVENT_ID}.csv)
data/processed/-- comments.csv, comment_embeddings.npy, comments_with_index.csv
outputs/       -- all figures and eda_summary.txt
```

Key data schema (`data/processed/comments.csv`):

| Column           | Type    | Notes                                     |
|------------------|---------|-------------------------------------------|
| event_id         | str     | e.g. AAPL_Q4_2023                         |
| ticker           | str     |                                           |
| event_time       | str     | ISO-8601 UTC                              |
| subreddit        | str     | stocks or wallstreetbets                  |
| thread_id        | str     |                                           |
| comment_id       | str     | unique                                    |
| parent_id        | str     | thread_id if top-level, else comment_id   |
| hours_from_event | float   | negative = before event                   |
| text             | str     |                                           |
| score            | int     | Reddit upvotes                            |
| depth            | int     | 0 = top-level post                        |
| source_type      | str     | "real" or "sim_naive"                     |
| stance           | str     | "bullish", "bearish", or "neutral"        |

---

## Pilot scope (locked)

- Event type: quarterly earnings announcements only
- Events: AAPL Q4 2023, NVDA Q3 2023, META Q3 2023
- Event timestamps: SEC 8-K filings + Nasdaq earnings calendar (public, free)
- Subreddits: r/stocks, r/wallstreetbets
- Window: -24h to +48h relative to official earnings release
- Unit of analysis: comments and replies (threaded)
- Bloomberg / Capital IQ: optional future enrichment, NOT required for pilot

---

## Agent design (pilot)

- 3 broad cohorts × 3 subtypes = 9 archetypes total
- Pilot: 3 agents per archetype = 27 agents
- Full design: up to 10 agents per archetype = 90 agents
- Cohorts are "behavioural cohorts", not personality archetypes — keep that framing

Cohort structure:
```
Long-horizon:    valuation-focused | fundamentals-focused | buy-the-dip
Short-horizon:   momentum-following | event-reactive | profit-taking
Info-seeking:    uncertain | evidence-seeking | wait-and-see
```

---

## Similarity metrics (keep exactly these 3)

| Metric         | Measures              | Library call                              |
|----------------|-----------------------|-------------------------------------------|
| MMD (RBF)      | Semantic similarity   | `mmd_rbf(X, Y)` in 04_compute_metrics.py |
| JSD            | Stance distribution   | `jsd_stance(real, sim)` in 04_...         |
| Wasserstein-1  | Temporal profile      | `wasserstein_time(real_h, sim_h)` in 04_  |

Do NOT add structural metrics (reply-tree depth etc.) until the pilot is complete.

---

## Sanity check results (synthetic pilot, 2026-03-19)

| Test                   | JSD stance | Wasserstein time | MMD semantic |
|------------------------|-----------|-----------------|--------------|
| A: Real vs Real        | 0.110     | 2.47            | 0.010        |
| B: Real vs Shuffled    | 0.110     | 2.47*           | 0.010        |
| C: Real vs Naive Sim   | 0.139     | 8.92            | 0.233        |

*Test B Wasserstein flat on synthetic data (hours already ~uniform).
With real Reddit data the temporal clustering around t=0 will make shuffling visible.
Test C confirms all metrics discriminate real from naive simulation — pipeline is valid.

---

## Environment variables

Copy `.env.example` to `.env` and fill in before running `01_collect_reddit.py`.

```
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=llm-investor-sim/0.1
```

Create a Reddit app at https://www.reddit.com/prefs/apps (choose "script" type).

---

## Conventions

- Scripts are numbered 00–06 for explicit execution order
- All outputs go to `outputs/` — never commit large outputs to version control
- `data/raw/` and `data/processed/` are gitignored (see .gitignore)
- `04_compute_metrics.py` is a pure function library — no side effects, no file I/O
- When adding a new metric, add it to `04_compute_metrics.py` and update `05_sanity_checks.py`
- Stance labels are always lowercase: "bullish", "bearish", "neutral"
- source_type values are always: "real", "sim_naive", "sim_agent" (future)

---

## What NOT to change without discussion

- The 3-metric evaluation framework (MMD / JSD / Wasserstein) — locked for the report
- The event window (-24h to +48h) — consistent with event-study literature
- The pilot event set (AAPL/NVDA/META Q3-Q4 2023) — already in the draft
- Hourly bin resolution for temporal metric — deliberate choice, documented in report
