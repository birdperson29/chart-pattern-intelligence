"""
Sentiment Analysis Module (Optional)
Integrates news and social media sentiment to validate/challenge technical signals.
Requires API keys to be set in .env
"""

import os
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta


def fetch_news_sentiment(symbol: str, days: int = 7) -> List[Dict]:
    """
    Fetch recent news articles and basic sentiment for a stock.
    Uses NewsAPI if configured, otherwise returns empty.
    """
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        return []

    # Strip .NS/.BO suffix for search
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": f"{clean_symbol} stock India",
            "from": from_date,
            "sortBy": "relevancy",
            "language": "en",
            "pageSize": 10,
            "apiKey": api_key,
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        articles = []
        for article in data.get("articles", []):
            # Simple keyword-based sentiment (replace with FinBERT for production)
            title = (article.get("title", "") or "").lower()
            desc = (article.get("description", "") or "").lower()
            text = title + " " + desc

            bullish_words = ["surge", "rally", "gain", "rise", "bullish", "buy", "upgrade",
                           "growth", "profit", "beat", "strong", "positive", "up"]
            bearish_words = ["fall", "drop", "crash", "bearish", "sell", "downgrade",
                           "loss", "miss", "weak", "negative", "down", "decline"]

            bull_score = sum(1 for w in bullish_words if w in text)
            bear_score = sum(1 for w in bearish_words if w in text)

            if bull_score > bear_score:
                sentiment = "positive"
            elif bear_score > bull_score:
                sentiment = "negative"
            else:
                sentiment = "neutral"

            articles.append({
                "title": article.get("title", ""),
                "source": article.get("source", {}).get("name", ""),
                "url": article.get("url", ""),
                "published_at": article.get("publishedAt", ""),
                "sentiment": sentiment,
            })

        return articles

    except Exception as e:
        print(f"[WARN] News sentiment fetch failed: {e}")
        return []


def aggregate_sentiment(articles: List[Dict]) -> Dict:
    """Aggregate sentiment from multiple articles."""
    if not articles:
        return {"overall": "neutral", "positive": 0, "negative": 0, "neutral": 0, "total": 0}

    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for a in articles:
        s = a.get("sentiment", "neutral")
        counts[s] = counts.get(s, 0) + 1

    total = len(articles)
    if counts["positive"] > counts["negative"]:
        overall = "positive"
    elif counts["negative"] > counts["positive"]:
        overall = "negative"
    else:
        overall = "neutral"

    return {
        "overall": overall,
        "positive": counts["positive"],
        "negative": counts["negative"],
        "neutral": counts["neutral"],
        "total": total,
        "positive_pct": round(counts["positive"] / total * 100, 1),
        "negative_pct": round(counts["negative"] / total * 100, 1),
    }


def get_sentiment_summary(symbol: str) -> Dict:
    """Get complete sentiment summary for a stock."""
    articles = fetch_news_sentiment(symbol)
    summary = aggregate_sentiment(articles)
    summary["articles"] = articles[:5]  # Top 5 articles
    return summary
