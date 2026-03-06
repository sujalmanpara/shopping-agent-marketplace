"""
Community scrapers for Feature 2: Community Truth Bomb
Uses PRAW (Reddit), Scrapling (Amazon Q&A), and yt-dlp (YouTube)
"""

import asyncio
import os
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import praw
import yt_dlp
from scrapling import StealthyFetcher

from agent.constants import SCRAPE_TIMEOUT


# ===== REDDIT SCRAPER (PRAW) =====

def scrape_reddit_discussions(product_name: str) -> Dict:
    """
    Scrape Reddit discussions using PRAW (official API)
    
    Searches targeted subreddits for product discussions
    Returns posts with scores, comments, and subreddit info
    """
    try:
        # Initialize PRAW
        # Note: Requires Reddit API credentials in environment variables
        # REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
        reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID', 'shopping-agent'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET', ''),
            user_agent=os.getenv('REDDIT_USER_AGENT', 'shopping-agent/1.0')
        )
        
        # If no credentials, fall back to read-only mode
        if not os.getenv('REDDIT_CLIENT_SECRET'):
            reddit = praw.Reddit(
                client_id='shopping-agent',
                client_secret='',
                user_agent='shopping-agent/1.0',
                check_for_async=False
            )
        
        # Targeted subreddits for product discussions
        target_subreddits = [
            'BuyItForLife',      # Durability focus
            'Frugal',            # Budget-conscious
            'AssholeDesign',     # Bad product design
            'ProductPorn',       # High-end products
            'reviews',           # General reviews
        ]
        
        all_posts = []
        
        # Search each subreddit
        for sub_name in target_subreddits:
            try:
                subreddit = reddit.subreddit(sub_name)
                
                # Search for product
                for submission in subreddit.search(product_name, limit=10):
                    # Get top comments
                    submission.comments.replace_more(limit=0)
                    top_comments = []
                    
                    for comment in submission.comments[:5]:  # Top 5 comments
                        top_comments.append({
                            'author': str(comment.author) if comment.author else '[deleted]',
                            'body': comment.body,
                            'score': comment.score,
                            'created': comment.created_utc
                        })
                    
                    all_posts.append({
                        'title': submission.title,
                        'selftext': submission.selftext,
                        'score': submission.score,
                        'url': submission.url,
                        'subreddit': sub_name,
                        'num_comments': submission.num_comments,
                        'created': submission.created_utc,
                        'top_comments': top_comments,
                        'author': str(submission.author) if submission.author else '[deleted]'
                    })
                    
            except Exception as e:
                print(f"Error searching {sub_name}: {e}")
                continue
        
        # Sort by score (most upvoted first)
        all_posts.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'success': True,
            'source': 'reddit',
            'posts': all_posts[:20],  # Top 20 posts
            'total_posts': len(all_posts),
            'subreddits_searched': target_subreddits
        }
        
    except Exception as e:
        return {
            'success': False,
            'source': 'reddit',
            'error': str(e),
            'posts': []
        }


# ===== AMAZON Q&A SCRAPER (Scrapling) =====

async def scrape_amazon_qa(asin: str, domain: str = 'amazon.com') -> Dict:
    """
    Scrape Amazon Q&A section using existing Scrapling infrastructure
    
    Uses StealthyFetcher (already proven to work for Amazon reviews)
    Just parses Q&A section instead of reviews
    """
    try:
        url = f"https://www.{domain}/dp/{asin}"
        
        # Use StealthyFetcher (same as our existing Amazon scraping)
        response = await asyncio.to_thread(
            StealthyFetcher.fetch,
            url,
            headless=True,
            network_idle=True,
            solve_cloudflare=True,
            timeout=SCRAPE_TIMEOUT
        )
        
        if not response or not response.text:
            return {
                'success': False,
                'source': 'amazon_qa',
                'error': 'Empty response',
                'questions': []
            }
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find Q&A section
        # Amazon has multiple possible selectors for Q&A
        qa_section = (
            soup.find('div', {'id': 'ask-dp-search'}) or
            soup.find('div', {'id': 'askDPSearchContent'}) or
            soup.find('div', class_='ask-widget')
        )
        
        if not qa_section:
            return {
                'success': False,
                'source': 'amazon_qa',
                'error': 'Q&A section not found',
                'questions': []
            }
        
        questions = []
        
        # Parse Q&A items
        qa_items = qa_section.find_all('div', class_='a-section askTeaserQuestions')
        
        for qa in qa_items[:20]:  # Top 20 Q&A
            try:
                question_elem = qa.find('a', class_='a-link-normal')
                answer_elem = qa.find('span', class_='askAnswerBody')
                votes_elem = qa.find('span', class_='count')
                
                if question_elem and answer_elem:
                    questions.append({
                        'question': question_elem.text.strip(),
                        'answer': answer_elem.text.strip(),
                        'votes': votes_elem.text.strip() if votes_elem else '0',
                        'url': f"https://www.{domain}{question_elem['href']}" if 'href' in question_elem.attrs else ''
                    })
            except Exception as e:
                continue
        
        return {
            'success': True,
            'source': 'amazon_qa',
            'questions': questions,
            'total_questions': len(questions)
        }
        
    except Exception as e:
        return {
            'success': False,
            'source': 'amazon_qa',
            'error': str(e),
            'questions': []
        }


