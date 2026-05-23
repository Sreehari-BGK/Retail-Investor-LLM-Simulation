# Simulating Retail Investor Discussion with LLM Agents

**Master of Data Science Thesis — University of Queensland, 2026**  
*School of Engineering, Architecture and Information Technology*

> Can LLM agents faithfully replicate the collective discourse of retail investors
> responding to earnings announcements? This project builds the first systematic
> evaluation framework comparing LLM-generated investor discussion against
> real Reddit data using distributional similarity metrics.

---

## Research Question

Given the same earnings event, how close is the discussion produced by LLM
agents to the discussion produced by real retail investors — measured in terms
of **semantic content**, **stance distribution**, and **temporal dynamics**?

---

## Dataset

Real-world benchmark: Reddit posts and comments from **r/stocks** and
**r/wallstreetbets**, collected around three quarterly earnings events.

| Event | Raw | Curated | Notes |
|---|---|---|---|
| NVDA Q3 FY2026 | 2,641 | 2,403 | Primary event (largest, cleanest) |
| META Q3 2025 | 1,444 | 344 | Heavy curation; wrong-company threads removed |
| AAPL Q4 FY2025 | 392 | 383 | Smaller supporting case |
| **Total** | **4,477** | **3,130** | |

Event times verified against **SEC EDGAR 8-K filings** (Item 2.02).  
Collection window: −24h to +48h relative to each earnings release.

> **Note:** Raw Reddit CSVs are not committed to this repository (Reddit ToS +
> privacy). See `scripts/01_collect_reddit.py` to reproduce collection.

---

## Evaluation Metrics

Three primary metrics, each targeting a different dimension of discussion fidelity:

| Metric | Dimension | Formula | Range |
|---|---|---|---|
| **MMD** (RBF kernel) | Semantic similarity | Gretton et al. (2012) | [0, ∞) — lower is closer |
| **JSD** (stance) | Bullish/bearish/neutral balance | Lin (1991) | [0, 1] — lower is closer |
| **Wasserstein-1** (temporal) | Posting-volume timing | Villani (2009) | [0, ∞) hours — lower is closer |

### Pilot Baseline Results (NVDA Q3 FY2026)

| Comparison | JSD ↓ | Wasserstein (h) ↓ | MMD ↓ |
|---|---|---|---|
| Real vs Real (split-half) | 0.023 | 0.41 | 0.00075 |
| Real vs Template Sim | 0.174 | 4.73 | 0.105 |
| Real vs Random | 0.277 | 16.26 | 0.041* |

*MMD random-baseline anomaly: concentration of measure in high dimensions collapses
RBF kernel — real-vs-real lower bound is the reliable reference point.

The metrics cleanly separate a genuine close comparison (real-vs-real) from a weaker
one (real-vs-simulation), confirming the evaluation framework is discriminative.

---

## Agent Design

Simulation uses **27 agents** arranged as **9 archetypes × 3 agents** across
three investor cohorts:

```
Long-horizon:   valuation-focused | fundamentals-focused | buy-the-dip
Short-horizon:  momentum-following | event-reactive | profit-taking
Info-seeking:   uncertain | evidence-seeking | wait-and-see
```

Agents run for **5 rounds** mapping to real discussion phases:
pre-event → immediate reaction → digest → follow-up → wind-down

---

## Pipeline

Scripts are numbered in execution order:

