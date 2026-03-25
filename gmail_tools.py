"""Gmail API wrapper functions."""

import base64
import email.utils
from email.mime.text import MIMEText
from typing import Any

from googleapiclient.discovery import build

from auth import get_credentials

_service = None


def _get_service():
    global _service
    if _service is None:
        creds = get_credentials()
        _service = build("gmail", "v1", credentials=creds)
    return _service


def _decode_body(payload: dict) -> str:
    """Extract plain text body from a message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = _decode_body(part)
        if result:
            return result
    return ""


def _header(headers: list[dict], name: str) -> str:
    """Get a header value by name."""
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _format_message(msg: dict, include_body: bool = True) -> dict:
    """Format a Gmail message into a clean dict."""
    headers = msg.get("payload", {}).get("headers", [])
    result = {
        "id": msg["id"],
        "threadId": msg["threadId"],
        "labelIds": msg.get("labelIds", []),
        "from": _header(headers, "From"),
        "to": _header(headers, "To"),
        "cc": _header(headers, "Cc"),
        "subject": _header(headers, "Subject"),
        "date": _header(headers, "Date"),
        "snippet": msg.get("snippet", ""),
    }
    if include_body:
        result["body"] = _decode_body(msg.get("payload", {}))
    return result


def search_emails(query: str, max_results: int = 10) -> list[dict]:
    """Search emails using Gmail query syntax."""
    svc = _get_service()
    resp = svc.users().messages().list(
        userId="me", q=query, maxResults=min(max_results, 50)
    ).execute()

    messages = resp.get("messages", [])
    if not messages:
        return []

    results = []
    for m in messages:
        msg = svc.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "To", "Cc", "Subject", "Date"]
        ).execute()
        results.append(_format_message(msg, include_body=False))
    return results


def read_email(message_id: str) -> dict:
    """Read a full email by ID."""
    svc = _get_service()
    msg = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
    return _format_message(msg, include_body=True)


def read_thread(thread_id: str) -> list[dict]:
    """Read all messages in a thread."""
    svc = _get_service()
    thread = svc.users().threads().get(userId="me", id=thread_id, format="full").execute()
    return [_format_message(m, include_body=True) for m in thread.get("messages", [])]


def mark_as_read(message_ids: list[str]) -> int:
    """Mark messages as read. Returns count of modified messages."""
    svc = _get_service()
    svc.users().messages().batchModify(
        userId="me",
        body={"ids": message_ids, "removeLabelIds": ["UNREAD"]}
    ).execute()
    return len(message_ids)


def mark_as_unread(message_ids: list[str]) -> int:
    """Mark messages as unread. Returns count of modified messages."""
    svc = _get_service()
    svc.users().messages().batchModify(
        userId="me",
        body={"ids": message_ids, "addLabelIds": ["UNREAD"]}
    ).execute()
    return len(message_ids)


def send_email(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> dict:
    """Send an email. Returns the sent message."""
    import os
    svc = _get_service()
    user_email = os.environ["USER_EMAIL"]

    msg = MIMEText(body)
    msg["To"] = to
    msg["From"] = user_email
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    sent = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"id": sent["id"], "threadId": sent["threadId"], "status": "sent"}


def create_draft(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> dict:
    """Create a draft without sending."""
    import os
    svc = _get_service()
    user_email = os.environ["USER_EMAIL"]

    msg = MIMEText(body)
    msg["To"] = to
    msg["From"] = user_email
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    draft = svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return {"id": draft["id"], "messageId": draft["message"]["id"], "status": "draft_created"}


def reply(thread_id: str, body: str, reply_all: bool = False) -> dict:
    """Reply to a thread. Gets the last message and replies to it."""
    import os
    svc = _get_service()
    user_email = os.environ["USER_EMAIL"]

    thread = svc.users().threads().get(userId="me", id=thread_id, format="metadata",
                                        metadataHeaders=["From", "To", "Cc", "Subject", "Message-ID"]).execute()
    last_msg = thread["messages"][-1]
    headers = last_msg.get("payload", {}).get("headers", [])

    original_from = _header(headers, "From")
    original_to = _header(headers, "To")
    original_cc = _header(headers, "Cc")
    original_subject = _header(headers, "Subject")
    message_id = _header(headers, "Message-ID")

    # Determine recipients
    to = original_from
    cc = ""
    if reply_all:
        all_recipients = set()
        for addr_str in [original_to, original_cc]:
            if addr_str:
                for _, addr in email.utils.getaddresses([addr_str]):
                    if addr.lower() != user_email.lower():
                        all_recipients.add(addr)
        # Remove the original sender from CC (they're in To)
        from_addr = email.utils.parseaddr(original_from)[1]
        all_recipients.discard(from_addr.lower())
        cc = ", ".join(all_recipients)

    subject = original_subject if original_subject.lower().startswith("re:") else f"Re: {original_subject}"

    msg = MIMEText(body)
    msg["To"] = to
    msg["From"] = user_email
    msg["Subject"] = subject
    msg["In-Reply-To"] = message_id
    msg["References"] = message_id
    if cc:
        msg["Cc"] = cc

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    sent = svc.users().messages().send(
        userId="me", body={"raw": raw, "threadId": thread_id}
    ).execute()
    return {"id": sent["id"], "threadId": sent["threadId"], "status": "replied"}


def list_labels() -> list[dict]:
    """List all labels with unread counts."""
    svc = _get_service()
    resp = svc.users().labels().list(userId="me").execute()
    labels = []
    for label in resp.get("labels", []):
        detail = svc.users().labels().get(userId="me", id=label["id"]).execute()
        labels.append({
            "id": detail["id"],
            "name": detail["name"],
            "type": detail.get("type", ""),
            "messagesTotal": detail.get("messagesTotal", 0),
            "messagesUnread": detail.get("messagesUnread", 0),
        })
    return labels
