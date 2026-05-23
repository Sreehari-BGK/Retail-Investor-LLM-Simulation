# LLM Investor Simulation — Project Handover

**Course:** Simulating the World, Sub-Track 3, University of Queensland
**Last updated:** 2026-04-01
**Report revised draft due:** Friday 20 March 2026, 4pm (reply-all email)
**Next meeting:** Monday 23 March 2026, 11:30am–12:30pm (online)

---

## 1. Project in One Sentence

Simulate retail investor discussions around quarterly earnings events using LLM-backed agents, then evaluate how closely the simulated discussions resemble real Reddit data using three distribution-similarity metrics (MMD, JSD, Wasserstein-1).

---

## 2. Status at Handover

| Component                        | Status       | Notes                                               |
|----------------------------------|--------------|-----------------------------------------------------|
| Synthetic pilot data             | Complete     | 300 comments (180 real, 120 sim_naive)              |
| Real Reddit data collection      | Complete     | Requires Reddit API credentials in `.env`           |
| SBERT embedding pipeline         | Complete     | all-MiniLM-L6-v2, 384-dim, L2-normalised            |
| Core metric library              | Complete     | `04_compute_metrics.py` — MMD, JSD, Wasserstein     |
| Sanity check validation (3-part) | Complete     | All metrics discriminate; results in CLAUDE.md      |
| EDA figures                      | Complete     | Temporal, stance, score distributions               |
| Template-based agent simulation  | Complete     | 27 agents, 9 archetypes, 5 rounds                   |
| Agent observability / auditing   | Complete     | `08_observability.py`, agent PNGs in outputs/       |
| Real vs Sim metric comparison    | Complete     | `09_real_vs_sim.py`, `real_vs_sim_metrics.json`     |
| Factual grounding evaluation     | Complete     | `12_eval_grounding.py`, grounding JSON files        |
| LLM one-shot run (Qwen)          | Complete     | `11_run_qwen_oneshot.py`                            |
| LaTeX report                     | In progress  | All new changes must use `\textcolor{blue}{xxx}`    |

---

## 3. Repository Layout

```
llm-investor-sim/
│
├── scripts/                          # Numbered execution pipeline
│   ├── 00_make_synthetic_data.py     # Synthetic pilot data (no API needed)
│   ├── 01_collect_reddit.py          # Real Reddit data via PRAW
│   ├── 02_prepare_event_windows.py   # Merge + filter raw CSVs
│   ├── 03_embed_comments.py          # SBERT embeddings
│   ├── 04_compute_metrics.py         # Core metric functions (importable)
│   ├── 05_sanity_checks.py           # 3-part validation experiment
│   ├── 06_explore_data.py            # EDA figures
│   ├── 07_agent_simulation.py        # Template-based 27-agent simulation
│   ├── 08_observability.py           # Agent behavior auditing + figures
│   ├── 09_real_vs_sim.py             # Real vs Sim metric comparison
│   ├── 10_metric_benchmark.py        # Metric sensitivity benchmarks
│   ├── 11_run_qwen_oneshot.py        # LLM one-shot evaluation (Qwen)
│   ├── 12_eval_grounding.py          # Factual grounding evaluation
│   ├── 14_sample_for_manual_audit.py # Sample for human auditing
│   ├── collect_real_reddit.py        # Enhanced collection with SEC EDGAR
│   ├── curate_and_freeze.py          # Data curation and freezing
│   └── label_stance_rulebased.py     # Rule-based stance labeling
│
├── data/
│   ├── raw/                          # One CSV per event from PRAW (gitignored)
│   ├── processed/                    # Merged data + embeddings (gitignored)
│   │   ├── comments.csv
│   │   ├── comment_embeddings.npy
│   │   └── comments_with_index.csv
│   └── event_cards/                  # Event metadata (earnings facts)
│
├── outputs/                          # All figures and reports (gitignored)
│
├── CLAUDE.md                         # Locked specs — read before changing anything
├── HANDOVER.md                       # This file
├── REAL_DATA_AUDIT.md                # What was collected from Reddit + SEC EDGAR
├── FINAL_METHOD_SUMMARY.md           # Methodology documentation
├── METRIC_SCAN.md                    # Detailed metric analysis
├── METRIC_BENCHMARK.md               # Metric performance benchmarks
├── CURATION_LOG.md                   # Data curation decisions
├── STANCE_LABEL_AUDIT.md             # Stance labeling rules and validation
├── SHORT_METHODS_FOR_REPORT.md       # Methods section (report-ready)
├── SHORT_RESULTS_FOR_REPORT.md       # Results section (report-ready)
├── SHORT_LIMITATIONS_FOR_REPORT.md   # Limitations section (report-ready)
├── SHORT_FIGURE_CAPTIONS.md          # Figure captions for submission
├── REPORT_TABLES.md                  # Summary tables
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 4. Environment Setup

### 4.1 Python Dependencies

```bash
pip install -r requirements.txt
```

Key packages and why they're needed:

| Package                | Purpose                                      |
|------------------------|----------------------------------------------|
| pandas, numpy, scipy   | Data manipulation, statistics                |
| scikit-learn           | RBF kernel / pairwise metrics for MMD        |
| sentence-transformers  | SBERT model (all-MiniLM-L6-v2)               |
| matplotlib             | All figures                                  |
| praw                   | Reddit API wrapper (01_collect_reddit.py)    |
| pydantic               | Data validation                              |

### 4.2 Environment Variables

Copy `.env.example` to `.env`:

```env
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=llm-investor-sim/0.1

