# Embedding Robustness Check — NVDA_Q3FY26

**Embedding model:** `Qwen/Qwen3-Embedding-0.6B`  
**Baseline embedding:** `all-MiniLM-L6-v2 (baseline)`  
**Event:** `NVDA_Q3FY26`  
**Real comments:** 2403  
**Generated:** 2026-04-01 14:16 UTC

---

## Semantic MMD Rankings (lower = more similar to real data)

| Rank | Run | Condition | MMD (Qwen3-Emb) | MMD (MiniLM) | Δ |
|------|-----|-----------|-----------------|--------------|---|
| 1 | `qwen35_2b_seed42_promptgrid_nvda` | `P2_V1` | 0.155795 | 0.103635 | +0.052160 |
| 2 | `qwen35_2b_temp07_seed42_promptgrid_nvda` | `P2_V1` | 0.189956 | 0.119651 | +0.070306 |
| 3 | `qwen25_3b_seed42_promptgrid_nvda` | `P0_V0` | 0.242719 | 0.137823 | +0.104896 |

### Ranking stability: **stable**

- Qwen3-Embedding-0.6B order: qwen35_2b_seed42_promptgrid_nvda/prompt_exp_P2_V1_comments > qwen35_2b_temp07_seed42_promptgrid_nvda/prompt_exp_P2_V1_comments > qwen25_3b_seed42_promptgrid_nvda/prompt_exp_P0_V0_comments
- MiniLM order:               qwen35_2b_seed42_promptgrid_nvda/prompt_exp_P2_V1_comments > qwen35_2b_temp07_seed42_promptgrid_nvda/prompt_exp_P2_V1_comments > qwen25_3b_seed42_promptgrid_nvda/prompt_exp_P0_V0_comments

_(best first in each list)_

---

## Paste-ready report sentence

> Using `Qwen/Qwen3-Embedding-0.6B` as an alternative embedding model, the best-performing condition (`P2_V1` from `qwen35_2b_seed42_promptgrid_nvda`) achieved MMD = 0.1558 and the worst (`P0_V0` from `qwen25_3b_seed42_promptgrid_nvda`) achieved MMD = 0.2427 (spread = 0.0869); the ranking was **identical** to the MiniLM baseline, confirming that the semantic-similarity conclusions are robust to the choice of embedding model.

---

## Notes

- MMD is computed with RBF kernel, median-heuristic bandwidth (Gretton et al., 2012), biased U-statistic estimator.
- Embeddings are L2-normalised before MMD computation.
- `Qwen/Qwen3-Embedding-0.6B` uses last-token pooling on the decoder hidden state.
- Real comments are filtered to `event_id = NVDA_Q3FY26`.
- Input CSV files were not modified.
