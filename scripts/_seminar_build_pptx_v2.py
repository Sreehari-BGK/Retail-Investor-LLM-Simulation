#!/usr/bin/env python3
"""Build DATA7901 seminar deck v2 — incorporates professor feedback.

Output: outputs/DATA7901_Seminar_Sreehari_s4906751_v2.pptx
  - 10 main content slides
  - 1 Thank You slide
  - 15 appendix slides (A1–A15)
"""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, 'outputs', 'seminar_support')
PS_FIG = os.path.join(ROOT, 'outputs', 'proposal_support')
OUT_PPTX = os.path.join(ROOT, 'outputs', 'DATA7901_Seminar_Sreehari_s4906751_v2.pptx')

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Palette
NAVY = RGBColor(0x1F, 0x4E, 0x79)
DARK = RGBColor(0x33, 0x33, 0x33)
GREY = RGBColor(0x7F, 0x7F, 0x7F)
ACCENT = RGBColor(0xC0, 0x00, 0x00)
GREEN = RGBColor(0x54, 0x82, 0x35)
AMBER = RGBColor(0xBF, 0x8F, 0x00)
LIGHT_BG = RGBColor(0xF2, 0xF2, 0xF2)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

BLANK = prs.slide_layouts[6]

# Total slide count (used by add_slide_number)
TOTAL_MAIN = 10
TOTAL_APP = 15

def add_textbox(slide, left, top, width, height, text, *,
                font_size=18, bold=False, color=DARK, align=PP_ALIGN.LEFT,
                anchor=MSO_ANCHOR.TOP, font='Calibri'):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.05); tf.margin_right = Inches(0.05)
    tf.margin_top = Inches(0.02); tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = anchor
    lines = text.split('\n') if isinstance(text, str) else text
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        run = p.add_run()
        run.text = ln
        run.font.name = font
        run.font.size = Pt(font_size)
        run.font.bold = bold
        run.font.color.rgb = color
    return tb

def add_bullets(slide, left, top, width, height, bullets, *,
                font_size=14, color=DARK, bullet_char='•', line_spacing=1.25):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, b in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.line_spacing = line_spacing
        run = p.add_run()
        run.text = f'{bullet_char}  {b}'
        run.font.name = 'Calibri'
        run.font.size = Pt(font_size)
        run.font.color.rgb = color
    return tb

def add_title_bar(slide, title, subtitle=None, fc=NAVY):
    stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.85))
    stripe.fill.solid(); stripe.fill.fore_color.rgb = fc
    stripe.line.fill.background()
    add_textbox(slide, Inches(0.5), Inches(0.13), Inches(12.5), Inches(0.55),
                title, font_size=24, bold=True, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
    if subtitle:
        add_textbox(slide, Inches(0.5), Inches(0.92), Inches(12.5), Inches(0.4),
                    subtitle, font_size=13, color=GREY)

def add_slide_footer(slide, n_label):
    """n_label like '1 / 10' for main or 'A1 / 15' for appendix."""
    add_textbox(slide, Inches(12.4), Inches(7.05), Inches(0.8), Inches(0.35),
                n_label, font_size=10, color=GREY, align=PP_ALIGN.RIGHT)
    add_textbox(slide, Inches(0.4), Inches(7.05), Inches(11.0), Inches(0.35),
                'Simulating Retail-Investor Discussion with LLM Agents — '
                'Sreehari Biji Kumar (s4906751)',
                font_size=10, color=GREY)

def add_notes(slide, text):
    notes = slide.notes_slide
    notes.notes_text_frame.text = text

def add_picture_fit(slide, path, left, top, width=None, height=None):
    if width and height:
        slide.shapes.add_picture(path, left, top, width=width, height=height)
    elif width:
        slide.shapes.add_picture(path, left, top, width=width)
    elif height:
        slide.shapes.add_picture(path, left, top, height=height)
    else:
        slide.shapes.add_picture(path, left, top)

def add_table(slide, left, top, width, height, data, *,
              header_fill=NAVY, header_color=WHITE, body_color=DARK,
              first_col_bold=False, font_size=11, col_widths_in=None):
    rows = len(data); cols = len(data[0])
    tbl_shape = slide.shapes.add_table(rows, cols, left, top, width, height)
    tbl = tbl_shape.table
    if col_widths_in:
        for i, w_in in enumerate(col_widths_in):
            tbl.columns[i].width = Inches(w_in)
    for r_idx, row in enumerate(data):
        for c_idx, val in enumerate(row):
            cell = tbl.cell(r_idx, c_idx)
            cell.text = ''
            tf = cell.text_frame
            tf.margin_left = Inches(0.06); tf.margin_right = Inches(0.06)
            tf.margin_top = Inches(0.03); tf.margin_bottom = Inches(0.03)
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if c_idx == 0 else PP_ALIGN.CENTER
            run = p.add_run(); run.text = str(val)
            run.font.name = 'Calibri'; run.font.size = Pt(font_size)
            if r_idx == 0:
                cell.fill.solid(); cell.fill.fore_color.rgb = header_fill
                run.font.color.rgb = header_color
                run.font.bold = True
            else:
                cell.fill.solid(); cell.fill.fore_color.rgb = WHITE if r_idx % 2 == 1 else LIGHT_BG
                run.font.color.rgb = body_color
                if first_col_bold and c_idx == 0:
                    run.font.bold = True
    return tbl

def add_card(slide, left, top, width, height, title, body, *,
             title_color=NAVY, border=NAVY, fc=WHITE, title_size=14, body_size=11):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    box.fill.solid(); box.fill.fore_color.rgb = fc
    box.line.color.rgb = border; box.line.width = Pt(1.2)
    add_textbox(slide, left + Inches(0.15), top + Inches(0.12),
                width - Inches(0.3), Inches(0.5),
                title, font_size=title_size, bold=True, color=title_color)
    add_textbox(slide, left + Inches(0.15), top + Inches(0.65),
                width - Inches(0.3), height - Inches(0.75),
                body, font_size=body_size, color=DARK)

def add_message_strip(slide, top_in, text):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                 Inches(0), Inches(top_in), prs.slide_width, Inches(0.55))
    bar.fill.solid(); bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()
    add_textbox(slide, Inches(0.4), Inches(top_in+0.07), Inches(12.5), Inches(0.42),
                text, font_size=14, bold=True, color=WHITE,
                align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# =====================================================================
# SLIDE 1 — Need / problem importance
# =====================================================================
s = prs.slides.add_slide(BLANK)
# Title block (cover-style)
top = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(3.6))
top.fill.solid(); top.fill.fore_color.rgb = NAVY; top.line.fill.background()
add_textbox(s, Inches(0.7), Inches(0.5), Inches(12), Inches(0.4),
            'DATA7901  •  Data Science Capstone Project 1', font_size=14, color=WHITE)
