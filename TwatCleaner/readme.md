# Tweet Deleter + Unliker

Bulk delete tweets and unlike posts using your Twitter archive. No API calls for fetching — only for deletions.

## How It Works

- Reads your tweets from the Twitter archive (`tweets.js`) — no API needed
- Reads your likes from the archive (`like.js`) — no API needed
- Compares against your whitelist to preserve tweets you want to keep
- Interleaves deletions and unlikes to use both rate limit pools simultaneously
- Saves progress so you can stop/resume anytime

## Setup

### 1. Download Your Twitter Archive

1. Go to **Settings → Your Account → Download an archive of your data**
2. Wait for Twitter to prepare it (can take hours)
3. Download and extract the zip
4. Copy `data/tweets.js` and `data/like.js` to this folder

### 2. Get API Credentials

1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Create a project and app
3. Enable **OAuth 1.0a** with **Read and Write** permissions
4. Generate all keys/tokens

### 3. Create config.json

```json
{
    "api_key": "your_api_key",
    "api_secret": "your_api_secret",
    "access_token": "your_access_token",
    "access_token_secret": "your_access_token_secret",
    "bearer_token": "your_bearer_token"
}
```

### 4. Create Your Whitelist

Create `whitelist.txt` with tweet IDs you want to **keep** (one per line):

```
1234567890123456789
1234567890123456790
https://x.com/username/status/1234567890123456791
```

Use the included `tweet_reviewer.html` to browse your archive and build this list.

### 5. Install Dependencies

```bash
pip install tweepy
```

## File Structure

```
├── delete_interleaved.py   # Main script
├── config.json             # API credentials
├── tweets.js               # From Twitter archive
├── like.js                 # From Twitter archive
├── whitelist.txt           # Tweet IDs to keep
├── progress_tweets.txt     # Auto-generated, tracks deleted tweets
├── progress_likes.txt      # Auto-generated, tracks unliked posts
└── deletion.log            # Auto-generated, detailed log
```

## Usage

### Run Directly

```bash
python3 delete_interleaved.py
```

### Run in Background (screen)

```bash
screen -S deleter
python3 delete_interleaved.py
# Ctrl+A, D to detach

# Reattach later:
screen -r deleter
```

### Run in Background (nohup)

```bash
nohup python3 delete_interleaved.py > deleter.log 2>&1 &

# Check progress:
tail -f deleter.log

# Stop:
pkill -f delete_interleaved.py
```

## Configuration

Edit the top of `delete_interleaved.py` to adjust:

```python
# Seconds between same-type operations (tweet-to-tweet or like-to-like)
# Default 20s = safe for 50 requests/15 min rate limit
# Since we interleave, effective rate is 1 action every 10 seconds
DELAY_BETWEEN_SAME_TYPE = 20
```

### Speed Guide

| Delay | Actions/Hour | 500 tweets + 5000 likes |
|-------|--------------|-------------------------|
| 20s   | 360          | ~15 hours               |
| 10s   | 720          | ~7.5 hours              |
| 5s    | 1440         | ~4 hours (risky)        |

## Output

```
[2024-02-07 14:30:00] [T:1/476 L:0/5000] DELETE TWEET 123... | Hello world...
[2024-02-07 14:30:10] [T:1/476 L:1/5000] UNLIKE 456... | Some liked tweet...
[2024-02-07 14:30:20] [T:2/476 L:1/5000] DELETE RETWEET 789... | RT @someone...
```

- `T:1/476` = Tweet progress (1 of 476)
- `L:1/5000` = Like progress (1 of 5000)

## Resuming

Just run the script again. It reads `progress_tweets.txt` and `progress_likes.txt` to skip already-processed items.

## Rate Limits

Twitter API limits (as of 2024):

| Endpoint | Limit |
|----------|-------|
| DELETE tweet | 50 per 15 min |
| DELETE like (unlike) | 50 per 15 min |

The script handles rate limits automatically by pausing and retrying.

## Troubleshooting

### "Rate limited" constantly
Increase `DELAY_BETWEEN_SAME_TYPE` to 30 or 60 seconds.

### Tweets not deleting
- Check your API app has **Read and Write** permissions
- Regenerate your access tokens after changing permissions

### Script crashes
Progress is saved automatically. Just re-run to continue.

### Want to start fresh
Delete `progress_tweets.txt` and `progress_likes.txt`.

## License

MIT — do whatever you want with it.
