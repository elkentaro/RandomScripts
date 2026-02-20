#!/usr/bin/env python3
"""
Tweet Cleanup - Scheduled Maintenance Script
Fetches tweets via API and deletes any not in the whitelist.
Run monthly via cron/systemd timer.

Usage:
    python3 tweet_cleanup.py              # Dry run (preview)
    python3 tweet_cleanup.py --execute    # Actually delete
    python3 tweet_cleanup.py --execute --likes  # Also unlike

Cron example (1st of every month at 3am):
    0 3 1 * * cd /path/to/scripts && python3 tweet_cleanup.py --execute >> cleanup.log 2>&1
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime

try:
    import tweepy
except ImportError:
    print("pip install tweepy")
    sys.exit(1)

# === CONFIGURATION ===
CONFIG_FILE = "config.json"
WHITELIST_FILE = "whitelist.txt"
LOG_FILE = "cleanup.log"

# API limits - will auto-detect from headers, these are fallbacks
DEFAULT_RATE_LIMIT_WAIT = 900  # 15 minutes

# Delay between operations (seconds)
DELAY_BETWEEN_OPS = 2

# === END CONFIGURATION ===


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_config():
    if not os.path.exists(CONFIG_FILE):
        log(f"ERROR: {CONFIG_FILE} not found")
        sys.exit(1)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def load_whitelist(filepath: str) -> set:
    """Load whitelisted tweet IDs."""
    whitelist = set()
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Handle URLs or raw IDs
                    if "/" in line:
                        line = line.rstrip("/").split("/")[-1].split("?")[0]
                    whitelist.add(line)
    return whitelist


def get_client(config: dict) -> tweepy.Client:
    return tweepy.Client(
        bearer_token=config.get("bearer_token"),
        consumer_key=config.get("api_key"),
        consumer_secret=config.get("api_secret"),
        access_token=config.get("access_token"),
        access_token_secret=config.get("access_token_secret"),
        wait_on_rate_limit=False
    )


def handle_rate_limit(e) -> int:
    """Extract reset time from rate limit exception, return seconds to wait."""
    if hasattr(e, 'response') and e.response is not None:
        reset_ts = e.response.headers.get('x-rate-limit-reset')
        if reset_ts:
            wait_secs = int(reset_ts) - int(time.time())
            if wait_secs > 0:
                return wait_secs + 1
    return DEFAULT_RATE_LIMIT_WAIT


def fetch_tweets(client, user_id: str) -> list:
    """Fetch all user tweets via API with rate limit handling."""
    tweets = []
    pagination_token = None
    
    log("Fetching tweets from API...")
    
    while True:
        try:
            response = client.get_users_tweets(
                id=user_id,
                max_results=100,
                pagination_token=pagination_token,
                tweet_fields=["created_at", "text"],
                exclude=["retweets"]  # Retweets fetched separately if needed
            )
            
            if response.data:
                for t in response.data:
                    tweets.append({
                        'id': str(t.id),
                        'text': t.text or '',
                        'date': str(t.created_at) if t.created_at else '',
                        'type': 'tweet'
                    })
                log(f"  Fetched {len(tweets)} tweets...")
            
            if response.meta and "next_token" in response.meta:
                pagination_token = response.meta["next_token"]
                time.sleep(1)
            else:
                break
                
        except tweepy.TooManyRequests as e:
            wait_secs = handle_rate_limit(e)
            log(f"  Rate limited fetching tweets. Waiting {wait_secs/60:.1f} minutes...")
            time.sleep(wait_secs)
            continue
        except tweepy.TwitterServerError as e:
            log(f"  Server error: {e}. Retrying in 30s...")
            time.sleep(30)
            continue
        except Exception as e:
            log(f"  Error fetching tweets: {e}")
            break
    
    return tweets


def fetch_likes(client, user_id: str) -> list:
    """Fetch user's liked tweets via API."""
    likes = []
    pagination_token = None
    
    log("Fetching likes from API...")
    
    while True:
        try:
            response = client.get_liked_tweets(
                id=user_id,
                max_results=100,
                pagination_token=pagination_token
            )
            
            if response.data:
                for t in response.data:
                    likes.append({
                        'id': str(t.id),
                        'text': t.text or '',
                        'date': '',
                        'type': 'like'
                    })
                log(f"  Fetched {len(likes)} likes...")
            
            if response.meta and "next_token" in response.meta:
                pagination_token = response.meta["next_token"]
                time.sleep(1)
            else:
                break
                
        except tweepy.TooManyRequests as e:
            wait_secs = handle_rate_limit(e)
            log(f"  Rate limited fetching likes. Waiting {wait_secs/60:.1f} minutes...")
            time.sleep(wait_secs)
            continue
        except tweepy.TwitterServerError as e:
            log(f"  Server error: {e}. Retrying in 30s...")
            time.sleep(30)
            continue
        except Exception as e:
            log(f"  Error fetching likes: {e}")
            break
    
    return likes


