#!/usr/bin/env python3
"""
Tweet Deleter + Unliker - Interleaved Edition
Alternates between deleting tweets and unliking to use both rate limits simultaneously.

Run with: python3 delete_interleaved.py
Background: nohup python3 delete_interleaved.py > deleter.log 2>&1 &
"""

import os
import sys
import time
import json
import re
import signal
from datetime import datetime

try:
    import tweepy
except ImportError:
    print("pip install tweepy")
    sys.exit(1)

# === CONFIGURATION ===
CONFIG_FILE = "config.json"
ARCHIVE_FILE = "tweets.js"
LIKES_FILE = "like.js"
WHITELIST_FILE = "whitelist.txt"  # Only for tweets, likes are all deleted

# Progress tracking (separate for tweets and likes)
TWEETS_PROGRESS = "progress_tweets.txt"
LIKES_PROGRESS = "progress_likes.txt"
LOG_FILE = "deletion.log"

# Pacing - minimum seconds between same-type operations
# With proper rate limit detection, we can go faster and just wait when limited
DELAY_BETWEEN_SAME_TYPE = 3  # seconds (will auto-wait on rate limit)

# === END CONFIGURATION ===


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def load_archive(filepath: str, item_type: str) -> list:
    if not os.path.exists(filepath):
        return []
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    json_str = re.sub(r'^window\.YTD\.\w+\.part0\s*=\s*', '', content)
    data = json.loads(json_str)
    
    items = []
    for item in data:
        if item_type == 'tweets' and 'tweet' in item:
            t = item['tweet']
            items.append({
                'id': t.get('id_str') or str(t.get('id')),
                'text': t.get('full_text', ''),
                'date': t.get('created_at', ''),
                'type': 'retweet' if t.get('full_text', '').startswith('RT @') else 'tweet'
            })
        elif item_type == 'likes' and 'like' in item:
            l = item['like']
            items.append({
                'id': l.get('tweetId'),
                'text': l.get('fullText', ''),
                'date': '',
                'type': 'like'
            })
    return items


def load_set(filepath: str) -> set:
    ids = set()
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "/" in line:
                        line = line.rstrip("/").split("/")[-1].split("?")[0]
                    ids.add(line)
    return ids


def save_id(filepath: str, tweet_id: str):
    with open(filepath, "a") as f:
        f.write(f"{tweet_id}\n")


def get_client(config: dict) -> tweepy.Client:
    return tweepy.Client(
        bearer_token=config.get("bearer_token"),
        consumer_key=config.get("api_key"),
        consumer_secret=config.get("api_secret"),
        access_token=config.get("access_token"),
        access_token_secret=config.get("access_token_secret"),
        wait_on_rate_limit=False
    )


def do_action(client, item: dict) -> tuple:
    """Returns: (status, reset_timestamp)
    status: 'done', 'rate_limit', 'error'
    reset_timestamp: unix timestamp when rate limit resets (or None)
    """
    tid = item['id']
    ttype = item['type']
    
    try:
        if ttype == 'like':
            client.unlike(tid)
        else:
            client.delete_tweet(tid)
        return ('done', None)
    except tweepy.NotFound:
        return ('done', None)  # Already gone
    except tweepy.Forbidden:
        return ('done', None)  # Can't delete, skip
    except tweepy.TooManyRequests as e:
        # Get reset time from response headers
        reset_time = None
        if hasattr(e, 'response') and e.response is not None:
            reset_ts = e.response.headers.get('x-rate-limit-reset')
            if reset_ts:
                reset_time = int(reset_ts)
        return ('rate_limit', reset_time)
    except Exception as e:
        log(f"    Error: {e}")
        return ('error', None)


