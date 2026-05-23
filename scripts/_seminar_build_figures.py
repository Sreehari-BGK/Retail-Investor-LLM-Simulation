#!/usr/bin/env python3
"""Build all 9 seminar support figures as PNGs in outputs/seminar_support/."""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import numpy as np

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

def clean_ax(ax):
    ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)

# ---------------------------------------------------------------
# 2. curation_flow.png
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 5))
clean_ax(ax)
ax.set_title('Curation flow: from raw Reddit search to curated reference corpus',
             fontsize=15, weight='bold', color=NAVY, pad=15)
# stages
boxes = [
    (0.3, 3.4, 1.8, 1.0, 'Reddit JSON API\nsearch (PRAW)', NAVY),
    (2.5, 3.4, 1.8, 1.0, 'Raw threads\n+ comments', NAVY_LIGHT, '#333333'),
    (4.7, 3.4, 1.8, 1.0, 'Manual thread\ndecision list', NAVY),
    (6.9, 3.4, 1.8, 1.0, 'Tag each thread:\nrelevant / marginal / remove', NAVY),
    (9.1, 3.4, 0.8, 1.0, 'Curated\ncorpus', GREEN),
]
for b in boxes:
    if len(b) == 6:
        x, y, w, h, t, fc = b
        fontcolor = WHITE
    else:
        x, y, w, h, t, fc, fontcolor = b
    box(ax, x, y, w, h, t, fc=fc, fontcolor=fontcolor, fontsize=10)
# arrows between boxes
for x1 in [2.1, 4.3, 6.5, 8.7]:
    arrow(ax, x1, 3.9, x1+0.4, 3.9)

# Definitions row at the bottom
ax.text(0.3, 2.4, 'Raw =', fontsize=12, color=NAVY, weight='bold')
ax.text(1.3, 2.4, 'every thread and comment the Reddit search returned within ±48 h of the earnings release.',
        fontsize=11, color='#333')
ax.text(0.3, 1.6, 'Curated =', fontsize=12, color=NAVY, weight='bold')
ax.text(1.6, 1.6, 'what remains after we drop threads about the wrong company or unrelated topics.',
        fontsize=11, color='#333')
ax.text(0.3, 0.8, 'Why it matters:', fontsize=12, color=RED, weight='bold')
ax.text(2.2, 0.8, 'METAs raw search returned 11 threads about other companies that same earnings week.',
        fontsize=11, color='#333')
ax.text(2.2, 0.3, 'Without curation, those would have polluted the benchmark.',
        fontsize=11, color='#333')

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'curation_flow.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  curation_flow.png')

# ---------------------------------------------------------------
# 3. event_prompt_agent_diagram.png
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 6))
clean_ax(ax); ax.set_ylim(0, 7)
ax.set_title('How one simulated comment is produced',
             fontsize=15, weight='bold', color=NAVY, pad=15)
# four input cards on the left
input_specs = [
    (0.2, 4.9, 2.4, 1.1, 'Event card', 'Short earnings-event summary\n(57B revenue, +62% YoY, Q4 guidance).\nNot the Reddit post headline.'),
    (0.2, 3.55, 2.4, 1.1, 'Persona / cohort', 'Simulated investor type\n(e.g. long-horizon valuation investor).'),
    (0.2, 2.2, 2.4, 1.1, 'Prompt', 'Instruction controlling style:\nP0 fact-heavy, P1 retail-balanced,\nP2 behaviour-first.'),
    (0.2, 0.85, 2.4, 1.1, 'Temperature', 'Randomness knob.\nLow = safer/repetitive.\nHigh = more varied/messier.'),
]
for x, y, w, h, title, body in input_specs:
    box(ax, x, y, w, h, '', fc=WHITE, ec=NAVY, fontcolor=NAVY)
    ax.text(x+0.15, y+h-0.25, title, fontsize=12, weight='bold', color=NAVY)
    ax.text(x+0.15, y+0.15, body, fontsize=9, color='#333', va='bottom')

# central arrow + LLM box
arrow(ax, 2.8, 3.5, 4.3, 3.5, color=NAVY, lw=2.2)
box(ax, 4.4, 2.8, 2.4, 1.4, 'Qwen LLM\ngeneration', fc=NAVY, fontsize=13)