add_textbox(s, Inches(0.7), Inches(1.1), Inches(12), Inches(1.7),
            'Can LLMs simulate investor reaction,\nor just sound like they can?',
            font_size=38, bold=True, color=WHITE)
add_textbox(s, Inches(0.7), Inches(3.0), Inches(12), Inches(0.5),
            'Sreehari Biji Kumar  •  s4906751  •  Master of Data Science  •  UQ',
            font_size=14, color=WHITE)

# Bottom: comment example + four cards
add_card(s, Inches(0.6), Inches(4.0), Inches(5.6), Inches(2.7),
         'A fluent LLM-generated comment',
         '"so glad we have a 62% jump in just one quarter, '
         "but I'm still wondering how Jensen will push it when the\n"
         'blackwell ramp actually hits the ground running…"\n\n'
         'Reads human. But does the corpus behave like real Reddit?',
         title_color=NAVY, border=NAVY, fc=LIGHT_BG, body_size=12)

# 4 small cards
add_textbox(s, Inches(6.6), Inches(4.0), Inches(6.5), Inches(0.4),
            'Four things one fluent comment cannot guarantee:',
            font_size=13, bold=True, color=NAVY)
def mini(left, top, label, body):
    add_card(s, left, top, Inches(3.1), Inches(1.0),
             label, body, title_color=NAVY, body_size=10, title_size=12)
mini(Inches(6.6), Inches(4.45), 'Mood mix', 'right bullish/bearish/neutral balance?')
mini(Inches(9.85), Inches(4.45), 'Meaning spread', 'same content space as real Reddit?')
mini(Inches(6.6), Inches(5.55), 'Fact-mention rate', 'right amount of fact restating?')
mini(Inches(9.85), Inches(5.55), 'Timing pattern', 'right when-in-window?')

add_message_strip(s, 6.85, 'LLMs can write comments that sound human. Simulation needs validation.')
add_slide_footer(s, '1 / 10')
add_notes(s,
"Open quickly. The question on the slide is the project in one sentence. "
"Below, a real generated comment that reads fluent. The point: fluency at the comment level "
"says nothing about whether the crowd behaves the right way. Four properties — mood mix, meaning spread, "
"fact-mention rate, timing — none of which a single fluent comment can guarantee. "
"(40 seconds.)")

# =====================================================================
# SLIDE 2 — Task / exact research question
# =====================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'The research question', 'Need → Task')

# Big question card
qbox = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                          Inches(0.7), Inches(1.55), Inches(11.9), Inches(2.0))
qbox.fill.solid(); qbox.fill.fore_color.rgb = LIGHT_BG
qbox.line.color.rgb = NAVY; qbox.line.width = Pt(1.5)
add_textbox(s, Inches(1.0), Inches(1.75), Inches(11.3), Inches(1.6),
            '"If real investors and simulated agents see the same earnings shock,\n'
            'how closely does the resulting Reddit discussion match?"',
            font_size=22, bold=True, color=NAVY,
            anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)

# Three event cards
def event_card(left, label, role, role_color):
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                             left, Inches(4.0), Inches(4.0), Inches(2.0))
    box.fill.solid(); box.fill.fore_color.rgb = WHITE
    box.line.color.rgb = role_color; box.line.width = Pt(1.8)
    add_textbox(s, left + Inches(0.2), Inches(4.15), Inches(3.6), Inches(0.5),
                label, font_size=18, bold=True, color=NAVY)
    pill = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                              left + Inches(0.2), Inches(4.7),
                              Inches(3.6), Inches(0.5))
    pill.fill.solid(); pill.fill.fore_color.rgb = role_color
    pill.line.fill.background()
    add_textbox(s, left + Inches(0.2), Inches(4.7), Inches(3.6), Inches(0.5),
                role, font_size=12, bold=True, color=WHITE,
                anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
event_card(Inches(0.65), 'NVDA Q3 FY26', 'PRIMARY', NAVY)
event_card(Inches(4.75), 'AAPL Q4 FY25', 'SECONDARY', GREY)
event_card(Inches(8.85), 'META Q3 2025', 'EXPLORATORY', AMBER)

# Sub-text under each
add_textbox(s, Inches(0.65), Inches(5.4), Inches(4.0), Inches(0.5),
            '2403 curated comments', font_size=11, color=DARK, align=PP_ALIGN.CENTER)
add_textbox(s, Inches(4.75), Inches(5.4), Inches(4.0), Inches(0.5),
            '383 curated  ·  cross-event check', font_size=11, color=DARK, align=PP_ALIGN.CENTER)
add_textbox(s, Inches(8.85), Inches(5.4), Inches(4.0), Inches(0.5),
            '344 curated  ·  stress-test only', font_size=11, color=DARK, align=PP_ALIGN.CENTER)

add_message_strip(s, 6.55, 'Same event. Real Reddit crowd vs simulated crowd.')
add_slide_footer(s, '2 / 10')
add_notes(s,
"This is the project in one sentence. NVDA is our depth case — the largest and cleanest. "
"AAPL is small but clean; it'll serve as a cross-event check. "
"META is heavily contaminated — useful as a stress-test only. "
"The whole study is comparing two crowds reacting to the same shock. (45 seconds.)")

# =====================================================================
# SLIDE 3 — Real-world example
# =====================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'Real-world example: NVDA Q3 earnings on Reddit',
              'Real-world hook')

