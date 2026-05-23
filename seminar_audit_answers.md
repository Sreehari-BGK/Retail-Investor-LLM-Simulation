# Seminar Audit Answers

Audit of the actual scripts and result files on disk. All citations are to file paths and line numbers in this repository.

---

## CRITICAL FINDING — read this first

**The 14 "finalist" CSVs in `runs/finalist_*/` contain DRY-RUN PLACEHOLDER text, not real LLM output.** Every row in every finalist CSV is literally `"[DRY-RUN] <archetype> #<idx>: Interesting quarter, watching closely."` (verified by md5: all six P0_V0 seed-42 files have identical hash `72180a0ff3a6`, and the first text is the dry-run placeholder).

That means:
- `finalist_rerun_results.json` and `finalist_results_table.csv/.md` reflect metrics computed on placeholder text, not on real generation.
- The identical JSD (0.2842) and MMD (~0.2251) across tau in {0.5, 0.9, 1.1} for Qwen2.5-3B P0_V0 is not a temperature-insensitivity result; it is the same dry-run text being scored repeatedly.
- The genuine experimental evidence that exists right now is the **pilot prompt-grid runs** in `runs/qwen25_3b_seed42_promptgrid_nvda/`, `runs/qwen35_2b_seed42_promptgrid_nvda/`, and `runs/qwen35_2b_temp07_seed42_promptgrid_nvda/`. These contain real Qwen-generated text at n = 27 per condition.

Any seminar slide that cites the n=108 finalist numbers as evidence is currently citing dry-run artefacts. The bundle README, manifest, and Table B.5 must be flagged accordingly or the entries removed until a real GPU rerun is executed.

---

## 1. Simulated timestamps

**Where the event-relative timestamp comes from.** It is sampled externally by the simulation pipeline. The LLM does not generate it and does not see it.

**Three timestamp generators exist in the repo, all using the same pattern (Gaussian draw per cohort, clipped to a range, then added to the fixed `EVENT_TIME`):**

