#!/bin/bash
set -e

# Install dependencies if needed
if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "Installing dependencies..."
  pip install -r requirements.txt -q
fi

# Check API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
  if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
  fi
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set."
  echo "Copy .env.example to .env and add your API key."
  exit 1
fi

echo "Starting Daily English News server at http://localhost:8000"
cd app && uvicorn main:app --host 0.0.0.0 --port 8000 --reload
