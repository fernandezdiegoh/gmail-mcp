#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Installing dependencies..."
.venv/bin/pip install -q -r requirements.txt

# Check for env vars
if [ -z "$GOOGLE_OAUTH_CLIENT_ID" ] || [ -z "$USER_EMAIL" ]; then
    if [ -f .env ]; then
        export $(grep -v '^#' .env | xargs)
    fi
fi

if [ -z "$GOOGLE_OAUTH_CLIENT_ID" ]; then
    echo "Set GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, and USER_EMAIL"
    echo "Either as env vars or in .env file (see .env.example)"
    exit 1
fi

echo "Running OAuth flow for $USER_EMAIL..."
.venv/bin/python3 -c "from auth import get_credentials; get_credentials(); print('Auth successful!')"

echo "Done. Token stored in ${CREDENTIALS_DIR:-~/.gmail-mcp}/"
