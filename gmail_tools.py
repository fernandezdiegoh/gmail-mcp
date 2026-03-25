"""Gmail API wrapper functions."""

import base64
import email.utils
import html.parser
import os
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth import get_credentials

_service = None


def _get_service():
    global _service
    if _service is None:
        creds = get_credentials()
        _service = build("gmail", "v1", credentials=creds)
    return _service


class _HTMLTextExtractor(html.parser.HTMLParser):
    """Minimal HTML to text converter."""

    def __init__(self):
        super().__init__()
        self._text = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True
        elif tag in ("br", "p", "div", "li", "tr"):
            self._text.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._text.append(data)

    def get_text(self) -> str:
        return "".join(self._text).strip()


def _strip_html(html_str: str) -> str:
    """Strip HTML tags and return plain text."""
    extractor = _HTMLTextExtractor()
    extractor.feed(html_str)
    return extractor.get_text()


def _decode_body(payload: dict) -> str:
    """Extract body from a message payload. Prefers text/plain, falls back to text/html."""
    # First pass: look for text/plain
    result = _decode_body_by_type(payload, "text/plain")
    if result:
        return result
    # Second pass: fall back to text/html (strip tags)
    result = _decode_body_by_type(payload, "text/html")
    if result:
        return _strip_html(result)
    return ""


def _decode_body_by_type(payload: dict, mime_type: str) -> str:
    """Recursively search for a specific MIME type in the payload."""
    if payload.get("mimeType") == mime_type and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = _decode_body_by_type(part, mime_type)
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


def _api_error(e: HttpError) -> dict:
    """Format an API error into a clean dict."""
    return {"error": e.resp.status, "message": str(e)}


def search_emails(query: str, max_results: int = 10) -> list[dict]:
    """Search emails using Gmail query syntax."""
    max_results = max(1, min(max_results, 50))
    svc = _get_service()
    try:
        resp = svc.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
    except HttpError as e:
        return [_api_error(e)]

    messages = resp.get("messages", [])
    if not messages:
        return []

    results = []
    for m in messages:
        try:
            msg = svc.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "To", "Cc", "Subject", "Date"]
            ).execute()
            results.append(_format_message(msg, include_body=False))
        except HttpError:
            continue
    return results


def read_email(message_id: str) -> dict:
    """Read a full email by ID."""
    svc = _get_service()
    try:
        msg = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
    except HttpError as e:
        return _api_error(e)
    return _format_message(msg, include_body=True)


def read_thread(thread_id: str) -> list[dict]:
    """Read all messages in a thread."""
    svc = _get_service()
    try:
        thread = svc.users().threads().get(userId="me", id=thread_id, format="full").execute()
    except HttpError as e:
        return [_api_error(e)]
    return [_format_message(m, include_body=True) for m in thread.get("messages", [])]


def mark_as_read(message_ids: list[str]) -> int | dict:
    """Mark messages as read. Returns count of modified messages."""
    if not message_ids:
        return 0
    svc = _get_service()
    try:
        svc.users().messages().batchModify(
            userId="me",
            body={"ids": message_ids, "removeLabelIds": ["UNREAD"]}
        ).execute()
    except HttpError as e:
        return _api_error(e)
    return len(message_ids)


def mark_as_unread(message_ids: list[str]) -> int | dict:
    """Mark messages as unread. Returns count of modified messages."""
    if not message_ids:
        return 0
    svc = _get_service()
    try:
        svc.users().messages().batchModify(
            userId="me",
            body={"ids": message_ids, "addLabelIds": ["UNREAD"]}
        ).execute()
    except HttpError as e:
        return _api_error(e)
    return len(message_ids)


def _build_mime(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> str:
    """Build a MIME message and return base64url-encoded raw string."""
    user_email = os.environ["USER_EMAIL"]
    msg = MIMEText(body)
    msg["To"] = to
    msg["From"] = user_email
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")


def send_email(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> dict:
    """Send an email. Returns the sent message."""
    svc = _get_service()
    raw = _build_mime(to, subject, body, cc, bcc)
    try:
        sent = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    except HttpError as e:
        return _api_error(e)
    return {"id": sent["id"], "threadId": sent["threadId"], "status": "sent"}


def create_draft(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> dict:
    """Create a draft without sending."""
    svc = _get_service()
    raw = _build_mime(to, subject, body, cc, bcc)
    try:
        draft = svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    except HttpError as e:
        return _api_error(e)
    return {"id": draft["id"], "messageId": draft["message"]["id"], "status": "draft_created"}


def reply(thread_id: str, body: str, reply_all: bool = False) -> dict:
    """Reply to a thread. Gets the last message and replies to it."""
    user_email = os.environ["USER_EMAIL"]
    svc = _get_service()

    try:
        thread = svc.users().threads().get(userId="me", id=thread_id, format="metadata",
                                            metadataHeaders=["From", "To", "Cc", "Subject", "Message-ID"]).execute()
    except HttpError as e:
        return _api_error(e)

    messages = thread.get("messages", [])
    if not messages:
        return {"error": "Thread has no messages"}

    last_msg = messages[-1]
    headers = last_msg.get("payload", {}).get("headers", [])

    original_from = _header(headers, "From")
    original_to = _header(headers, "To")
    original_cc = _header(headers, "Cc")
    original_subject = _header(headers, "Subject")
    message_id = _header(headers, "Message-ID")

    to = original_from
    cc = ""
    if reply_all:
        all_recipients = set()
        for addr_str in [original_to, original_cc]:
            if addr_str:
                for _, addr in email.utils.getaddresses([addr_str]):
                    if addr.lower() != user_email.lower():
                        all_recipients.add(addr)
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
    try:
        sent = svc.users().messages().send(
            userId="me", body={"raw": raw, "threadId": thread_id}
        ).execute()
    except HttpError as e:
        return _api_error(e)
    return {"id": sent["id"], "threadId": sent["threadId"], "status": "replied"}


def list_labels() -> list[dict]:
    """List all labels with unread counts."""
    svc = _get_service()
    try:
        resp = svc.users().labels().list(userId="me").execute()
    except HttpError as e:
        return [_api_error(e)]
    labels = []
    for label in resp.get("labels", []):
        try:
            detail = svc.users().labels().get(userId="me", id=label["id"]).execute()
        except HttpError:
            continue
        labels.append({
            "id": detail["id"],
            "name": detail["name"],
            "type": detail.get("type", ""),
            "messagesTotal": detail.get("messagesTotal", 0),
            "messagesUnread": detail.get("messagesUnread", 0),
        })
    return labels