```
scripts/
  00_make_synthetic_data.py        ← generate synthetic pilot data (no API needed)
  01_collect_reddit.py             ← collect real Reddit data via PRAW
  02_prepare_event_windows.py      ← merge + filter raw CSVs into event windows
  03_embed_comments.py             ← sentence-BERT embeddings (all-MiniLM-L6-v2)
  04_compute_metrics.py            ← MMD / JSD / Wasserstein implementations
  05_sanity_checks.py              ← sanity-check: RvR < RvS < RvRand
  06_explore_data.py               ← EDA figures
  07_agent_simulation.py           ← template-based pilot simulation (27 agents, 5 rounds)
  08_observability.py              ← agent trace inspection
  09_real_vs_sim.py                ← head-to-head comparison
  10_metric_benchmark.py           ← full metric sweep (15 metrics across 5 categories)
  11_run_qwen_oneshot.py           ← Qwen LLM one-shot generation
  12_eval_grounding.py             ← grounding evaluation (event-fact mentions)
  13_prompt_condition_experiment.py← prompt ablation (3 conditions × 2 variants)
  14_sample_for_manual_audit.py    ← sample for human review
  17_embedding_robustness.py       ← embedding model robustness check
  18_finalist_rerun.py             ← finalist model runs with seeds
  label_stance_rulebased.py        ← keyword-based bullish/bearish/neutral labeller
  collect_real_reddit.py           ← production Reddit collection script
  curate_and_freeze.py             ← curation pipeline
```

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/YOUR_USERNAME/retail-investor-llm-simulation.git
cd retail-investor-llm-simulation
pip install -r requirements.txt

# Run without any API keys (synthetic data)
python scripts/00_make_synthetic_data.py
python scripts/03_embed_comments.py
python scripts/05_sanity_checks.py
python scripts/06_explore_data.py
```

**With real Reddit data:**
```bash
# 1. Create a Reddit app at https://www.reddit.com/prefs/apps (script type)
# 2. Copy .env.example to .env and fill in credentials
cp .env.example .env

# 3. Collect + process
python scripts/01_collect_reddit.py
python scripts/02_prepare_event_windows.py
python scripts/03_embed_comments.py
python scripts/07_agent_simulation.py
python scripts/09_real_vs_sim.py
```

**With LLM API (Ollama/local):**
```bash
# Pull a model via Ollama first
ollama pull qwen2.5:7b

# Then run the LLM simulation
python scripts/13_prompt_condition_experiment.py
```

---

## Prompt Conditions

Three prompt conditions tested in ablation:

| Condition | Variant | Description |
|---|---|---|
| P0 | V0 | Minimal: archetype + event summary only |
| P1 | V0 | + Reddit community context |
| P2 | V1 | + explicit reasoning instruction + grounding prompt |

Best results: **P2_V1** with Qwen2.5-3B-Instruct (JSD: 0.284, Wass: 3.06h)

---

## Key Findings (Pilot)

- The evaluation framework successfully **discriminates** between real discussion and simulation
- Template-based simulation falls predictably between real-vs-real and real-vs-random baselines
- **Grounding is the primary failure mode**: 66.7% of Qwen2.5-3B comments contained no
  verifiable event facts (0% grounding score across all prompt conditions)
- Temporal gap (Wasserstein 3–4.7h) is partly structural: 5 discrete rounds vs.
  continuous real posting stream
- Next step: memory-augmented agents + frontier LLMs (Claude Opus, Gemini 2.5 Pro)

---

## Repo Structure

```
retail-investor-llm-simulation/
├── data/
│   ├── event_cards/          ← event metadata (ticker, time, SEC filing info)
│   └── processed/            ← embeddings + labeled CSVs (gitignored — regenerate)
├── scripts/                  ← full numbered pipeline (see above)
├── outputs/                  ← figures, metric results, audit logs
│   └── proposal_bundle/      ← supporting analysis for proposal
├── .env.example              ← credential template
├── requirements.txt
└── README.md
```

---

## Status

**Current stage:** Pilot complete (template-based simulation, metric framework validated)  
**Next stage:** Full LLM simulation across frontier models (Claude Opus, Gemini 2.5 Pro,
Llama 3.3 70B, DeepSeek R1) with memory-augmented agents and LLM-based stance classification

*Work in progress — thesis submission 2026*

---

## Citation

If you use the evaluation framework or dataset curation approach:

```bibtex
@mastersthesis{sreeharibjkumar2026,
  author = {Sreehari Biji Kumar},
  title  = {Simulating Retail Investor Discussion with LLM Agents},
  school = {University of Queensland},
  year   = {2026}
}
```

---

## Acknowledgements

Data collected from Reddit's public JSON API.
Event times verified against SEC EDGAR 8-K filings.
Conducted under the UQ DATA7901 "Simulating the World" project,
supervised by [Supervisor Name], School of EAIT.
