"""NewsAPI integration helpers."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import List

import requests


NEWSAPI_KEY = os.getenv("NEWSAPI_API_KEY") or ""
IS_AVAILABLE = bool(NEWSAPI_KEY)


def _require_key():
    if not NEWSAPI_KEY:
        raise RuntimeError("NEWSAPI_API_KEY is not set. Export it to enable NewsAPI vendor.")


def _fetch(url: str, params: dict) -> dict:
    _require_key()
    params = {**params, "apiKey": NEWSAPI_KEY}
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "ok":
        raise RuntimeError(f"NewsAPI error: {data.get('message', 'unknown error')}")
    return data


def _format_articles(articles: List[dict], header: str) -> str:
    if not articles:
        return f"{header}\nNo matching articles."\

    lines = [header]
    for article in articles[:10]:
        published = article.get("publishedAt", "")
        try:
            published_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            published = published_dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
        lines.append(
            f"- **{article.get('title', 'Untitled')}** ({published})\n  {article.get('description', '')}\n  Source: {article.get('source', {}).get('name', 'Unknown')}"
        )
    return "\n".join(lines)


def get_newsapi_company_news(query: str, start_date: str, end_date: str) -> str:
    data = _fetch(
        "https://newsapi.org/v2/everything",
        {
            "q": query,
            "from": start_date,
            "to": end_date,
            "sortBy": "relevancy",
            "language": "en",
            "pageSize": 20,
        },
    )
    header = f"## NewsAPI Coverage for {query} ({start_date} → {end_date})"
    return _format_articles(data.get("articles", []), header)


def get_newsapi_global_news(curr_date: str, look_back_days: int = 7, limit: int = 5) -> str:
    end_dt = datetime.fromisoformat(curr_date)
    start_dt = end_dt - timedelta(days=look_back_days)

    data = _fetch(
        "https://newsapi.org/v2/top-headlines",
        {
            "language": "en",
            "pageSize": limit,
        },
    )
    header = f"## Global Headlines ({start_dt.strftime('%Y-%m-%d')} → {curr_date})"
    return _format_articles(data.get("articles", []), header)
