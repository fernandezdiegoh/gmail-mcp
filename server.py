"""Gmail MCP Server — manages Gmail via Claude Code tools."""

import json
import os
import sys

from mcp.server.fastmcp import FastMCP

import gmail_tools

email = os.environ.get("USER_EMAIL", "unknown")
mcp = FastMCP(f"Gmail ({email})")


@mcp.tool()
def search_emails(query: str, max_results: int = 10) -> str:
    """Search emails using Gmail query syntax.

    Examples: "is:unread", "from:alice@example.com", "subject:invoice after:2026/03/01"

    Args:
        query: Gmail search query (same syntax as Gmail search bar)
        max_results: Maximum number of results (1-50, default 10)
    """
    results = gmail_tools.search_emails(query, max_results)
    return json.dumps(results, indent=2, ensure_ascii=False)


@mcp.tool()
def read_email(message_id: str) -> str:
    """Read the full content of an email by its ID.

    Args:
        message_id: The Gmail message ID (from search_emails results)
    """
    result = gmail_tools.read_email(message_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def read_thread(thread_id: str) -> str:
    """Read all messages in a thread.

    Args:
        thread_id: The Gmail thread ID (from search_emails results)
    """
    results = gmail_tools.read_thread(thread_id)
    return json.dumps(results, indent=2, ensure_ascii=False)


@mcp.tool()
def mark_as_read(message_ids: list[str]) -> str:
    """Mark one or more emails as read.

    Args:
        message_ids: List of Gmail message IDs to mark as read
    """
    count = gmail_tools.mark_as_read(message_ids)
    return json.dumps({"marked_as_read": count})


@mcp.tool()
def mark_as_unread(message_ids: list[str]) -> str:
    """Mark one or more emails as unread.

    Args:
        message_ids: List of Gmail message IDs to mark as unread
    """
    count = gmail_tools.mark_as_unread(message_ids)
    return json.dumps({"marked_as_unread": count})


@mcp.tool()
def send_email(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> str:
    """Send an email.

    Args:
        to: Recipient email address(es), comma-separated
        subject: Email subject
        body: Email body (plain text)
        cc: CC recipients, comma-separated (optional)
        bcc: BCC recipients, comma-separated (optional)
    """
    result = gmail_tools.send_email(to, subject, body, cc, bcc)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def create_draft(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> str:
    """Create an email draft without sending it.

    Args:
        to: Recipient email address(es), comma-separated
        subject: Email subject
        body: Email body (plain text)
        cc: CC recipients, comma-separated (optional)
        bcc: BCC recipients, comma-separated (optional)
    """
    result = gmail_tools.create_draft(to, subject, body, cc, bcc)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def reply(thread_id: str, body: str, reply_all: bool = False) -> str:
    """Reply to an email thread.

    Args:
        thread_id: The Gmail thread ID to reply to
        body: Reply body (plain text)
        reply_all: If True, reply to all recipients (default: False)
    """
    result = gmail_tools.reply(thread_id, body, reply_all)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def list_labels() -> str:
    """List all Gmail labels with message counts."""
    results = gmail_tools.list_labels()
    return json.dumps(results, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
