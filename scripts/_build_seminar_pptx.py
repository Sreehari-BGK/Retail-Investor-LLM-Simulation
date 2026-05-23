#!/usr/bin/env python3
"""Build the DATA7901 seminar PowerPoint deck."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from copy import deepcopy
from lxml import etree

# ---- paths ----
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG_DIR = os.path.join(ROOT, 'outputs', 'proposal_support')
OUT_PPTX = os.path.join(ROOT, 'outputs', 'DATA7901_Seminar_Sreehari_s4906751.pptx')

# ---- generate supporting figures for slides ----
def make_retention_chart():
    fig, ax = plt.subplots(figsize=(7, 4))
    events = ['NVDA Q3 FY26', 'AAPL Q4 FY25', 'META Q3 2025']
    raw = [2641, 392, 1444]
    curated = [2403, 383, 344]
    x = np.arange(len(events))
    w = 0.35
    bars1 = ax.bar(x - w/2, raw, w, label='Raw', color='#9bb7d4', edgecolor='white')
    bars2 = ax.bar(x + w/2, curated, w, label='Curated', color='#1f4e79', edgecolor='white')
    for b in bars1: ax.text(b.get_x()+b.get_width()/2, b.get_height()+30, f'{int(b.get_height())}', ha='center', fontsize=9)
    for b in bars2: ax.text(b.get_x()+b.get_width()/2, b.get_height()+30, f'{int(b.get_height())}', ha='center', fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(events, fontsize=10)
    ax.set_ylabel('Comments')
    ax.set_title('Raw vs curated benchmark size, by event', fontsize=12)
    ax.legend(loc='upper right')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    plt.tight_layout()
    path = os.path.join(FIG_DIR, 'slide3_retention.png')
    fig.savefig(path, dpi=200); plt.close()
    return path

def make_tradeoff_chart():
    # MMD (x) vs Grounded% (y), colour by model+prompt, marker by seed
    rows = [
        # (model+prompt, tau, seed, MMD, Grounded%)
        ('Qwen3.5-2B + P2_V1', 0.5, 42, 0.11397, 85.2),
        ('Qwen3.5-2B + P2_V1', 0.5, 123, 0.11744, 86.1),
        ('Qwen3.5-2B + P2_V1', 0.7, 42, 0.09662, 86.1),
        ('Qwen3.5-2B + P2_V1', 0.7, 123, 0.09672, 80.6),
        ('Qwen3.5-2B + P2_V1', 0.9, 42, 0.07958, 73.1),
        ('Qwen3.5-2B + P2_V1', 0.9, 123, 0.07826, 71.3),
        ('Qwen3.5-2B + P2_V1', 1.1, 42, 0.06842, 64.8),
        ('Qwen3.5-2B + P2_V1', 1.1, 123, 0.06530, 57.4),
        ('Qwen2.5-3B + P0_V0', 0.5, 42, 0.11589, 69.4),
        ('Qwen2.5-3B + P0_V0', 0.5, 123, 0.12106, 75.9),
        ('Qwen2.5-3B + P0_V0', 0.9, 42, 0.11028, 70.4),
        ('Qwen2.5-3B + P0_V0', 0.9, 123, 0.11780, 61.1),
        ('Qwen2.5-3B + P0_V0', 1.1, 42, 0.10878, 64.8),
        ('Qwen2.5-3B + P0_V0', 1.1, 123, 0.10897, 66.7),
    ]
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    colours = {'Qwen3.5-2B + P2_V1': '#1f4e79', 'Qwen2.5-3B + P0_V0': '#a6a6a6'}
    for label in colours:
        xs = [r[3] for r in rows if r[0] == label]
        ys = [r[4] for r in rows if r[0] == label]
        taus = [r[1] for r in rows if r[0] == label]
        ax.scatter(xs, ys, s=80, c=colours[label], label=label, edgecolor='white', linewidth=1, alpha=0.85)
        # annotate tau values for the semantic-first runs
        if label == 'Qwen3.5-2B + P2_V1':
            for x, y, t in zip(xs, ys, taus):
                ax.annotate(f'τ={t}', (x, y), xytext=(6, 4), textcoords='offset points', fontsize=8, color='#1f4e79')
    # real-Reddit reference line for grounded%
    ax.axhline(2.5, color='#c00000', linestyle='--', linewidth=1.2, alpha=0.9)
    ax.text(0.063, 5, 'Real Reddit grounded = 2.5%', color='#c00000', fontsize=9)
    ax.set_xlabel('MMD semantic (lower = closer to real)')
    ax.set_ylabel('Grounded % (lower = closer to real)')
    ax.set_title('Trade-off: semantic similarity vs. fact-mention density', fontsize=12)
    ax.legend(loc='upper right')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    plt.tight_layout()
    path = os.path.join(FIG_DIR, 'slide6_tradeoff.png')
    fig.savefig(path, dpi=200); plt.close()
    return path

retention_png = make_retention_chart()
tradeoff_png = make_tradeoff_chart()
stance_png = os.path.join(FIG_DIR, 'stance_distribution_grouped.png')
timeline_png = os.path.join(FIG_DIR, 'temporal_timeline_all_events.png')

# ---- build pptx ----
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# colours
NAVY = RGBColor(0x1F, 0x4E, 0x79)
DARK = RGBColor(0x33, 0x33, 0x33)
GREY = RGBColor(0x7F, 0x7F, 0x7F)
ACCENT = RGBColor(0xC0, 0x00, 0x00)
LIGHT_BG = RGBColor(0xF2, 0xF2, 0xF2)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

BLANK = prs.slide_layouts[6]

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
                font_size=16, color=DARK, bullet_char='•', line_spacing=1.2):
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

def add_title_bar(slide, title, subtitle=None):
    # navy stripe + title
    stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.85))
    stripe.fill.solid(); stripe.fill.fore_color.rgb = NAVY
    stripe.line.fill.background()
    add_textbox(slide, Inches(0.5), Inches(0.13), Inches(12.5), Inches(0.55),
                title, font_size=26, bold=True, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
    if subtitle:
        add_textbox(slide, Inches(0.5), Inches(0.92), Inches(12.5), Inches(0.4),
                    subtitle, font_size=14, color=GREY)

def add_slide_number(slide, n, total=8):
    add_textbox(slide, Inches(12.5), Inches(7.05), Inches(0.7), Inches(0.35),
                f'{n} / {total}', font_size=10, color=GREY, align=PP_ALIGN.RIGHT)
    add_textbox(slide, Inches(0.4), Inches(7.05), Inches(8.0), Inches(0.35),
                'Simulating Retail-Investor Discussion with LLM Agents — Sreehari Biji Kumar (s4906751)',
                font_size=10, color=GREY)

def add_notes(slide, text):
    notes = slide.notes_slide
    tf = notes.notes_text_frame
    tf.text = text

def add_table(slide, left, top, width, height, data, *,
              header_fill=NAVY, header_color=WHITE, body_color=DARK,
              first_col_bold=False, font_size=12):
    rows = len(data); cols = len(data[0])
    tbl = slide.shapes.add_table(rows, cols, left, top, width, height).table
    for r_idx, row in enumerate(data):
        for c_idx, val in enumerate(row):
            cell = tbl.cell(r_idx, c_idx)
            cell.text = ''
            tf = cell.text_frame
            tf.margin_left = Inches(0.08); tf.margin_right = Inches(0.08)
            tf.margin_top = Inches(0.04); tf.margin_bottom = Inches(0.04)
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

# =========================================================================
# Slide 1 — Title
# =========================================================================
s = prs.slides.add_slide(BLANK)
# big navy block top half
top_block = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(4.4))
top_block.fill.solid(); top_block.fill.fore_color.rgb = NAVY
top_block.line.fill.background()

add_textbox(s, Inches(0.7), Inches(0.5), Inches(12), Inches(0.5),
            'DATA7901  •  Data Science Capstone Project 1',
            font_size=16, color=WHITE)
add_textbox(s, Inches(0.7), Inches(1.1), Inches(12), Inches(1.4),
            'Simulating Retail-Investor Discussion\nwith LLM Agents',
            font_size=40, bold=True, color=WHITE)
add_textbox(s, Inches(0.7), Inches(3.2), Inches(12), Inches(0.6),
            'Track: Simulating the World — Towards Social Simulation via Large Language Models',
            font_size=14, color=WHITE)

# question card
q = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.7), Inches(4.7), Inches(11.9), Inches(1.3))
q.fill.solid(); q.fill.fore_color.rgb = LIGHT_BG
q.line.color.rgb = NAVY; q.line.width = Pt(1.5)
add_textbox(s, Inches(1.0), Inches(4.85), Inches(11.3), Inches(1.0),
            '"If real investors and simulated agents see the same earnings shock,\nhow closely does the resulting Reddit discussion match?"',
            font_size=18, bold=True, color=NAVY, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)

# author block
add_textbox(s, Inches(0.7), Inches(6.25), Inches(8), Inches(0.4),
            'Sreehari Biji Kumar  •  Student ID: s4906751', font_size=14, bold=True, color=DARK)
add_textbox(s, Inches(0.7), Inches(6.65), Inches(8), Inches(0.4),
            'Master of Data Science  •  The University of Queensland', font_size=12, color=GREY)
add_textbox(s, Inches(10.5), Inches(6.65), Inches(2.5), Inches(0.4),
            'NVDA primary  |  AAPL secondary  |  META exploratory',
            font_size=10, color=GREY, align=PP_ALIGN.RIGHT)
add_slide_number(s, 1)
add_notes(s,
"Quick intro. The project asks one concrete question — the one on the slide. "
"When real investors and simulated agents react to the same earnings shock, how closely does the resulting discussion match? "
"NVDA Q3 FY2026 is the primary event; AAPL and META are secondary. "
"The point isn't to build a chatbot — it's to build a yardstick for measuring how realistic LLM-driven social simulation actually is. "
"(30–40 seconds — keep it brisk and move on.)")

# =========================================================================
# Slide 2 — Fluency is not validation
# =========================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'Problem: fluency is not validation',
              'A simulator can sound like Reddit while missing the real crowd pattern.')

# left card: sample comment
card = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), Inches(1.6), Inches(5.4), Inches(4.6))
card.fill.solid(); card.fill.fore_color.rgb = LIGHT_BG
card.line.color.rgb = GREY; card.line.width = Pt(0.75)
add_textbox(s, Inches(0.75), Inches(1.75), Inches(5.0), Inches(0.4),
            'Sample LLM-generated comment', font_size=13, bold=True, color=NAVY)
add_textbox(s, Inches(0.75), Inches(2.2), Inches(5.0), Inches(3.6),
            '"so glad we have a 62% jump in just one quarter, '
            "but I'm still wondering how Jensen will push it when the "
            'blackwell ramp actually hits the ground running…"',
            font_size=15, color=DARK)
add_textbox(s, Inches(0.75), Inches(5.65), Inches(5.0), Inches(0.4),
            'Reads fluent. But is the corpus realistic?', font_size=12,
            color=ACCENT, bold=True)

# right column: three axes
add_textbox(s, Inches(6.4), Inches(1.6), Inches(6.5), Inches(0.5),
            'Three things a fluent comment cannot guarantee:', font_size=15, bold=True, color=NAVY)

def axis_box(top_in, title, body):
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                             Inches(6.4), Inches(top_in), Inches(6.5), Inches(1.25))
    box.fill.solid(); box.fill.fore_color.rgb = WHITE
    box.line.color.rgb = NAVY; box.line.width = Pt(1.0)
    add_textbox(s, Inches(6.6), Inches(top_in + 0.1), Inches(6.2), Inches(0.4),
                title, font_size=15, bold=True, color=NAVY)
    add_textbox(s, Inches(6.6), Inches(top_in + 0.55), Inches(6.2), Inches(0.7),
                body, font_size=13, color=DARK)

axis_box(2.2, 'Stance',
         'Is the bullish / bearish / neutral mix right?')
axis_box(3.6, 'Timing',
         'When in the event window do comments arrive?')
axis_box(5.0, 'Content',
         'Does the language inhabit the same space as real Reddit?')

add_textbox(s, Inches(0.5), Inches(6.4), Inches(12.5), Inches(0.5),
            'Takeaway: plausible ≠ realistic. Validation needs distributional measurement, not impressions.',
            font_size=14, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
add_slide_number(s, 2)
add_notes(s,
"Current LLM-simulation literature often stops at plausibility — the model produces text that reads like a Reddit comment and people say 'looks good'. "
"But a finance simulator has to do more than sound right. It has to get the crowd pattern right — stance, timing, content. "
"A simulator can sound like Reddit while completely missing all three. "
"This whole project is framed around catching that gap with explicit distributional measurements rather than vibes. (70 seconds.)")

# =========================================================================
# Slide 3 — Benchmark + curation
# =========================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'Real Reddit benchmark',
              'Manual thread-level curation. NVDA primary, AAPL secondary, META exploratory.')

# chart
s.shapes.add_picture(retention_png, Inches(0.5), Inches(1.6), height=Inches(4.6))

# retention table on right
tbl = [
    ['Event', 'Raw', 'Curated', 'Retention'],
    ['NVDA Q3 FY26', '2641', '2403', '91%'],
    ['AAPL Q4 FY25', '392', '383', '98%'],
    ['META Q3 2025', '1444', '344', '24%'],
]
add_table(s, Inches(8.6), Inches(1.8), Inches(4.3), Inches(2.0), tbl, font_size=12)

# notes box
add_textbox(s, Inches(8.6), Inches(4.1), Inches(4.3), Inches(0.4),
            'Why META loses 76%:', font_size=13, bold=True, color=NAVY)
add_bullets(s, Inches(8.6), Inches(4.5), Inches(4.4), Inches(1.7),
            ['11 of 15 threads about other companies during',
             '   the same earnings week (GOOG, RDDT, CMG…)',
             'Only 4 threads directly discuss META Q3',
             'Curation is manual + reproducible (committed list)'],
            font_size=12)

add_textbox(s, Inches(0.5), Inches(6.55), Inches(12.5), Inches(0.4),
            'Window: −24 h to +48 h around the earnings release. r/stocks + r/wallstreetbets.',
            font_size=11, color=GREY, align=PP_ALIGN.CENTER)

add_slide_number(s, 3)
add_notes(s,
"Reddit collection: r/stocks and r/wallstreetbets, aligned to a -24 h to +48 h window around each earnings release. "
"Threads are curated manually at the thread level — I read the title and tag it relevant, marginal, or remove. "
"NVDA keeps 91% of comments — threads are clean. AAPL keeps 98% but is small. "
"META loses 76% because the Reddit API returned 11 threads about other companies during the same earnings week. "
"That's why NVDA is primary, AAPL is secondary, and META is exploratory only. (70 seconds.)")

# =========================================================================
# Slide 4 — Pipeline
# =========================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'Pipeline: real corpus vs simulated corpus',
              'Both sides go through the same four metrics for an apples-to-apples comparison.')

# flow diagram boxes
def flow_box(left, top, width, height, text, fill, font_size=13, color=WHITE, bold=True):
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    b.fill.solid(); b.fill.fore_color.rgb = fill
    b.line.fill.background()
    add_textbox(s, left, top, width, height, text,
                font_size=font_size, bold=bold, color=color,
                align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# real branch (top)
flow_box(Inches(0.5), Inches(1.7), Inches(2.4), Inches(0.9),
         'Reddit JSON\nAPI', NAVY, font_size=13)
flow_box(Inches(3.5), Inches(1.7), Inches(2.4), Inches(0.9),
         'Manual\ncuration', NAVY, font_size=13)
flow_box(Inches(6.5), Inches(1.7), Inches(2.7), Inches(0.9),
         'Real corpus\n(2403 NVDA)', NAVY, font_size=13)

# sim branch (bottom)
flow_box(Inches(0.5), Inches(4.2), Inches(2.4), Inches(0.9),
         'Event card\n+ persona', GREY, font_size=13)
flow_box(Inches(3.5), Inches(4.2), Inches(2.4), Inches(0.9),
         'Qwen LLM\ngeneration', GREY, font_size=13)
flow_box(Inches(6.5), Inches(4.2), Inches(2.7), Inches(0.9),
         'Sim corpus\n(108 per run)', GREY, font_size=13)

# converge box on right
flow_box(Inches(10.0), Inches(2.95), Inches(2.9), Inches(1.4),
         'Same four\nmetrics', ACCENT, font_size=16)

# arrows (simple straight lines)
def arrow(x1, y1, x2, y2, colour=DARK):
    conn = s.shapes.add_connector(2, Emu(int(x1*914400)), Emu(int(y1*914400)),
                                  Emu(int(x2*914400)), Emu(int(y2*914400)))
    conn.line.color.rgb = colour
    conn.line.width = Pt(2)
    # arrow head
    line = conn.line
    lnEnd = etree.SubElement(line._get_or_add_ln(), qn('a:tailEnd'))
    lnEnd.set('type', 'triangle')

arrow(2.9, 2.15, 3.5, 2.15)
arrow(5.9, 2.15, 6.5, 2.15)
arrow(9.2, 2.15, 10.0, 3.2)
arrow(2.9, 4.65, 3.5, 4.65)
arrow(5.9, 4.65, 6.5, 4.65)
arrow(9.2, 4.65, 10.0, 4.1)

# grid spec box at bottom — the corrected wording
spec = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), Inches(5.55), Inches(12.4), Inches(1.3))
spec.fill.solid(); spec.fill.fore_color.rgb = LIGHT_BG
spec.line.color.rgb = NAVY; spec.line.width = Pt(1.0)
add_textbox(s, Inches(0.7), Inches(5.7), Inches(12.1), Inches(0.4),
            'Finalist grid (14 runs total, n = 108 comments each):',
            font_size=14, bold=True, color=NAVY)
add_textbox(s, Inches(0.7), Inches(6.1), Inches(12.1), Inches(0.75),
            '• Qwen2.5-3B + P0_V0 across three temperatures (0.5, 0.9, 1.1) and two seeds (42, 123)  →  6 runs\n'
            '• Qwen3.5-2B + P2_V1 across four temperatures (0.5, 0.7, 0.9, 1.1) and two seeds (42, 123)  →  8 runs',
            font_size=13, color=DARK)

add_slide_number(s, 4)
add_notes(s,
"The pipeline is symmetric. On one side: curated real Reddit. On the other: simulated comments from a Qwen model "
"conditioned on a persona and an event card. Both go through the same four metrics, so the comparison is apples to apples. "
"The finalist grid contains 14 runs: Qwen2.5/P0_V0 across three temperatures and two seeds, and Qwen3.5/P2_V1 across "
"four temperatures and two seeds. Each run generates 108 comments. (70 seconds.)")

# =========================================================================
# Slide 5 — Four metrics
# =========================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'Four realism metrics',
              'Independent diagnostics. Reported separately — not collapsed into one score.')

def metric_card(left, top, title, body, accent=NAVY):
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                             left, top, Inches(6.0), Inches(2.3))
    box.fill.solid(); box.fill.fore_color.rgb = WHITE
    box.line.color.rgb = accent; box.line.width = Pt(1.5)
    add_textbox(s, left + Inches(0.25), top + Inches(0.15), Inches(5.6), Inches(0.55),
                title, font_size=18, bold=True, color=accent)
    add_textbox(s, left + Inches(0.25), top + Inches(0.85), Inches(5.6), Inches(1.3),
                body, font_size=13, color=DARK)

metric_card(Inches(0.4), Inches(1.7),
            'JSD  —  stance',
            'Jensen–Shannon divergence on the bullish / bearish / neutral mix.\nLower = closer stance balance to real Reddit.')

metric_card(Inches(6.9), Inches(1.7),
            'Wasserstein-1  —  timing',
            'Earth-mover distance on hourly posting profile, in hours.\nMeasures the scheduler. The LLM does not set timestamps.')

metric_card(Inches(0.4), Inches(4.2),
            'MMD  —  content',
            'Maximum Mean Discrepancy on Sentence-BERT embeddings.\nWhole-corpus distance in semantic space.')

metric_card(Inches(6.9), Inches(4.2),
            'Grounding  —  fact-mention',
            'Share of comments referencing earnings facts (revenue, EPS, Blackwell, etc.).\nBehavioural diagnostic, not factual correctness.')

add_textbox(s, Inches(0.4), Inches(6.7), Inches(12.5), Inches(0.4),
            'Reported as four independent diagnostics — collapsing them would hide the trade-offs that matter.',
            font_size=12, color=GREY, align=PP_ALIGN.CENTER, bold=True)
add_slide_number(s, 5)
add_notes(s,
"Four independent diagnostics, each measuring something different. "
"JSD: stance balance. Wasserstein-1: temporal posting profile, in hours — but be aware it measures the external scheduler, "
"not the LLM, because the LLM never sees the timestamp. "
"MMD: semantic distribution distance using Sentence-BERT embeddings. "
"Grounding: how often comments reference earnings facts. I report all four separately. "
"Combining them into a weighted realism score would hide the trade-offs, which is exactly the most interesting result. (75 seconds.)")

# =========================================================================
# Slide 6 — Results
# =========================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'Finalist results at n = 108',
              'Higher temperature → better MMD, lower grounding rate. Best run still over-grounds vs real.')

# left: top-3 table
tbl = [
    ['Run', 'τ', 'MMD ↓', 'Grounded'],
    ['Qwen3.5-2B  P2_V1  (s=123)', '1.1', '0.0653', '57.4%'],
    ['Qwen3.5-2B  P2_V1  (s=42)',  '1.1', '0.0684', '64.8%'],
    ['Qwen3.5-2B  P2_V1  (s=123)', '0.9', '0.0783', '71.3%'],
]
add_table(s, Inches(0.4), Inches(1.7), Inches(6.0), Inches(2.1), tbl, font_size=12, first_col_bold=True)

# headline callout
hc = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                       Inches(0.4), Inches(4.05), Inches(6.0), Inches(1.3))
hc.fill.solid(); hc.fill.fore_color.rgb = NAVY
hc.line.fill.background()
add_textbox(s, Inches(0.6), Inches(4.15), Inches(5.6), Inches(0.5),
            'Best run', font_size=14, bold=True, color=WHITE)
add_textbox(s, Inches(0.6), Inches(4.55), Inches(5.6), Inches(0.75),
            'Qwen3.5-2B + P2_V1 + τ=1.1 + seed=123\nMMD 0.0653  •  JSD 0.4062  •  Grounded 57.4%',
            font_size=13, color=WHITE)

# real vs LLM grounding bar (use simple shapes)
add_textbox(s, Inches(0.4), Inches(5.55), Inches(6.0), Inches(0.4),
            'Grounding rate, real vs best LLM:',
            font_size=13, bold=True, color=NAVY)
# real bar (2.5%)
real_bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.4), Inches(6.0), Inches(0.13), Inches(0.35))
real_bar.fill.solid(); real_bar.fill.fore_color.rgb = NAVY
real_bar.line.fill.background()
add_textbox(s, Inches(0.6), Inches(5.95), Inches(2.0), Inches(0.45),
            'Real  2.5%', font_size=12, color=NAVY, bold=True)
# LLM bar (57.4% → ~3.0 inches at 5%=0.262in)
llm_bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.4), Inches(6.5), Inches(3.0), Inches(0.35))
llm_bar.fill.solid(); llm_bar.fill.fore_color.rgb = ACCENT
llm_bar.line.fill.background()
add_textbox(s, Inches(3.5), Inches(6.45), Inches(2.5), Inches(0.45),
            'LLM  57.4%', font_size=12, color=ACCENT, bold=True)

# right: trade-off scatter
s.shapes.add_picture(tradeoff_png, Inches(6.7), Inches(1.65), height=Inches(4.8))

add_textbox(s, Inches(6.7), Inches(6.55), Inches(6.5), Inches(0.4),
            'Qwen3.5/P2_V1 dominates on MMD. Grounding still ~22× real Reddit.',
            font_size=11, color=GREY, align=PP_ALIGN.CENTER, bold=True)
add_slide_number(s, 6)
add_notes(s,
"Across the 14 finalist runs at n=108, Qwen3.5-2B with the behaviour-first prompt at temperature 1.1 is the best on semantic similarity — "
"MMD of 0.065. As temperature goes up in that block, MMD improves and the grounding rate drops. "
"So temperature is trading fact-mention density for distributional realism — the trade-off the proposal predicted. "
"Honest framing: even the best run grounds 57% of comments, while real Reddit grounds only 2.5%. "
"Real investors react to the news; they don't restate it. The simulator is still over-grounded by more than 20×. "
"Real progress on semantic similarity, but the behavioural realism gap is still visible. (80 seconds.)")

# =========================================================================
# Slide 7 — Limitations
# =========================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'Limitations and next steps',
              'Stated up front — not buried in an appendix.')

tbl = [
    ['Limitation', 'Status', 'Next step'],
    ['Timestamps are scheduler-driven, not LLM-driven',
     'Known, by design',
     'Document explicitly; Wasserstein measures the scheduler, not the model'],
    ['Over-grounding (57% LLM vs 2.5% real)',
     'Confirmed at n = 108',
     'Longer prompts, fact-suppression instructions, retrieval-free generation'],
    ['Stance labeler is rule-based (κ = 0.45)',
     'Hand-audited, moderate agreement',
     'Compare against FinBERT or LLM-assisted stance labels as a robustness check'],
    ['AAPL cross-event validation pending',
     'Scheduled for Semester 2',
     'Adapt pipeline; test whether NVDA finalists transfer'],
]
add_table(s, Inches(0.4), Inches(1.7), Inches(12.5), Inches(4.4), tbl, font_size=12, first_col_bold=True)

add_textbox(s, Inches(0.4), Inches(6.3), Inches(12.5), Inches(0.5),
            'Every limitation has a concrete next step. None of them invalidate the framework.',
            font_size=13, color=NAVY, align=PP_ALIGN.CENTER, bold=True)
add_slide_number(s, 7)
add_notes(s,
"Four honest limitations. Timestamps: the simulator's comment times come from an external Gaussian scheduler the LLM never sees, "
"so Wasserstein measures whether that scheduler is calibrated, not whether the model is realistic in time. "
"Over-grounding: the biggest behavioural gap; the best LLM mentions facts 22 times more often than real investors. "
"Stance labeler: keyword-based with kappa 0.45 — good enough for distributional JSD, not for individual classifications. "
"Comparison against FinBERT or LLM-assisted stance is on the list as a robustness check. "
"AAPL cross-event validation is scheduled for Semester 2. (75 seconds.)")

# =========================================================================
# Slide 8 — Takeaway
# =========================================================================
s = prs.slides.add_slide(BLANK)
add_title_bar(s, 'Takeaway',
              '')

# headline
add_textbox(s, Inches(0.5), Inches(1.8), Inches(12.3), Inches(1.0),
            'What I built is a validation framework, not a solved simulator.',
            font_size=28, bold=True, color=NAVY, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# three contribution cards
def contrib_card(left, top, num, head, body):
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                             left, top, Inches(4.0), Inches(3.3))
    box.fill.solid(); box.fill.fore_color.rgb = WHITE
    box.line.color.rgb = NAVY; box.line.width = Pt(1.5)
    # number badge
    badge = s.shapes.add_shape(MSO_SHAPE.OVAL,
                               left + Inches(0.2), top + Inches(0.2), Inches(0.6), Inches(0.6))
    badge.fill.solid(); badge.fill.fore_color.rgb = NAVY
    badge.line.fill.background()
    add_textbox(s, left + Inches(0.2), top + Inches(0.2), Inches(0.6), Inches(0.6),
                num, font_size=18, bold=True, color=WHITE,
                align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_textbox(s, left + Inches(0.95), top + Inches(0.25), Inches(2.9), Inches(0.55),
                head, font_size=15, bold=True, color=NAVY)
    add_textbox(s, left + Inches(0.25), top + Inches(1.05), Inches(3.5), Inches(2.2),
                body, font_size=13, color=DARK)

contrib_card(Inches(0.4), Inches(3.2), '1', 'Reusable benchmark',
             'Curated event-aligned Reddit corpus + four independent metrics. Any future simulator must beat this baseline on all four.')

contrib_card(Inches(4.65), Inches(3.2), '2', 'Honest evidence',
             'Current open-weight LLMs improve semantic realism vs templates but over-ground ~22× compared with real investors.')

contrib_card(Inches(8.9), Inches(3.2), '3', 'Defined next stage',
             'Cross-event validation on AAPL, stance-labeler robustness check, prompt-level grounding suppression.')

add_textbox(s, Inches(0.5), Inches(6.7), Inches(12.5), Inches(0.4),
            'Thank you — happy to take questions.',
            font_size=14, color=GREY, align=PP_ALIGN.CENTER)
add_slide_number(s, 8)
add_notes(s,
"Closing message: the contribution isn't 'a realistic investor simulator' — that would be overclaiming. "
"The contribution is a benchmark and a measurement framework. Any future richer interactive simulator has to beat this simple one-shot "
"baseline on JSD, MMD, Wasserstein, and grounding simultaneously, against a real-vs-real noise floor I've already established. "
"If the result later is strong, the framework supports cautious use of LLM simulation for behavioural stress-testing. "
"If it's weak, it tells us exactly which dimension is still failing. Either way, the project produces something usable. "
"Thanks — happy to take questions. (65 seconds.)")

# save
prs.save(OUT_PPTX)
sz = os.path.getsize(OUT_PPTX)
print(f'Saved: {OUT_PPTX}  ({sz:,} bytes, {len(prs.slides)} slides)')