# Thread metadata card
add_card(s, Inches(0.5), Inches(1.55), Inches(6.3), Inches(2.4),
         'Thread r/stocks · 1p1ked6',
         '"NVDA Quarterly Revenue $57 billion (up 62% YoY)"\n\n'
         'Subreddit:  r/stocks\n'
         'Comments:  227  (all retained in curated corpus)\n'
         'URL:  https://www.reddit.com/r/stocks/comments/1p1ked6/',
         title_color=NAVY, border=NAVY, body_size=12)

# Screenshot placeholder
ph = s.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                        Inches(7.0), Inches(1.55), Inches(5.9), Inches(4.0))
ph.fill.solid(); ph.fill.fore_color.rgb = LIGHT_BG
ph.line.color.rgb = GREY; ph.line.width = Pt(2.0)
add_textbox(s, Inches(7.0), Inches(1.55), Inches(5.9), Inches(4.0),
            'Insert Reddit screenshot here', font_size=15, bold=True,
            color=GREY, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# Why this thread + alternative
add_textbox(s, Inches(0.5), Inches(4.1), Inches(6.3), Inches(0.45),
            'Why this thread', font_size=14, bold=True, color=NAVY)
add_bullets(s, Inches(0.5), Inches(4.5), Inches(6.3), Inches(2.0),
            ['Title mirrors what the LLM sees in its event card',
             'Mid-size discussion — readable on one slide',
             'Mix of analytical and reactive comments'],
            font_size=12)

# Alt thread note
alt = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                          Inches(7.0), Inches(5.7), Inches(5.9), Inches(0.8))
alt.fill.solid(); alt.fill.fore_color.rgb = LIGHT_BG
alt.line.color.rgb = GREY; alt.line.width = Pt(0.8)
add_textbox(s, Inches(7.15), Inches(5.78), Inches(5.7), Inches(0.7),
            'Alternative (appendix A1):  r/wallstreetbets · 1p1kake\n'
            '"Nvidia Beat Earnings And Raise Guidance, as usual"  (294 comments)',
            font_size=11, color=DARK)

add_message_strip(s, 6.8, 'This is the kind of crowd we want the simulator to resemble.')
add_slide_footer(s, '3 / 10')
add_notes(s,
"A concrete example so the audience has something to picture. "
"Thread 1p1ked6 — the title alone matches the LLM event card almost word for word. "
"227 comments, all retained. If you want a more colourful WSB example, A1 in the appendix has 1p1kake. "
"(45 seconds.)")

# =====================================================================
# SLIDE 4 — Data + EDA: what the Reddit data looks like
# =====================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'What the collected Reddit data looks like',
              'Data + exploratory analysis')

s.shapes.add_picture(os.path.join(FIG, 'data_eda_slide_visual.png'),
                     Inches(0.4), Inches(1.05), width=Inches(12.5))

add_message_strip(s, 6.85, 'Public Reddit comments, time-aligned to each earnings release.')
add_slide_footer(s, '4 / 10')
add_notes(s,
"Direct answer to professor feedback: what does the data look like? "
"r/stocks and r/wallstreetbets, -24h to +48h window, one comment per row, "
"with the schema fields you'd expect — text, timestamp, hours-from-event, subreddit, thread/comment IDs, score, depth. "
"Quick EDA: raw vs curated bars on the left, NVDA temporal histogram on the right showing post-event clustering. "
"(65 seconds.)")

# =====================================================================
# SLIDE 5 — Curation / reference corpus
# =====================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'From raw collection to diagnostic reference corpus',
              'How the comparison set is built')

s.shapes.add_picture(os.path.join(FIG, 'curation_flow.png'),
                     Inches(0.4), Inches(1.05), width=Inches(12.5))

# retention cards
def ret_card(left, label, raw, cur, pct, color):
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                             left, Inches(5.4), Inches(4.0), Inches(1.3))
    box.fill.solid(); box.fill.fore_color.rgb = WHITE
    box.line.color.rgb = color; box.line.width = Pt(1.5)
    add_textbox(s, left + Inches(0.15), Inches(5.45), Inches(3.7), Inches(0.4),
                label, font_size=13, bold=True, color=NAVY)
    add_textbox(s, left + Inches(0.15), Inches(5.85), Inches(3.7), Inches(0.4),
                f'{raw} raw → {cur} curated', font_size=12, color=DARK)
    add_textbox(s, left + Inches(0.15), Inches(6.25), Inches(3.7), Inches(0.45),
                f'Retention: {pct}', font_size=13, bold=True, color=color)
ret_card(Inches(0.55), 'NVDA Q3 FY26', '2641', '2403', '91%', NAVY)
ret_card(Inches(4.65), 'AAPL Q4 FY25', '392', '383', '98%', GREEN)
ret_card(Inches(8.75), 'META Q3 2025', '1444', '344', '24%', AMBER)

add_slide_footer(s, '5 / 10')
add_notes(s,
"Curation is manual at the thread level. PRAW collects everything; I read titles and decide relevant, marginal, or remove. "
"NVDA keeps 91%, AAPL 98%, META only 24% because of wrong-company contamination. "
"That's why we use the phrase 'diagnostic reference corpus' — not yet a benchmark; that needs more events and stronger instruments. "
"(55 seconds.)")

# =====================================================================
# SLIDE 6 — Model setup
# =====================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'Model setup — input, prompt, output',
              'Input → Qwen → output')

s.shapes.add_picture(os.path.join(FIG, 'model_io_prompt_visual.png'),
                     Inches(0.3), Inches(0.95), width=Inches(12.7))

