# Real GPU Run Audit

> **OBSOLETE — superseded by [`UPDATED_REAL_GPU_RUN_AUDIT.md`](UPDATED_REAL_GPU_RUN_AUDIT.md) on 2026-05-12.**
>
> This audit was based on a stale local snapshot in which `runs/finalist_*/` still contained dry-run placeholders from local smoke-tests dated 2026-04-21. The real n=108 finalist runs were executed on Rangpur on 2026-04-25 and lived only on the cluster at the time this audit was written. After a manual Rangpur check confirmed the real outputs and the laptop was synced, all 14 `runs/finalist_qwen_*/` folders now contain real Qwen-generated comments with `dry_run: False`. See the updated audit for the current state, the corrected finalist results table, and the corrected interpretation.
>
> The body below is kept for historical record of what the laptop looked like before the sync.

---

# (Historical) Real GPU Run Audit

**Audit date:** 2026-05-12
**Audited proposal:** `DATA7901_Proposal_Sreehari_s4906751.pdf` (dated 2026-04-27)
**Audit scope:** entire local repository plus any logs, JSON, JSONL, slurm-style files

---

## Headline finding

**No real n=108 finalist GPU outputs exist anywhere on the laptop.** Every one of the 14 finalist run folders under `runs/finalist_*/` contains:

- a CSV in which **every single row** is the placeholder string
  `[DRY-RUN] <archetype> #<idx>: Interesting quarter, watching closely.`
- a JSONL metadata file in which **every record** has `dry_run: True`

The submitted proposal repeatedly refers to *"completed 108-comment finalist reruns"* (Chapters 3.3, 6.2, 8, 9, 10, 12, Appendix). That claim is not supported by any file in the repository as of the audit date. The only real GPU-generated outputs that exist locally are the **n=27 prompt-grid pilot** runs from 2026-04-01.

---

## Could real outputs exist on Rangpur but never have been synced back?

In principle yes, but the local evidence makes this unlikely:

| Signal | What we'd expect if a real Rangpur run had happened | What we actually see |
|--------|----------------------------------------------------|---------------------|
| Slurm `gen_%j.out` / `gen_%j.err` in `outputs/logs/` | Files present after sync | Directory does not exist at all; no `.out` or `.err` files anywhere |
| Bash audit log for `scp` / `rsync` / `ssh` to rangpur | At least one matching line | Zero matches in `.claude/bash_audit.log` |
| Finalist CSVs locally modified after a real GPU run | mtime in late April with real model output | All 14 CSVs mtime 2026-04-21 14:19–15:43 with `[DRY-RUN]` placeholder text |
| `prompt_exp_metadata.jsonl` per-comment record | `dry_run: False` somewhere | All 14 JSONLs have `dry_run: True` on every line, model output is the placeholder string |
| Companion log file like `runs/finalist_*/...log` | A real-run log mirroring the n=27 logs | No log files inside any `finalist_*/` folder; only dry-run logs from April 1 elsewhere |
| `data/processed/sim_comments_qwen_oneshot*.csv` from `submit_qwen.sh` | Two real CSVs (seeds 42, 123) | Neither file exists; `submit_qwen.sh` was never followed through |

The April 21 mtimes of the finalist CSVs correspond exactly to the smoke-test and packaging actions logged in the session transcript (semantic_first dry-run, stance_first dry-run, optional_tau07 dry-run). Those local dry-run executions are the only thing that ever wrote into `runs/finalist_*/`.

If real Rangpur outputs do exist, they are on the Rangpur filesystem only. Nothing on the laptop indicates that they were ever produced or pulled.

---

## Per-file evidence (all 42 candidate generation CSVs)

### Group A — Real n=27 prompt-grid runs (the only real LLM outputs in the repo)

