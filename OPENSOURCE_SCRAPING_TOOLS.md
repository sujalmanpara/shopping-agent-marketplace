# 🛠️ Open-Source Tools for Community Truth Bomb

## 🎯 The Question: Are There Open-Source Tools That Can Help?

**YES!** There are several excellent open-source tools we can use instead of building everything from scratch!

---

## ✅ **RECOMMENDED TOOLS**

### **1. Reddit Scraping**

#### **PRAW (Python Reddit API Wrapper)** ⭐⭐⭐⭐⭐
**GitHub**: https://github.com/praw-dev/praw  
**Stars**: 3.2k+ ⭐  
**License**: BSD-2-Clause (permissive)

**What it does**:
- Official Reddit API wrapper
- Easy to use, well-maintained
- Gets posts, comments, user info
- Handles rate limiting automatically

**Installation**:
```bash
pip install praw
```

**Example**:
```python
import praw

reddit = praw.Reddit(
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_SECRET',
    user_agent='shopping-agent/1.0'
)

# Search for product discussions
subreddit = reddit.subreddit('BuyItForLife')
for post in subreddit.search('iPhone 15', limit=10):
    print(post.title, post.score, post.url)
```

**Pros**:
- ✅ Official API (reliable)
- ✅ Easy to use
- ✅ Handles authentication
- ✅ Well documented

**Cons**:
- ⚠️ Requires Reddit API key (FREE but needs registration)
- ⚠️ Rate limits (60 requests/min)

**Verdict**: **HIGHLY RECOMMENDED** ✅

---

#### **Pushshift API** ⭐⭐⭐⭐ (Archive Service)
**GitHub**: https://github.com/pushshift/api  
**Website**: https://pushshift.io

**What it does**:
- Historical Reddit data archive
- Search ALL Reddit posts/comments
- No authentication needed (for basic use)
- More flexible than PRAW

**Example**:
```python
import requests

# Search Pushshift for Reddit posts
url = "https://api.pushshift.io/reddit/search/submission/"
params = {
    'q': 'iPhone 15',
    'subreddit': 'BuyItForLife',
    'size': 100
}

response = requests.get(url, params=params)
posts = response.json()['data']

for post in posts:
    print(post['title'], post['score'])
```

**Pros**:
- ✅ No API key needed
- ✅ Historical data (years back)
- ✅ Very flexible queries
- ✅ Fast

**Cons**:
- ⚠️ Sometimes slow/down
- ⚠️ Not official (community-run)

**Verdict**: **GREAT BACKUP** ✅

---

### **2. Amazon Q&A Scraping**

#### **Amazon Scraper (apify/amazon-scraper)** ⭐⭐⭐⭐
**GitHub**: https://github.com/apify/actor-amazon-crawler  
**License**: Apache 2.0

**What it does**:
- Scrapes Amazon product pages
- Includes Q&A section
- Handles anti-bot protection
- Production-ready

**Installation**:
```bash
# Use as library (simplified version)
# Or run via Apify platform (free tier)
```

**Pros**:
- ✅ Battle-tested
- ✅ Handles Q&A extraction
- ✅ Anti-bot bypass included

**Cons**:
- ⚠️ Complex setup
- ⚠️ Better to use our existing Scrapling approach