add_message_strip(s, 6.85, 'Each run produces 108 comments. 14 finalist runs total.')
add_slide_footer(s, '6 / 10')
add_notes(s,
"Direct answer to professor feedback on the model description. "
"Inputs: event card (the earnings summary), persona, prompt (P0/P1/P2), and temperature. "
"Output: one simulated Reddit-style comment per call, 108 per run. "
"The strip at the bottom names the best run and the headline metrics so the audience sees where the story is going. "
"(60 seconds.)")

# =====================================================================
# SLIDE 7 — Evaluation checks in plain English
# =====================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'Evaluation checks in plain English',
              'Three headline diagnostics, one secondary')

s.shapes.add_picture(os.path.join(FIG, 'metrics_plain_language.png'),
                     Inches(0.35), Inches(1.05), width=Inches(12.6))

add_message_strip(s, 6.85, 'Reported separately. Collapsing them would hide the trade-offs that matter.')
add_slide_footer(s, '7 / 10')
add_notes(s,
"Four checks, plain-English first. Meaning spread, fact-mention rate, mood mix are the headline diagnostics. "
"Timing is secondary because the LLM never sees the timestamp — the scheduler does that — so timing measures the scheduler, not the model. "
"That's covered in detail in appendix A11. (55 seconds.)")

# =====================================================================
# SLIDE 8 — Main result
# =====================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'Main result: behaviour-first prompting helps, but over-grounding remains',
              'Headline n = 108 finding')

s.shapes.add_picture(os.path.join(FIG, 'content_results_dashboard.png'),
                     Inches(0.3), Inches(1.05), width=Inches(12.7))

add_message_strip(s, 6.85, 'The model sounds closer, but still behaves too much like an analyst.')
add_slide_footer(s, '8 / 10')
add_notes(s,
"Headline. Best run is Qwen3.5-2B with the behaviour-first prompt at temperature 1.1. "
"MMD 0.0653, JSD 0.4062. Meaningfully better than the template baseline at 0.148. "
"But — and this is the honest framing — real Reddit users mention earnings facts 2.5% of the time. "
"The best LLM does so 57.4% of the time. About 22 times too often. "
"The simulator is becoming semantically closer, but still behaves like an analyst note rather than a real investor. (70 seconds.)")

# =====================================================================
# SLIDE 9 — Temperature trade-off
# =====================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'The temperature trade-off',
              'Higher temperature improves meaning, reduces fact-mention — but does not reach real Reddit')

s.shapes.add_picture(os.path.join(FIG, 'temperature_tradeoff.png'),
                     Inches(0.3), Inches(1.05), width=Inches(12.7))

add_message_strip(s, 6.85, 'Higher τ moves both metrics in the right direction. Real Reddit grounding is still far below.')
add_slide_footer(s, '9 / 10')
add_notes(s,
"Within the semantic-first block, as temperature goes up, two things happen: meaning-spread improves, and fact-mention rate drops. "
"The dial is doing real work. But even at τ=1.1, grounding is 57% — about 22× the real 2.5%. "
"So temperature is a partial knob, not a fix. (55 seconds.)")

# =====================================================================
# SLIDE 10 — Meaning, limitations, next test
# =====================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'What this means, limitations, and next test',
              'Conclusion')

# Three-column structure
def col(left, header, header_color, items):
    add_textbox(s, left, Inches(1.3), Inches(4.2), Inches(0.5),
                header, font_size=15, bold=True, color=header_color)
    add_bullets(s, left, Inches(1.85), Inches(4.2), Inches(4.6), items,
                font_size=12)

col(Inches(0.4), 'What it means', NAVY, [
    'Prompting can make the model sound more Reddit-like',
    'But it still over-explains, like an analyst',
    'Yardstick for any future, richer simulator'
])
col(Inches(4.65), 'Honest limitations', AMBER, [
    'One-shot, persona-only agents',
    'Timing is scheduler-driven',
    'Stance labeler is noisy (κ = 0.45)',
    'One main event (NVDA)',
])
col(Inches(8.95), 'Focused next test', GREEN, [
    'History-conditioned generation:',
    '   feed behavioural examples',
    '   instead of only persona labels',
    'AAPL transfer as robustness check'
])

# Bottom callout
add_message_strip(s, 6.55,
                  'Contribution: a diagnostic protocol — not a solved simulator.')
add_slide_footer(s, '10 / 10')
add_notes(s,
"Closing. Three columns. What it means in plain English: model is closer, still analyst-flavoured. "
"Honest limitations stated up front. Then one named next experiment — history-conditioned generation — "
"is the concrete falsifiable next step, not vague 'future work'. "
"AAPL transfer is robustness, not headline. (55 seconds.)")

# =====================================================================
# THANK YOU slide
# =====================================================================
s = prs.slides.add_slide(BLANK)
top = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(2.6))
top.fill.solid(); top.fill.fore_color.rgb = NAVY; top.line.fill.background()
add_textbox(s, Inches(0.7), Inches(0.7), Inches(12), Inches(1.0),
            'Thank you', font_size=46, bold=True, color=WHITE)
add_textbox(s, Inches(0.7), Inches(1.8), Inches(12), Inches(0.5),
            'Questions?', font_size=22, color=WHITE)

# Mini appendix TOC
add_textbox(s, Inches(0.5), Inches(2.85), Inches(12.3), Inches(0.4),
            'Backup slides — index for Q&A', font_size=14, bold=True, color=NAVY)
toc_items = [
    'A1  Reddit threads (NVDA)',
    'A2  Reddit threads (AAPL & META)',
    'A3  Data schema / columns',
    'A4  Curation decision logic',
    'A5  Exact event card text',
    'A6  Prompt conditions P0 / P1 / P2',
    'A7  Personas / cohorts V0 / V1',
    'A8  Model input–output example',
    'A9  Stance classifier rule',
    'A10  Grounding classifier rule',
    'A11  Timestamp scheduler',
    'A12  Temperature explanation',
    'A13  Full 14-run finalist table',
    'A14  Metric formulas + caveats',
    'A15  Literature anchors',
]
# Two columns
for i, t in enumerate(toc_items):
    col = i % 3
    row = i // 3
    add_textbox(s, Inches(0.5 + col * 4.3), Inches(3.4 + row * 0.5),
                Inches(4.2), Inches(0.45),
                t, font_size=11, color=DARK)

