#!/usr/bin/env python3
"""Rebuild seminar support figures with professor-feedback corrections.

Rebuilds (with fixes):
  curation_flow.png
  stance_rule_backup.png
  metrics_plain_language.png
  temperature_backup.png

Adds (new):
  data_eda_slide_visual.png
  model_io_prompt_visual.png
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Patch
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'outputs', 'seminar_support')
os.makedirs(OUT, exist_ok=True)

NAVY = '#1F4E79'
NAVY_LIGHT = '#9BB7D4'
GREY = '#808080'
LIGHT_BG = '#F2F2F2'
RED = '#C00000'
GREEN = '#548235'
WHITE = '#FFFFFF'
AMBER = '#BF8F00'

def box(ax, x, y, w, h, text, fc=NAVY, ec='none', fontcolor=WHITE,
        fontsize=11, weight='bold', radius=0.06):
    patch = FancyBboxPatch((x, y), w, h, boxstyle=f'round,pad=0,rounding_size={radius}',
                           fc=fc, ec=ec, linewidth=1.2)
    ax.add_patch(patch)
    ax.text(x+w/2, y+h/2, text, ha='center', va='center',
            fontsize=fontsize, color=fontcolor, weight=weight, wrap=True)

def arrow(ax, x1, y1, x2, y2, color=GREY, lw=1.6):
    a = FancyArrowPatch((x1, y1), (x2, y2),
                        arrowstyle='-|>', mutation_scale=18,
                        color=color, linewidth=lw)
    ax.add_patch(a)

def clean_ax(ax, x=10, y=6):
    ax.set_xlim(0, x); ax.set_ylim(0, y)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)

# =====================================================================
# FIX 1 — curation_flow.png  (revised wording)
# =====================================================================
fig, ax = plt.subplots(figsize=(12, 5))
clean_ax(ax)
ax.set_title('Curation flow: from raw Reddit collection to diagnostic reference corpus',
             fontsize=15, weight='bold', color=NAVY, pad=15)

boxes = [
    (0.3, 3.4, 1.8, 1.0, 'Reddit collection\nusing PRAW', NAVY, WHITE),
    (2.5, 3.4, 1.8, 1.0, 'Raw threads\n+ comments', NAVY_LIGHT, '#222'),
    (4.7, 3.4, 1.8, 1.0, 'Manual thread\ndecision list', NAVY, WHITE),
    (6.9, 3.4, 1.8, 1.0, 'Tag each thread:\nrelevant / marginal / remove', NAVY, WHITE),
    (9.1, 3.4, 0.8, 1.0, 'Curated\ncorpus', GREEN, WHITE),
]
for x, y, w, h, t, fc, fontcolor in boxes:
    box(ax, x, y, w, h, t, fc=fc, fontcolor=fontcolor, fontsize=10)
for x1 in [2.1, 4.3, 6.5, 8.7]:
    arrow(ax, x1, 3.9, x1+0.4, 3.9)

ax.text(0.3, 2.4, 'Raw =', fontsize=12, color=NAVY, weight='bold')
ax.text(1.2, 2.4, 'every thread and comment the Reddit search returned from r/stocks and r/wallstreetbets.',
        fontsize=11, color='#222')
ax.text(0.3, 1.8, '', fontsize=11, color='#222')
ax.text(1.2, 1.8, 'Window: −24h to +48h around the earnings release.',
        fontsize=11, color='#222', style='italic')
ax.text(0.3, 1.1, 'Curated =', fontsize=12, color=NAVY, weight='bold')
ax.text(1.6, 1.1, 'what remains after we drop threads about the wrong company or unrelated topics.',
        fontsize=11, color='#222')
ax.text(0.3, 0.4, 'Why it matters:', fontsize=12, color=RED, weight='bold')
ax.text(2.2, 0.4, "META's raw search returned 11 threads about other companies that same earnings week.",
        fontsize=11, color='#222')

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'curation_flow.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  [fixed] curation_flow.png')

# =====================================================================
# FIX 2 — stance_rule_backup.png  (revised hand-audit phrasing)
# =====================================================================
fig, ax = plt.subplots(figsize=(11, 6))
clean_ax(ax)
ax.set_title('Stance classifier — bullish / bearish / neutral rule',
             fontsize=15, weight='bold', color=NAVY, pad=15)

rows = [
    ('If…', 'Then label =', '#'),
    ('bullish keywords > bearish keywords', 'bullish', NAVY),
    ('bearish keywords > bullish keywords', 'bearish', RED),
    ('counts tied (including 0 vs 0)', 'neutral', GREY),
]
y = 4.2
for i, (cond, lab, col) in enumerate(rows):
    if i == 0:
        ax.add_patch(Rectangle((0.4, y), 11.0, 0.5, fc=NAVY, ec='none'))
        ax.text(0.7, y+0.25, cond, fontsize=12, weight='bold', color=WHITE, va='center')
        ax.text(8.0, y+0.25, lab, fontsize=12, weight='bold', color=WHITE, va='center')
    else:
        bg = LIGHT_BG if i % 2 == 0 else WHITE
        ax.add_patch(Rectangle((0.4, y), 11.0, 0.5, fc=bg, ec='none'))
        ax.text(0.7, y+0.25, cond, fontsize=11, color='#222', va='center')
        ax.text(8.0, y+0.25, lab, fontsize=12, weight='bold', color=col, va='center')
    y -= 0.55

ax.text(0.4, 2.4, 'Example keyword patterns (word-boundary regex, lowercased):',
        fontsize=11, weight='bold', color=NAVY)
ax.text(0.4, 1.9, 'Bullish:  buy, long, beat, strong, bullish, surge, rally, moon, upside, outperform, …  (37 patterns)',
        fontsize=10, color='#222')
ax.text(0.4, 1.5, 'Bearish:  sell, short, miss, weak, bearish, drop, dump, crash, overvalued, bubble, …  (38 patterns)',
        fontsize=10, color='#222')

ax.add_patch(FancyBboxPatch((0.4, 0.15), 11.0, 1.05, boxstyle='round,pad=0,rounding_size=0.05',
                            fc=LIGHT_BG, ec=NAVY, linewidth=1.0))
ax.text(0.6, 1.0, 'Hand-audit (100 NVDA comments, fixed seed):', fontsize=11, weight='bold', color=NAVY)
ax.text(0.6, 0.65, "Cohen's κ = 0.448  ·  Accuracy = 65.0%  ·  F1: bullish 0.525 / bearish 0.718 / neutral 0.700",
        fontsize=10.5, color='#222')
# Revised wording
ax.text(0.6, 0.30, 'Same labeler improves comparability, but this remains a noisy distribution-level proxy.',
        fontsize=10, color=RED, style='italic')

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'stance_rule_backup.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  [fixed] stance_rule_backup.png')

# =====================================================================
# FIX 3 — metrics_plain_language.png  (compact, clear hierarchy)
# =====================================================================
fig, ax = plt.subplots(figsize=(13, 5.5))
clean_ax(ax, x=13, y=5.5)
ax.set_title('Four diagnostic checks — three headline, one secondary',
             fontsize=15, weight='bold', color=NAVY, pad=12)

# Three headline cards across the top
headline_cards = [
    (0.3, 2.6, 'Meaning spread', 'MMD',
     'How close is the overall language of\nsimulated comments to real Reddit?',
     '(Sentence-BERT embedding distance)'),
    (4.5, 2.6, 'Fact-mention rate', 'Grounding',
     'Are simulated comments restating\nearnings facts more than real ones?',
     '(keyword coverage across 6 fact categories)'),
    (8.7, 2.6, 'Mood mix', 'JSD',
     'Bullish / bearish / neutral balance:\ndoes the crowd lean the right way?',
     '(Jensen–Shannon divergence)'),
]
for x, y, plain, technical, body, note in headline_cards:
    w, h = 4.0, 2.6
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=0.10',
                                fc=WHITE, ec=NAVY, linewidth=2.0))
    # "Headline" badge
    ax.add_patch(FancyBboxPatch((x+w-1.05, y+h-0.45), 0.95, 0.32,
                                boxstyle='round,pad=0,rounding_size=0.10',
                                fc=NAVY, ec='none'))
    ax.text(x+w-0.575, y+h-0.29, 'Headline', fontsize=8.5, weight='bold',
            color=WHITE, ha='center', va='center')
    # plain name + technical name
    ax.text(x+0.2, y+h-0.45, plain, fontsize=13, weight='bold', color=NAVY)
    ax.text(x+0.2, y+h-0.85, f'({technical})', fontsize=10, color=GREY, style='italic')
    # body
    ax.text(x+0.2, y+h-1.55, body, fontsize=10.5, color='#222', va='top')
    # note
    ax.text(x+0.2, y+0.25, note, fontsize=9, color=GREY, style='italic')

# Secondary card (full-width, slimmer)
y, w, h = 0.5, 12.4, 1.7
x = 0.3
ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=0.10',
                            fc=LIGHT_BG, ec=GREY, linewidth=1.5))
ax.add_patch(FancyBboxPatch((x+w-1.05, y+h-0.45), 0.95, 0.32,
                            boxstyle='round,pad=0,rounding_size=0.10',
                            fc=GREY, ec='none'))
ax.text(x+w-0.575, y+h-0.29, 'Secondary', fontsize=8.5, weight='bold',
        color=WHITE, ha='center', va='center')
ax.text(x+0.2, y+h-0.45, 'Timing pattern', fontsize=13, weight='bold', color='#333')
ax.text(x+0.2, y+h-0.85, '(Wasserstein-1)', fontsize=10, color=GREY, style='italic')
ax.text(x+0.2, y+0.30,
        'How comment timing is distributed across the event window.\n'
        'Scheduler diagnostic: in the current setup the LLM does not choose the timestamp.',
        fontsize=10.5, color='#222', va='bottom')

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'metrics_plain_language.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  [fixed] metrics_plain_language.png')

# =====================================================================
# FIX 4 — temperature_backup.png  (revised wording, no overclaim)
# =====================================================================
fig, ax = plt.subplots(figsize=(11, 6))
clean_ax(ax)
ax.set_title('Temperature — what it does to LLM output',
             fontsize=15, weight='bold', color=NAVY, pad=15)

box(ax, 0.4, 1.9, 5.0, 3.3, '', fc=LIGHT_BG, ec=NAVY, fontcolor=NAVY)
ax.text(0.6, 4.9, 'Low temperature  (τ = 0.5)', fontsize=13, weight='bold', color=NAVY)
ax.text(0.6, 4.5, 'Sampling concentrates on the most likely tokens.', fontsize=10.5, color='#222')
ax.text(0.6, 4.15, '→ Safer, more predictable text.', fontsize=10.5, color='#222')
ax.text(0.6, 3.80, '→ Tends to repeat the canonical earnings facts.', fontsize=10.5, color='#222')
ax.text(0.6, 3.45, '→ Higher fact-mention density.', fontsize=10.5, color=AMBER, weight='bold')
ax.text(0.6, 2.95, 'Sample at τ = 0.5:', fontsize=10, weight='bold', color=NAVY)
ax.text(0.6, 2.30, '"Jensen, I know you\'re the guy selling the best chips in\nthe world, but I\'m just glad you\'re raising guidance again…"',
        fontsize=9.5, color='#333', style='italic')

box(ax, 6.1, 1.9, 5.0, 3.3, '', fc=LIGHT_BG, ec=AMBER, fontcolor=AMBER)
ax.text(6.3, 4.9, 'High temperature  (τ = 1.1)', fontsize=13, weight='bold', color=AMBER)
ax.text(6.3, 4.5, 'Sampling spreads over a wider set of tokens.', fontsize=10.5, color='#222')
ax.text(6.3, 4.15, '→ More varied, less predictable text.', fontsize=10.5, color='#222')
ax.text(6.3, 3.80, '→ Less likely to follow the analyst-summary template.', fontsize=10.5, color='#222')
ax.text(6.3, 3.45, '→ Lower fact-mention density.', fontsize=10.5, color=GREEN, weight='bold')
ax.text(6.3, 2.95, 'Sample at τ = 1.1:', fontsize=10, weight='bold', color=AMBER)
ax.text(6.3, 2.30, '"Jensen raising G2Q4 sounds great on paper, but\nhonestly, I need to see more on the capital…"',
        fontsize=9.5, color='#333', style='italic')

# Corrected summary stripe
ax.add_patch(Rectangle((0.4, 0.55), 10.7, 1.05, fc=NAVY, ec='none'))
ax.text(5.75, 1.30,
        'Higher temperature reduces fact-mention density overall,',
        ha='center', va='center', fontsize=12, color=WHITE, weight='bold')
ax.text(5.75, 0.85,
        'but generated comments remain much more grounded than real Reddit.',
        ha='center', va='center', fontsize=11.5, color=WHITE)

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'temperature_backup.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  [fixed] temperature_backup.png')

# =====================================================================
# NEW 1 — data_eda_slide_visual.png
# =====================================================================
fig = plt.figure(figsize=(14, 7))
fig.suptitle('What the collected Reddit data looks like',
             fontsize=16, weight='bold', color=NAVY, y=0.98)

# Top-left: data definition card
ax_def = fig.add_axes([0.04, 0.55, 0.45, 0.38])
ax_def.set_xlim(0, 10); ax_def.set_ylim(0, 5); ax_def.axis('off')
ax_def.add_patch(FancyBboxPatch((0, 0), 10, 5, boxstyle='round,pad=0,rounding_size=0.15',
                                fc=LIGHT_BG, ec=NAVY, linewidth=1.5))
ax_def.text(0.4, 4.55, 'Data at a glance', fontsize=14, weight='bold', color=NAVY)
items = [
    ('Source', 'r/stocks  +  r/wallstreetbets'),
    ('Tool', 'Reddit collection using PRAW'),
    ('Event window', '−24 h to +48 h around earnings release'),
    ('Unit', 'one Reddit comment (or post)'),
    ('Events', 'NVDA Q3 FY26  ·  AAPL Q4 FY25  ·  META Q3 2025'),
]
y = 3.85
for k, v in items:
    ax_def.text(0.4, y, k, fontsize=10.5, weight='bold', color=NAVY)
    ax_def.text(2.6, y, v, fontsize=10.5, color='#222')
    y -= 0.5

# Top-right: fields stored card
ax_fields = fig.add_axes([0.52, 0.55, 0.45, 0.38])
ax_fields.set_xlim(0, 10); ax_fields.set_ylim(0, 5); ax_fields.axis('off')
ax_fields.add_patch(FancyBboxPatch((0, 0), 10, 5, boxstyle='round,pad=0,rounding_size=0.15',
                                   fc=LIGHT_BG, ec=NAVY, linewidth=1.5))
ax_fields.text(0.4, 4.55, 'Fields stored per comment', fontsize=14, weight='bold', color=NAVY)
fields = [
    ('text', 'comment or post body'),
    ('timestamp', 'UTC time the comment was posted'),
    ('hours_from_event', 'signed hours relative to earnings release'),
    ('subreddit', 'stocks or wallstreetbets'),
    ('thread_id  /  comment_id  /  parent_id', 'Reddit IDs (no usernames stored)'),
    ('score  /  depth', 'upvotes; reply depth in the thread'),
]
y = 3.85
for k, v in fields:
    ax_fields.text(0.4, y, k, fontsize=10, weight='bold', color=NAVY, family='monospace')
    ax_fields.text(5.5, y, v, fontsize=10, color='#222')
    y -= 0.5

# Bottom-left: raw vs curated bar chart
ax_bar = fig.add_axes([0.05, 0.10, 0.42, 0.36])
events = ['NVDA Q3 FY26', 'AAPL Q4 FY25', 'META Q3 2025']
raw = [2641, 392, 1444]; curated = [2403, 383, 344]
x_idx = np.arange(len(events)); w = 0.36
ax_bar.bar(x_idx - w/2, raw, w, label='Raw', color=NAVY_LIGHT, edgecolor='white')
b2 = ax_bar.bar(x_idx + w/2, curated, w, label='Curated', color=NAVY, edgecolor='white')
for xi, r, c in zip(x_idx, raw, curated):
    ax_bar.text(xi-w/2, r+50, str(r), ha='center', fontsize=9, color=NAVY)
    ax_bar.text(xi+w/2, c+50, str(c), ha='center', fontsize=9, color=NAVY, weight='bold')
ax_bar.set_xticks(x_idx); ax_bar.set_xticklabels(events, fontsize=10)
ax_bar.set_ylabel('Comments', fontsize=10)
ax_bar.set_title('Raw vs curated', fontsize=12, weight='bold', color=NAVY)
ax_bar.legend(loc='upper right', fontsize=9)
ax_bar.spines['top'].set_visible(False); ax_bar.spines['right'].set_visible(False)

# Bottom-right: temporal distribution NVDA
ax_time = fig.add_axes([0.55, 0.10, 0.42, 0.36])
cur = pd.read_csv(os.path.join(ROOT, 'data', 'processed', 'real_comments_curated_labeled.csv'))
nvda_hours = cur[cur['event_id']=='NVDA_Q3FY26']['hours_from_event'].dropna()
ax_time.hist(nvda_hours, bins=np.arange(-24, 50, 2), color=NAVY, edgecolor='white', linewidth=0.4)
ax_time.axvline(0, color=RED, ls='--', lw=1.4, alpha=0.9)
y_top = ax_time.get_ylim()[1]
ax_time.text(1.0, y_top*0.92, 'earnings release', color=RED, fontsize=9, ha='left', va='top')
ax_time.set_xlabel('Hours from earnings release', fontsize=10)
ax_time.set_ylabel('NVDA real comments', fontsize=10)
ax_time.set_title('When real comments arrive (NVDA)', fontsize=12, weight='bold', color=NAVY)
ax_time.spines['top'].set_visible(False); ax_time.spines['right'].set_visible(False)

plt.savefig(os.path.join(OUT, 'data_eda_slide_visual.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  [new]   data_eda_slide_visual.png')

# =====================================================================
# NEW 2 — model_io_prompt_visual.png
# =====================================================================
fig = plt.figure(figsize=(14, 7))
fig.suptitle('Model setup — input, prompt, output, headline result',
             fontsize=16, weight='bold', color=NAVY, y=0.98)

# Main canvas
ax = fig.add_axes([0.02, 0.10, 0.96, 0.84])
ax.set_xlim(0, 14); ax.set_ylim(0, 7); ax.axis('off')

# Inputs column (left)
input_specs = [
    (0.3, 5.4, 3.2, 1.2, 'Event card', 'Short earnings summary (e.g. $57B revenue, +62% YoY,\nQ4 guidance raised). Not the Reddit headline.'),
    (0.3, 3.95, 3.2, 1.2, 'Persona / cohort', 'Investor type (e.g. long-horizon valuation,\nshort-horizon momentum, info-seeking).'),
    (0.3, 2.5, 3.2, 1.2, 'Prompt', 'Instruction controlling style:\nP0 fact-heavy · P1 retail-balanced · P2 behaviour-first.'),
    (0.3, 1.05, 3.2, 1.2, 'Temperature', 'Randomness dial:\nlow = safer, high = more varied.'),
]
for x, y, w, h, title, body in input_specs:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=0.08',
                                fc=WHITE, ec=NAVY, linewidth=1.3))
    ax.text(x+0.15, y+h-0.30, title, fontsize=12, weight='bold', color=NAVY)
    ax.text(x+0.15, y+0.20, body, fontsize=9.5, color='#222', va='bottom')

# Arrow into LLM
arrow(ax, 3.7, 3.7, 5.0, 3.7, color=NAVY, lw=2.4)

# LLM box (centre)
ax.add_patch(FancyBboxPatch((5.05, 3.0), 2.6, 1.4, boxstyle='round,pad=0,rounding_size=0.10',
                            fc=NAVY, ec='none'))
ax.text(6.35, 3.95, 'Qwen LLM', fontsize=14, weight='bold', color=WHITE, ha='center')
ax.text(6.35, 3.40, '(2.5-3B Instruct · 3.5-2B)', fontsize=9.5, color='#dde', ha='center', style='italic')

# Arrow to output
arrow(ax, 7.8, 3.7, 9.0, 3.7, color=NAVY, lw=2.4)

# Output card
ax.add_patch(FancyBboxPatch((9.05, 2.8), 4.7, 1.9, boxstyle='round,pad=0,rounding_size=0.10',
                            fc=LIGHT_BG, ec=GREEN, linewidth=1.3))
ax.text(9.20, 4.45, 'Output', fontsize=12, weight='bold', color=GREEN)
ax.text(9.20, 3.95, 'One simulated Reddit-style comment.', fontsize=10.5, color='#222')
ax.text(9.20, 3.40, '"Solid quarter — beat by $1.8B but the\nH100 ramp is the real story for me…"',
        fontsize=9.5, color='#222', style='italic')
ax.text(9.20, 2.95, '108 comments per run.', fontsize=9.5, color=GREY)

# Best-run result card across the bottom
ax.add_patch(FancyBboxPatch((0.3, -0.05), 13.5, 1.0, boxstyle='round,pad=0,rounding_size=0.10',
                            fc=NAVY, ec='none'))
ax.text(0.6, 0.65, 'Best run:', fontsize=12, weight='bold', color=WHITE)
ax.text(2.05, 0.65, 'Qwen3.5-2B  +  P2_V1  +  τ = 1.1  +  seed = 123',
        fontsize=12, weight='bold', color=WHITE)
ax.text(2.05, 0.20, '14 finalist runs total.  n = 108 per run.',
        fontsize=9.5, color='#cfd', style='italic')

# headline numbers right side of the result strip
ax.text(7.5, 0.65, 'MMD 0.0653', fontsize=11.5, weight='bold', color=WHITE)
ax.text(9.4, 0.65, '·  JSD 0.4062', fontsize=11.5, color=WHITE)
ax.text(11.4, 0.65, '·  Grounded 57.4%', fontsize=11.5, color=WHITE)

plt.savefig(os.path.join(OUT, 'model_io_prompt_visual.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  [new]   model_io_prompt_visual.png')

print('\nAll figures saved to', OUT)