# output box
arrow(ax, 7.0, 3.5, 8.3, 3.5, color=NAVY, lw=2.2)
box(ax, 8.4, 2.5, 3.4, 2.0, '', fc=LIGHT_BG, ec=GREEN, fontcolor=GREEN, radius=0.08)
ax.text(8.55, 4.2, 'One simulated comment', fontsize=11, weight='bold', color=GREEN)
ax.text(8.55, 3.4, '"Solid quarter — beat by\n$1.8B but H100 ramp\nis the real story."', fontsize=10,
        color='#222', style='italic')
ax.text(8.55, 2.7, '108 comments per run', fontsize=9, color=GREY)

# footer note
ax.text(0.2, 0.15, 'Repeat 108 times per run with the same prompt and persona mix, varying only seed and temperature.',
        fontsize=10, color=NAVY, weight='bold')

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'event_prompt_agent_diagram.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  event_prompt_agent_diagram.png')

# ---------------------------------------------------------------
# 4. metrics_plain_language.png
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 6.2))
clean_ax(ax); ax.set_ylim(0, 6)
ax.set_title('Four diagnostic metrics — plain-language summary',
             fontsize=15, weight='bold', color=NAVY, pad=15)

cards = [
    (0.2, 3.1, 5.6, 2.4, 'Mood mix  (JSD)',
     'Bullish / bearish / neutral balance.\nDoes the simulated crowd lean the same way as the real one?',
     'headline'),
    (6.1, 3.1, 5.6, 2.4, 'Meaning spread  (MMD)',
     'Distance between the real and simulated language in semantic space\n'
     '(Sentence-BERT embeddings, set-to-set).',
     'headline'),
    (0.2, 0.4, 5.6, 2.4, 'Fact-mention rate  (Grounding)',
     'Share of comments that explicitly cite earnings facts\n'
     '(revenue, EPS, Blackwell, guidance).',
     'headline'),
    (6.1, 0.4, 5.6, 2.4, 'Timing pattern  (Wasserstein)',
     'Distance between hourly posting profiles.\n'
     'Secondary metric: timestamps are scheduler-driven, not LLM-chosen.',
     'secondary'),
]
for x, y, w, h, title, body, kind in cards:
    fc = WHITE
    ec = NAVY if kind == 'headline' else GREY
    box(ax, x, y, w, h, '', fc=fc, ec=ec, fontcolor=NAVY)
    badge = 'Headline' if kind == 'headline' else 'Secondary'
    badge_color = NAVY if kind == 'headline' else GREY
    ax.text(x+0.2, y+h-0.35, title, fontsize=14, weight='bold', color=NAVY)
    ax.text(x+w-0.2, y+h-0.35, badge, fontsize=9, weight='bold',
            color=WHITE, ha='right',
            bbox=dict(facecolor=badge_color, edgecolor='none', boxstyle='round,pad=0.25'))
    ax.text(x+0.2, y+0.25, body, fontsize=10.5, color='#333', va='bottom')

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'metrics_plain_language.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  metrics_plain_language.png')

# ---------------------------------------------------------------
# 5. stance_rule_backup.png
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 6))
clean_ax(ax); ax.set_ylim(0, 6)
ax.set_title('Stance classifier — bullish / bearish / neutral rule',
             fontsize=15, weight='bold', color=NAVY, pad=15)

# Rule table
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

# keyword examples
ax.text(0.4, 2.4, 'Example keyword patterns (word-boundary regex, lowercased):',
        fontsize=11, weight='bold', color=NAVY)
ax.text(0.4, 1.9, 'Bullish:  buy, long, beat, strong, bullish, surge, rally, moon, upside, outperform, …  (37 patterns)',
        fontsize=10, color='#222')
ax.text(0.4, 1.5, 'Bearish:  sell, short, miss, weak, bearish, drop, dump, crash, overvalued, bubble, …  (38 patterns)',
        fontsize=10, color='#222')

# hand-audit
ax.add_patch(FancyBboxPatch((0.4, 0.15), 11.0, 1.05, boxstyle='round,pad=0,rounding_size=0.05',
                            fc=LIGHT_BG, ec=NAVY, linewidth=1.0))
ax.text(0.6, 1.0, 'Hand-audit (100 NVDA comments, fixed seed):', fontsize=11, weight='bold', color=NAVY)
ax.text(0.6, 0.65, "Cohen's κ = 0.448  ·  Accuracy = 65.0%  ·  F1: bullish 0.525 / bearish 0.718 / neutral 0.700",
        fontsize=10.5, color='#222')