| Path | Rows | Mtime | DRY-RUN? | Model | Real evidence |
|------|------|-------|----------|-------|---------------|
| `runs/qwen25_3b_seed42_promptgrid_nvda/prompt_exp_P0_V0_comments.csv` | 27 | 2026-04-01 23:13 | **no** | Qwen2.5-3B-Instruct | log shows real CUDA load, 58.6s generation |
| `runs/qwen25_3b_seed42_promptgrid_nvda/prompt_exp_P1_V0_comments.csv` | 27 | 2026-04-01 23:13 | no | Qwen2.5-3B-Instruct | as above |
| `runs/qwen25_3b_seed42_promptgrid_nvda/prompt_exp_P2_V1_comments.csv` | 27 | 2026-04-01 23:13 | no | Qwen2.5-3B-Instruct | as above |
| `runs/qwen25_3b_seed42_promptgrid_nvda/prompt_exp_all_comments.csv` | 81 | 2026-04-01 23:13 | no | Qwen2.5-3B-Instruct | concatenation of the 3 above |
| `runs/qwen35_2b_seed42_promptgrid_nvda/prompt_exp_*_comments.csv` (4 files) | 27 + 27 + 27 + 81 | 2026-04-01 23:13 | no | Qwen3.5-2B | log `13_prompt_condition_experiment_qwen35_2b_seed42.log` shows real run |
| `runs/qwen35_2b_temp07_seed42_promptgrid_nvda/prompt_exp_*_comments.csv` (4 files) | 27 + 27 + 27 + 81 | 2026-04-01 23:13 | no | Qwen3.5-2B (tau=0.7) | log `13_prompt_condition_experiment_qwen35_2b_temp07_seed42.log` shows real run |
| `runs/final_backup_apr1/...` (12 files mirroring above) | 27/81 | 2026-04-01 23:13 | no | mirror | backup copy of the same April 1 runs |
| `outputs/prompt_exp_*_comments.csv` (4 files) | 27/81 | 2026-04-01 23:13 | no | (latest run) | output mirror of the same April 1 runs |

**These 26 files are safe to cite as real evidence.** They are all from the same April 1 prompt-grid execution and its backups/mirrors. n = 27 per condition, seed 42 only.

#### First 3 generated comments (verified real)

`qwen25_3b_seed42_promptgrid_nvda/prompt_exp_P0_V0_comments.csv`:
1. *"Man, NVIDIA hit the $57B mark again and they're guiding higher for Q4. That's good company news, but with the stock already at these lofty P…"*
2. *"So the numbers look solid, but let's see if this is sustainable. Q4 guidance sounds great, but I'm keeping an eye on those high P/E multiple…"*
3. *"Wow, NVIDIA crushed it again! Revenue growth at 62% versus 50% expectations — that's insane. Let's see if the stock price follows suit thoug…"*

`qwen35_2b_seed42_promptgrid_nvda/prompt_exp_P2_V1_comments.csv`:
1. *"Still can't believe they are releasing full-year data for Q3, but the 'blackwell ramp' narrative has to be solidifying eventually…"*
2. *"Looks like another one of those reports where the stock goes up 20% after hours and stays flat all day. Honestly, at 500b revenue I'm just w…"*
3. *"Honestly, the margin of error on a 30% revenue beat feels thin to me right now. I'm worried Jensen's Q4 guidance isn't fully backed by the p…"*

`qwen35_2b_temp07_seed42_promptgrid_nvda/prompt_exp_P2_V1_comments.csv`:
1. *"Still can't believe they're selling off the whole portfolio for this, but I'm not surprised. They basically just announced that they're goin…"*
2. *"Looks like a solid business report, but honestly, they're now looking at a 3-5 year horizon for this company. The stock is still up 600% in …"*
3. *"Honestly, the fact that they raised guidance and beat the numbers on revenue while the market was panicking on after-hours volatility is the…"*

### Group B — n=108 "finalist" CSVs (DRY-RUN ONLY, do not cite)

