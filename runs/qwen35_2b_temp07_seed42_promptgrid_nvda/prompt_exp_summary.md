# Prompt Condition Experiment — NVDA Q3 FY2026

**Generated:** 2026-04-01 06:32 UTC  
**Model:** `Qwen/Qwen3.5-2B`  
**Temperature:** 0.7 | **Top-p:** 0.95 | **Top-k:** 50 | **Max new tokens:** 150  
**Base seed:** 42  
**Dry run:** False

---

## Combinations Run

| # | Prompt | Persona | N comments |
|---|--------|---------|------------|
| 1 | `P0_baseline_current` | `V0_current` | 27 |
| 2 | `P1_balanced_retail_reaction` | `V0_current` | 27 |
| 3 | `P2_behavior_first_diversity` | `V1_three_archetypes` | 27 |

---

## Evaluation Metrics vs Real NVDA Data

| Condition | JSD Stance ↓ | Wasserstein Time ↓ | MMD Semantic ↓ |
|-----------|-------------|-------------------|----------------|
| `P0_V0` | 0.6000 | 2.7066 | 0.1321 |
| `P1_V0` | 0.4441 | 2.7066 | 0.1428 |
| `P2_V1` | 0.4828 | 2.7066 | 0.1197 |

↓ = lower is more similar to real data

---

## Stance Distribution per Condition

| Condition | % Bullish | % Bearish | % Neutral | N |
|-----------|-----------|-----------|-----------|---|
| `P0_V0` | 85.2% | 7.4% | 7.4% | 27 |
| `P1_V0` | 66.7% | 14.8% | 18.5% | 27 |
| `P2_V1` | 70.4% | 14.8% | 14.8% | 27 |

---

## Output Files

| File | Contents |
|------|----------|
| `prompt_exp_P0_V0_comments.csv` | P0+V0 generated comments |
| `prompt_exp_P1_V0_comments.csv` | P1+V0 generated comments |
| `prompt_exp_P2_V1_comments.csv` | P2+V1 generated comments |
| `prompt_exp_all_comments.csv` | All conditions combined |
| `prompt_exp_metadata.jsonl` | Per-comment: exact prompts + hyperparams |
| `prompt_exp_metrics.json` | Evaluation metrics per condition |
| `prompt_exp_summary.md` | This file |

## Notes

- All three conditions use **the same base seed** (`base_seed`), with `gen_seed = base_seed + global_comment_index`.
- `hours_from_event` is sampled from the same temporal distribution (bucket weights: 10% pre-event, 40% immediate, 30% digest, 15% follow-up, 5% wind-down).
- Stance is assigned post-hoc using the rule-based keyword labeler (`_label_stance` in this script); not pre-assigned by the model.
- Evaluation is skipped gracefully if real NVDA data files are absent.
