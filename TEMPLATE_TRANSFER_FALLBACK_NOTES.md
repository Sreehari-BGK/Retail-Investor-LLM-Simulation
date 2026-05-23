# Template transfer — fallback notes

**Date:** 2026-05-14
**File this concerns:** `outputs/DATA7901_Seminar_Sreehari_s4906751_v3_content_ready.pptx`

---

## What happened

You asked me to "use the uploaded UQ template PowerPoint as the design/theme base". The artefact you uploaded was the UQ "Working Remotely" deck **as a PDF** (`UQ-Working-Remotely.pdf`), not as a `.pptx` file.

`python-pptx` cannot use a PDF as a theme/master source. To transfer onto an actual UQ template, the build script needs the original `.pptx` (with its slide masters, layouts, fonts, and theme colours) to attach `Presentation(template_path)` against. That file wasn't provided.

Per **Part G** of your brief — *"If you cannot reliably apply the uploaded UQ template … do NOT waste time forcing it"* — I produced the content-ready fallback instead, approximating the UQ visual style by hand:

- UQ purple palette (`#512D6F`, with a `#B6258C` magenta accent strip on title/Thank-You slides)
- Thin purple header bar across the top of every content slide (matches the UQ template convention)
- Footer rule + page numbers + course label on every slide
- Calibri sans-serif throughout
- Light purple-tinted card backgrounds (`#F4F1F8`) so cards read as part of the UQ palette rather than vanilla grey
- No CRICOS code (you asked me to ignore it)
- No UQ logo image (I don't have the official asset on disk and won't substitute)

This deck is **content-final**. The remaining template step is a 1-minute manual swap in PowerPoint, described below.

---

## How to apply the real UQ template manually (~1 minute)

1. Open your UQ `.pptx` template in PowerPoint.
2. Open `outputs/DATA7901_Seminar_Sreehari_s4906751_v3_content_ready.pptx` in a second window.
3. In the v3 deck: `Home` → click any slide thumbnail → **Ctrl+A** to select all slides.
4. **Ctrl+C** to copy.
5. Switch to the UQ template deck. Click after its title slide.
6. **Right-click → Paste Options → "Use Destination Theme"** (or `Ctrl+Alt+V` → Keep Source Formatting if you want to preserve the cards/colours exactly).
7. The UQ master slides will now apply — title bars, fonts, page numbers, and the UQ logo will inherit automatically.
8. Save as `outputs/DATA7901_Seminar_Sreehari_s4906751_v3_UQ_template.pptx`.

**Watch-outs during the paste:**

- **Page numbers.** The v3 deck has manual text boxes at the bottom-right (`1 / 10`, `A1 / 16`, etc.) so they survive the paste. If you'd rather use the UQ master's automatic slide numbers, delete the manual boxes after pasting.
- **Embedded images.** All 12 figures are embedded as PNGs inside the .pptx, so they travel with the paste. No external file dependencies.
- **Speaker notes.** Notes are stored per-slide and copy through "Paste All Slides".
- **Charts.** There are no native PowerPoint charts in this deck — all charts are pre-rendered PNGs — so theme-colour bleed-through on charts is not a risk.

---

## Files ready for the manual swap

| File | Purpose |
|------|---------|
| `outputs/DATA7901_Seminar_Sreehari_s4906751_v3_content_ready.pptx` | The 27-slide content deck. Paste this into your UQ template. |
| `outputs/seminar_support/data_eda_slide_visual.png` | Slide 4 figure |
| `outputs/seminar_support/curation_flow.png` | Slide 5 + A4 figure |
| `outputs/seminar_support/model_io_prompt_visual.png` | Slide 6 + A8 figure |
| `outputs/seminar_support/metrics_plain_language.png` | Slide 7 figure |
| `outputs/seminar_support/content_results_dashboard.png` | Slide 8 figure |
| `outputs/seminar_support/temperature_tradeoff.png` | Slide 9 figure |
| `outputs/seminar_support/stance_rule_backup.png` | A9 figure |
| `outputs/seminar_support/grounding_rule_backup.png` | A10 figure |
| `outputs/seminar_support/timestamp_scheduler_backup.png` | A11 figure |
| `outputs/seminar_support/temperature_backup.png` | A12 figure |
| `outputs/seminar_support/top_level_grounding_comparison.png` | A16 figure |
| `outputs/seminar_support/SEMINAR_SPEAKER_NOTES_V2.md` | Per-slide speaker notes (v2 still valid; only Slides 8 + 10 + A16 differ — see speaker notes inside the pptx) |
| `outputs/seminar_support/top_level_vs_replies_robustness.md` | Q&A-ready paragraph for the A16 question |

---

## What is NOT in this fallback deck (but would be after template transfer)

- The official UQ logo (top-right of every slide on the real template)
- UQ-defined theme fonts (the real template may use a specific font family — Calibri is a safe Microsoft default)
- CRICOS code in the footer (you asked me to ignore this)
- The faint white wave/curve graphic on the bottom-right of UQ title slides

Everything else — slide content, page numbers, speaker notes, the 12 embedded figures, the colour palette, the deck structure — is final.

---

## If you'd rather I take a second pass with a real `.pptx`

If you can drop the actual `.pptx` template (any UQ-themed deck will do — even an empty one with the right masters), I can rerun `scripts/_seminar_build_pptx_v3.py` against that base by adding `Presentation('<path-to-template>.pptx')` as the start of the build. The 27 slides would then inherit the real UQ masters automatically, and you'd get `DATA7901_Seminar_Sreehari_s4906751_v3_UQ_template.pptx` directly. Estimated extra time: ~2 minutes to wire up, ~5 seconds to run.

For now, the manual paste described above is the cleanest finish.
