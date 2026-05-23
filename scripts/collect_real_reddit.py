"""
collect_real_reddit.py
Real Reddit data collection via public JSON API (no OAuth required).
Collects comments around earnings event windows.

Events confirmed via SEC EDGAR 8-K Item 2.02 filings.
Event times set to 21:00 UTC on the filing date (4pm ET market close),
consistent with standard after-hours earnings release convention.
"""

import requests
import time
import json
import datetime
import os
import csv

HEADERS = {
    'User-Agent': 'academic-research-bot/0.1 (UQ student project, non-commercial research)'
}

# Event windows (-24h to +48h around event_time)
EVENTS = [
    {
        'event_id': 'NVDA_Q3FY26',
        'ticker': 'NVDA',
        'event_time': datetime.datetime(2025, 11, 19, 21, 0, 0, tzinfo=datetime.timezone.utc),
        'sec_8k_accession': '0001045810-25-000228',
        'sec_8k_url': 'https://www.sec.gov/Archives/edgar/data/1045810/000104581025000228/0001045810-25-000228-index.htm',
        'sec_submissions_url': 'https://data.sec.gov/submissions/CIK0001045810.json',
        'queries': ['NVDA earnings', 'Nvidia earnings', 'Nvidia Q3 2026', '$NVDA earnings'],
        'subreddits': ['stocks', 'wallstreetbets'],
    },
    {
        'event_id': 'META_Q3_2025',
        'ticker': 'META',
        'event_time': datetime.datetime(2025, 10, 29, 21, 0, 0, tzinfo=datetime.timezone.utc),
        'sec_8k_accession': '0001628280-25-047114',
        'sec_8k_url': 'https://www.sec.gov/Archives/edgar/data/1326801/000162828025047114/0001628280-25-047114-index.htm',
        'sec_submissions_url': 'https://data.sec.gov/submissions/CIK0001326801.json',
        'queries': ['META earnings', 'Meta earnings Q3', '$META earnings', 'Facebook earnings'],
        'subreddits': ['stocks', 'wallstreetbets'],
    },
    {
        'event_id': 'AAPL_Q4FY25',
        'ticker': 'AAPL',
        'event_time': datetime.datetime(2025, 10, 30, 21, 0, 0, tzinfo=datetime.timezone.utc),
        'sec_8k_accession': '0000320193-25-000077',
        'sec_8k_url': 'https://www.sec.gov/Archives/edgar/data/320193/000032019325000077/0000320193-25-000077-index.htm',
        'sec_submissions_url': 'https://data.sec.gov/submissions/CIK0000320193.json',
        'queries': ['AAPL earnings', 'Apple earnings Q4', '$AAPL earnings', 'Apple Q4 2025'],
        'subreddits': ['stocks', 'wallstreetbets'],
    },
]

WINDOW_BEFORE_H = 24
WINDOW_AFTER_H = 48

# Reddit API rate limit: max 1 req/sec without OAuth
REQUEST_DELAY = 1.2


def get_window(event_time):
    return (
        event_time - datetime.timedelta(hours=WINDOW_BEFORE_H),
        event_time + datetime.timedelta(hours=WINDOW_AFTER_H),
    )


def hours_from_event(ts, event_time):
    return (ts - event_time).total_seconds() / 3600.0


def reddit_get(url, params=None, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=20)
            if r.status_code == 429:
                wait = int(r.headers.get('Retry-After', 60))
                print(f'    Rate limited — waiting {wait}s')
                time.sleep(wait)
                continue
            return r
        except requests.RequestException as e:
            print(f'    Request error ({attempt+1}/{retries}): {e}')
            time.sleep(5)
    return None


def search_posts(subreddit, query, event):
    window_start, window_end = get_window(event['event_time'])
    posts = []
    seen = set()

    # Try t=year and t=month; filter locally by timestamp
    for timefilter in ['year', 'month']:
        url = f'https://www.reddit.com/r/{subreddit}/search.json'
        params = {
            'q': query,
            'sort': 'new',
            'restrict_sr': 'on',
            'limit': 100,
            't': timefilter,
        }
        r = reddit_get(url, params)
        time.sleep(REQUEST_DELAY)

        if not r or r.status_code != 200:
            print(f'    Search failed: {r.status_code if r else "no response"}')
            continue

        try:
            data = r.json()
        except Exception as e:
            print(f'    JSON parse error: {e}')
            continue

        children = data.get('data', {}).get('children', [])
        for child in children:
            p = child.get('data', {})
            post_id = p.get('id', '')
            if post_id in seen:
                continue
            post_ts = datetime.datetime.fromtimestamp(
                p.get('created_utc', 0), tz=datetime.timezone.utc
            )
            if window_start <= post_ts <= window_end:
                posts.append({
                    'id': post_id,
                    'title': p.get('title', ''),
                    'selftext': p.get('selftext', ''),
                    'score': p.get('score', 0),
                    'created_utc': p.get('created_utc', 0),
                    'ts': post_ts,
                    'subreddit': subreddit,
                })
                seen.add(post_id)

    return posts