add_slide_footer(s, 'Thank You')
add_notes(s,
"Thanks — happy to take questions. Backup slides A1 through A15 cover every technical detail; "
"I can jump to any of them directly.")

# =====================================================================
# APPENDIX SLIDES
# =====================================================================
def appendix_slide(title, subtitle=None):
    s_ = prs.slides.add_slide(BLANK)
    add_title_bar(s_, title, subtitle, fc=DARK)
    return s_

# ---- A1: NVDA threads ----
s = appendix_slide('A1 — Reddit threads used (NVDA Q3 FY26)',
                   '13 raw threads → 9 retained (6 relevant + 3 marginal) → 4 removed')
data = [
    ['Decision', 'Thread', 'Subreddit', 'Raw', 'Curated', 'Title'],
    ['relevant', '1p1gh2w', 'wallstreetbets', '417', '417', 'NVIDIA Q3 2026 Earnings Call · Live Transcript'],
    ['relevant', '1p1kd0p', 'stocks', '411', '411', 'Nvidia shares rise on stronger than expected revenue'],
    ['relevant', '1p1kake', 'wallstreetbets', '294', '294', 'Nvidia Beat Earnings And Raise Guidance, as usual'],
    ['relevant', '1p1ked6', 'stocks', '227', '227', 'NVDA Quarterly Revenue $57 billion (up 62% YoY)'],
    ['relevant', '1p1k9ic', 'wallstreetbets', '189', '189', 'NVDA Earnings with the Double Beat'],
    ['relevant', '1p1pyaw', 'stocks', '93', '93', "Burry's Tweets: Week of Nvidia Q3 Earnings"],
    ['marginal', '1p1jbwk', 'wallstreetbets', '396', '396', 'Fork in the road'],
    ['marginal', '1p1no2c', 'wallstreetbets', '287', '287', 'Why the "bubble" narrative is missing the point'],
    ['marginal', '1p37j7u', 'wallstreetbets', '89', '89', 'Trump team floats selling Nvidia H200 chips to China'],
    ['remove', '1p2fpnz', 'wallstreetbets', '211', '0', 'Fixed that meme from earlier'],
    ['remove', '1p36q7u', 'wallstreetbets', '14', '0', 'Anatomy of a tenbagger (general thesis)'],
    ['remove', '1p1zbmk', 'wallstreetbets', '12', '0', '(WMT) Walmart Q3 2026 Earnings Call'],
    ['remove', '1p13lj6', 'wallstreetbets', '1', '0', '(TGT) Target Q3 2026 Earnings Call'],
]
add_table(s, Inches(0.4), Inches(1.4), Inches(12.5), Inches(5.4), data,
          font_size=10, first_col_bold=True,
          col_widths_in=[1.0, 1.0, 1.6, 0.7, 0.8, 7.4])
add_slide_footer(s, 'A1 / 15')
add_notes(s, 'NVDA threads list. Source: outputs/seminar_support/exact_reddit_threads_all_events.md')

# ---- A2: AAPL + META threads ----
s = appendix_slide('A2 — Reddit threads (AAPL & META)',
                   'AAPL: 4 raw → 3 retained, 1 removed.  META: 15 raw → 4 retained, 11 removed.')

# AAPL table
add_textbox(s, Inches(0.4), Inches(1.4), Inches(6), Inches(0.4),
            'AAPL Q4 FY25', font_size=13, bold=True, color=NAVY)
aapl = [
    ['Decision', 'Thread', 'Raw', 'Curated', 'Title'],
    ['relevant', '1okb9l1', '74', '74', 'Apple earnings strong beat and ecosystem domination'],
    ['marginal', '1okpz3y', '293', '293', 'r/Stocks Daily Discussion · Oct 31'],
    ['marginal', '1ojkjhb', '16', '16', 'Apple to split in 2026?'],
    ['remove', '1oky7mz', '9', '0', 'Seagate: -7.60%, why??'],
]
add_table(s, Inches(0.4), Inches(1.85), Inches(6.0), Inches(2.2), aapl,
          font_size=9, first_col_bold=True,
          col_widths_in=[0.95, 0.95, 0.55, 0.7, 2.85])

# META table - retained only + summary of removed
add_textbox(s, Inches(6.9), Inches(1.4), Inches(6), Inches(0.4),
            'META Q3 2025 — retained', font_size=13, bold=True, color=NAVY)
meta_keep = [
    ['Decision', 'Thread', 'Raw/Cur', 'Title'],
    ['relevant', '1ojfjyr', '129', 'Meta reports earnings, tax charge'],
    ['relevant', '1ojfizn', '123', 'Meta stock sinks after tax hit'],
    ['relevant', '1ojvqv2', '54', 'Devaluation of Deferred Tax Assets'],
    ['relevant', '1ojqk3q', '38', 'What is this Meta tax issue?'],
]
add_table(s, Inches(6.9), Inches(1.85), Inches(6.0), Inches(2.2), meta_keep,
          font_size=9, first_col_bold=True,
          col_widths_in=[0.95, 0.95, 0.8, 3.3])

# META removed summary
add_textbox(s, Inches(0.4), Inches(4.3), Inches(12.5), Inches(0.4),
            'META Q3 2025 — removed (11 threads, dominantly wrong-company contamination)',
            font_size=13, bold=True, color=ACCENT)
