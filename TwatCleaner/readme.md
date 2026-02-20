# Tweet Deleter + Unliker

Tools for bulk deleting tweets and unlikes, plus ongoing maintenance.

## Two Scripts, Two Use Cases

| Script | Purpose | Data Source | When to Use |
|--------|---------|-------------|-------------|
| `delete_interleaved.py` | Initial bulk cleanup | Twitter archive | First-time purge of years of tweets/likes |
| `tweet_cleanup.py` | Ongoing maintenance | Live API | Monthly scheduled cleanup of new tweets |

---

## Script 1: delete_interleaved.py (Bulk Cleanup)

For **initial mass deletion** using your Twitter archive. Best when you have thousands of tweets/likes to delete.

### Why Use Archive?

- No API rate limits for *reading* data
- Can review all tweets locally before deciding
- Works even if API is rate-limited for reads

### Setup

#### 1. Download Your Twitter Archive

1. Go to **Settings → Your Account → Download an archive of your data**
2. Wait for Twitter to prepare it (can take hours)
3. Download and extract the zip
4. Copy `data/tweets.js` and `data/like.js` to this folder

#### 2. Get API Credentials

1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Create a project and app
3. Enable **OAuth 1.0a** with **Read and Write** permissions
4. Generate all keys/tokens

#### 3. Create config.json

```json
{
    "api_key": "your_api_key",
    "api_secret": "your_api_secret",
    "access_token": "your_access_token",
    "access_token_secret": "your_access_token_secret",
    "bearer_token": "your_bearer_token"
}
```

#### 4. Create Your Whitelist

Create `whitelist.txt` with tweet IDs you want to **keep** (one per line):

```
1234567890123456789
1234567890123456790
https://x.com/username/status/1234567890123456791
```

Use the included `tweet_reviewer.html` to browse your archive and build this list.

#### 5. Install Dependencies

```bash
pip install tweepy
```

### Usage

```bash
# Run directly
python3 delete_interleaved.py

# Run in background (screen)
screen -S deleter
python3 delete_interleaved.py
# Ctrl+A, D to detach
# screen -r deleter to reattach

# Run in background (nohup)
nohup python3 delete_interleaved.py > deleter.log 2>&1 &
tail -f deleter.log
```

### How It Works

- Reads tweets from `tweets.js` and likes from `like.js`
- Compares against `whitelist.txt`
- **Interleaves** tweet deletions and unlikes to use both rate limit pools
- Waits for rate limit reset using `x-rate-limit-reset` header
- Saves progress to resume if interrupted

### File Structure

```
├── delete_interleaved.py   # Bulk deletion script
├── config.json             # API credentials
├── tweets.js               # From Twitter archive
├── like.js                 # From Twitter archive
├── whitelist.txt           # Tweet IDs to keep
├── progress_tweets.txt     # Auto-generated, tracks deleted tweets
├── progress_likes.txt      # Auto-generated, tracks unliked posts
└── deletion.log            # Auto-generated, detailed log
```

### Configuration

Edit the top of `delete_interleaved.py`:

```python
DELAY_BETWEEN_SAME_TYPE = 3  # Seconds between same-type operations
```

### Resuming

Just run the script again. It reads `progress_tweets.txt` and `progress_likes.txt` to skip already-processed items.

---

## Script 2: tweet_cleanup.py (Scheduled Maintenance)

For **ongoing monthly cleanup** via API. Use after the initial bulk purge to keep your account clean.

### Why Use This?

- No need to download archive every month
- Fetches current tweets directly from API
- Can be scheduled via cron/systemd
- Deletes anything not in your whitelist

### Setup

Same `config.json` and `whitelist.txt` as above. No archive files needed.

### Usage

```bash
# Dry run - preview what would be deleted
python3 tweet_cleanup.py

# Actually delete tweets
python3 tweet_cleanup.py --execute

# Also remove likes
python3 tweet_cleanup.py --execute --likes

# Use different whitelist
python3 tweet_cleanup.py --execute -w my_whitelist.txt
```

### Schedule with Cron

Run monthly on the 1st at 3am:

```bash
crontab -e
```

Add:
```
0 3 1 * * cd /path/to/twitter-deleter && /usr/bin/python3 tweet_cleanup.py --execute >> cleanup.log 2>&1
```

### Schedule with Systemd Timer

Create `/etc/systemd/system/tweet-cleanup.service`:
```ini
[Unit]
Description=Tweet Cleanup

[Service]
Type=oneshot
WorkingDirectory=/path/to/twitter-deleter
ExecStart=/usr/bin/python3 tweet_cleanup.py --execute
User=youruser
```

Create `/etc/systemd/system/tweet-cleanup.timer`:
```ini
[Unit]
Description=Monthly Tweet Cleanup

[Timer]
OnCalendar=monthly
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl enable tweet-cleanup.timer
sudo systemctl start tweet-cleanup.timer
```

### How It Works

1. Authenticates with Twitter API
2. Fetches all your current tweets (and likes if `--likes`)
3. Compares against whitelist
4. Deletes anything not whitelisted
5. Handles rate limits automatically using reset headers

### File Structure

```
├── tweet_cleanup.py        # Scheduled cleanup script
├── config.json             # API credentials  
├── whitelist.txt           # Tweet IDs to keep (same as bulk script)
└── cleanup.log             # Auto-generated log
```

---

## Comparison

| Feature | delete_interleaved.py | tweet_cleanup.py |
|---------|----------------------|------------------|
| Data source | Local archive files | Twitter API |
| Best for | Initial bulk purge | Ongoing maintenance |
| Archive needed | Yes | No |
| Handles likes | Yes (from like.js) | Yes (--likes flag) |
| Progress resume | Yes | No (runs to completion) |
| Rate limit handling | Yes (waits for reset) | Yes (waits for reset) |
| Scheduling | Manual run | Cron/systemd |

---

## Workflow

### First Time Setup

1. Download Twitter archive
2. Use `tweet_reviewer.html` to review and build whitelist
3. Run `delete_interleaved.py` to purge everything
4. Set up `tweet_cleanup.py` on a monthly schedule

### Monthly Maintenance

The `tweet_cleanup.py` script runs automatically, deleting any new tweets that aren't whitelisted.

---

## Rate Limits

Twitter API limits (as of 2024):

| Endpoint | Limit |
|----------|-------|
| GET tweets | 1500 per 15 min |
| DELETE tweet | 50 per 15 min |
| Unlike | 50 per 15 min |

Both scripts handle rate limits automatically by reading the `x-rate-limit-reset` header and waiting until the limit resets.

---

## Troubleshooting

### "Rate limited" constantly
The scripts now wait for the actual reset time from headers. If issues persist, check your API tier.

### Tweets not deleting
- Check your API app has **Read and Write** permissions
- Regenerate your access tokens after changing permissions

### Script crashes
- `delete_interleaved.py`: Progress is saved, just re-run
- `tweet_cleanup.py`: Re-run manually or wait for next scheduled run

### Want to start fresh with bulk script
Delete `progress_tweets.txt` and `progress_likes.txt`.

---

## License

MIT — do whatever you want with it.
