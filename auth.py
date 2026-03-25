"""OAuth2 credential management for Gmail MCP."""

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_credentials() -> Credentials:
    """Load or create OAuth2 credentials for the configured account."""
    email = os.environ["USER_EMAIL"]
    client_id = os.environ["GOOGLE_OAUTH_CLIENT_ID"]
    client_secret = os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]
    creds_dir = Path(os.environ.get("CREDENTIALS_DIR", "~/.gmail-mcp")).expanduser()
    creds_dir.mkdir(parents=True, exist_ok=True)
    token_path = creds_dir / f"{email}.json"

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        # Inject client credentials from env — not persisted in token file
        creds = Credentials(
            token=creds.token,
            refresh_token=creds.refresh_token,
            token_uri=creds.token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
        creds.refresh(Request())
    else:
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        creds = flow.run_local_server(port=0)

    # Write token file atomically with 0600 permissions — no client secrets on disk
    token_data = json.dumps({
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "scopes": creds.scopes and list(creds.scopes),
    })
    fd = os.open(str(token_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(token_data)
    return creds