ax.text(0.6, 0.30, "Distribution-level proxy. Same labeler applied to real and simulated text, so any bias cancels at the corpus level.",
        fontsize=10, color=RED, style='italic')

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'stance_rule_backup.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  stance_rule_backup.png')

# ---------------------------------------------------------------
# 6. grounding_rule_backup.png
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 6.3))
clean_ax(ax); ax.set_ylim(0, 6.5)
ax.set_title('Grounding (fact-mention) classifier — categories and thresholds',
             fontsize=15, weight='bold', color=NAVY, pad=15)

# Six categories
cats = [
    ('Revenue', '"revenue", "57", "57 billion", "$57", "sales", "top line", "62%", "YoY"'),
    ('Earnings', '"EPS", "earnings per share", "earnings", "profit", "net income", "bottom line"'),
    ('Guidance', '"guidance", "outlook", "Q4", "next quarter", "forecast", "raised", "guide higher"'),
    ('Product / AI / GPU / data centre', '"Blackwell", "GPU", "chips", "AI chip", "data center", "H100", "H200", "Hopper"'),
    ('Valuation', '"PE", "P/E", "valuation", "overvalued", "multiple", "market cap", "trillion"'),
    ('Price action', '"after hours", "AH", "dip", "sold off", "premarket"'),
]
ax.text(0.4, 5.6, 'Six keyword categories (case-insensitive):', fontsize=12, weight='bold', color=NAVY)
y = 5.1
for name, examples in cats:
    ax.text(0.6, y, '•', fontsize=12, color=NAVY)
    ax.text(0.9, y, name, fontsize=11, weight='bold', color=NAVY)
    ax.text(4.0, y, examples, fontsize=9.5, color='#333')
    y -= 0.4

# thresholds box
ax.add_patch(FancyBboxPatch((0.4, 1.6), 5.2, 1.1, boxstyle='round,pad=0,rounding_size=0.05',
                            fc=LIGHT_BG, ec=NAVY, linewidth=1.0))
ax.text(0.6, 2.45, 'Threshold rule', fontsize=11, weight='bold', color=NAVY)
ax.text(0.6, 2.12, 'Grounded:  ≥ 3 categories  OR  ≥ 2 categories + a number', fontsize=10, color='#222')
ax.text(0.6, 1.85, 'Weakly grounded:  ≥ 1 category', fontsize=10, color='#222')
ax.text(0.6, 1.7, 'Ungrounded:  zero categories', fontsize=10, color='#222')

# Real vs LLM comparison
ax.add_patch(FancyBboxPatch((5.9, 1.6), 5.2, 1.1, boxstyle='round,pad=0,rounding_size=0.05',
                            fc=LIGHT_BG, ec=RED, linewidth=1.0))
ax.text(6.1, 2.45, 'Headline contrast', fontsize=11, weight='bold', color=RED)
ax.text(6.1, 2.0, 'Real NVDA Reddit:  2.5% grounded', fontsize=11, color=NAVY, weight='bold')
ax.text(6.1, 1.7, 'Best LLM finalist:  57.4% grounded  (~22× over)', fontsize=11, color=RED, weight='bold')

ax.text(0.4, 1.1, 'Interpretation:', fontsize=11, weight='bold', color=NAVY)
ax.text(0.4, 0.7, 'Keyword coverage of the released earnings facts, not factual correctness.', fontsize=10, color='#333')
ax.text(0.4, 0.35, 'Real investors react to the news; the simulator still over-restates it.', fontsize=10, color=RED, style='italic')

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'grounding_rule_backup.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  grounding_rule_backup.png')

# ---------------------------------------------------------------
# 7. timestamp_scheduler_backup.png
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 5.8))
clean_ax(ax); ax.set_ylim(0, 6)
ax.set_title('Timestamp scheduler — cohort-conditional Gaussian (LLM does not see this)',
             fontsize=14.5, weight='bold', color=NAVY, pad=15)

# table
headers = ['Cohort', 'Distribution', 'Mean (hours from event)', 'Clip range']
rows = [
    ('Short-horizon', 'Gaussian(μ=2, σ=3)', '+2 h', '[−1 h, +12 h]'),
    ('Information-seeking', 'Gaussian(μ=6, σ=6)', '+6 h', '[0 h, +36 h]'),
    ('Long-horizon', 'Gaussian(μ=10, σ=10)', '+10 h', '[−6 h, +48 h]'),
]
# header
y = 4.4
xs = [0.4, 2.8, 5.5, 8.3]
ax.add_patch(Rectangle((0.3, y), 11.1, 0.6, fc=NAVY, ec='none'))
for x, h in zip(xs, headers):
    ax.text(x, y+0.3, h, fontsize=11, weight='bold', color=WHITE, va='center')
