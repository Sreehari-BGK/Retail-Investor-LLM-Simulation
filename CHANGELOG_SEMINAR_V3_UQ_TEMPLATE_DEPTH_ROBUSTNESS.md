# Changelog — Seminar deck v3 (UQ-styled + depth robustness)

**Date:** 2026-05-14
**Author:** Sreehari Biji Kumar (s4906751)
**Output:** `outputs/DATA7901_Seminar_Sreehari_s4906751_v3_content_ready.pptx` (27 slides)

---

## Template transfer status

**Fallback applied.** The "UQ template" was uploaded as a PDF preview (`UQ-Working-Remotely.pdf`), not as a `.pptx` file. python-pptx requires an actual `.pptx` (with slide masters) to use as a theme base. Per Part G of the brief — *"do not waste time forcing it"* — I built the **content-ready** deck with UQ-style visual conventions hand-applied:

- UQ purple primary (`#512D6F`) and magenta accent (`#B6258C`)
- Thin purple header bar across every content slide
- Purple title text on white body
- Light purple-tinted card fills
- Page numbers in the bottom-right of every slide
- Course/title footer line above the page number
- No CRICOS code, no UQ logo asset (neither available locally)

`TEMPLATE_TRANSFER_FALLBACK_NOTES.md` documents the 1-minute manual paste path to apply the real UQ template.

---

## Confirmation checklist

| Required check | Status |
|----------------|--------|
| UQ template applied OR fallback used | **Fallback used** (PDF preview, not `.pptx`) |
| Slide 10 renamed "Conclusion and Next Steps" | **Yes** — verified by inspecting the saved pptx (`"Conclusion and Next Steps" in slide_10_text == True`) |
| A16 (top-level vs replies robustness) added | **Yes** — final appendix slide; uses `top_level_grounding_comparison.png` |
| Slide 8 speaker notes updated | **Yes** — added: *"This is not caused by including replies: top-level-only Reddit comments are 2.6% grounded, while the best LLM is still 57.4%; see appendix A16."* |
| Slide 10 speaker notes updated | **Yes** — added: *"Although the simulator is one-shot, the grounding gap remains even when real Reddit is restricted to top-level comments only."* |
| Page numbers preserved | **Yes** — `N / 10` on main slides, `Thank You` on the thanks slide, `Ax / 16` on appendix slides |
| Obsolete dry-run issue mentioned anywhere | **No** — not in slides, not in notes, not in this changelog |

### Professor feedback addressed

| Feedback item | Where in v3 |
|---------------|-------------|
| Page numbers on every slide | Every slide footer; bottom-right text box with bold UQ-purple page label |
| Data described + EDA | Slide 4 uses `data_eda_slide_visual.png` (sources, window, fields, raw-vs-curated bars, NVDA temporal histogram). Schema details in A3. |
| Model input / output / prompt / results clearly described | Slide 6 uses `model_io_prompt_visual.png` (event card / persona / prompt / temperature → Qwen → output) + best-run results strip. Full I/O example duplicated in A8. |
| More figures, less text | Every main slide is figure-driven; no slide contains a multi-line paragraph. Body content is cards, short bullets, or visual diagrams. |

---

## Deck structure (v2 → v3 diff)

**v2:** 26 slides (10 content + Thank You + 15 appendix A1–A15)
**v3:** 27 slides (10 content + Thank You + **16 appendix A1–A16**)

### What changed slide-by-slide

| Slide | Status | Change |
|-------|--------|--------|
| 1–7  | unchanged | Visual repaint into UQ purple palette only |
| 8  | speaker notes updated | Added the top-level robustness reference sentence |
| 9  | unchanged | UQ palette repaint |
| **10** | **renamed + restructured** | Title changed to "Conclusion and Next Steps". Layout switched to three colour-coded blocks: *Conclusion / Practical value / Next steps* — matching the brief's three-block content spec. Practical-value text: *"This diagnostic catches a hidden risk in financial AI simulation: realistic-looking LLM crowds may overstate how informed real retail investors are."* Speaker notes updated with the top-level robustness sentence. |
| Thank You | updated | Appendix TOC now shows 16 items (A16 added) |
| A1–A15 | unchanged | UQ palette repaint; page footer changed from `Ax / 15` to `Ax / 16` |
| **A16** | **NEW** | "Grounding robustness: top-level vs replies". Uses `top_level_grounding_comparison.png`. Key bullets: real all 2.5%, real top-level 2.6%, real replies 2.1%, best LLM 57.4%; OP/post rows reported separately. |

