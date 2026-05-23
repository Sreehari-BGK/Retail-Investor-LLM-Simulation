# Changelog — DATA7901 seminar final rebuild

**Date:** 2026-05-14
**Rebuild authored by:** Sreehari Biji Kumar (s4906751)

This rebuild incorporates the professor's seminar-feedback and the requested support-pack corrections. Below is a full diff at the deliverable level.

---

## New artefacts

| File | Purpose |
|------|---------|
| `outputs/DATA7901_Seminar_Sreehari_s4906751_v2.pptx` | New 26-slide deck (10 main + Thank You + 15 appendix). Replaces the 8-slide v1. |
| `outputs/seminar_support/SEMINAR_SPEAKER_NOTES_V2.md` | Per-slide speaker notes for the v2 deck, with timing budget. |
| `outputs/seminar_support/data_eda_slide_visual.png` | New data + EDA panel for slide 4 (sources / window / fields / raw-vs-curated / NVDA temporal histogram). |
| `outputs/seminar_support/model_io_prompt_visual.png` | New model-setup panel for slide 6 (event card → persona → prompt → temperature → Qwen → output + best run). |
| `scripts/_seminar_rebuild_figures.py` | Reproducible script for all 6 rebuilt/added figures. |
| `scripts/_seminar_build_pptx_v2.py` | Reproducible script for the v2 deck. |
| `CHANGELOG_SEMINAR_FINAL_REBUILD.md` | This file. |

---

## Updated artefacts (in `outputs/seminar_support/`)

These four PNGs were regenerated with content corrections:

| File | What changed |
|------|-------------|
| `curation_flow.png` | (1) "±48 h" → **"−24 h to +48 h around earnings release"**.  (2) **"METAs"** → **"META's"**.  (3) **"Reddit JSON API search"** → **"Reddit collection using PRAW"**. |
| `stance_rule_backup.png` | "Same labeler applied to real and simulated text, so any bias cancels at the corpus level" → **"Same labeler improves comparability, but this remains a noisy distribution-level proxy."** |
| `metrics_plain_language.png` | Redesigned as a compact 3-card + 1-strip layout. Hierarchy explicit: **Headline** badge on MMD, Grounding, JSD; **Secondary** badge on Wasserstein with one-line scheduler caveat. Less empty space. |
| `temperature_backup.png` | Avoids "high temperature solves grounding" framing. Summary stripe now reads: **"Higher temperature reduces fact-mention density overall, but generated comments remain much more grounded than real Reddit."** |

---

## Unchanged support-pack artefacts (kept as-is)

These were already in the support pack and remain unchanged:

- `outputs/seminar_support/exact_reddit_threads_all_events.md`
- `outputs/seminar_support/slide_restructure_recommendation.md`
- `outputs/seminar_support/appendix_slide_plan.md`
- `outputs/seminar_support/_threads_inventory.csv`
- `outputs/seminar_support/grounding_rule_backup.png`
- `outputs/seminar_support/timestamp_scheduler_backup.png`
- `outputs/seminar_support/content_results_dashboard.png`
- `outputs/seminar_support/temperature_tradeoff.png`
- `outputs/seminar_support/event_prompt_agent_diagram.png` (kept for reference; the deck now uses the new `model_io_prompt_visual.png`)

---

## Deck structure (v1 → v2)

### v1 structure (8 content slides)

1. Title  ·  2. Problem  ·  3. Benchmark + curation  ·  4. Pipeline + grid  ·  5. Four metrics  ·  6. Finalist results  ·  7. Limitations  ·  8. Takeaway

### v2 structure (10 content slides + Thank You + 15 appendix)