| Path | Rows | Mtime | DRY-RUN? | Metadata `dry_run` | First text |
|------|------|-------|----------|--------------------|-----------|
| `runs/finalist_qwen_qwen2_5_3b_instruct_P0_V0_t0.5_s42/prompt_exp_P0_V0_comments.csv` | 108 | 2026-04-21 14:19 | **yes** | `True` | `[DRY-RUN] valuation-focused #0: Interesting quarter, watching closely.` |
| `..._P0_V0_t0.5_s123/...` | 108 | 2026-04-21 14:22 | yes | True | same placeholder |
| `..._P0_V0_t0.9_s42/...` | 108 | 2026-04-21 14:24 | yes | True | same placeholder |
| `..._P0_V0_t0.9_s123/...` | 108 | 2026-04-21 14:27 | yes | True | same placeholder |
| `..._P0_V0_t1.1_s42/...` | 108 | 2026-04-21 14:29 | yes | True | same placeholder |
| `..._P0_V0_t1.1_s123/...` | 108 | 2026-04-21 14:30 | yes | True | same placeholder |
| `..._P2_V1_t0.5_s42/...` | 108 | 2026-04-21 15:35 | yes | True | `[DRY-RUN] long_horizon #0: Interesting quarter, watching closely.` |
| `..._P2_V1_t0.5_s123/...` | 108 | 2026-04-21 15:36 | yes | True | same placeholder |
| `..._P2_V1_t0.7_s42/...` | 108 | 2026-04-21 14:36 | yes | True | same placeholder |
| `..._P2_V1_t0.7_s123/...` | 108 | 2026-04-21 14:38 | yes | True | same placeholder |
| `..._P2_V1_t0.9_s42/...` | 108 | 2026-04-21 15:38 | yes | True | same placeholder |
| `..._P2_V1_t0.9_s123/...` | 108 | 2026-04-21 15:40 | yes | True | same placeholder |
| `..._P2_V1_t1.1_s42/...` | 108 | 2026-04-21 15:43 | yes | True | same placeholder |
| `..._P2_V1_t1.1_s123/...` | 108 | 2026-04-21 15:43 | yes | True | same placeholder |

Every record in every JSONL has the literal field `"dry_run": True`. **None of these are safe to cite.** The MD5 hashes of all six Qwen2.5-3B P0_V0 seed-42 text columns are identical (`72180a0ff3a6…`) — they are byte-identical dry-run placeholders.

### Group C — Other simulated CSVs (not n=108 finalists)

| Path | Rows | Mtime | DRY-RUN? | Source | Citable? |
|------|------|-------|----------|--------|---------|
| `data/processed/sim_comments.csv` | 48 | (template) | no | hand-written template from `07_agent_simulation.py` | yes, as **template baseline** (not LLM) |
| `data/processed/comments.csv` | 300 | (synthetic) | no | synthetic pilot from `00_make_synthetic_data.py` | only as synthetic pilot |

---

## Logs inspected

| File | Size | Mtime | Real GPU run? |
|------|------|-------|---------------|
| `logs/13_prompt_condition_experiment_dryrun.log` | 1031 B | 2026-04-01 | dry-run smoke test |
| `logs/13_prompt_condition_experiment_dryrun_a100.log` | 4811 B | 2026-04-01 | dry-run on A100 (no real generation) |
| `logs/13_prompt_condition_experiment_seed42.log` | 5419 B | 2026-04-01 | **real**: shows Qwen2.5-3B-Instruct loaded on CUDA, 58.6s per condition |
| `logs/13_prompt_condition_experiment_qwen35_2b_seed42.log` | 5484 B | 2026-04-01 | **real**: Qwen3.5-2B on CUDA |
| `logs/13_prompt_condition_experiment_qwen35_2b_temp07_seed42.log` | 5476 B | 2026-04-01 | **real**: Qwen3.5-2B tau=0.7 on CUDA |
| (same files mirrored under `runs/final_backup_apr1/` and per-run subfolders) | — | 2026-04-01 | backups |

**No log files exist from after April 1.** No slurm `gen_%j.out` files exist anywhere. No log files exist inside any `runs/finalist_*/` folder.

---

## Master results JSON: `outputs/finalist_rerun_results.json`

14 entries. Every entry has `n_comments: 108`. The numerical fields (`jsd_stance`, `mmd_semantic`) are not zero, which can be misread as evidence of real generation, but they are simply the metrics computed on the dry-run placeholder corpus. The placeholder phrase *"Interesting quarter, watching closely"* matches the `quarter`-adjacent keyword in the grounding classifier (giving 33.3% weakly-grounded for the P0_V0 block and 100% ungrounded for the P2_V1 block) and produces a fixed embedding distance against real Reddit, which is why all six tau-and-seed variants within each block return nearly identical metric values.

