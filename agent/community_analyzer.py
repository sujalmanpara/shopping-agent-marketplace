"""
Community data analyzer for Feature 2: Community Truth Bomb
Extracts insights, common complaints, and credibility scores
"""

from typing import Dict, List
from collections import Counter
import re


# ===== COMMON COMPLAINT EXTRACTION =====

def extract_common_complaints(community_data: Dict) -> List[Dict]:
    """
    Extract common complaints from community discussions
    
    Uses keyword matching + frequency analysis
    Returns top complaints with confidence scores
    """
    
    # Common complaint keywords
    COMPLAINT_PATTERNS = {
        'breaks': ['broke', 'broken', 'stopped working', 'died', 'failed', 'defective'],
        'quality': ['cheap', 'flimsy', 'poor quality', 'terrible quality', 'cheap material'],
        'battery': ['battery life', 'battery drain', 'battery sucks', 'dies quickly'],
        'overpriced': ['overpriced', 'too expensive', 'waste of money', 'not worth'],
        'customer_service': ['customer service', 'support', 'warranty', 'refund'],
        'misleading': ['misleading', 'not as described', 'false advertising', 'scam'],
        'durability': ['wear out', 'fall apart', 'doesnt last', 'short lifespan'],
        'functionality': ['doesnt work', 'not working', 'malfunction', 'glitchy']
    }
    
    complaint_counts = Counter()
    complaint_examples = {}
    
    # Analyze Reddit posts
    if community_data.get('reddit') and community_data['reddit'].get('success'):
        for post in community_data['reddit']['posts']:
            text = f"{post['title']} {post['selftext']}".lower()
            
            for category, keywords in COMPLAINT_PATTERNS.items():
                for keyword in keywords:
                    if keyword in text:
                        complaint_counts[category] += post['score']  # Weight by upvotes
                        
                        if category not in complaint_examples:
                            complaint_examples[category] = []
                        
                        complaint_examples[category].append({
                            'text': post['title'][:150],
                            'score': post['score'],
                            'source': 'reddit',
                            'subreddit': post['subreddit']
                        })
    
    # Analyze Amazon Q&A
    if community_data.get('amazon_qa') and community_data['amazon_qa'].get('success'):
        for qa in community_data['amazon_qa']['questions']:
            text = f"{qa['question']} {qa['answer']}".lower()
            
            for category, keywords in COMPLAINT_PATTERNS.items():
                for keyword in keywords:
                    if keyword in text:
                        votes = int(qa['votes'].replace(',', '') if qa['votes'] else 0)
                        complaint_counts[category] += votes
                        
                        if category not in complaint_examples:
                            complaint_examples[category] = []
                        
                        complaint_examples[category].append({
                            'text': qa['question'][:150],
                            'votes': votes,
                            'source': 'amazon_qa'
                        })
    
    # Analyze YouTube comments
    if community_data.get('youtube') and community_data['youtube'].get('success'):
        for comment in community_data['youtube']['comments']:
            text = comment['text'].lower()
            
            for category, keywords in COMPLAINT_PATTERNS.items():
                for keyword in keywords:
                    if keyword in text:
                        complaint_counts[category] += comment['likes']
                        
                        if category not in complaint_examples:
                            complaint_examples[category] = []
                        
                        complaint_examples[category].append({
                            'text': comment['text'][:150],
                            'likes': comment['likes'],
                            'source': 'youtube'
                        })
    
    # Build complaint list
    complaints = []
    total_weight = sum(complaint_counts.values()) or 1
    
    for category, weight in complaint_counts.most_common(5):  # Top 5 complaints
        confidence = min(100, int((weight / total_weight) * 100))
        
        complaints.append({
            'category': category.replace('_', ' ').title(),
            'weight': weight,
            'confidence': confidence,
            'examples': complaint_examples.get(category, [])[:3],  # Top 3 examples
            'mentions': len(complaint_examples.get(category, []))
        })
    
    return complaints


# ===== USER CREDIBILITY SCORING =====

def score_user_credibility(author_info: Dict) -> float:
    """
    Score user credibility based on account metrics
    
    Factors:
    - Account age (older = more credible)
    - Karma/score (higher = more trusted)
    - Activity level (moderate = best)
    
    Returns: 0.0 - 1.0 credibility score
    """
    
    score = 0.5  # Base credibility
    
    # Account age score (if available)
    if 'account_age_days' in author_info:
        age = author_info['account_age_days']
        if age > 365:  # 1+ year
            score += 0.2
        elif age > 180:  # 6+ months
            score += 0.1
        elif age < 30:  # New account
            score -= 0.1
    
    # Karma/score (if available)
    if 'karma' in author_info or 'score' in author_info:
        karma = author_info.get('karma', author_info.get('score', 0))
        if karma > 10000:
            score += 0.2
        elif karma > 1000:
            score += 0.1
        elif karma < 10:
            score -= 0.1
    
    # Check for deleted/removed (low credibility)
    if author_info.get('author') in ['[deleted]', '[removed]', 'deleted']:
        score = 0.3
    
    # Clamp to 0-1 range
    return max(0.0, min(1.0, score))


