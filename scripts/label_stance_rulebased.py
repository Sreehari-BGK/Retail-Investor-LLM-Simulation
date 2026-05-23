"""
label_stance_rulebased.py
Provisional rule-based stance labeling for real Reddit comments.

Method: keyword counting with weighted lists.
- Count bullish-keyword matches in lowercased text
- Count bearish-keyword matches in lowercased text
- Assign: bullish if bull_count > bear_count
          bearish if bear_count > bull_count
          neutral if tied (including 0-0)

This is PROVISIONAL. It is transparent and reproducible but does not use
a trained classifier. Limitations: does not handle negation, sarcasm, or
context. Accuracy on financial Reddit text is estimated ~55-65% vs ground
truth (based on published results for simple keyword baselines on StockTwits).

Reference for keyword lists: adapted from Loughran & McDonald (2011)
financial sentiment word lists and common Reddit investor slang.
"""

import re
import pandas as pd

# ---------------------------------------------------------------------------
# Keyword lists — lowercase, matched as word-boundary substrings
# ---------------------------------------------------------------------------
BULLISH_KEYWORDS = [
    r'\bbull(ish)?\b', r'\bbuy\b', r'\bbuying\b', r'\bbought\b',
    r'\blong\b', r'\bcalls?\b', r'\bbeat\b', r'\bbeats?\b',
    r'\bstrong\b', r'\bsolid\b', r'\bgrowth\b', r'\bgained?\b',
    r'\bprofit\b', r'\bprofitable\b', r'\bgood\b', r'\bgreat\b',
    r'\bimpressive\b', r'\bgreen\b', r'\brise\b', r'\brising\b',
    r'\bsurge\b', r'\bsurging\b', r'\brally\b', r'\bbreakout\b',
    r'\bhold\b', r'\bholding\b', r'\badd(ing)?\b', r'\bmoon\b',
    r'\bupside\b', r'\boutperform\b', r'\bexceed(ed|ing)?\b',
    r'\bbetter than expected\b', r'\brecord\b', r'\bhigh(er)?\b',
    r'\bpositive\b', r'\boptimist(ic)?\b', r'\bconfident\b',
]

BEARISH_KEYWORDS = [
    r'\bbear(ish)?\b', r'\bsell\b', r'\bselling\b', r'\bsold\b',
    r'\bshort(ing)?\b', r'\bputs?\b', r'\bmiss(ed|ing)?\b',
    r'\bweak\b', r'\bdown\b', r'\bcrash(ing)?\b', r'\bdump(ing)?\b',
    r'\bdrop(ping)?\b', r'\bdecline\b', r'\bdeclining\b',
    r'\bbad\b', r'\bpoor\b', r'\bdisappoint(ed|ing|ment)?\b',
    r'\bred\b', r'\blow(er)?\b', r'\bcorrection\b', r'\bovervalued?\b',
    r'\bbubble\b', r'\bfad(e|ing)\b', r'\bexit\b', r'\bworried?\b',
    r'\bconcern(ed|ing)?\b', r'\bnegative\b', r'\bpessimist(ic)?\b',
    r'\boverextend\b', r'\btopped?\b', r'\bfear(ful)?\b',
    r'\brisky?\b', r'\bavoid\b',
]

_BULL_PATTERNS = [re.compile(p) for p in BULLISH_KEYWORDS]
_BEAR_PATTERNS = [re.compile(p) for p in BEARISH_KEYWORDS]


def label_text(text: str) -> str:
    """Return 'bullish', 'bearish', or 'neutral' for a single comment."""
    t = str(text).lower()
    bull = sum(1 for p in _BULL_PATTERNS if p.search(t))
    bear = sum(1 for p in _BEAR_PATTERNS if p.search(t))
    if bull > bear:
        return 'bullish'
    elif bear > bull:
        return 'bearish'
    else:
        return 'neutral'


def main(input_csv: str, output_csv: str):
    df = pd.read_csv(input_csv)
    print(f'Loaded {len(df)} rows from {input_csv}')

    df['stance'] = df['text'].apply(label_text)

    # Report distribution
    print('\nStance distribution:')
    counts = df['stance'].value_counts()
    for label, n in counts.items():
        print(f'  {label}: {n} ({n/len(df)*100:.1f}%)')

    print('\nPer event:')
    print(df.groupby(['event_id', 'stance']).size().unstack(fill_value=0).to_string())

    df.to_csv(output_csv, index=False)
    print(f'\nSaved {len(df)} labeled rows to {output_csv}')
    print('\nNOTE: Labels are PROVISIONAL rule-based. Not validated against human annotations.')


if __name__ == '__main__':
    main('data/processed/real_comments.csv',
         'data/processed/real_comments_labeled.csv')
