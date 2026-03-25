# gmail-mcp

Minimal Gmail MCP server for Claude Code. Zero third-party code — only official Google and Anthropic libraries.

## Tools

| Tool | Description |
|------|-------------|
| `search_emails` | Search with Gmail query syntax (`is:unread`, `from:x`, `after:2026/03/01`) |
| `read_email` | Read full email by ID (headers + plain text body, HTML fallback) |
| `read_thread` | Read all messages in a thread |
| `mark_as_read` | Mark one or more emails as read |
| `mark_as_unread` | Mark one or more emails as unread |
| `send_email` | Send email (to, cc, bcc, subject, body) |
| `create_draft` | Create draft without sending |
| `reply` | Reply to a thread (supports reply-all) |
| `list_labels` | List all labels with unread counts |

## Architecture

```
gmail-mcp/
├── server.py          # FastMCP server — 9 tools, stdio transport
├── auth.py            # OAuth2 flow + credential management
├── gmail_tools.py     # Gmail API wrapper functions
├── requirements.txt   # 3 dependencies (all official)
├── setup.sh           # Create venv + install + first-time OAuth
├── .env.example       # Template for OAuth credentials
└── .gitignore
```

- **Transport:** stdio (standard for Claude Code MCPs)
- **Auth:** OAuth2 with `gmail.modify` scope (covers read + modify + send)
- **Multi-account:** Two instances in `~/.claude.json` with different env vars
- **Token storage:** `~/.gmail-mcp/{email}.json` per account, `0600` permissions

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

`setup.sh` creates the venv, installs deps, and runs the browser OAuth flow.

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

Register multiple instances with different keys (e.g., `gmail` and `gmail-personal`) pointing to the same `server.py` but different env vars. Each account gets its own token file in `CREDENTIALS_DIR`.

## Dependencies

| Package | Purpose | Source |
|---------|---------|--------|
| `mcp` | MCP SDK (FastMCP) | Anthropic (official) |
| `google-auth-oauthlib` | OAuth2 flow | Google (official) |
| `google-api-python-client` | Gmail API client | Google (official) |

## Requirements

- Python 3.10+

## License

MIT
