import html
import re
import xml.etree.ElementTree as ET
from typing import Any

import httpx

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
        "name": "NPR News",
        "url": "https://feeds.npr.org/1001/rss.xml",
        "category": "World",
    },
    {
        "name": "NPR Technology",
        "url": "https://feeds.npr.org/1019/rss.xml",
        "category": "Technology",
    },
]


def _strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_feed(feed_info: dict[str, str]) -> list[dict[str, Any]]:
    articles = []
    try:
        resp = httpx.get(feed_info["url"], timeout=10, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        ns = {"media": "http://search.yahoo.com/mrss/",
              "content": "http://purl.org/rss/1.0/modules/content/"}

        items = root.findall(".//item")
        for item in items[:6]:
            title = item.findtext("title", "").strip()
            description = item.findtext("description", "") or ""
            description = _strip_tags(description)
            link = item.findtext("link", "").strip()
            pub_date = item.findtext("pubDate", "")

            if not title or len(description) < 30:
                continue

            articles.append({
                "title": title,
                "summary": description[:800],
                "link": link,
                "published": pub_date,
                "source": feed_info["name"],
                "category": feed_info["category"],
            })
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

    seen_titles: set[str] = set()
    unique_articles = []
    for article in all_articles:
        title_key = article["title"][:50].lower()
        if title_key not in seen_titles and article["title"]:
            seen_titles.add(title_key)
            unique_articles.append(article)

    return unique_articles[:max_articles]