| # | Title | Story role | Visual |
|---|-------|-----------|--------|
| 1 | Can LLMs simulate investor reaction, or just sound like they can? | Need | sample comment + 4 cards |
| 2 | The research question | Need → Task | big question + 3 event cards |
| 3 | Real-world example: NVDA Q3 earnings on Reddit | Real-world hook | thread metadata + screenshot placeholder |
| 4 | What the collected Reddit data looks like | Data + EDA | `data_eda_slide_visual.png` |
| 5 | From raw collection to diagnostic reference corpus | Task setup | `curation_flow.png` + retention cards |
| 6 | Model setup — input, prompt, output | Task setup | `model_io_prompt_visual.png` |
| 7 | Evaluation checks in plain English | Method | `metrics_plain_language.png` |
| 8 | Main result: behaviour-first prompting helps | Message | `content_results_dashboard.png` |
| 9 | The temperature trade-off | Message detail | `temperature_tradeoff.png` |
| 10 | Meaning, limitations, next test | Conclusion | three columns |
| — | Thank You | — | appendix table of contents |
| A1 | Reddit threads (NVDA) | backup | table |
| A2 | Reddit threads (AAPL & META) | backup | tables + removed list |
| A3 | Data schema (columns) | backup | table |
| A4 | Curation decision logic | backup | flow diagram + rules |
| A5 | Exact event card text | backup | verbatim block |
| A6 | Prompts P0 / P1 / P2 | backup | three colour-coded cards |
| A7 | Personas / cohorts V0 / V1 | backup | side-by-side columns |
| A8 | Model input → output example | backup | full diagram |
| A9 | Stance classifier rule | backup | `stance_rule_backup.png` |
| A10 | Grounding rule | backup | `grounding_rule_backup.png` |
| A11 | Timestamp scheduler | backup | `timestamp_scheduler_backup.png` |
| A12 | Temperature explanation | backup | `temperature_backup.png` |
| A13 | Full 14-run finalist table | backup | sortable table |
| A14 | Metric formulas + caveats | backup | four cards |
| A15 | Literature anchors | backup | positioning table |

Total: **26 slides** in the new deck (was 8).

---

## How each piece of professor feedback was addressed

| Feedback item | Where addressed in v2 |
|---------------|----------------------|
| **Page numbers on every slide** | Every slide has a footer like `1 / 10`, `7 / 10`, `A4 / 15`, plus a running title strip with student name + ID. |
| **Describe what the collected data looks like + EDA** | New slide 4 (`data_eda_slide_visual.png`) explicitly answers: source, tool (PRAW), window, unit, events, fields stored, raw-vs-curated bar chart, and NVDA temporal distribution. Schema details broken out further in A3. |
| **Model: input / output / prompt / results clearly described** | New slide 6 (`model_io_prompt_visual.png`) names all four explicitly (Event card / Persona / Prompt / Temperature) and ends with a navy strip showing the best-run config and headline metrics. Full I/O example duplicated in A8 for Q&A. |
| **More figures, fewer text blocks** | Every main slide is figure-driven. No slide has a multi-line paragraph; all body content is in cards, tables, short bullets, or visual diagrams. |

---

## What was *not* changed

- Underlying real-result files (`outputs/finalist_rerun_results.json`, `outputs/proposal_support/finalist_results_table.{csv,md}`, the 14 `runs/finalist_qwen_*/` folders) — read-only.
- The corrected status from `UPDATED_REAL_GPU_RUN_AUDIT.md` and `CLAUDE.md` — both still authoritative.
- The v1 PowerPoint file (`DATA7901_Seminar_Sreehari_s4906751.pptx`) — kept on disk for reference; the v2 file lives alongside it with the `_v2` suffix.
- No new generation, no new metric runs, no overwrites of synced Rangpur outputs.

---

## How to reproduce the rebuild

```bash
# 1. Regenerate the 6 figures
python scripts/_seminar_rebuild_figures.py

# 2. Rebuild the v2 deck
python scripts/_seminar_build_pptx_v2.py
```

Both scripts are idempotent and only touch files in `outputs/seminar_support/` and the new `_v2.pptx` filename. No source data is altered.

---

## Open items / things to do before the talk

These are the only manual edits left to make in PowerPoint:

1. **Slide 3:** drop in the actual Reddit screenshot of thread `1p1ked6`. The placeholder box is already laid out at the correct dimensions.
2. **Optional polish:** PowerPoint will alias the embedded PNGs; if needed, switch to "Insert from file" for the same images at higher DPI.
3. **Practice run:** read through speaker notes once at conversational pace. Target is ~9:15; built-in slack is on slides 7 and 9 if running long.

---

## Provenance

- Reddit thread list: `outputs/seminar_support/_threads_inventory.csv` (built by `scripts/_seminar_thread_inventory.py` from raw CSVs + `curate_and_freeze.py THREAD_DECISIONS`).
- Finalist results: `outputs/finalist_rerun_results.json` (synced from Rangpur 2026-04-25; verified by `UPDATED_REAL_GPU_RUN_AUDIT.md`).
- Real NVDA grounding 2.5%: computed by `12_eval_grounding.py` on `data/processed/real_comments_curated_labeled.csv`.
- LLM grounding rates per finalist run: stored in each `runs/finalist_qwen_*/metrics.json` and aggregated in the master results JSON.
- Stance hand-audit (κ = 0.448): from the 100-comment audit sampled in `outputs/proposal_support/stance_validation_sample.csv`.
- All prompt / persona / event-card text: verbatim from `scripts/13_prompt_condition_experiment.py` and `scripts/18_finalist_rerun.py`.