add_bullets(s, Inches(0.4), Inches(4.75), Inches(12.5), Inches(2.2), [
    'GOOG · Alphabet $100B quarterly revenue  (1ojf9mj, 297 comments)',
    'RDDT · Reddit teen-survey + Reddit Q3 earnings beat  (1oko5wp 251, 1okaep4 174, 1okar62 77)',
    'CMG · Chipotle same-store sales forecast cut  (1ojfcc2, 169)',
    'NOW · ServiceNow earnings + 5-for-1 split  (1ojffro, 18)',
    'AMZN · "Thank you $AMZN"  (1okbxi0, 22)',
    'KVUE · Kenvue split-off  (1okx9vg, 35)',
    'MSFT · Microsoft earnings  (1ojag2j, 27)',
    'AAPL · stock-split speculation  (1ojkjhb, 16)',
    'LITE · Lumentum NVDA-supplier post  (1ojdtli, 14)',
], font_size=11)
add_slide_footer(s, 'A2 / 15')
add_notes(s, 'AAPL + META threads. META loses 76% to wrong-company contamination.')

# ---- A3: Data schema ----
s = appendix_slide('A3 — Data schema (columns stored per comment)',
                   'From 01_collect_reddit.py and the raw + curated CSVs')
schema = [
    ['Column', 'Type', 'Notes'],
    ['event_id', 'str', 'e.g. NVDA_Q3FY26'],
    ['ticker', 'str', 'NVDA / AAPL / META'],
    ['event_time', 'str', 'ISO-8601 UTC earnings release time'],
    ['subreddit', 'str', 'stocks or wallstreetbets'],
    ['thread_id', 'str', 'Reddit post ID; permalink = reddit.com/r/{sub}/comments/{id}/'],
    ['comment_id', 'str', 'unique per comment (equal to thread_id for the post itself)'],
    ['parent_id', 'str', 'thread_id if top-level reply, else parent comment id'],
    ['timestamp', 'str', 'comment posted time, UTC'],
    ['hours_from_event', 'float', '(comment_time − event_time) in hours; signed'],
    ['text', 'str', 'comment body (or post title + selftext for the post row)'],
    ['score', 'int', 'Reddit upvotes'],
    ['depth', 'int', 'reply depth (0 = top level)'],
    ['source_type', 'str', '"real" for collected; "sim_agent" for generated'],
    ['stance', 'str', '"bullish" / "bearish" / "neutral" (added by labeler)'],
    ['relevance', 'str', '"relevant" / "marginal" (added by curation; "remove" rows are dropped)'],
]
add_table(s, Inches(0.4), Inches(1.3), Inches(12.5), Inches(5.5), schema,
          font_size=10, first_col_bold=True,
          col_widths_in=[2.0, 1.0, 9.5])
add_textbox(s, Inches(0.4), Inches(6.85), Inches(12.5), Inches(0.4),
            'No usernames or user IDs are collected or stored anywhere in the pipeline.',
            font_size=11, color=ACCENT, bold=True, align=PP_ALIGN.CENTER)
add_slide_footer(s, 'A3 / 15')
add_notes(s, 'Schema. Useful when a marker asks "what exactly is in the corpus?"')

# ---- A4: Curation decision logic ----
s = appendix_slide('A4 — Curation decision logic',
                   'Manual at thread level; documented as a committed Python list')
s.shapes.add_picture(os.path.join(FIG, 'curation_flow.png'),
                     Inches(0.4), Inches(1.2), width=Inches(12.5))
add_bullets(s, Inches(0.4), Inches(5.2), Inches(12.5), Inches(1.8), [
    'Rule 1: Wrong company → remove (e.g. Alphabet thread inside the META window).',
    'Rule 2: Clearly off-topic → remove (memes, generic thesis posts).',
    'Rule 3: Company-adjacent but not earnings-focused → marginal (kept).',
    'Rule 4: Mixed-content megathreads → marginal (kept).',
], font_size=12)
add_slide_footer(s, 'A4 / 15')

# ---- A5: Exact event card ----
s = appendix_slide('A5 — Exact event card given to the LLM',
                   'Verbatim from 13_prompt_condition_experiment.py')
ev_box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                            Inches(0.5), Inches(1.4), Inches(12.3), Inches(4.5))
ev_box.fill.solid(); ev_box.fill.fore_color.rgb = LIGHT_BG
ev_box.line.color.rgb = NAVY; ev_box.line.width = Pt(1.2)
add_textbox(s, Inches(0.8), Inches(1.6), Inches(11.8), Inches(4.1),
            '"NVIDIA reported Q3 FY2026 revenue of $57 billion, up 62% year-over-year, '
            'driven by strong data center demand and the Blackwell GPU production ramp. '
            'The company beat analyst expectations on both revenue and earnings per share. '
            'CEO Jensen Huang raised guidance for Q4, citing continued AI infrastructure demand. '
            'The stock had a mixed after-hours reaction despite the beat."',
            font_size=16, color=DARK, anchor=MSO_ANCHOR.MIDDLE)
add_textbox(s, Inches(0.5), Inches(6.1), Inches(12.5), Inches(0.5),
            'Same event card across all 14 finalist runs. No Reddit text used as exemplar.',
            font_size=12, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
add_slide_footer(s, 'A5 / 15')

# ---- A6: Prompt conditions ----
s = appendix_slide('A6 — Prompt conditions P0 / P1 / P2',
                   'Three system-prompt variants over the same event card')
prompts = [
    ('P0 — baseline fact-heavy', NAVY,
     '"You are simulating a retail investor… Use casual Reddit language. '
     'Reference specific facts from the earnings when relevant to your persona. '
     'Do NOT write disclaimers or break character."'),
    ('P1 — balanced retail reaction', GREY,
     '"React like a person, not like a financial report. '
     'You may be bullish, bearish, neutral, or unsure. '
     'Do not over-explain. Do not sound like an analyst note. '
     'Avoid always sounding optimistic."'),
    ('P2 — behaviour-first + diversity', GREEN,
     '"Reflect this user\'s behaviour, priorities, and time horizon more than perfect '
     'factual coverage. It should not read like a clean earnings summary. '
     'Do not make every comment sound rational, complete, or polished."'),
]
y = 1.3
for title, col, body in prompts:
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                             Inches(0.4), Inches(y), Inches(12.5), Inches(1.7))
    box.fill.solid(); box.fill.fore_color.rgb = WHITE
    box.line.color.rgb = col; box.line.width = Pt(1.5)
    add_textbox(s, Inches(0.55), Inches(y+0.1), Inches(12.2), Inches(0.45),
                title, font_size=14, bold=True, color=col)
    add_textbox(s, Inches(0.55), Inches(y+0.55), Inches(12.2), Inches(1.1),
                body, font_size=12, color=DARK)
    y += 1.85