y -= 0.65
for i, row in enumerate(rows):
    bg = LIGHT_BG if i % 2 == 0 else WHITE
    ax.add_patch(Rectangle((0.3, y), 11.1, 0.55, fc=bg, ec='none'))
    for x, v in zip(xs, row):
        ax.text(x, y+0.28, v, fontsize=11, color='#222', va='center',
                weight=('bold' if x == xs[0] else 'normal'))
    y -= 0.6

# caveat box
ax.add_patch(FancyBboxPatch((0.3, 0.5), 11.1, 1.8, boxstyle='round,pad=0,rounding_size=0.05',
                            fc=LIGHT_BG, ec=RED, linewidth=1.2))
ax.text(0.55, 2.0, 'Important caveat:', fontsize=12, weight='bold', color=RED)
ax.text(0.55, 1.65, '• The LLM is never told the timestamp. The hour is sampled by the external scheduler before generation.',
        fontsize=10.5, color='#222')
ax.text(0.55, 1.3, '• Timestamp assignment is not content-aware (does not read the generated text).',
        fontsize=10.5, color='#222')
ax.text(0.55, 0.95, '• Wasserstein-1 therefore measures whether the scheduler is well-calibrated against real Reddit,',
        fontsize=10.5, color='#222')
ax.text(0.55, 0.65, '   not whether the LLM exhibits realistic temporal behaviour autonomously.',
        fontsize=10.5, color='#222')

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'timestamp_scheduler_backup.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  timestamp_scheduler_backup.png')

# ---------------------------------------------------------------
# 8. temperature_backup.png
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 5.8))
clean_ax(ax); ax.set_ylim(0, 6)
ax.set_title('Temperature — what it does to LLM output',
             fontsize=15, weight='bold', color=NAVY, pad=15)

# Two columns
box(ax, 0.4, 1.8, 5.0, 3.3, '', fc=LIGHT_BG, ec=NAVY, fontcolor=NAVY)
ax.text(0.6, 4.8, 'Low temperature  (τ = 0.5)', fontsize=13, weight='bold', color=NAVY)
ax.text(0.6, 4.4, 'Sampling is concentrated on the most likely tokens.', fontsize=10.5, color='#222')
ax.text(0.6, 4.05, '→ Safer, more predictable text.', fontsize=10.5, color='#222')
ax.text(0.6, 3.7, '→ More likely to restate the canonical earnings facts.', fontsize=10.5, color='#222')
ax.text(0.6, 3.35, '→ Higher fact-mention density (over-grounding).', fontsize=10.5, color=RED, weight='bold')
ax.text(0.6, 2.9, 'Sample at τ=0.5:', fontsize=10, weight='bold', color=NAVY)
ax.text(0.6, 2.45, '"Jensen, I know you\'re the guy selling the best chips in the\nworld, but I\'m just glad you\'re raising guidance again…"',
        fontsize=9.5, color='#333', style='italic')

box(ax, 6.1, 1.8, 5.0, 3.3, '', fc=LIGHT_BG, ec=RED, fontcolor=RED)
ax.text(6.3, 4.8, 'High temperature  (τ = 1.1)', fontsize=13, weight='bold', color=RED)
ax.text(6.3, 4.4, 'Sampling spreads over a wider set of tokens.', fontsize=10.5, color='#222')
ax.text(6.3, 4.05, '→ More varied, less predictable text.', fontsize=10.5, color='#222')
ax.text(6.3, 3.7, '→ Less likely to follow the analyst-summary template.', fontsize=10.5, color='#222')
ax.text(6.3, 3.35, '→ Lower fact-mention density (closer to real Reddit).', fontsize=10.5, color=GREEN, weight='bold')
ax.text(6.3, 2.9, 'Sample at τ=1.1:', fontsize=10, weight='bold', color=RED)
ax.text(6.3, 2.45, '"Jensen raising G2Q4 sounds great on paper, but\nhonestly, I need to see more on the capital…"',
        fontsize=9.5, color='#333', style='italic')

