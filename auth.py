"""OAuth2 credential management for Gmail MCP."""

import json
import os
import stat
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _require_env(name: str) -> str:
    """Get a required env var or exit with a clear message."""
    val = os.environ.get(name)
    if not val:
        print(f"ERROR: {name} env var is required but not set.", file=sys.stderr)
        sys.exit(1)
    return val


def get_credentials() -> Credentials:
    """Load or create OAuth2 credentials for the configured account."""
    email = _require_env("USER_EMAIL")
    creds_dir = Path(os.environ.get("CREDENTIALS_DIR", "~/.gmail-mcp")).expanduser()
    creds_dir.mkdir(parents=True, exist_ok=True)
    token_path = creds_dir / f"{email}.json"

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        client_config = {
            "installed": {
                "client_id": _require_env("GOOGLE_OAUTH_CLIENT_ID"),
                "client_secret": _require_env("GOOGLE_OAUTH_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        creds = flow.run_local_server(port=0)

    # Write token file with restricted permissions (600) — no client secrets
    token_data = json.dumps({
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "scopes": creds.scopes and list(creds.scopes),
    })
    token_path.write_text(token_data)
    token_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return creds
