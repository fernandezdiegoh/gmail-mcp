# gmail-mcp

Minimal Gmail MCP server for Claude Code. Zero third-party code — only official Google and Anthropic libraries.

## Tools

| Tool | Description |
|------|-------------|
| `search_emails` | Search with Gmail query syntax |
| `read_email` | Read full email by ID |
| `read_thread` | Read full thread by ID |
| `mark_as_read` | Mark emails as read |
| `mark_as_unread` | Mark emails as unread |
| `send_email` | Send email (to, cc, bcc, subject, body) |
| `create_draft` | Create draft without sending |
| `reply` | Reply to a thread (supports reply-all) |
| `list_labels` | List all labels with unread counts |

## Setup

### 1. Google Cloud Console

- Enable the Gmail API in your GCP project
- Create an OAuth 2.0 Client ID (Desktop application)
- Add `https://www.googleapis.com/auth/gmail.modify` to allowed scopes

### 2. Install

```bash
git clone https://github.com/fernandezdiegoh/gmail-mcp.git
cd gmail-mcp
cp .env.example .env
# Edit .env with your OAuth credentials
bash setup.sh
```

### 3. Register in Claude Code

Add to `~/.claude.json` under `"mcpServers"`:

```json
"gmail": {
  "type": "stdio",
  "command": "/path/to/gmail-mcp/.venv/bin/python3",
  "args": ["/path/to/gmail-mcp/server.py"],
  "env": {
    "GOOGLE_OAUTH_CLIENT_ID": "your-client-id",
    "GOOGLE_OAUTH_CLIENT_SECRET": "your-client-secret",
    "USER_EMAIL": "you@example.com",
    "CREDENTIALS_DIR": "~/.gmail-mcp"
  }
}
```

### Multi-account

Register multiple instances with different keys (e.g., `gmail` and `gmail-personal`) pointing to the same `server.py` but different env vars.

## Dependencies

- `mcp` — Anthropic's official MCP SDK (FastMCP)
- `google-auth-oauthlib` — Google OAuth2 (official)
- `google-api-python-client` — Google API client (official)

## License

MIT