# Summary stripe at bottom
ax.add_patch(Rectangle((0.4, 0.5), 10.7, 0.85, fc=NAVY, ec='none'))
ax.text(5.75, 0.92, 'Higher temperature improves meaning-spread (MMD) but reduces fact-mention rate.',
        ha='center', va='center', fontsize=12, color=WHITE, weight='bold')

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'temperature_backup.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  temperature_backup.png')

# ---------------------------------------------------------------
# 9. content_results_dashboard.png
# ---------------------------------------------------------------
fig = plt.figure(figsize=(13, 6.5))
fig.suptitle('Main result at n = 108 — semantic similarity improves, grounding still off',
             fontsize=15, weight='bold', color=NAVY, y=0.98)

# Big-number panel (left)
ax1 = fig.add_axes([0.05, 0.12, 0.40, 0.78])
ax1.set_xlim(0,10); ax1.set_ylim(0,10); ax1.axis('off')
ax1.text(0.5, 9.3, 'Best run', fontsize=14, weight='bold', color=NAVY)
ax1.add_patch(FancyBboxPatch((0.5, 6.7), 9.0, 2.0, boxstyle='round,pad=0,rounding_size=0.15',
                             fc=NAVY, ec='none'))
ax1.text(0.8, 8.1, 'Qwen3.5-2B  +  P2_V1', fontsize=14, weight='bold', color=WHITE)
ax1.text(0.8, 7.5, 'τ = 1.1   ·   seed = 123   ·   n = 108', fontsize=11, color=WHITE)
ax1.text(0.8, 7.0, 'Reference: real NVDA Reddit corpus (n = 2,403)', fontsize=9.5, color='#e0e0e0')

# Metric tiles
def tile(ax, x, y, w, h, label, value, color, sub=''):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=0.12',
                                fc='white', ec=color, linewidth=1.5))
    ax.text(x+0.2, y+h-0.5, label, fontsize=10, weight='bold', color=color)
    ax.text(x+w/2, y+0.85, value, fontsize=22, weight='bold', color=color, ha='center')
    if sub:
        ax.text(x+w/2, y+0.35, sub, fontsize=9, color=GREY, ha='center')

tile(ax1, 0.5, 4.4, 4.3, 2.0, 'MMD (meaning spread) ↓', '0.0653', NAVY, 'lower = closer to real')
tile(ax1, 5.2, 4.4, 4.3, 2.0, 'JSD (mood mix) ↓', '0.4062', NAVY, 'lower = closer to real')
tile(ax1, 0.5, 2.1, 9.0, 2.0, 'Grounded — fact-mention rate', '', NAVY)
ax1.text(2.0, 3.05, 'Real Reddit  2.5%', fontsize=12, color=NAVY, weight='bold')
ax1.text(7.6, 3.05, 'LLM  57.4%', fontsize=12, color=RED, weight='bold')
# bars
ax1.add_patch(Rectangle((1.0, 2.5), 0.25, 0.25, fc=NAVY))
ax1.add_patch(Rectangle((1.0, 2.2), 5.74, 0.25, fc=RED))
ax1.text(0.5, 1.5, 'About 22× more fact-mentions than real Reddit.', fontsize=10.5, color=RED, style='italic')
ax1.text(0.5, 1.05, 'The simulator is becoming semantically closer,', fontsize=10, color='#333')
ax1.text(0.5, 0.65, 'but still behaves too much like an analyst note.', fontsize=10, color='#333')

# Right panel: 14-run summary scatter (MMD vs grounded), highlight semantic-first
ax2 = fig.add_axes([0.50, 0.12, 0.46, 0.78])
runs_p2v1 = [
    (0.5, 42, 0.11397, 85.2),(0.5, 123, 0.11744, 86.1),
    (0.7, 42, 0.09662, 86.1),(0.7, 123, 0.09672, 80.6),
    (0.9, 42, 0.07958, 73.1),(0.9, 123, 0.07826, 71.3),
    (1.1, 42, 0.06842, 64.8),(1.1, 123, 0.06530, 57.4),
]
runs_p0v0 = [
    (0.5, 42, 0.11589, 69.4),(0.5, 123, 0.12106, 75.9),
    (0.9, 42, 0.11028, 70.4),(0.9, 123, 0.11780, 61.1),
    (1.1, 42, 0.10878, 64.8),(1.1, 123, 0.10897, 66.7),
]
x_p2 = [r[2] for r in runs_p2v1]; y_p2 = [r[3] for r in runs_p2v1]
x_p0 = [r[2] for r in runs_p0v0]; y_p0 = [r[3] for r in runs_p0v0]
ax2.scatter(x_p0, y_p0, s=80, c=GREY, label='Qwen2.5-3B + P0_V0', alpha=0.6, edgecolor='white')
ax2.scatter(x_p2, y_p2, s=100, c=NAVY, label='Qwen3.5-2B + P2_V1  (semantic-first)',
            edgecolor='white', linewidth=1.5)