1. [scripts/11_run_qwen_oneshot.py:122-133](scripts/11_run_qwen_oneshot.py#L122-L133) — `assign_hour_bin(archetype_id, rng)`. Cohort-conditional Gaussian:
   - short-horizon: `gauss(mu=2, sigma=3)` clipped to `[-1, 12]`
   - long-horizon: `gauss(mu=10, sigma=10)` clipped to `[-6, 48]`
   - info-seeking: `gauss(mu=6, sigma=6)` clipped to `[0, 36]`
   The wall-clock timestamp is then `EVENT_TIME + timedelta(hours=hours)` at [11_run_qwen_oneshot.py:261](scripts/11_run_qwen_oneshot.py#L261).

2. [scripts/13_prompt_condition_experiment.py:96-111](scripts/13_prompt_condition_experiment.py#L96-L111) — `_sample_hours(n, seed)`. Uniform-within-bucket draw from five weighted buckets:
   - [-12, -2) weight 0.10 (pre-event)
   - [0, 2) weight 0.40 (immediate)
   - [2, 12) weight 0.30 (digest)
   - [12, 24) weight 0.15 (follow-up)
   - [24, 48) weight 0.05 (wind-down)

3. [scripts/18_finalist_rerun.py:172-181](scripts/18_finalist_rerun.py#L172-L181) — `assign_hour(cohort, rng)`. Same Gaussian-per-cohort scheme as 11_run_qwen_oneshot.py.

**Column that stores it.** Hours-from-event is stored in `hours_from_event`; the ISO wall-clock form (where written) is stored in `simulated_timestamp`. Both columns appear in [data/processed/sim_comments.csv](data/processed/sim_comments.csv) (template) and in every finalist `prompt_exp_*_comments.csv`.

**Which script creates it.** For the template baseline, [scripts/07_agent_simulation.py](scripts/07_agent_simulation.py). For the one-shot LLM baseline, [scripts/11_run_qwen_oneshot.py](scripts/11_run_qwen_oneshot.py). For the prompt/persona ablation, [scripts/13_prompt_condition_experiment.py](scripts/13_prompt_condition_experiment.py). For the finalist rerun grid, [scripts/18_finalist_rerun.py](scripts/18_finalist_rerun.py).

**Does the LLM see the timestamp in the prompt? No.** Inspecting all three prompt builders ([scripts/13_prompt_condition_experiment.py:295-379](scripts/13_prompt_condition_experiment.py#L295-L379) for P0/P1/P2 and [scripts/11_run_qwen_oneshot.py:101-119](scripts/11_run_qwen_oneshot.py#L101-L119) for the baseline) confirms the chat messages contain only the event summary, persona description, and writing style. The hour is appended to the record **after** generation, by `assign_hour_bin()`. The timestamp is therefore a property of the orchestrator, not of the model.

---

## 2. Temporal metric (Wasserstein-1)

**Exact calculation** — from [scripts/04_compute_metrics.py:67-97](scripts/04_compute_metrics.py#L67-L97):

1. `binned_time_distribution(hours, start_h=-24, end_h=48, bin_size=1.0)` builds a histogram with `np.arange(-24, 49, 1.0)`, i.e. **72 hourly bins** spanning the full event window.
2. The histogram is normalised to sum to 1.
3. The support is integer bin indices `0..71`, not signed hour values, and `scipy.stats.wasserstein_distance(support, support, u_weights=p, v_weights=q)` returns Wasserstein-1 in **bin units = hours** because `bin_size=1`.

**Are both real and sim binned the same way?** Yes. Both real and simulated `hours_from_event` go through the same `binned_time_distribution` call with the same range and bin size in [04_compute_metrics.py:85-97](scripts/04_compute_metrics.py#L85-L97).

**Why some temporal distances are identical across prompt/model runs.**

Because *the timestamp is not produced by the LLM*. Within a single pilot run script, hours are drawn from `_sample_hours(n, seed)` (in `13_prompt_condition_experiment.py`) once per (n, seed) combination, then *reused* across all prompt and model conditions in that script. So P0_V0, P1_V0, and P2_V1 at the same seed share an identical `hours_from_event` array, which guarantees identical Wasserstein-time values. In the pilot results file [runs/qwen25_3b_seed42_promptgrid_nvda/prompt_exp_metrics.json](runs/qwen25_3b_seed42_promptgrid_nvda/prompt_exp_metrics.json) all three conditions report `wasserstein_time = 2.7066…` for exactly this reason.

In the finalist runs the same effect surfaces but for a different reason: temperature does not enter the temporal sampler, so Wasserstein varies only with `seed`. The two distinct seeds (42 and 123) give exactly two distinct Wasserstein values (3.06 and 3.13) across all 14 finalist rows. This is expected behaviour, not a metric bug — temperature is a property of token sampling, not of comment scheduling.

**Implication for slides.** Wasserstein-1 currently measures the quality of the *external scheduler*, not the quality of the LLM. Any temperature-vs-Wasserstein plot will be flat by construction.

---

## 3. Prompt conditions

Defined in [scripts/13_prompt_condition_experiment.py:295-379](scripts/13_prompt_condition_experiment.py#L295-L379). Personas defined in [scripts/13_prompt_condition_experiment.py:144-287](scripts/13_prompt_condition_experiment.py#L144-L287).

### P0_baseline_current (with V0 = 9 archetypes)

**System:**
> You are simulating a retail investor posting on Reddit after NVIDIA's earnings announcement. Write exactly ONE short Reddit-style comment (1-4 sentences max). Rules: Use casual Reddit language, not formal finance writing. **Reference specific facts from the earnings when relevant to your persona.** Do NOT write disclaimers, headers, or break character. Do NOT say 'As a [type] investor'. Output ONLY the comment text.

**User:** structured with `EARNINGS EVENT`, `YOUR INVESTOR PROFILE`, `WRITING STYLE`, ending "Write one Reddit comment from this investor's perspective about this NVIDIA earnings result."

**Encourages** number citation via the explicit "reference specific facts" instruction.

### P1_balanced_retail_reaction (with V0)

**System:**
> You are writing like a retail investor commenting on Reddit after a company earnings event. Write one short Reddit-style comment reacting to the event. Important: React like a person, not like a financial report. You may be bullish, bearish, neutral, or unsure. Focus on expectations, surprise, risk, sentiment, valuation, guidance, or what this could mean next. You do not need to mention every fact from the event. Do not over-explain. **Do not sound like an analyst note.** Casual language is fine, but stay coherent. It is okay to be uncertain or conflicted. Avoid always sounding optimistic.

**Discourages** analyst tone explicitly ("Do not sound like an analyst note", "you do not need to mention every fact").

### P2_behavior_first_diversity (with V1 = 3 broad cohorts)

**System:**
> You are simulating one Reddit user reacting to a company earnings event. Write one short comment that reflects how this kind of user would actually react online. The comment should reflect the user's behaviour, priorities, and time horizon more than perfect factual coverage. [...list of behaviours...] Important: The comment can be bullish, bearish, neutral, or mixed. The comment can be uncertain. The comment does not need to mention all details. **It should not read like a clean earnings summary.** It should feel like a real post/comment, not a textbook answer. Keep it short and natural. Mild informality is good. Do not make every comment sound rational, complete, or polished.

**User:** drops the formal "WRITING STYLE" block; uses `USER TYPE` + `BEHAVIOUR PROFILE`.

**Most aggressively discourages over-grounding** ("not a clean earnings summary", "not a textbook answer", "behaviour more than perfect factual coverage").

### Which prompt discourages analyst-style citation / over-grounding

- **P0:** actively encourages fact citation.
- **P1:** explicitly discourages analyst tone but still keeps the structured profile block.
- **P2:** most strongly discourages summary/analyst tone and explicitly downgrades factual coverage relative to behaviour. **P2 is the de-grounding prompt.**

### Do any prompts use real Reddit exemplars?

**No.** All three prompts use only the `EVENT_SUMMARY` string (a hand-written four-sentence NVIDIA Q3 FY26 description in [13_prompt_condition_experiment.py:84-90](scripts/13_prompt_condition_experiment.py#L84-L90)) and the persona descriptions. There is no few-shot block, no retrieved real comment, no exemplar pool. The simulator is fully zero-shot from a fixed event card and persona card.

---

## 4. Grounding

### Definition

From [scripts/12_eval_grounding.py:38-67](scripts/12_eval_grounding.py#L38-L67) and `classify_grounding` at [12_eval_grounding.py:129-142](scripts/12_eval_grounding.py#L129-L142).

A comment is scored on six NVDA-fact categories:
- **revenue** — keywords `revenue`, `57`, `57 billion`, `$57`, `57b`, `sales`, `top line` (+ growth keywords `62%`, `yoy`)
- **earnings** — `eps`, `earnings per share`, `earnings`, `profit`, `net income`
- **guidance** — `guidance`, `outlook`, `q4`, `forecast`, `raised`, `guided higher`, etc.
- **product** — `blackwell`, `gpu`, `chips`, `data center`, `h100`/`h200`/`b100`/`b200`, `hopper`
- **valuation** — `pe`, `p/e`, `valuation`, `multiple`, `market cap`, `trillion`
- **price_action** — `after hours`, `ah`, `dip`, `sold off`, `premarket`

The label assignment is:
- **grounded** = at least 3 categories mentioned, OR at least 2 categories *and* the text contains at least one number.
- **weakly_grounded** = at least 1 category mentioned.
- **ungrounded** = zero categories mentioned.

This is a keyword-coverage heuristic, not a factual-correctness check. (Separately, `check_directional_correctness` looks for beat/miss and raised/lowered language and compares against `DIRECTION_TRUTH = {beat: True, guidance_raised: True}`.)

### Latest grounding rates

Computed just now using the same `evaluate_corpus()` function on:

| Corpus | n | grounded % | weakly_grounded % | ungrounded % |
|--------|---|-----------|------------------|--------------|
| Real NVDA Reddit (curated) | 2403 | **2.5** | 15.0 | 82.4 |
| Template baseline (`sim_comments.csv`) | 48 | **52.1** | 45.8 | 2.1 |
| Finalist P0_V0 (tau=0.9, s=42)* | 108 | **0.0** | 33.3 | 66.7 |
| Finalist P2_V1 (tau=0.9, s=42)* | 108 | **0.0** | 0.0 | 100.0 |

*finalist runs are dry-run text — see Critical Finding above; the 33.3% weakly-grounded P0 number reflects the placeholder phrase "interesting quarter" matching the `quarter`-adjacent keywords, not real generation.

The key qualitative observation that does survive: **the template baseline is wildly over-grounded compared to real Reddit** (52% vs 2.5%). The template was hand-written to namedrop facts; real Reddit comments mostly do not.

---

## 5. Latest results — does the earlier claim still hold?

### The earlier claim

From the pilot prompt-grid analysis (n=27 per condition, real Qwen output): **Qwen2.5-3B with P0_V0 is best on JSD stance, Qwen3.5-2B with P2_V1 is best on MMD semantic.** Pareto trade-off — no single winner.

### Canonical / latest finalist results table

The current canonical files are:
- [outputs/finalist_rerun_results.json](outputs/finalist_rerun_results.json) (14 entries, master JSON)
- [outputs/proposal_support/finalist_results_table.csv](outputs/proposal_support/finalist_results_table.csv) / `.md`

### Do the latest results support the earlier claim?

**No — and the reason is not a real finding but a process error.** As documented in the Critical Finding above, every "finalist" CSV under `runs/finalist_*/` is dry-run placeholder text. The metrics in `finalist_rerun_results.json` therefore measure how the placeholder string compares against real Reddit, not how the model output compares.

Within those dry-run numbers, P0_V0 placeholders happen to score better than P2_V1 placeholders on both JSD (0.284 vs 0.448) and MMD (0.225 vs 0.302), but that is an artefact of which placeholder strings the two scripts happen to use, not an experimental result.

### The genuine current evidence (n = 27 prompt-grid runs)

From [runs/qwen25_3b_seed42_promptgrid_nvda/prompt_exp_metrics.json](runs/qwen25_3b_seed42_promptgrid_nvda/prompt_exp_metrics.json) and the matching Qwen3.5-2B file:

| Model | Condition | JSD stance | MMD semantic |
|-------|-----------|-----------|--------------|
| Qwen2.5-3B | P0_V0 | **0.407** | 0.138 |
| Qwen2.5-3B | P1_V0 | 0.481 | 0.190 |
| Qwen2.5-3B | P2_V1 | 0.517 | 0.171 |
| Qwen3.5-2B | P0_V0 | 0.634 | 0.133 |
| Qwen3.5-2B | P1_V0 | 0.460 | 0.132 |
| Qwen3.5-2B | P2_V1 | 0.417 | **0.104** |
| Qwen3.5-2B (tau=0.7) | P2_V1 | 0.483 | 0.120 |

These numbers do support the earlier Pareto claim: **best stance = Qwen2.5-3B + P0_V0 (JSD 0.407); best semantic = Qwen3.5-2B + P2_V1 (MMD 0.104)**. No single condition dominates the other on both metrics.

### Action items before any seminar slide is built

1. **Re-execute the finalist grid on a real GPU.** The current 14 rows are placeholders. Until rerun, do not cite n=108 numbers.
2. **Refresh the bundle.** Once real outputs exist, regenerate `finalist_results_table.csv/.md` via `python scripts/make_finalist_summary.py`.
3. **Update README, manifest, and Table B.5** in `outputs/proposal_bundle/` to remove or flag the dry-run results.
4. **Keep the n=27 pilot grid as the headline result** in seminar slides until real n=108 evidence exists. The Pareto trade-off statement is still defensible from the n=27 data.