add_slide_footer(s, 'A6 / 15')

# ---- A7: Personas V0 / V1 ----
s = appendix_slide('A7 — Personas / cohorts: V0 (9 archetypes) and V1 (3 broad cohorts)',
                   None)

# Left column: V0
add_textbox(s, Inches(0.5), Inches(1.3), Inches(6.0), Inches(0.5),
            'V0 — 9 archetypes (3 cohorts × 3 subtypes)',
            font_size=14, bold=True, color=NAVY)
v0 = [
    ('Long-horizon', ['valuation-focused', 'fundamentals-focused', 'buy-the-dip']),
    ('Short-horizon', ['momentum-following', 'event-reactive', 'profit-taking']),
    ('Info-seeking', ['uncertain', 'evidence-seeking', 'wait-and-see']),
]
y = 1.85
for cohort, subs in v0:
    add_textbox(s, Inches(0.5), Inches(y), Inches(6.0), Inches(0.4),
                cohort, font_size=12, bold=True, color=NAVY)
    add_textbox(s, Inches(0.7), Inches(y+0.4), Inches(5.7), Inches(0.7),
                '  •  '.join(subs), font_size=11, color=DARK)
    y += 1.05

# Right column: V1
add_textbox(s, Inches(7.0), Inches(1.3), Inches(6.0), Inches(0.5),
            'V1 — 3 broad cohorts (behaviour-first)',
            font_size=14, bold=True, color=GREEN)
v1 = [
    ('long_horizon', 'Thinks in years, not days. Cares about quality and competitive position.'),
    ('short_horizon', 'Focused on near-term action: momentum, beats/misses, AH moves.'),
    ('information_seeking', 'Unsure, wants more data, expresses uncertainty.'),
]
y = 1.85
for arch, desc in v1:
    add_textbox(s, Inches(7.0), Inches(y), Inches(6.0), Inches(0.4),
                arch, font_size=12, bold=True, color=GREEN)
    add_textbox(s, Inches(7.0), Inches(y+0.4), Inches(6.0), Inches(0.7),
                desc, font_size=11, color=DARK)
    y += 1.05

add_textbox(s, Inches(0.5), Inches(6.5), Inches(12.5), Inches(0.4),
            'V0 pairs with P0 / P1; V1 pairs with P2.   Same archetype list across all events.',
            font_size=11, color=GREY, align=PP_ALIGN.CENTER, bold=True)
add_slide_footer(s, 'A7 / 15')

# ---- A8: Model I/O example ----
s = appendix_slide('A8 — Model input → output (single call)',
                   'One generation call · best-run config')
s.shapes.add_picture(os.path.join(FIG, 'model_io_prompt_visual.png'),
                     Inches(0.3), Inches(1.2), width=Inches(12.7))
add_slide_footer(s, 'A8 / 15')

# ---- A9: Stance classifier ----
s = appendix_slide('A9 — Stance classifier rule',
                   'Rule-based; same labeler on real and simulated comments')
s.shapes.add_picture(os.path.join(FIG, 'stance_rule_backup.png'),
                     Inches(1.0), Inches(1.1), width=Inches(11.3))
add_slide_footer(s, 'A9 / 15')

# ---- A10: Grounding rule ----
s = appendix_slide('A10 — Grounding (fact-mention) rule',
                   'Six keyword categories, threshold over hits')
s.shapes.add_picture(os.path.join(FIG, 'grounding_rule_backup.png'),
                     Inches(1.0), Inches(1.1), width=Inches(11.3))
add_slide_footer(s, 'A10 / 15')

# ---- A11: Timestamp scheduler ----
s = appendix_slide('A11 — Timestamp scheduler',
                   'Why Wasserstein is a scheduler diagnostic, not an LLM metric')
s.shapes.add_picture(os.path.join(FIG, 'timestamp_scheduler_backup.png'),
                     Inches(1.0), Inches(1.1), width=Inches(11.3))
add_slide_footer(s, 'A11 / 15')

# ---- A12: Temperature ----
s = appendix_slide('A12 — Temperature explained',
                   'Sampling randomness knob')
s.shapes.add_picture(os.path.join(FIG, 'temperature_backup.png'),
                     Inches(1.0), Inches(1.1), width=Inches(11.3))
add_slide_footer(s, 'A12 / 15')

# ---- A13: Full 14-run table ----
s = appendix_slide('A13 — Full 14-run finalist results',
                   'n = 108 per run · sorted by MMD ascending (best = top)')
