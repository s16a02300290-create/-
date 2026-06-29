import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from news_fetcher import fetch_all_news  # noqa: E402
from summarizer import create_daily_news  # noqa: E402

app = FastAPI(title="Daily English News Listening App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


def get_today_file() -> Path:
    return DATA_DIR / f"{date.today().isoformat()}.json"


def generate_daily_news() -> dict:
    today_file = get_today_file()
    if today_file.exists():
        with open(today_file) as f:
            return json.load(f)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching news...")
    articles = fetch_all_news(max_articles=20)

    if not articles:
        raise RuntimeError("No articles fetched")

    print(f"Fetched {len(articles)} articles. Generating summaries...")
    daily_news = create_daily_news(articles)

    with open(today_file, "w", encoding="utf-8") as f:
        json.dump(daily_news, f, ensure_ascii=False, indent=2)

    print(f"Saved to {today_file}")
    return daily_news


@app.get("/api/news/today")
async def get_today_news():
    today_file = get_today_file()
    if not today_file.exists():
        raise HTTPException(status_code=404, detail="Today's news not generated yet. Call /api/news/generate first.")
    with open(today_file) as f:
        return json.load(f)


@app.post("/api/news/generate")
async def generate_news():
    try:
        data = generate_daily_news()
        return {"status": "ok", "articles_count": len(data.get("articles", [])), "date": data.get("date")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news/history")
async def get_history():
    files = sorted(DATA_DIR.glob("*.json"), reverse=True)[:30]
    history = []
    for f in files:
        try:
            with open(f) as fp:
                data = json.load(fp)
                history.append(
                    {
                        "date": data.get("date", f.stem),
                        "articles_count": len(data.get("articles", [])),
                    }
                )
        except Exception:
            pass
    return history


@app.get("/api/news/{date_str}")
async def get_news_by_date(date_str: str):
    news_file = DATA_DIR / f"{date_str}.json"
    if not news_file.exists():
        raise HTTPException(status_code=404, detail=f"No news for {date_str}")
    with open(news_file) as f:
        return json.load(f)


@app.get("/")
async def serve_frontend():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index_file)


scheduler = BackgroundScheduler()
scheduler.add_job(
    generate_daily_news,
    trigger="cron",
    hour=6,
    minute=0,
    timezone="Asia/Tokyo",
    id="daily_news",
    replace_existing=True,
)


@app.on_event("startup")
async def startup_event():
    scheduler.start()
    print("Scheduler started. Daily news generation at 06:00 JST.")
    if not get_today_file().exists() and os.environ.get("AUTO_GENERATE_ON_STARTUP", "true").lower() == "true":
        try:
            generate_daily_news()
        except Exception as e:
            print(f"Startup generation failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