---

## Language discipline (Part F) — what was avoided and what was used

**Avoided in slide visible text:**
- "benchmark" as the headline claim → replaced with "diagnostic reference corpus" and "diagnostic protocol"
- "solved simulator", "realistic simulator" → not used anywhere
- "autonomous timing behaviour" → not used; timing is consistently framed as a *scheduler diagnostic*
- "validation proves human realism" → not used; framing is *content-level gap* and *over-grounding*

**Used:**
- "diagnostic protocol"
- "reference corpus" / "diagnostic reference corpus"
- "content-level gap" (Slide 8 message strip; Slide 10 Conclusion block)
- "over-grounding" (Slide 8 title; A16; speaker notes)
- "scheduler diagnostic" (Slide 7 secondary card; A11)

Main value proposition (lifted into Slide 10 block 2 verbatim):
*"This diagnostic catches a hidden risk in financial AI simulation: realistic-looking LLM crowds may overstate how informed real retail investors are."*

---

## Files produced or updated in this rebuild

| File | Status |
|------|--------|
| `outputs/DATA7901_Seminar_Sreehari_s4906751_v3_content_ready.pptx` | **new** — 27-slide content-ready deck |
| `scripts/_seminar_build_pptx_v3.py` | **new** — reproducible build script |
| `TEMPLATE_TRANSFER_FALLBACK_NOTES.md` | **new** — manual UQ template paste instructions |
| `CHANGELOG_SEMINAR_V3_UQ_TEMPLATE_DEPTH_ROBUSTNESS.md` | **new** — this file |

### Files used (not modified)

- All 12 figures in `outputs/seminar_support/*.png` (4 corrected + 2 new in the v2 rebuild; 1 new top-level robustness; rest unchanged from earlier sessions)
- `outputs/seminar_support/SEMINAR_SPEAKER_NOTES_V2.md` (still valid as a companion; the deck contains its own embedded speaker notes for v3 with the two updated sentences)
- `outputs/seminar_support/top_level_vs_replies_robustness.md` (the Q&A paragraph for A16 was authored here)

---

## Operational checks

| Check | Result |
|-------|--------|
| `pptx.Presentation(...)` loads the v3 file without error | ✅ |
| Total slide count | **27** (10 + 1 + 16) |
| "Conclusion and Next Steps" appears in Slide 10 text | ✅ |
| "top-level" appears in Slide 8 speaker notes | ✅ |
| "top-level" appears in Slide 10 speaker notes | ✅ |
| "A16" appears in Slide A16 title | ✅ |
| No occurrence of "dry-run" / "dry run" / "DRY-RUN" anywhere in deck text or speaker notes | ✅ |
| All 12 figure PNGs embedded into the pptx (file size 1.8 MB) | ✅ |
| Page-number labels present on every slide | ✅ |

---

## What was *not* changed

- `outputs/finalist_rerun_results.json` and all `runs/finalist_qwen_*/` files — read-only, untouched
- The v2 pptx file (`outputs/DATA7901_Seminar_Sreehari_s4906751_v2.pptx`) — kept alongside v3 for reference
- The corrected status documented in `CLAUDE.md` and `UPDATED_REAL_GPU_RUN_AUDIT.md` — both still authoritative
- No new generation, no new metric runs, no overwrites of synced Rangpur outputs

---

## How to reproduce

```bash
# 1. Confirm all 12 figures are present
ls outputs/seminar_support/*.png

# 2. Build the v3 deck
python scripts/_seminar_build_pptx_v3.py
```

Build is idempotent and only writes to `outputs/DATA7901_Seminar_Sreehari_s4906751_v3_content_ready.pptx`.

---

## Final note

If you can drop a UQ `.pptx` template into the repo, `scripts/_seminar_build_pptx_v3.py` can be re-run against it in ~10 seconds to produce `outputs/DATA7901_Seminar_Sreehari_s4906751_v3_UQ_template.pptx` directly. Until then the manual paste described in `TEMPLATE_TRANSFER_FALLBACK_NOTES.md` is the cleanest finishing step.
