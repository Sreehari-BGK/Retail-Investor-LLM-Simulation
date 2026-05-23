"""
01_collect_reddit.py
Collect Reddit comments around earnings events using PRAW.

Usage:
    Set environment variables REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
    or fill in the constants below.
    Then: python 01_collect_reddit.py

Output: data/raw/reddit_raw_{ticker}_{event_id}.csv for each event.
"""

import os
import datetime
import time
import pandas as pd
import praw

# ---------------------------------------------------------------------------
# CONFIGURATION — fill these in or set as environment variables
# ---------------------------------------------------------------------------
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "YOUR_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "llm-investor-sim/0.1")

# Pilot events: quarterly earnings announcements
# event_time is the official earnings release time (UTC)
PILOT_EVENTS = [
    {
        "event_id": "AAPL_Q4_2023",
        "ticker": "AAPL",
        "event_time": datetime.datetime(2023, 11, 2, 17, 0, 0,
                                        tzinfo=datetime.timezone.utc),
        "keywords": ["AAPL", "Apple earnings", "Apple Q4"],
        "subreddits": ["stocks", "wallstreetbets"],
    },
    {
        "event_id": "NVDA_Q3_2023",
        "ticker": "NVDA",
        "event_time": datetime.datetime(2023, 11, 21, 16, 30, 0,
                                        tzinfo=datetime.timezone.utc),
        "keywords": ["NVDA", "Nvidia earnings", "Nvidia Q3"],
        "subreddits": ["stocks", "wallstreetbets"],
    },
    {
        "event_id": "META_Q3_2023",
        "ticker": "META",
        "event_time": datetime.datetime(2023, 10, 25, 17, 0, 0,
                                        tzinfo=datetime.timezone.utc),
        "keywords": ["META", "Meta earnings", "Meta Q3"],
        "subreddits": ["stocks", "wallstreetbets"],
    },
]

WINDOW_BEFORE_H = 24   # hours before event
WINDOW_AFTER_H = 48    # hours after event
MAX_POSTS = 50         # search results to scan per keyword per subreddit


def hours_from_event(comment_dt: datetime.datetime,
                     event_dt: datetime.datetime) -> float:
    delta = comment_dt - event_dt
    return delta.total_seconds() / 3600.0


def collect_event(reddit: praw.Reddit, event: dict) -> list[dict]:
    event_time = event["event_time"]
    window_start = event_time - datetime.timedelta(hours=WINDOW_BEFORE_H)
    window_end = event_time + datetime.timedelta(hours=WINDOW_AFTER_H)

    rows = []
    seen_ids = set()

    for subreddit_name in event["subreddits"]:
        subreddit = reddit.subreddit(subreddit_name)

        for keyword in event["keywords"]:
            print(f"  Searching r/{subreddit_name} for '{keyword}' ...")
            try:
                results = subreddit.search(
                    query=keyword,
                    sort="new",
                    time_filter="month",
                    limit=MAX_POSTS,
                )
            except Exception as e:
                print(f"    Search error: {e}")
                continue

            for post in results:
                post_time = datetime.datetime.fromtimestamp(
                    post.created_utc, tz=datetime.timezone.utc
                )
                if not (window_start <= post_time <= window_end):
                    continue

                # Collect post itself as a comment
                if post.id not in seen_ids:
                    seen_ids.add(post.id)
                    rows.append({
                        "event_id": event["event_id"],
                        "ticker": event["ticker"],
                        "event_time": event_time.isoformat(),
                        "subreddit": subreddit_name,
                        "thread_id": post.id,
                        "comment_id": post.id,
                        "parent_id": None,
                        "timestamp": post_time.isoformat(),
                        "hours_from_event": hours_from_event(post_time, event_time),
                        "text": post.title + " " + (post.selftext or ""),
                        "score": post.score,
                        "depth": 0,
                        "source_type": "real",
                        "stance": None,  # filled in later
                    })

                # Collect all comments in the thread
                try:
                    post.comments.replace_more(limit=0)
                    for comment in post.comments.list():
                        if comment.id in seen_ids:
                            continue
                        seen_ids.add(comment.id)
                        c_time = datetime.datetime.fromtimestamp(
                            comment.created_utc, tz=datetime.timezone.utc
                        )
                        if not (window_start <= c_time <= window_end):
                            continue
                        rows.append({
                            "event_id": event["event_id"],
                            "ticker": event["ticker"],
                            "event_time": event_time.isoformat(),
                            "subreddit": subreddit_name,
                            "thread_id": post.id,
                            "comment_id": comment.id,
                            "parent_id": comment.parent_id,
                            "timestamp": c_time.isoformat(),
                            "hours_from_event": hours_from_event(c_time, event_time),
                            "text": comment.body,
                            "score": comment.score,
                            "depth": comment.depth if hasattr(comment, "depth") else None,
                            "source_type": "real",
                            "stance": None,
                        })
                except Exception as e:
                    print(f"    Comment fetch error for post {post.id}: {e}")

                time.sleep(0.5)  # polite rate limiting

    return rows


def main():
    if REDDIT_CLIENT_ID == "YOUR_CLIENT_ID":
        print("ERROR: Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET before running.")
        print("       Or run 00_make_synthetic_data.py to generate synthetic data.")
        return

    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )

    os.makedirs("data/raw", exist_ok=True)

    for event in PILOT_EVENTS:
        print(f"\nCollecting event: {event['event_id']}")
        rows = collect_event(reddit, event)
        if not rows:
            print(f"  No data found for {event['event_id']}")
            continue
        df = pd.DataFrame(rows)
        out_path = f"data/raw/reddit_raw_{event['event_id']}.csv"
        df.to_csv(out_path, index=False)
        print(f"  Saved {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main()
