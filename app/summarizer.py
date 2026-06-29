import json
import os
from typing import Any

import anthropic


def create_daily_news(articles: list[dict[str, Any]]) -> dict[str, Any]:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    articles_text = "\n\n".join(
        f"[{i+1}] Source: {a['source']} | Category: {a['category']}\n"
        f"Title: {a['title']}\n"
        f"Summary: {a['summary']}"
        for i, a in enumerate(articles)
    )

    prompt = f"""You are an English language learning assistant.
I will give you a list of news articles. Please select the 5 most interesting and educational articles,
then create learning-friendly summaries for English listening practice.

For each selected article, create:
1. A clear, simple English summary (3-5 sentences, using B2-C1 level vocabulary)
2. 3-5 key vocabulary words with definitions
3. One comprehension question

Return a JSON object in exactly this format:
{{
  "date": "today's date in YYYY-MM-DD format",
  "articles": [
    {{
      "id": 1,
      "title": "Engaging title for the news",
      "category": "category name",
      "source": "news source name",
      "summary": "Clear 3-5 sentence summary in natural English suitable for listening practice",
      "vocabulary": [
        {{"word": "word", "definition": "simple definition", "example": "example sentence"}},
        ...
      ],
      "question": "One comprehension question about the article",
      "difficulty": "beginner|intermediate|advanced"
    }}
  ]
}}

Here are the available articles:

{articles_text}

Select the 5 most educational and interesting articles and create the JSON response."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text

    start = response_text.find("{")
    end = response_text.rfind("}") + 1
    if start != -1 and end > start:
        json_str = response_text[start:end]
        return json.loads(json_str)

    raise ValueError("Could not parse JSON from Claude response")
