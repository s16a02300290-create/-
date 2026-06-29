"""
Daily news generation script for GitHub Actions.
Fetches RSS news, summarizes with Claude, saves JSON, sends Gmail.
"""

import html
import json
import os
import re
import smtplib
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import google.generativeai as genai
import httpx

RSS_FEEDS = [
    {"name": "BBC World News",   "url": "https://feeds.bbci.co.uk/news/world/rss.xml",                      "category": "World"},
    {"name": "BBC Technology",   "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",                  "category": "Technology"},
    {"name": "BBC Science",      "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",     "category": "Science"},
    {"name": "NPR News",         "url": "https://feeds.npr.org/1001/rss.xml",                                "category": "World"},
    {"name": "NPR Technology",   "url": "https://feeds.npr.org/1019/rss.xml",                                "category": "Technology"},
    {"name": "Reuters Top News", "url": "https://feeds.reuters.com/reuters/topNews",                         "category": "World"},
    {"name": "The Guardian",     "url": "https://www.theguardian.com/world/rss",                             "category": "World"},
]


def strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_feed(feed: dict) -> list[dict]:
    articles = []
    try:
        r = httpx.get(feed["url"], timeout=12, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"})
        r.raise_for_status()
        root = ET.fromstring(r.text)
        for item in root.findall(".//item")[:6]:
            title = (item.findtext("title") or "").strip()
            desc = strip_tags(item.findtext("description") or "")
            if not title or len(desc) < 40:
                continue
            articles.append({
                "title": title,
                "summary": desc[:600],
                "source": feed["name"],
                "category": feed["category"],
            })
    except Exception as e:
        print(f"  ⚠ {feed['name']}: {e}", file=sys.stderr)
    return articles


def fetch_all_news(max_articles: int = 25) -> list[dict]:
    all_articles: list[dict] = []
    for feed in RSS_FEEDS:
        all_articles.extend(fetch_feed(feed))
        if len(all_articles) >= max_articles:
            break

    seen: set[str] = set()
    unique = []
    for a in all_articles:
        key = a["title"][:50].lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique[:max_articles]


def create_daily_news(articles: list[dict]) -> dict:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")

    articles_text = "\n\n".join(
        f"[{i+1}] Source: {a['source']} | Category: {a['category']}\n"
        f"Title: {a['title']}\nSummary: {a['summary']}"
        for i, a in enumerate(articles)
    )

    prompt = f"""You are an English language learning assistant.
Select the 5 most interesting and educational articles from the list below,
then create learning-friendly content for English listening practice.

Return a JSON object in exactly this format:
{{
  "date": "{date.today().isoformat()}",
  "articles": [
    {{
      "id": 1,
      "title": "Engaging title",
      "category": "category name",
      "source": "news source name",
      "summary": "Clear 3-5 sentence summary in natural English (B2-C1 level)",
      "vocabulary": [
        {{"word": "word", "definition": "日本語で簡単な意味の説明", "example": "example sentence in English"}}
      ],
      "question": "One comprehension question",
      "difficulty": "beginner|intermediate|advanced"
    }}
  ]
}}

Articles:
{articles_text}

Return only the JSON object, no other text."""

    response = model.generate_content(prompt)
    text = response.text
    start, end = text.find("{"), text.rfind("}") + 1
    if start == -1 or end <= start:
        raise ValueError("No JSON in response")
    return json.loads(text[start:end])


def send_gmail(data: dict, pages_url: str) -> None:
    gmail_user = os.environ["GMAIL_USER"]
    gmail_pass = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT_EMAIL", gmail_user)

    titles = "\n".join(
        f"  {i+1}. {a['title']} [{a.get('difficulty','?')}]"
        for i, a in enumerate(data["articles"])
    )

    today_str = data["date"]
    subject = f"🎧 Today's English News — {today_str}"

    plain = f"""Hello!

Today's English listening practice news is ready.

{titles}

Open in your browser:
{pages_url}

Happy studying!
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:sans-serif;background:#0f1117;color:#e8eaf0;padding:24px;max-width:540px;margin:0 auto;">
  <div style="background:#1e2235;border-radius:16px;padding:24px;">
    <h2 style="margin:0 0 4px;background:linear-gradient(135deg,#6c63ff,#ff6584);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
      🎧 Daily English News
    </h2>
    <p style="color:#8b92a8;font-size:13px;margin:0 0 20px;">{today_str}</p>

    <p style="color:#c8cad8;font-size:14px;margin:0 0 16px;">Today's 5 articles:</p>
    <ol style="color:#e8eaf0;font-size:14px;line-height:1.9;padding-left:20px;margin:0 0 24px;">
      {''.join(
        f'<li><b>{a["title"]}</b> <span style="color:#8b92a8;font-size:12px;">[{a.get("difficulty","?")}]</span></li>'
        for a in data["articles"]
      )}
    </ol>

    <a href="{pages_url}"
       style="display:block;background:#6c63ff;color:white;text-decoration:none;
              text-align:center;border-radius:10px;padding:14px;font-weight:700;font-size:15px;">
      ▶ Open &amp; Listen Now
    </a>
    <p style="color:#8b92a8;font-size:11px;text-align:center;margin:12px 0 0;">
      Tap the button above on your smartphone
    </p>
  </div>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_user, gmail_pass)
        smtp.sendmail(gmail_user, recipient, msg.as_string())
    print(f"✉ Email sent to {recipient}")


def main():
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    today = date.today().isoformat()
    out_file = data_dir / f"{today}.json"
    latest_file = data_dir / "latest.json"

    if out_file.exists():
        print(f"Already generated for {today}, skipping fetch.")
        data = json.loads(out_file.read_text())
    else:
        print("Fetching news...")
        articles = fetch_all_news(25)
        if not articles:
            print("ERROR: No articles fetched", file=sys.stderr)
            sys.exit(1)
        print(f"Fetched {len(articles)} articles. Calling Claude API...")
        data = create_daily_news(articles)
        out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"Saved {out_file}")

    # Save as latest
    latest_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    # Update index.json (list of all available dates, newest first)
    index_file = data_dir / "index.json"
    existing = json.loads(index_file.read_text()) if index_file.exists() else []
    if today not in existing:
        existing.insert(0, today)
    index_file.write_text(json.dumps(existing[:60], ensure_ascii=False))
    print(f"Index updated ({len(existing)} dates)")

    # Send email
    pages_url = os.environ.get("PAGES_URL", "https://s16a02300290-create.github.io/-/")
    if os.environ.get("GMAIL_USER") and os.environ.get("GMAIL_APP_PASSWORD"):
        print("Sending email...")
        send_gmail(data, pages_url)
    else:
        print("GMAIL_USER / GMAIL_APP_PASSWORD not set — skipping email.")

    print("Done!")


if __name__ == "__main__":
    main()
