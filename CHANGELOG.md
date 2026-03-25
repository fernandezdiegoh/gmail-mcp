# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## 2026-03-24

### v1.0.1 — Review fixes

- Fixed: token file written with `0600` permissions instead of default `644` — OAuth tokens are secrets
- Fixed: removed `client_id` and `client_secret` from persisted token JSON — not needed for refresh, less secrets on disk
- Fixed: HTML body fallback when `text/plain` is missing — uses `html.parser` to strip tags, many modern emails are HTML-only
- Fixed: empty `message_ids` guard on `mark_as_read`/`mark_as_unread` — Gmail API throws on empty list
- Fixed: `reply` handles empty threads gracefully instead of `IndexError`
- Fixed: `max_results` clamped to `[1, 50]` — prevents undefined behavior on 0 or negative values
- Added: `HttpError` handling on all Gmail API calls — returns `{"error": status, "message": ...}` instead of raw tracebacks
- Added: env var validation at startup (`USER_EMAIL`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`) with clear error messages
- Improved: `setup.sh` uses `set -a; source .env; set +a` instead of fragile `export $(grep ...)` — handles spaces and special chars
- Improved: `os` import moved to top-level in `gmail_tools.py` — was imported inside 3 functions
- Improved: `.gitignore` no longer blanket-ignores `*.json` — was too broad
- Added: Python 3.10+ requirement documented in README

### v1.0.0 — Initial release

- 9 tools: `search_emails`, `read_email`, `read_thread`, `mark_as_read`, `mark_as_unread`, `send_email`, `create_draft`, `reply`, `list_labels`
- Single OAuth scope: `gmail.modify` (covers read + modify + send)
- Multi-account via env vars — same `server.py`, different instances in `~/.claude.json`
- Token storage at `~/.gmail-mcp/{email}.json`
- stdio transport for Claude Code
- Zero third-party code — only `mcp` (Anthropic), `google-auth-oauthlib`, `google-api-python-client`