# Optional
HF_TOKEN=                          # Removes HuggingFace rate-limit warnings
HF_HUB_DISABLE_SYMLINKS_WARNING=1  # Windows symlink warning

# Future (not yet needed)
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
```

Create a Reddit app at https://www.reddit.com/prefs/apps (choose **"script"** type).

---

## 5. How to Run the Pipeline

### 5.1 Full Pipeline — Synthetic Data (No API Required)

```bash
# From project root: llm-investor-sim/
python scripts/00_make_synthetic_data.py
python scripts/03_embed_comments.py
python scripts/05_sanity_checks.py
python scripts/06_explore_data.py
```

### 5.2 Full Pipeline — Real Reddit Data

```bash
python scripts/01_collect_reddit.py           # Requires .env credentials
python scripts/02_prepare_event_windows.py    # Merge + filter
python scripts/03_embed_comments.py           # SBERT embed
python scripts/05_sanity_checks.py            # Validate metrics
python scripts/06_explore_data.py             # EDA
python scripts/07_agent_simulation.py         # Run 27-agent simulation
python scripts/08_observability.py            # Agent auditing + figures
python scripts/09_real_vs_sim.py              # Final metric comparison
```

### 5.3 One-liner (Synthetic, No API)

```bash
python scripts/00_make_synthetic_data.py && \
python scripts/03_embed_comments.py && \
python scripts/05_sanity_checks.py && \
python scripts/06_explore_data.py
```

---

## 6. Pilot Scope (Locked)

**Do not change these without discussion** — they are referenced in the draft report.

| Parameter       | Value                                                 |
|-----------------|-------------------------------------------------------|
| Event type      | Quarterly earnings announcements only                 |
| Events          | AAPL Q4 2023, NVDA Q3 2023, META Q3 2023              |
| Subreddits      | r/stocks, r/wallstreetbets                            |
| Event window    | -24h to +48h relative to official earnings release    |
| Event timestamps| SEC 8-K filings + Nasdaq earnings calendar            |
| Unit of analysis| Comments and replies (threaded)                       |

### Event Timestamps

| Event ID      | Ticker | Release (UTC)    |
|---------------|--------|------------------|
| AAPL_Q4_2023  | AAPL   | 2023-11-02 17:00 |
| NVDA_Q3_2023  | NVDA   | 2023-11-21 16:30 |
| META_Q3_2023  | META   | 2023-10-25 17:00 |

---

## 7. Data Schema

**Primary file:** `data/processed/comments.csv`

| Column           | Type  | Notes                                           |
|------------------|-------|-------------------------------------------------|
| event_id         | str   | e.g. AAPL_Q4_2023                              |
| ticker           | str   | Stock symbol                                    |
| event_time       | str   | ISO-8601 UTC                                    |
| subreddit        | str   | stocks or wallstreetbets                        |
| thread_id        | str   | Reddit post ID                                  |
| comment_id       | str   | Unique comment ID                               |
| parent_id        | str   | thread_id if top-level, else parent comment_id  |
| hours_from_event | float | Negative = before event, positive = after       |
| text             | str   | Comment text                                    |
| score            | int   | Reddit upvotes                                  |
| depth            | int   | 0 = top-level post                              |
| source_type      | str   | "real", "sim_naive", or "sim_agent"             |
| stance           | str   | "bullish", "bearish", "neutral" (always lowercase) |

**Embeddings file:** `data/processed/comment_embeddings.npy`
- Shape: `(N, 384)` — float32, L2-normalised (unit sphere)
- Row order matches `comments_with_index.csv`

---

## 8. Evaluation Metrics (Locked — Do Not Add/Remove)

All three metrics are implemented as pure functions in `scripts/04_compute_metrics.py`.

### 8.1 MMD with RBF Kernel — Semantic Similarity

```python
from scripts.compute_metrics import mmd_rbf
score = mmd_rbf(X_embeddings, Y_embeddings, gamma=None)
```

- Measures distributional similarity in SBERT embedding space
- `gamma=None` → uses median heuristic (Gretton et al., 2012)
- Formula: MMD² = E[k(x,x')] + E[k(y,y')] − 2·E[k(x,y)]
- Range: [0, ∞), lower = more similar
- **Interpretation:** How similar is the semantic content and topic coverage?

### 8.2 JSD on Stance Distribution — Opinion Mix

```python
from scripts.compute_metrics import jsd_stance
score = jsd_stance(real_labels, sim_labels,
                   label_order=["bullish", "bearish", "neutral"])