The `elapsed_s` values (107.7s — 182.8s) are also consistent with dry-run: they include model-loading time and embedding time, not real per-comment sampling.

---

## Cross-check against the submitted proposal

| Proposal sentence (verbatim) | Page | Audit verdict |
|-----------------------------|------|--------------|
| *"Current pilot evidence and completed 108-comment finalist reruns both suggest that realism is multi-dimensional"* | i (Abstract) | **Not supported.** No real 108-comment runs exist. |
| *"The completed 108-comment finalist reruns strengthen that same picture rather than overturning it."* | 9 (§3.2) | **Not supported.** |
| *"It is now paired with completed 108-comment finalist reruns, which serve as proposal-stage validation runs"* | 10 (§3.3) | **Not supported.** |
| *"The completed finalist reruns also improve the temperature story."* | 11 (§3.5) | **Not supported.** |
| *"I have already completed the first larger validation tier: 14 finalist A100 reruns at 108 comments per run."* | 18 (§6.2) | **Not supported.** No A100 evidence; all 14 are local dry-run. |
| *"Completed finalist GPU reruns on Rangpur — 24 hours"* | 24 (Table 9.1) | **Not supported as completed work.** |
| *"completed 108-comment validation-tier reruns already exist"* | 23 (§8) | **Not supported.** |
| *"It now also includes uncertainty-aware benchmark evidence through bootstrap intervals, a hand-audited check on the stance labeler, and completed 108-comment finalist reruns"* | 28 (Conclusion) | **Bootstrap intervals: supported.** Stance hand-audit: supported. **108-comment finalist reruns: not supported.** |

The other strong claims in the proposal **are** supported by local files:

- The n=27 prompt-grid Pareto trade-off (Table B.1, Figure 3.1): supported by `runs/qwen{25_3b,35_2b,35_2b_temp07}_seed42_promptgrid_nvda/*`.
- Bootstrap intervals (Table 3.1, Table B.4): supported by `outputs/proposal_support/bootstrap_metrics.csv` and `bootstrap_summary.md`.
- Embedding robustness check (Table B.2): supported by `outputs/embedding_robustness_qwen_qwen3-embedding-0_6b.{json,md}`.
- Stance labeler hand-audit (Appendix C, kappa 0.448): supported by `outputs/proposal_support/stance_validation_sample.csv` and the hand-annotated audit file.
- 150-token cap justification (Table 6.1, Appendix A): supported by `outputs/proposal_support/comment_length_stats.csv`.
- Benchmark retention table (Table 2.1): supported by `outputs/proposal_support/event_summary.csv`.

---

## What to do

1. **Treat the finalist results as not-yet-existing.** Any seminar slide or follow-up document that references n=108 numbers from `outputs/finalist_rerun_results.json` or `finalist_results_table.csv` should be marked pending until real GPU execution.
2. **If real outputs are on Rangpur**, sync them down (`scp rangpur:~/llm-investor-sim/runs/finalist_*/ runs/`) and rerun `scripts/make_finalist_summary.py` to verify the dry-run flag flips to `False` and the placeholder text is gone.
3. **If real outputs are not on Rangpur either**, execute the finalist grid with `scripts/18_finalist_rerun.py --batch semantic_first` (and `--batch stance_first`) on a real A100 session, then sync.
4. **Update the proposal record.** For now, the n=27 prompt-grid pilot plus bootstrap intervals plus stance hand-audit is the genuine evidence base. The proposal's claim that 108-comment runs are *completed* is the single largest discrepancy between the document and the repository as it currently stands.

---

## Files inventoried in this audit

- 42 generation CSVs (above)
- 14 finalist metadata JSONLs (all `dry_run: True`)
- 17 log files (newest 2026-04-01; no late-April logs)
- 2 master results JSONs (`outputs/finalist_rerun_results.json`, mirror in `runs/`)
- 3 shell scripts (`submit_qwen.sh`, `setup_rangpur.sh`, `13_run_all_eval.sh`)
- `.claude/bash_audit.log` (no ssh/scp/rsync to rangpur)
- `HANDOVER.md` (as of April 1: "no actual LLM generation in the main pipeline")