# ===== YOUTUBE COMMENT SCRAPER (yt-dlp) =====

async def scrape_youtube_comments(product_name: str) -> Dict:
    """
    Scrape YouTube comments from review videos using yt-dlp
    
    Searches for "{product} review" videos
    Extracts top comments from top 3 videos
    """
    try:
        # Search for review videos
        search_query = f"{product_name} review"
        search_url = f"ytsearch3:{search_query}"  # ytsearch3 = top 3 results
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Don't download, just get info
            'skip_download': True
        }
        
        # Get video URLs
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = await asyncio.to_thread(
                ydl.extract_info,
                search_url,
                download=False
            )
        
        if not search_results or 'entries' not in search_results:
            return {
                'success': False,
                'source': 'youtube',
                'error': 'No videos found',
                'comments': []
            }
        
        all_comments = []
        
        # Get comments from each video
        for entry in search_results['entries'][:3]:  # Top 3 videos
            try:
                video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                
                comment_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'getcomments': True,
                    'max_comments': 50,  # Top 50 comments per video
                    'writesubtitles': False,
                    'writeautomaticsub': False
                }
                
                with yt_dlp.YoutubeDL(comment_opts) as ydl:
                    info = await asyncio.to_thread(
                        ydl.extract_info,
                        video_url,
                        download=False
                    )
                
                if info and 'comments' in info:
                    for comment in info['comments'][:20]:  # Top 20 per video
                        all_comments.append({
                            'text': comment.get('text', ''),
                            'author': comment.get('author', ''),
                            'likes': comment.get('like_count', 0),
                            'video_title': entry.get('title', ''),
                            'video_url': video_url,
                            'timestamp': comment.get('timestamp', 0)
                        })
                        
            except Exception as e:
                print(f"Error getting comments from video: {e}")
                continue
        
        # Sort by likes (most helpful first)
        all_comments.sort(key=lambda x: x['likes'], reverse=True)
        
        return {
            'success': True,
            'source': 'youtube',
            'comments': all_comments[:30],  # Top 30 comments overall
            'total_comments': len(all_comments),
            'videos_searched': len(search_results['entries'][:3])
        }
        
    except Exception as e:
        return {
            'success': False,
            'source': 'youtube',
            'error': str(e),
            'comments': []
        }


# ===== SMART FALLBACK ORCHESTRATOR =====

async def get_community_truth(product_name: str, asin: Optional[str] = None, domain: str = 'amazon.com') -> Dict:
    """
    Smart fallback chain for community data
    
    Priority order:
    1. Reddit (best quality)
    2. Amazon Q&A (best coverage)
    3. YouTube (bonus insights)
    
    Returns first successful source or combines all
    """
    
    results = {
        'reddit': None,
        'amazon_qa': None,
        'youtube': None,
        'primary_source': None,
        'total_data_points': 0
    }
    
    # Try Reddit first (best quality)
    try:
        reddit_data = await asyncio.to_thread(scrape_reddit_discussions, product_name)
        results['reddit'] = reddit_data
        
        if reddit_data['success'] and len(reddit_data['posts']) >= 5:
            results['primary_source'] = 'reddit'
            results['total_data_points'] += len(reddit_data['posts'])
    except Exception as e:
        print(f"Reddit scraping failed: {e}")
    
    # Try Amazon Q&A (best coverage)
    if asin:
        try:
            qa_data = await scrape_amazon_qa(asin, domain)
            results['amazon_qa'] = qa_data
            
            if qa_data['success'] and len(qa_data['questions']) >= 10:
                if not results['primary_source']:
                    results['primary_source'] = 'amazon_qa'
                results['total_data_points'] += len(qa_data['questions'])
        except Exception as e:
            print(f"Amazon Q&A scraping failed: {e}")
    
    # Try YouTube (bonus)
    try:
        youtube_data = await scrape_youtube_comments(product_name)
        results['youtube'] = youtube_data
        
        if youtube_data['success'] and len(youtube_data['comments']) >= 20:
            if not results['primary_source']:
                results['primary_source'] = 'youtube'
            results['total_data_points'] += len(youtube_data['comments'])
    except Exception as e:
        print(f"YouTube scraping failed: {e}")
    
    # Set final status
    if results['total_data_points'] > 0:
        results['success'] = True
        results['message'] = f"Found {results['total_data_points']} community data points"
    else:
        results['success'] = False
        results['message'] = "No community discussions found for this product"
        results['primary_source'] = 'none'
    
    return results