```

- Compares bullish/bearish/neutral proportions as probability distributions
- Range: [0, 1] (base-2 bits), lower = more similar
- **Interpretation:** Does the simulation produce the right opinion mix?

### 8.3 Wasserstein-1 on Temporal Distribution — Posting Timing

```python
from scripts.compute_metrics import wasserstein_time
score = wasserstein_time(real_hours, sim_hours)
```

- Compares posting-volume histograms over hourly bins (−24h to +48h, 72 bins)
- Optimal transport distance (Villani, 2009)
- Range: [0, ∞), lower = more similar
- **Interpretation:** Does simulated activity cluster correctly around the event?

---

## 9. Sanity Check Results

Three-part validation confirming the metric pipeline works correctly.
Run: `python scripts/05_sanity_checks.py`

| Test                   | JSD Stance | Wasserstein Time | MMD Semantic |
|------------------------|-----------|-----------------|--------------|
| A: Real vs Real (split)| 0.110     | 2.47            | 0.010        |
| B: Real vs Shuffled    | 0.110     | 2.47*           | 0.010        |
| C: Real vs Naive Sim   | 0.139     | 8.92            | 0.233        |

**How to read this:**
- **Test A** is the baseline (same distribution split in half). These values are the noise floor.
- **Test B** should show Wasserstein increase if timestamps are shuffled (flat on synthetic because synthetic hours are already near-uniform; will be visible on real data).
- **Test C** must show all metrics ≥ Test A. It does — this confirms the metrics can discriminate real from naive simulation. Pipeline is valid.

---

## 10. Agent Design

### 10.1 Cohort Structure

| Cohort          | Subtypes                                               |
|-----------------|--------------------------------------------------------|
| Long-horizon    | valuation-focused, fundamentals-focused, buy-the-dip   |
| Short-horizon   | momentum-following, event-reactive, profit-taking       |
| Info-seeking    | uncertain, evidence-seeking, wait-and-see               |

- 3 cohorts × 3 subtypes = **9 archetypes**
- **Pilot:** 3 agents per archetype = **27 agents**
- **Full design:** up to 10 agents per archetype = 90 agents
- Terminology: "behavioural cohorts", not "personality archetypes"

### 10.2 Simulation Rounds (Script 07)

The current implementation is **template-based** (no live LLM API call):

| Round | Timing             | Theme                                 |
|-------|--------------------|---------------------------------------|
| 1     | Pre-event (−12h)   | Anticipation, positioning             |
| 2     | Immediate (0–2h)   | First reactions to earnings           |
| 3     | Digest (2–12h)     | Deeper analysis, counter-arguments    |
| 4     | Follow-up (12–24h) | Position revisions, broader context   |
| 5     | Wind-down (24–48h) | Final takes, forward-looking          |

Agents update their stance probabilistically based on cohort rules and earnings direction.

**Output:** `outputs/sim_agent_trace.csv`, `outputs/sim_comments.csv`

### 10.3 Observability (Script 08)

Produces three figures for agent transparency:
- `agent_activity_timeline.png` — when each agent posts
- `agent_interaction_graph.png` — who replies to whom
- `agent_stance_trajectories.png` — stance evolution over rounds

---

## 11. Key Design Decisions and Rationale

| Decision                              | Rationale                                              |
|---------------------------------------|--------------------------------------------------------|
| Event window: -24h to +48h           | Standard in event-study literature                     |
| 1-hour bins for Wasserstein           | Deliberate; documented in report                       |
| L2-normalised SBERT embeddings        | Ensures cosine = dot product; required for RBF MMD    |
| Median heuristic for RBF bandwidth    | Data-adaptive; avoids arbitrary hyperparameter tuning  |
| Pilot events: AAPL, NVDA, META        | High-traffic subreddits, clear earnings reactions      |
| Source type: "real" / "sim_naive" / "sim_agent" | Clean provenance tracking through the pipeline |
| Stance: always lowercase              | Convention to avoid silent case-matching bugs          |
| 04_compute_metrics.py: no file I/O   | Pure function library — easy to import and test        |
| Scripts numbered 00–14               | Explicit execution order, no ambiguity                 |

---

## 12. What NOT to Change Without Discussion

From `CLAUDE.md` (locked specifications):

- The **3-metric evaluation framework** (MMD / JSD / Wasserstein)
- The **event window** (−24h to +48h)
- The **pilot event set** (AAPL/NVDA/META Q3-Q4 2023)
- The **hourly bin resolution** for the Wasserstein temporal metric
- Do not add structural metrics (reply-tree depth etc.) until after the pilot is complete

---

## 13. Report Conventions

- All new or revised content in the LaTeX report must be wrapped in `\textcolor{blue}{xxx}`
- Figures live in `outputs/` — use the PNGs directly
- Report-ready sections are pre-drafted:
  - `SHORT_METHODS_FOR_REPORT.md`
  - `SHORT_RESULTS_FOR_REPORT.md`
  - `SHORT_LIMITATIONS_FOR_REPORT.md`
  - `SHORT_FIGURE_CAPTIONS.md`
  - `REPORT_TABLES.md`

---

## 14. Known Limitations and Future Work

### Current Limitations
- **Synthetic pilot data only** — real Reddit data requires API credentials and is gitignored
- **Template-based simulation** — agents use canned text; no actual LLM generation in the main pipeline
- **Test B Wasserstein flat on synthetic data** — temporal shuffle is invisible because synthetic hours are near-uniform; this will resolve with real Reddit data
- **No structural metrics** — reply-tree depth, thread branching factor not yet included (intentionally deferred)
- **Stance labels are rule-based** — keyword heuristics, not LLM-classified (see `STANCE_LABEL_AUDIT.md`)

### Planned Extensions
- Replace template-based agents with live LLM calls (Qwen/GPT/Claude) via `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
- Scale to 90 agents (10 per archetype)
- Bloomberg / Capital IQ enrichment for event cards (optional, not required for pilot)
- Structural similarity metrics (after pilot is complete)

