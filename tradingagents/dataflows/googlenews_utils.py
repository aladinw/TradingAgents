"""Google News RSS feed utilities for fetching news data."""

import feedparser
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List
from urllib.parse import quote_plus


def getNewsData(query: str, start_date: str, end_date: str) -> List[dict]:
    """Fetch Google News results for a query within a date range.

    Args:
        query: Search query (spaces should be replaced with '+').
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.

    Returns:
        List of dicts with keys: title, source, snippet, link, published.
    """
    try:
        # Google News RSS feed URL with date filtering
        url = (
            f"https://news.google.com/rss/search?"
            f"q={quote_plus(query)}+after:{start_date}+before:{end_date}&hl=en&gl=US&ceid=US:en"
        )
        feed = feedparser.parse(url)

        results = []
        for entry in feed.entries:
            source = entry.get("source", {})
            source_name = source.get("title", "Unknown") if isinstance(source, dict) else str(source)
            results.append({
                "title": entry.get("title", ""),
                "source": source_name,
                "snippet": entry.get("summary", entry.get("description", "")),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })

        return results
    except Exception as e:
        print(f"[GoogleNews] Error fetching news for '{query}': {e}")
        return []


def getGlobalNewsData(
    curr_date: str,
    look_back_days: int = 7,
    limit: int = 10,
) -> List[dict]:
    """Fetch global/macro financial news via Google News RSS feed.

    Args:
        curr_date: Current date in YYYY-MM-DD format.
        look_back_days: Number of days to look back.
        limit: Maximum number of news items to return.

    Returns:
        List of dicts with keys: title, source, snippet, link, published.
    """
    try:
        end_date = curr_date
        start_dt = datetime.strptime(curr_date, "%Y-%m-%d") - relativedelta(days=look_back_days)
        start_date = start_dt.strftime("%Y-%m-%d")

        query = "stock+market+finance+economy"
        url = (
            f"https://news.google.com/rss/search?"
            f"q={query}+after:{start_date}+before:{end_date}&hl=en&gl=US&ceid=US:en"
        )
        feed = feedparser.parse(url)

        results = []
        for entry in feed.entries[:limit]:
            source = entry.get("source", {})
            source_name = source.get("title", "Unknown") if isinstance(source, dict) else str(source)
            results.append({
                "title": entry.get("title", ""),
                "source": source_name,
                "snippet": entry.get("summary", entry.get("description", "")),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })

        return results
    except Exception as e:
        print(f"[GoogleNews] Error fetching global news: {e}")
        return []