def collect_comments(post, event):
    post_id = post['id']
    subreddit = post['subreddit']
    event_time = event['event_time']
    window_start, window_end = get_window(event_time)

    url = f'https://www.reddit.com/r/{subreddit}/comments/{post_id}.json'
    params = {'limit': 500, 'depth': 10}
    r = reddit_get(url, params)
    time.sleep(REQUEST_DELAY)

    if not r or r.status_code != 200:
        return []

    try:
        data = r.json()
    except Exception:
        return []

    rows = []

    # First element is the post itself, second is comments
    # Add the post as a row
    post_ts = post['ts']
    post_text = (post['title'] + ' ' + post['selftext']).strip()
    if len(post_text) >= 10 and window_start <= post_ts <= window_end:
        rows.append({
            'event_id': event['event_id'],
            'ticker': event['ticker'],
            'event_time': event['event_time'].isoformat(),
            'subreddit': subreddit,
            'thread_id': post_id,
            'comment_id': post_id,
            'parent_id': None,
            'timestamp': post_ts.isoformat(),
            'hours_from_event': round(hours_from_event(post_ts, event_time), 4),
            'text': post_text,
            'score': post['score'],
            'depth': 0,
            'source_type': 'real',
        })

    # Walk comment tree
    def walk(comments, depth=1):
        for item in comments:
            if item.get('kind') != 't1':
                continue
            c = item.get('data', {})
            c_id = c.get('id', '')
            c_ts_raw = c.get('created_utc', 0)
            if not c_ts_raw:
                continue
            c_ts = datetime.datetime.fromtimestamp(c_ts_raw, tz=datetime.timezone.utc)
            c_text = c.get('body', '')
            if (len(c_text) >= 10
                    and c_text not in ('[deleted]', '[removed]')
                    and window_start <= c_ts <= window_end):
                rows.append({
                    'event_id': event['event_id'],
                    'ticker': event['ticker'],
                    'event_time': event['event_time'].isoformat(),
                    'subreddit': subreddit,
                    'thread_id': post_id,
                    'comment_id': c_id,
                    'parent_id': c.get('parent_id', ''),
                    'timestamp': c_ts.isoformat(),
                    'hours_from_event': round(hours_from_event(c_ts, event_time), 4),
                    'text': c_text,
                    'score': c.get('score', 0),
                    'depth': depth,
                    'source_type': 'real',
                })
            replies = c.get('replies', {})
            if isinstance(replies, dict):
                walk(replies.get('data', {}).get('children', []), depth + 1)

    if len(data) >= 2:
        comment_listing = data[1].get('data', {}).get('children', [])
        walk(comment_listing, depth=1)

    return rows


def main():
    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)

    all_rows = []
    collection_log = []

    for event in EVENTS:
        event_rows = []
        post_ids_seen = set()
        print(f'\n=== Collecting {event["event_id"]} ===')
        print(f'    Event time: {event["event_time"].isoformat()}')
        w_start, w_end = get_window(event['event_time'])
        print(f'    Window: {w_start.isoformat()} to {w_end.isoformat()}')

        for sub in event['subreddits']:
            sub_posts = []
            for query in event['queries']:
                print(f'  Searching r/{sub} for "{query}" ...')
                posts = search_posts(sub, query, event)
                new_posts = [p for p in posts if p['id'] not in post_ids_seen]
                post_ids_seen.update(p['id'] for p in new_posts)
                sub_posts.extend(new_posts)
                print(f'    Found {len(new_posts)} new posts in window')

            print(f'  Collecting comments from {len(sub_posts)} posts in r/{sub} ...')
            for post in sub_posts:
                print(f'    post {post["id"]}: {post["title"][:50]}')
                rows = collect_comments(post, event)
                event_rows.extend(rows)
                print(f'      {len(rows)} comments/replies in window')

        # Save raw per-event file
        if event_rows:
            raw_path = f'data/raw/real_reddit_{event["event_id"]}.csv'
            fieldnames = [
                'event_id', 'ticker', 'event_time', 'subreddit',
                'thread_id', 'comment_id', 'parent_id', 'timestamp',
                'hours_from_event', 'text', 'score', 'depth', 'source_type'
            ]
            with open(raw_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(event_rows)
            print(f'\n  Saved {len(event_rows)} rows to {raw_path}')
        else:
            print(f'\n  WARNING: 0 rows collected for {event["event_id"]}')

        collection_log.append({
            'event_id': event['event_id'],
            'ticker': event['ticker'],
            'event_time': event['event_time'].isoformat(),
            'sec_8k_accession': event['sec_8k_accession'],
            'sec_8k_url': event['sec_8k_url'],
            'rows_collected': len(event_rows),
            'posts_found': len(post_ids_seen),
        })
        all_rows.extend(event_rows)

    # Save combined processed file
    if all_rows:
        proc_path = 'data/processed/real_comments.csv'
        fieldnames = [
            'event_id', 'ticker', 'event_time', 'subreddit',
            'thread_id', 'comment_id', 'parent_id', 'timestamp',
            'hours_from_event', 'text', 'score', 'depth', 'source_type'
        ]
        with open(proc_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)
        print(f'\n=== Combined: {len(all_rows)} total real rows -> {proc_path} ===')

    # Save collection log
    log_path = 'data/raw/collection_log.json'
    with open(log_path, 'w') as f:
        json.dump(collection_log, f, indent=2)
    print(f'Collection log -> {log_path}')

    # Print summary
    print('\n=== COLLECTION SUMMARY ===')
    for entry in collection_log:
        print(f'  {entry["event_id"]}: {entry["rows_collected"]} rows from {entry["posts_found"]} posts')


if __name__ == '__main__':
    main()
