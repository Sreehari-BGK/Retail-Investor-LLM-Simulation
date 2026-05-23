"""
00_make_synthetic_data.py
Generate a small synthetic dataset to test the pipeline without real Reddit data.
Run this first if you don't have real data yet.
"""

import numpy as np
import pandas as pd
import random

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

STANCES = ["bullish", "bearish", "neutral"]

REAL_TEMPLATES = [
    "Beat EPS estimates by a wide margin. Adding to my position here.",
    "Revenue miss despite EPS beat. Guidance looks weak. Selling.",
    "Not sure how to read this. Will wait for analyst notes.",
    "This is a solid quarter. Long term bull on this one.",
    "Margins are contracting. That worries me more than the headline number.",
    "Short squeeze incoming. Shorts are getting crushed.",
    "Underwhelming guidance for next quarter. Market overreacting.",
    "The numbers are better than feared. Holding my shares.",
    "Volume on puts spiked before announcement. Something is off.",
    "Good report but priced in already. Not chasing.",
    "FCF growth is the real story here, not EPS.",
    "Sold half my position into the pop. Let the rest ride.",
    "Bears were wrong. Simple as that.",
    "This is a dead-cat bounce. Fundamentals are deteriorating.",
    "Q4 comps will be tough. Cautiously watching.",
]

NAIVE_TEMPLATES = [
    "This company just released its earnings report.",
    "Investors are discussing the quarterly results.",
    "The earnings announcement has been made public.",
    "Analysts are reviewing the latest financial figures.",
    "The company reported its earnings for this quarter.",
]

STANCE_MAP = {
    "Beat EPS estimates by a wide margin. Adding to my position here.": "bullish",
    "Revenue miss despite EPS beat. Guidance looks weak. Selling.": "bearish",
    "Not sure how to read this. Will wait for analyst notes.": "neutral",
    "This is a solid quarter. Long term bull on this one.": "bullish",
    "Margins are contracting. That worries me more than the headline number.": "bearish",
    "Short squeeze incoming. Shorts are getting crushed.": "bullish",
    "Underwhelming guidance for next quarter. Market overreacting.": "bearish",
    "The numbers are better than feared. Holding my shares.": "bullish",
    "Volume on puts spiked before announcement. Something is off.": "bearish",
    "Good report but priced in already. Not chasing.": "neutral",
    "FCF growth is the real story here, not EPS.": "bullish",
    "Sold half my position into the pop. Let the rest ride.": "neutral",
    "Bears were wrong. Simple as that.": "bullish",
    "This is a dead-cat bounce. Fundamentals are deteriorating.": "bearish",
    "Q4 comps will be tough. Cautiously watching.": "neutral",
}

EVENTS = [
    {"event_id": "AAPL_Q4_2023", "ticker": "AAPL",
     "event_time": "2023-11-02 17:00:00", "subreddit": "stocks"},
    {"event_id": "NVDA_Q3_2023", "ticker": "NVDA",
     "event_time": "2023-11-21 16:30:00", "subreddit": "wallstreetbets"},
    {"event_id": "META_Q3_2023", "ticker": "META",
     "event_time": "2023-10-25 17:00:00", "subreddit": "stocks"},
]


def make_real_comments(event, n=60):
    rows = []
    for i in range(n):
        # Most activity between -2h and +12h; lighter before and after
        if i < 10:
            hours = np.random.uniform(-24, -2)
        elif i < 50:
            hours = np.random.uniform(-2, 12)
        else:
            hours = np.random.uniform(12, 48)

        text = random.choice(REAL_TEMPLATES)
        stance = STANCE_MAP.get(text, "neutral")
        rows.append({
            "event_id": event["event_id"],
            "ticker": event["ticker"],
            "event_time": event["event_time"],
            "subreddit": event["subreddit"],
            "thread_id": f"thread_{event['ticker']}_{i // 10}",
            "comment_id": f"c_{event['ticker']}_{i:03d}",
            "parent_id": f"thread_{event['ticker']}_{i // 10}" if i % 10 == 0 else f"c_{event['ticker']}_{(i // 10) * 10:03d}",
            "hours_from_event": round(hours, 2),
            "text": text,
            "score": int(np.random.lognormal(2, 1.5)),
            "depth": 0 if i % 10 == 0 else np.random.randint(1, 4),
            "source_type": "real",
            "stance": stance,
        })
    return rows


def make_naive_sim_comments(event, n=40):
    rows = []
    for i in range(n):
        # Naive sim: uniformly spread, no clustering around event
        hours = np.random.uniform(-24, 48)
        text = random.choice(NAIVE_TEMPLATES)
        stance = random.choice(STANCES)
        rows.append({
            "event_id": event["event_id"],
            "ticker": event["ticker"],
            "event_time": event["event_time"],
            "subreddit": event["subreddit"],
            "thread_id": f"sim_thread_{event['ticker']}_{i // 8}",
            "comment_id": f"sim_c_{event['ticker']}_{i:03d}",
            "parent_id": f"sim_thread_{event['ticker']}_{i // 8}",
            "hours_from_event": round(hours, 2),
            "text": text,
            "score": 1,
            "depth": 0,
            "source_type": "sim_naive",
            "stance": stance,
        })
    return rows


def main():
    all_rows = []
    for event in EVENTS:
        all_rows.extend(make_real_comments(event, n=60))
        all_rows.extend(make_naive_sim_comments(event, n=40))

    df = pd.DataFrame(all_rows)
    out_path = "data/processed/comments.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")
    print(df["source_type"].value_counts())
    print(df["stance"].value_counts())


if __name__ == "__main__":
    main()