---

## 15. Quick Reference: Key Files

| File                                    | What you need it for                          |
|-----------------------------------------|-----------------------------------------------|
| `scripts/04_compute_metrics.py`         | Import `mmd_rbf`, `jsd_stance`, `wasserstein_time` |
| `scripts/05_sanity_checks.py`           | Re-run the 3-test validation                  |
| `data/processed/comments.csv`           | Primary dataset                               |
| `data/processed/comment_embeddings.npy` | SBERT embeddings, row-aligned to comments_with_index.csv |
| `outputs/real_vs_sim_metrics.json`      | Final metric numbers for the report           |
| `outputs/sanity_check_results.png`      | Figure 1 in the report (metric validation)    |
| `CLAUDE.md`                             | Locked specifications — read first            |
| `REAL_DATA_AUDIT.md`                    | Provenance of the Reddit + SEC data           |
| `METRIC_SCAN.md`                        | Detailed metric analysis and discussion       |
| `.env.example`                          | Template for Reddit API credentials           |

---

## 16. Contact / Collaboration Notes

- Revised draft due: **Friday 20 March 2026, 4pm** (reply-all email to supervisors)
- Next meeting: **Monday 23 March 2026, 11:30am–12:30pm** (online)
- All changes tracked via `\textcolor{blue}{xxx}` in LaTeX
- Data files (`data/`, `outputs/`) are gitignored — share via external storage if needed
