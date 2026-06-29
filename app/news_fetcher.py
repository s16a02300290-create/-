import feedparser
import httpx
from datetime import datetime, timezone
from typing import Any

RSS_FEEDS = [
    {
        "name": "BBC World News",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "category": "World",
    },
    {
        "name": "BBC Technology",
        "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "category": "Technology",
    },
    {
        "name": "BBC Science",
        "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "category": "Science",
    },
    {
        "name": "Reuters Top News",
        "url": "https://feeds.reuters.com/reuters/topNews",
        "category": "World",
    },
    {
        "name": "Reuters Business",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "category": "Business",
    },
]

FALLBACK_FEEDS = [
    {
        "name": "NPR News",
        "url": "https://feeds.npr.org/1001/rss.xml",
        "category": "World",
    },
    {
        "name": "NPR Technology",
        "url": "https://feeds.npr.org/1019/rss.xml",
        "category": "Technology",
    },
    {
        "name": "Associated Press Top Headlines",
        "url": "https://rsshub.app/apnews/topics/apf-topnews",
        "category": "World",
    },
]


def fetch_feed(feed_info: dict[str, str]) -> list[dict[str, Any]]:
    articles = []
    try:
        parsed = feedparser.parse(feed_info["url"])
        for entry in parsed.entries[:5]:
            summary = entry.get("summary", "") or entry.get("description", "")
            if len(summary) < 30:
                continue
            articles.append(
                {
                    "title": entry.get("title", ""),
                    "summary": summary,
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": feed_info["name"],
                    "category": feed_info["category"],
                }
            )
    except Exception as e:
        print(f"Error fetching {feed_info['name']}: {e}")
    return articles


def fetch_all_news(max_articles: int = 20) -> list[dict[str, Any]]:
    all_articles: list[dict[str, Any]] = []

    for feed in RSS_FEEDS:
        articles = fetch_feed(feed)
        all_articles.extend(articles)
        if len(all_articles) >= max_articles:
            break

    if len(all_articles) < 10:
        for feed in FALLBACK_FEEDS:
            articles = fetch_feed(feed)
            all_articles.extend(articles)
            if len(all_articles) >= max_articles:
                break

    seen_titles: set[str] = set()
    unique_articles = []
    for article in all_articles:
        title_key = article["title"][:50].lower()
        if title_key not in seen_titles and article["title"]:
            seen_titles.add(title_key)
            unique_articles.append(article)

    return unique_articles[:max_articles]
