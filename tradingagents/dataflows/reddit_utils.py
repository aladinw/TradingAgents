"""Utility helpers for reading locally-cached Reddit data."""

import json
import os
from typing import List, Optional


def fetch_top_from_category(
    category: str,
    date: str,
    limit: int = 5,
    query: Optional[str] = None,
    data_path: str = "./data/reddit_data",
) -> List[dict]:
    """Read top Reddit posts for a given category and date from local JSON files.

    Args:
        category: e.g. "global_news" or "company_news".
        date: Date string in YYYY-MM-DD format.
        limit: Maximum number of posts to return.
        query: Optional ticker/company filter (used for company_news).
        data_path: Root directory containing the cached Reddit data.

    Returns:
        A list of dicts with keys ``title`` and ``content``.
    """
    if query:
        file_path = os.path.join(data_path, category, f"{query}_{date}.json")
    else:
        file_path = os.path.join(data_path, category, f"{date}.json")

    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

    posts = data if isinstance(data, list) else data.get("posts", [])
    return posts[:limit]
