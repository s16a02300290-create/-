# Daily English News — Listening Practice App

英語のリスニング力を鍛えるための毎日自動ニュース要約アプリです。

## 機能

- **毎日自動取得**: BBC・Reutersなど英語ニュースソースからRSSで最新ニュースを収集
- **AI要約**: Claude APIがB2-C1レベルの学習しやすい英語にリライト
- **音声再生**: Web Speech API でネイティブ音声読み上げ（速度調整付き）
- **語彙学習**: 各記事のキーワードと定義・例文
- **理解確認**: 各記事に理解度チェック問題
- **難易度表示**: beginner / intermediate / advanced 分類
- **履歴閲覧**: 過去のニュース一覧

## 使い方

### 1. セットアップ

```bash
# リポジトリをクローン後
cp .env.example .env
# .env を編集して ANTHROPIC_API_KEY を設定
```

### 2. 起動

```bash
pip install -r requirements.txt
bash run.sh
```

ブラウザで http://localhost:8000 を開く。

### 3. ニュース生成

- サーバー起動時に自動でその日のニュースを生成（約30秒）
- 画面右上の **Generate** ボタンで手動生成も可能
- 毎朝 **6:00 JST** に自動で新しいニュースを生成

## 技術スタック

| 層 | 技術 |
|---|---|
| バックエンド | Python / FastAPI |
| ニュース取得 | RSS (BBC, Reuters) / feedparser |
| AI要約 | Claude API (claude-sonnet-4-6) |
| スケジューラ | APScheduler (毎朝6時JST) |
| フロントエンド | HTML / CSS / Vanilla JS |
| 音声 | Web Speech API |

## ディレクトリ構成

```
.
├── app/
│   ├── main.py           # FastAPI サーバー & スケジューラ
│   ├── news_fetcher.py   # RSS ニュース取得
│   └── summarizer.py     # Claude API 要約生成
├── frontend/
│   └── index.html        # Web UI
├── data/                 # 生成されたニュース JSON (YYYY-MM-DD.json)
├── requirements.txt
├── run.sh
└── .env.example
```

## API エンドポイント

| Method | Path | 説明 |
|---|---|---|
| GET | `/` | Web UI |
| GET | `/api/news/today` | 今日のニュース取得 |
| POST | `/api/news/generate` | ニュース生成（強制） |
| GET | `/api/news/history` | 過去の日付一覧 |
| GET | `/api/news/{date}` | 指定日のニュース |