def main():
    log("=" * 60)
    log("Tweet Deleter + Unliker - Interleaved Mode")
    log("=" * 60)
    
    config = load_config()
    client = get_client(config)
    
    # Load tweets
    log(f"Loading tweets: {ARCHIVE_FILE}")
    all_tweets = load_archive(ARCHIVE_FILE, 'tweets')
    log(f"  Found {len(all_tweets)} tweets/retweets")
    
    # Load likes
    log(f"Loading likes: {LIKES_FILE}")
    all_likes = load_archive(LIKES_FILE, 'likes')
    log(f"  Found {len(all_likes)} likes")
    
    # Load whitelist (only for tweets)
    whitelist = load_set(WHITELIST_FILE)
    log(f"Tweet whitelist: {len(whitelist)} IDs")
    
    # Load progress
    done_tweets = load_set(TWEETS_PROGRESS)
    done_likes = load_set(LIKES_PROGRESS)
    log(f"Already done: {len(done_tweets)} tweets, {len(done_likes)} likes")
    
    # Build queues
    tweet_queue = [t for t in all_tweets if t['id'] not in whitelist and t['id'] not in done_tweets]
    like_queue = [l for l in all_likes if l['id'] not in done_likes]
    
    # Sort tweets oldest first
    def parse_date(d):
        try:
            return datetime.strptime(d, "%a %b %d %H:%M:%S %z %Y")
        except:
            return datetime.min.replace(tzinfo=None)
    
    tweet_queue.sort(key=lambda t: parse_date(t['date']) if t['date'] else datetime.min.replace(tzinfo=None))
    
    log(f"\nQueues: {len(tweet_queue)} tweets, {len(like_queue)} likes")
    
    total = len(tweet_queue) + len(like_queue)
    if total == 0:
        log("Nothing to do!")
        return
    
    # Estimate time (interleaved = 2x speed)
    est_seconds = total * (DELAY_BETWEEN_SAME_TYPE / 2)
    est_hours = est_seconds / 3600
    log(f"Estimated time: {est_hours:.1f} hours")
    log("")
    
    # Counters
    tweets_deleted = 0
    likes_deleted = 0
    tweet_idx = 0
    like_idx = 0
    
    # Track last action time per type
    last_tweet_time = 0
    last_like_time = 0
    
    # Track rate limit reset times
    tweet_reset_time = 0
    like_reset_time = 0
    
    # Interleave: alternate between tweets and likes
    while tweet_idx < len(tweet_queue) or like_idx < len(like_queue):
        now = time.time()
        
        # Check if rate limited
        tweet_rate_limited = now < tweet_reset_time
        like_rate_limited = now < like_reset_time
        
        # Decide what to do next based on which is ready
        can_tweet = (tweet_idx < len(tweet_queue) and 
                     not tweet_rate_limited and
                     (now - last_tweet_time >= DELAY_BETWEEN_SAME_TYPE))
        can_like = (like_idx < len(like_queue) and 
                    not like_rate_limited and
                    (now - last_like_time >= DELAY_BETWEEN_SAME_TYPE))
        
        action = None
        
        if can_tweet and can_like:
            # Both ready, alternate (prefer whichever waited longer)
            if last_tweet_time <= last_like_time:
                action = 'tweet'
            else:
                action = 'like'
        elif can_tweet:
            action = 'tweet'
        elif can_like:
            action = 'like'
        else:
            # Neither ready - figure out why and wait appropriately
            tweets_remaining = tweet_idx < len(tweet_queue)
            likes_remaining = like_idx < len(like_queue)
            
            # If both are rate limited, wait until the earlier reset
            if tweets_remaining and likes_remaining and tweet_rate_limited and like_rate_limited:
                wait_until = min(tweet_reset_time, like_reset_time)
                wait_secs = wait_until - now
                if wait_secs > 0:
                    wait_mins = wait_secs / 60
                    log(f"    Both rate limited. Waiting {wait_mins:.1f} minutes until reset...")
                    time.sleep(wait_secs + 1)
                continue
            
            # If only one type left and it's rate limited, wait for its reset
            if tweets_remaining and not likes_remaining and tweet_rate_limited:
                wait_secs = tweet_reset_time - now
                if wait_secs > 0:
                    wait_mins = wait_secs / 60
                    log(f"    Tweets rate limited. Waiting {wait_mins:.1f} minutes until reset...")
                    time.sleep(wait_secs + 1)
                continue
            
            if likes_remaining and not tweets_remaining and like_rate_limited:
                wait_secs = like_reset_time - now
                if wait_secs > 0:
                    wait_mins = wait_secs / 60
                    log(f"    Likes rate limited. Waiting {wait_mins:.1f} minutes until reset...")
                    time.sleep(wait_secs + 1)
                continue
            
            # Otherwise just wait for the delay
            wait = min(
                DELAY_BETWEEN_SAME_TYPE - (now - last_tweet_time) if tweets_remaining else 9999,
                DELAY_BETWEEN_SAME_TYPE - (now - last_like_time) if likes_remaining else 9999
            )
            if wait > 0:
                time.sleep(min(wait, 5))
            continue
        
        # Execute action
        if action == 'tweet':
            item = tweet_queue[tweet_idx]
            progress = f"[T:{tweet_idx+1}/{len(tweet_queue)} L:{like_idx}/{len(like_queue)}]"
            preview = item['text'][:40].replace('\n', ' ') if item['text'] else ''
            log(f"{progress} DELETE {item['type'].upper()} {item['id']} | {preview}...")
            
            result, reset_ts = do_action(client, item)
            
            if result == 'done':
                save_id(TWEETS_PROGRESS, item['id'])
                tweets_deleted += 1
                tweet_idx += 1
                last_tweet_time = time.time()
            elif result == 'rate_limit':
                if reset_ts:
                    tweet_reset_time = reset_ts
                    wait_secs = reset_ts - time.time()
                    log(f"    ⏳ Tweet rate limited. Reset in {wait_secs/60:.1f} minutes")
                else:
                    tweet_reset_time = time.time() + 900  # Default 15 min
                    log(f"    ⏳ Tweet rate limited. Waiting 15 minutes (no reset header)")
            else:
                tweet_idx += 1  # Skip on error
                
        elif action == 'like':
            item = like_queue[like_idx]
            progress = f"[T:{tweet_idx}/{len(tweet_queue)} L:{like_idx+1}/{len(like_queue)}]"
            preview = item['text'][:40].replace('\n', ' ') if item['text'] else ''
            log(f"{progress} UNLIKE {item['id']} | {preview}...")
            
            result, reset_ts = do_action(client, item)
            
            if result == 'done':
                save_id(LIKES_PROGRESS, item['id'])
                likes_deleted += 1
                like_idx += 1
                last_like_time = time.time()
            elif result == 'rate_limit':
                if reset_ts:
                    like_reset_time = reset_ts
                    wait_secs = reset_ts - time.time()
                    log(f"    ⏳ Like rate limited. Reset in {wait_secs/60:.1f} minutes")
                else:
                    like_reset_time = time.time() + 900  # Default 15 min
                    log(f"    ⏳ Like rate limited. Waiting 15 minutes (no reset header)")
            else:
                like_idx += 1  # Skip on error
    
    log("")
    log("=" * 60)
    log(f"COMPLETE! Tweets deleted: {tweets_deleted}, Likes removed: {likes_deleted}")
    log("=" * 60)


def handle_signal(signum, frame):
    log("\nInterrupted. Progress saved. Re-run to continue.")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    main()