# ===== SENTIMENT ANALYSIS =====

def analyze_community_sentiment(community_data: Dict) -> Dict:
    """
    Analyze overall sentiment from community discussions
    
    Returns sentiment breakdown (positive/negative/neutral)
    """
    
    # Simple keyword-based sentiment
    POSITIVE_KEYWORDS = ['love', 'great', 'excellent', 'amazing', 'perfect', 'best', 'recommend', 'worth it']
    NEGATIVE_KEYWORDS = ['hate', 'terrible', 'awful', 'worst', 'avoid', 'regret', 'waste', 'disappointed']
    
    sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
    total_items = 0
    
    # Analyze Reddit
    if community_data.get('reddit') and community_data['reddit'].get('success'):
        for post in community_data['reddit']['posts']:
            text = f"{post['title']} {post['selftext']}".lower()
            total_items += 1
            
            pos_count = sum(1 for word in POSITIVE_KEYWORDS if word in text)
            neg_count = sum(1 for word in NEGATIVE_KEYWORDS if word in text)
            
            if pos_count > neg_count:
                sentiment_counts['positive'] += 1
            elif neg_count > pos_count:
                sentiment_counts['negative'] += 1
            else:
                sentiment_counts['neutral'] += 1
    
    # Analyze Amazon Q&A
    if community_data.get('amazon_qa') and community_data['amazon_qa'].get('success'):
        for qa in community_data['amazon_qa']['questions']:
            text = f"{qa['question']} {qa['answer']}".lower()
            total_items += 1
            
            pos_count = sum(1 for word in POSITIVE_KEYWORDS if word in text)
            neg_count = sum(1 for word in NEGATIVE_KEYWORDS if word in text)
            
            if pos_count > neg_count:
                sentiment_counts['positive'] += 1
            elif neg_count > pos_count:
                sentiment_counts['negative'] += 1
            else:
                sentiment_counts['neutral'] += 1
    
    # Analyze YouTube
    if community_data.get('youtube') and community_data['youtube'].get('success'):
        for comment in community_data['youtube']['comments']:
            text = comment['text'].lower()
            total_items += 1
            
            pos_count = sum(1 for word in POSITIVE_KEYWORDS if word in text)
            neg_count = sum(1 for word in NEGATIVE_KEYWORDS if word in text)
            
            if pos_count > neg_count:
                sentiment_counts['positive'] += 1
            elif neg_count > pos_count:
                sentiment_counts['negative'] += 1
            else:
                sentiment_counts['neutral'] += 1
    
    # Calculate percentages
    if total_items > 0:
        sentiment_percentages = {
            'positive': int((sentiment_counts['positive'] / total_items) * 100),
            'negative': int((sentiment_counts['negative'] / total_items) * 100),
            'neutral': int((sentiment_counts['neutral'] / total_items) * 100)
        }
    else:
        sentiment_percentages = {'positive': 0, 'negative': 0, 'neutral': 0}
    
    # Overall verdict
    if sentiment_percentages['positive'] > sentiment_percentages['negative'] + 20:
        overall = 'MOSTLY POSITIVE'
    elif sentiment_percentages['negative'] > sentiment_percentages['positive'] + 20:
        overall = 'MOSTLY NEGATIVE'
    else:
        overall = 'MIXED'
    
    return {
        'overall': overall,
        'breakdown': sentiment_percentages,
        'total_analyzed': total_items
    }


# ===== MAIN ANALYSIS FUNCTION =====

def analyze_community_data(community_data: Dict) -> Dict:
    """
    Main analysis function - combines all analysis methods
    
    Returns comprehensive community insights
    """
    
    if not community_data.get('success'):
        return {
            'success': False,
            'message': community_data.get('message', 'No community data available')
        }
    
    # Extract insights
    complaints = extract_common_complaints(community_data)
    sentiment = analyze_community_sentiment(community_data)
    
    # Build summary
    analysis = {
        'success': True,
        'primary_source': community_data.get('primary_source'),
        'total_data_points': community_data.get('total_data_points', 0),
        'common_complaints': complaints,
        'sentiment': sentiment,
        'sources_used': []
    }
    
    # Track which sources were used
    if community_data.get('reddit') and community_data['reddit'].get('success'):
        analysis['sources_used'].append({
            'name': 'Reddit',
            'posts': len(community_data['reddit']['posts']),
            'subreddits': community_data['reddit'].get('subreddits_searched', [])
        })
    
    if community_data.get('amazon_qa') and community_data['amazon_qa'].get('success'):
        analysis['sources_used'].append({
            'name': 'Amazon Q&A',
            'questions': len(community_data['amazon_qa']['questions'])
        })
    
    if community_data.get('youtube') and community_data['youtube'].get('success'):
        analysis['sources_used'].append({
            'name': 'YouTube',
            'comments': len(community_data['youtube']['comments']),
            'videos': community_data['youtube'].get('videos_searched', 0)
        })
    
    return analysis