**Verdict**: **REFERENCE IMPLEMENTATION** (Study their code, don't use directly)

---

#### **Our Current Approach (Scrapling)** ⭐⭐⭐⭐⭐
**We already have this working!**

```python
# agent/scrapers.py already uses StealthyFetcher for Amazon
response = await StealthyFetcher.fetch(
    f"https://www.amazon.com/dp/{asin}",
    headless=True,
    network_idle=True,
    solve_cloudflare=True
)

# Just need to add Q&A CSS selectors!
```

**Verdict**: **USE WHAT WE HAVE** ✅

---

### **3. YouTube Comment Scraping**

#### **youtube-comment-downloader** ⭐⭐⭐⭐
**GitHub**: https://github.com/egbertbouman/youtube-comment-downloader  
**Stars**: 1.3k+ ⭐  
**License**: MIT

**What it does**:
- Downloads all comments from a video
- No API key needed
- Handles pagination automatically

**Installation**:
```bash
pip install youtube-comment-downloader
```

**Example**:
```python
from youtube_comment_downloader import *

downloader = YoutubeCommentDownloader()
comments = downloader.get_comments_from_url('https://youtube.com/watch?v=VIDEO_ID')

for comment in comments:
    print(comment['author'], comment['text'], comment['votes'])
```

**Pros**:
- ✅ No API key needed
- ✅ Easy to use
- ✅ Gets ALL comments

**Cons**:
- ⚠️ Can be slow for videos with many comments
- ⚠️ YouTube might block (use proxies)

**Verdict**: **WORTH TRYING** ✅

---

#### **yt-dlp** (Video + Comments) ⭐⭐⭐⭐⭐
**GitHub**: https://github.com/yt-dlp/yt-dlp  
**Stars**: 70k+ ⭐ (very popular!)  
**License**: Unlicense

**What it does**:
- Downloads videos + metadata
- Can extract comments too
- Very well-maintained
- Handles YouTube anti-bot

**Installation**:
```bash
pip install yt-dlp
```

**Example**:
```python
import yt_dlp

opts = {
    'skip_download': True,  # Don't download video
    'getcomments': True,    # Get comments
    'max_comments': 100
}

with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info('https://youtube.com/watch?v=VIDEO_ID')
    comments = info.get('comments', [])
    
    for comment in comments:
        print(comment['author'], comment['text'])
```

**Pros**:
- ✅ Very reliable
- ✅ Well-maintained (active development)
- ✅ Handles YouTube changes automatically
- ✅ No API key needed

**Cons**:
- ⚠️ Heavy dependency (but worth it!)

**Verdict**: **BEST OPTION FOR YOUTUBE** ✅

---

## 🎯 **FINAL RECOMMENDED STACK**

### **Phase 1 (MVP) - 2-3 Days**

#### **1. Reddit → Use PRAW** ✅
```bash
pip install praw
```
**Why**: Official, reliable, well-documented

**Alternative**: Pushshift API (if PRAW rate limits are issue)

---

#### **2. Amazon Q&A → Use Our Existing Scrapling** ✅
```python
# Already in agent/scrapers.py!
# Just add Q&A CSS selectors
```
**Why**: Already working, no new dependencies

---

#### **3. YouTube → Use yt-dlp** ✅
```bash
pip install yt-dlp
```
**Why**: Most reliable, handles anti-bot, actively maintained

---

## 📦 **Updated requirements.txt**

```txt
# Existing dependencies
scrapling>=0.2.0
beautifulsoup4>=4.12.0
scikit-learn>=1.3.0
numpy>=1.24.0
statsmodels>=0.14.0

# NEW: Community Truth Bomb
praw>=7.7.1              # Reddit API wrapper
yt-dlp>=2024.3.1         # YouTube comments
```

**No need for**: Forums, Twitter (skipping those!)

---

## 🎉 **Benefits of Using Open-Source Tools**

1. **Faster Development**: Don't reinvent the wheel
2. **Better Reliability**: Battle-tested by thousands of users
3. **Active Maintenance**: Security updates, bug fixes
4. **Community Support**: Stack Overflow answers, GitHub issues
5. **Less Code**: Fewer bugs, easier to maintain

---

## ⚠️ **Trade-offs**

### **PRAW (Reddit)**
- **Pro**: Official API, reliable
- **Con**: Requires Reddit API key (FREE registration)
- **Setup Time**: 5 minutes to register

### **yt-dlp (YouTube)**
- **Pro**: Very reliable, handles anti-bot
- **Con**: Larger dependency (~50MB)
- **Setup Time**: Just `pip install`

---

## 🚀 **Implementation Plan**

### **Step 1: Add Dependencies** (5 min)
```bash
cd /root/.openclaw/workspace/shopping-agent-marketplace
pip install praw yt-dlp
echo "praw>=7.7.1" >> requirements.txt
echo "yt-dlp>=2024.3.1" >> requirements.txt
```

### **Step 2: Register Reddit API** (5 min)
1. Go to https://www.reddit.com/prefs/apps
2. Create app (script type)
3. Get client_id + client_secret
4. Store in environment variables

### **Step 3: Create Scrapers** (2-3 days)
```
agent/community_scrapers.py:
- scrape_reddit_praw()      # Using PRAW
- scrape_amazon_qa()        # Using existing Scrapling
- scrape_youtube_ytdlp()    # Using yt-dlp
```

### **Step 4: Integrate** (1 day)
Update `agent/executor.py` to call community scrapers

---

## 💰 **Cost Analysis**

| Tool | Cost | Setup Time | Maintenance |
|------|------|-----------|-------------|
| **PRAW** | FREE | 5 min | LOW |
| **Scrapling** | FREE | 0 (already have) | LOW |
| **yt-dlp** | FREE | 1 min | LOW |

**Total Cost**: **$0** ✅  
**Total Setup**: **<10 minutes** ✅

---

## 🎯 **Verdict: USE OPEN-SOURCE TOOLS!**

**Don't build scrapers from scratch when excellent tools exist!**

**Recommended Stack**:
1. ✅ PRAW for Reddit (official API)
2. ✅ Scrapling for Amazon Q&A (already have it)
3. ✅ yt-dlp for YouTube (battle-tested)

**Result**: Faster development, more reliable, easier to maintain! 🚀

---

*Created: March 6, 2026*  
*Recommendation: Use PRAW + Scrapling + yt-dlp*