# annotate tau on P2_V1 best
ax2.annotate('τ=1.1\nbest', (0.06530, 57.4), xytext=(0.062, 38),
             fontsize=10, color=NAVY, weight='bold',
             arrowprops=dict(arrowstyle='->', color=NAVY, lw=1.2))
ax2.axhline(2.5, color=RED, ls='--', lw=1.5, alpha=0.9)
ax2.text(0.123, 5, 'Real Reddit = 2.5%', color=RED, fontsize=10)
ax2.set_xlabel('MMD semantic   (lower = closer to real)', fontsize=11)
ax2.set_ylabel('Grounded %   (lower = closer to real)', fontsize=11)
ax2.set_title('All 14 finalist runs', fontsize=12, weight='bold')
ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
ax2.legend(loc='upper right', fontsize=9)

plt.savefig(os.path.join(OUT, 'content_results_dashboard.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  content_results_dashboard.png')

# ---------------------------------------------------------------
# 10. temperature_tradeoff.png
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 6))
# semantic-first runs only, sorted by tau, averaged across the two seeds
import collections
acc = collections.defaultdict(list)
for tau, seed, mmd, gnd in runs_p2v1:
    acc[tau].append((mmd, gnd))
taus = sorted(acc.keys())
mean_mmd = [np.mean([x[0] for x in acc[t]]) for t in taus]
mean_gnd = [np.mean([x[1] for x in acc[t]]) for t in taus]

# Plot individual points and a connected mean line
for tau, seed, mmd, gnd in runs_p2v1:
    ax.scatter(mmd, gnd, s=90, c=NAVY, alpha=0.65, edgecolor='white', linewidth=1.2)

ax.plot(mean_mmd, mean_gnd, color=NAVY, lw=2.5, marker='o', markersize=11,
        markerfacecolor=NAVY, markeredgecolor='white', markeredgewidth=1.5,
        label='Qwen3.5-2B + P2_V1  (seed-averaged)')

for t, mx, my in zip(taus, mean_mmd, mean_gnd):
    ax.annotate(f'τ = {t}', (mx, my), xytext=(8, 8), textcoords='offset points',
                fontsize=11, color=NAVY, weight='bold')

# real Reddit reference
ax.axhline(2.5, color=RED, ls='--', lw=1.5)
ax.text(0.123, 4.5, 'Real Reddit grounded = 2.5%', color=RED, fontsize=10, weight='bold')

# annotations explaining direction
ax.annotate('', xy=(0.065, 25), xytext=(0.115, 25),
            arrowprops=dict(arrowstyle='->', color=GREEN, lw=2))
ax.text(0.090, 21, 'Higher temperature\n→ better MMD', ha='center', fontsize=10, color=GREEN, weight='bold')

ax.set_xlabel('MMD semantic   (lower = closer to real Reddit)', fontsize=12)
ax.set_ylabel('Grounded %   (lower = closer to real Reddit)', fontsize=12)
ax.set_title('Temperature trade-off in the semantic-first finalist (Qwen3.5-2B + P2_V1)',
             fontsize=14, weight='bold', color=NAVY)
ax.set_ylim(0, 100)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
ax.legend(loc='lower right', fontsize=10)

# bottom caption box
fig.text(0.5, 0.005, 'Message:  higher temperature improves meaning-spread (MMD) and reduces fact-mention rate, '
                    'but the best run still grounds ~57% vs real Reddit ~2.5%.',
         ha='center', fontsize=10.5, color=NAVY, style='italic',
         bbox=dict(facecolor=LIGHT_BG, edgecolor=NAVY, boxstyle='round,pad=0.4'))

plt.tight_layout(rect=[0, 0.06, 1, 1])
plt.savefig(os.path.join(OUT, 'temperature_tradeoff.png'), dpi=200, bbox_inches='tight')
plt.close()
print('  temperature_tradeoff.png')

print('\nAll figures written to', OUT)