runs = [
    ['#', 'Model', 'Prompt', 'τ', 'Seed', 'JSD', 'Wass', 'MMD', 'Gnd%'],
    ['1', 'Qwen3.5-2B', 'P2_V1', '1.1', '123', '0.4062', '3.13', '0.0653', '57.4'],
    ['2', 'Qwen3.5-2B', 'P2_V1', '1.1', '42',  '0.4069', '3.06', '0.0684', '64.8'],
    ['3', 'Qwen3.5-2B', 'P2_V1', '0.9', '123', '0.4400', '3.13', '0.0783', '71.3'],
    ['4', 'Qwen3.5-2B', 'P2_V1', '0.9', '42',  '0.4286', '3.06', '0.0796', '73.1'],
    ['5', 'Qwen3.5-2B', 'P2_V1', '0.7', '42',  '0.4688', '3.06', '0.0966', '86.1'],
    ['6', 'Qwen3.5-2B', 'P2_V1', '0.7', '123', '0.4605', '3.13', '0.0967', '80.6'],
    ['7', 'Qwen2.5-3B-I', 'P0_V0', '1.1', '42',  '0.4942', '3.06', '0.1088', '64.8'],
    ['8', 'Qwen2.5-3B-I', 'P0_V0', '1.1', '123', '0.5929', '3.13', '0.1090', '66.7'],
    ['9', 'Qwen2.5-3B-I', 'P0_V0', '0.9', '42',  '0.5319', '3.06', '0.1103', '70.4'],
    ['10', 'Qwen3.5-2B', 'P2_V1', '0.5', '42',  '0.4605', '3.06', '0.1140', '85.2'],
    ['11', 'Qwen2.5-3B-I', 'P0_V0', '0.5', '42',  '0.5487', '3.06', '0.1159', '69.4'],
    ['12', 'Qwen3.5-2B', 'P2_V1', '0.5', '123', '0.4239', '3.13', '0.1174', '86.1'],
    ['13', 'Qwen2.5-3B-I', 'P0_V0', '0.9', '123', '0.6015', '3.13', '0.1178', '61.1'],
    ['14', 'Qwen2.5-3B-I', 'P0_V0', '0.5', '123', '0.5233', '3.13', '0.1211', '75.9'],
]
add_table(s, Inches(0.5), Inches(1.3), Inches(12.3), Inches(5.5), runs,
          font_size=10, first_col_bold=True,
          col_widths_in=[0.4, 1.6, 1.0, 0.6, 0.7, 1.0, 1.0, 1.0, 1.0])
add_textbox(s, Inches(0.5), Inches(6.85), Inches(12.5), Inches(0.35),
            'Lower is better for JSD, Wasserstein, MMD. Real Reddit grounded = 2.5% for reference.',
            font_size=11, color=GREY, align=PP_ALIGN.CENTER)
add_slide_footer(s, 'A13 / 15')

# ---- A14: Metric formulas ----
s = appendix_slide('A14 — Metric formulas + caveats',
                   'For the technical marker')
# four mini cards
def metric_card(left, top, w, h, name, formula, caveat):
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                             left, top, w, h)
    box.fill.solid(); box.fill.fore_color.rgb = WHITE
    box.line.color.rgb = NAVY; box.line.width = Pt(1.2)
    add_textbox(s, left + Inches(0.15), top + Inches(0.1),
                w - Inches(0.3), Inches(0.4),
                name, font_size=13, bold=True, color=NAVY)
    add_textbox(s, left + Inches(0.15), top + Inches(0.55),
                w - Inches(0.3), Inches(1.0),
                formula, font_size=11, color=DARK, font='Consolas')
    add_textbox(s, left + Inches(0.15), top + Inches(1.55),
                w - Inches(0.3), h - Inches(1.6),
                caveat, font_size=10, color=GREY)

metric_card(Inches(0.4), Inches(1.3), Inches(6.2), Inches(2.6),
            'Jensen–Shannon (mood mix)',
            'JS(P,Q) = ½ KL(P‖M) + ½ KL(Q‖M)\nM = ½(P + Q)\nBounded [0, log 2]',
            'Caveat: 3-way categorical (bullish / bearish / neutral); same labeler on real and sim.')
metric_card(Inches(6.8), Inches(1.3), Inches(6.2), Inches(2.6),
            'Wasserstein-1 (timing)',
            'W₁(P,Q) over hourly histograms\n72 bins, −24 h to +48 h\nUnits: hours',
            'Caveat: measures the external scheduler; LLM never sees the timestamp.')
metric_card(Inches(0.4), Inches(4.05), Inches(6.2), Inches(2.6),
            'MMD (meaning spread)',
            'MMD²(X,Y) = Ê[k(x,x′)] + Ê[k(y,y′)] − 2Ê[k(x,y)]\n'
            'RBF kernel; γ from median heuristic\nEmbeddings: all-MiniLM-L6-v2',
            'Robustness: ranking preserved under Qwen3-Embedding-0.6B.')
metric_card(Inches(6.8), Inches(4.05), Inches(6.2), Inches(2.6),
            'Grounding (fact-mention)',
            'Categories hit ≥ 3, OR ≥ 2 + a number → grounded\n'
            '≥ 1 → weakly grounded\n0 → ungrounded',
            'Caveat: keyword coverage, not factual correctness. Six NVDA-specific categories.')
add_slide_footer(s, 'A14 / 15')

# ---- A15: Literature anchors ----
s = appendix_slide('A15 — Literature anchors',
                   'Positioning, not exhaustive review')
lit_data = [
    ['Anchor', 'Used here for'],
    ['Park et al. (UIST 2023) — Generative agents',
     'Believability baseline; this project goes further with distributional validation.'],
    ['Argyle et al. (PolAnal 2023) — Out of one, many',
     'LLMs as samplers of human distributions → motivates distribution-level evaluation.'],
    ['Hullman (heuristic-validation line)',
     'Rule-based labelers are defensible when applied identically to both sides.'],
    ['Anthis (alienness / sycophancy line)',
     'LLM agents are too analyst-like and too agreeable; over-grounding is one concrete instance.'],
    ['Schwager (history-conditioned generation)',
     'Motivates the named next experiment: behavioural exemplars instead of persona-only prompts.'],
]
add_table(s, Inches(0.5), Inches(1.4), Inches(12.3), Inches(4.5), lit_data,
          font_size=12, first_col_bold=True,
          col_widths_in=[4.5, 7.8])
add_textbox(s, Inches(0.5), Inches(6.0), Inches(12.5), Inches(1.0),
            'Citations already in the submitted proposal: Park, Argyle, Aher, Horton, Cookson, '
            'Bradley, Gretton (MMD), Lin (JSD), Villani (Wasserstein), Reimers & Gurevych (S-BERT), Qwen.',
            font_size=11, color=GREY)
add_slide_footer(s, 'A15 / 15')

prs.save(OUT_PPTX)
sz = os.path.getsize(OUT_PPTX)
print(f'Saved: {OUT_PPTX}  ({sz:,} bytes, {len(prs.slides)} slides)')