def delete_item(client, item: dict) -> tuple:
    """Delete a tweet or unlike. Returns (success, should_retry, wait_seconds)."""
    tid = item['id']
    ttype = item['type']
    
    try:
        if ttype == 'like':
            client.unlike(tid)
        else:
            client.delete_tweet(tid)
        return (True, False, 0)
    
    except tweepy.NotFound:
        return (True, False, 0)  # Already gone
    except tweepy.Forbidden:
        return (True, False, 0)  # Can't delete, skip
    except tweepy.TooManyRequests as e:
        wait_secs = handle_rate_limit(e)
        return (False, True, wait_secs)
    except Exception as e:
        log(f"    Error: {e}")
        return (False, False, 0)


def main():
    parser = argparse.ArgumentParser(description="Scheduled tweet cleanup")
    parser.add_argument("--execute", action="store_true", help="Actually delete (default: dry run)")
    parser.add_argument("--likes", action="store_true", help="Also remove likes not in whitelist")
    parser.add_argument("-w", "--whitelist", default=WHITELIST_FILE, help="Whitelist file path")
    args = parser.parse_args()
    
    log("=" * 60)
    log("Tweet Cleanup - Scheduled Maintenance")
    log("=" * 60)
    
    # Load config and authenticate
    config = load_config()
    client = get_client(config)
    
    try:
        me = client.get_me()
        if not me.data:
            log("ERROR: Failed to authenticate")
            sys.exit(1)
        user_id = str(me.data.id)
        username = me.data.username
        log(f"Authenticated as @{username}")
    except Exception as e:
        log(f"ERROR: Authentication failed: {e}")
        sys.exit(1)
    
    # Load whitelist
    whitelist = load_whitelist(args.whitelist)
    log(f"Whitelist: {len(whitelist)} IDs protected")
    
    # Fetch current tweets
    tweets = fetch_tweets(client, user_id)
    log(f"Found {len(tweets)} tweets")
    
    # Fetch likes if requested
    likes = []
    if args.likes:
        likes = fetch_likes(client, user_id)
        log(f"Found {len(likes)} likes")
    
    # Filter out whitelisted items
    tweets_to_delete = [t for t in tweets if t['id'] not in whitelist]
    likes_to_delete = [l for l in likes if l['id'] not in whitelist]
    
    log("")
    log(f"Tweets to delete: {len(tweets_to_delete)} (keeping {len(tweets) - len(tweets_to_delete)})")
    if args.likes:
        log(f"Likes to remove: {len(likes_to_delete)} (keeping {len(likes) - len(likes_to_delete)})")
    
    # Combine
    all_to_delete = tweets_to_delete + likes_to_delete
    
    if not all_to_delete:
        log("\nNothing to delete. All clean!")
        return
    
    # Dry run
    if not args.execute:
        log("\n--- DRY RUN (use --execute to actually delete) ---\n")
        for item in all_to_delete[:15]:
            preview = item['text'][:50].replace('\n', ' ') if item['text'] else '[no text]'
            log(f"  Would delete {item['type'].upper()}: {item['id']} | {preview}...")
        if len(all_to_delete) > 15:
            log(f"  ... and {len(all_to_delete) - 15} more")
        return
    
    # Execute deletions
    log("\n--- EXECUTING DELETIONS ---\n")
    
    deleted = 0
    skipped = 0
    total = len(all_to_delete)
    
    i = 0
    while i < len(all_to_delete):
        item = all_to_delete[i]
        preview = item['text'][:40].replace('\n', ' ') if item['text'] else ''
        log(f"[{i+1}/{total}] {item['type'].upper()} {item['id']} | {preview}...")
        
        success, should_retry, wait_secs = delete_item(client, item)
        
        if success:
            deleted += 1
            i += 1
            time.sleep(DELAY_BETWEEN_OPS)
        elif should_retry:
            log(f"    ⏳ Rate limited. Waiting {wait_secs/60:.1f} minutes...")
            time.sleep(wait_secs)
            # Don't increment i, retry same item
        else:
            skipped += 1
            i += 1
    
    log("")
    log("=" * 60)
    log(f"COMPLETE! Deleted: {deleted}, Skipped: {skipped}")
    log("=" * 60)


if __name__ == "__main__":
    main()
