import os
import re
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SENDER_EMAIL = os.getenv("MAIL_ID")


def _get_gmail_service():
    """Builds an authenticated Gmail API service using OAuth2 refresh token."""
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError(
            "Gmail credentials missing. Set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, "
            "and GMAIL_REFRESH_TOKEN in your .env file."
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


PORTFOLIO_URL = "https://parvachaudhari.vercel.app"
PORTFOLIO_LABEL = "Parva's Portfolio"


def _plain_to_html(text: str) -> str:
    """
    Converts a plain-text email body to minimal HTML:
    - Wraps paragraphs in <p> tags
    - Replaces portfolio URL with a clickable <a> tag
    - Keeps the rest as-is (no font injections, stays clean)
    """
    # Escape any raw HTML characters to be safe
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Replace portfolio URL (must be done after escaping)
    text = text.replace(
        PORTFOLIO_URL,
        f'<a href="{PORTFOLIO_URL}" style="color:#1a73e8;text-decoration:none;">{PORTFOLIO_LABEL}</a>',
    )

    # Split on double newlines to get paragraphs, then wrap each in <p>
    paragraphs = re.split(r"\n{2,}", text.strip())
    html_paragraphs = "".join(f"<p style=\"margin:0 0 12px 0;\">{p.replace(chr(10), '<br>')}</p>" for p in paragraphs)

    return f"""\
<html><body style="font-family:Arial,sans-serif;font-size:14px;color:#202124;line-height:1.6;max-width:600px;">
{html_paragraphs}
</body></html>"""


async def save_as_draft(to: str, subject: str, body: str) -> str:
    """
    Creates a Gmail draft (does NOT send). Returns the Gmail draft ID.

    Sends as a multipart/alternative message with both plain text and HTML
    parts so the portfolio URL is clickable in HTML-capable clients, while
    remaining readable in plain-text clients.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Plain-text email body (auto-converted to HTML internally)

    Returns:
        Gmail draft ID string (e.g. "r-12345678")

    Raises:
        Exception if Gmail API call fails
    """
    service = _get_gmail_service()

    # Build multipart/alternative message (plain + HTML)
    message = MIMEMultipart("alternative")
    message["to"] = to
    message["from"] = SENDER_EMAIL
    message["subject"] = subject

    # Plain text part (fallback for clients that don't render HTML)
    text_part = MIMEText(body, "plain")
    message.attach(text_part)

    # HTML part (shown by Gmail and most modern clients)
    html_body = _plain_to_html(body)
    html_part = MIMEText(html_body, "html")
    message.attach(html_part)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw}},
    ).execute()

    draft_id = draft["id"]
    logger.info(f"Gmail draft saved: {draft_id} -> {to} | {subject}")
    return draft_id
