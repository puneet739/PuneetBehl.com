from __future__ import annotations

import datetime as dt
import logging

import httpx

log = logging.getLogger("app.emailer")
RESEND_URL = "https://api.resend.com/emails"


def utc_now_str() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def build_contact_text(form, *, ip: str, when: str) -> str:
    return "\n".join([
        f"Name: {form.name}",
        f"Email: {form.email}",
        f"Company: {form.company or '—'}",
        f"Kind: {form.kind}",
        "",
        "Message:",
        form.msg,
        "",
        f"Submitted {when} from {ip}",
    ])


def build_interview_text(form, *, ip: str, when: str) -> str:
    return "\n".join([
        f"Name: {form.name}",
        f"Email: {form.email}",
        f"Format: {form.format}",
        f"Target: {form.target or '—'}",
        "",
        "Windows offered:",
        form.slots,
        "",
        f"Submitted {when} from {ip}",
    ])


def build_subscribe_text(email: str, *, ip: str, when: str) -> str:
    return f"Newsletter signup: {email}\n\nSubmitted {when} from {ip}"


async def send_form_email(
    settings,
    *,
    subject: str,
    text: str,
    reply_to: str | None,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Send one plain-text notification through Resend.

    Returns False rather than raising: a submission the visitor already saw
    succeed must not turn into a 500, so the body is logged for recovery.
    """
    if settings.dry_run:
        log.info("DRY RUN email\nSubject: %s\n%s", subject, text)
        return True

    payload = {
        "from": settings.mail_from,
        "to": [settings.mail_to],
        "subject": subject,
        "text": text,
    }
    if reply_to:
        payload["reply_to"] = reply_to

    owns = client is None
    client = client or httpx.AsyncClient(timeout=10)
    try:
        resp = await client.post(
            RESEND_URL,
            json=payload,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        )
        if resp.status_code // 100 == 2:
            return True
        log.error("Resend %s: %s\nSubject: %s\n%s", resp.status_code, resp.text, subject, text)
        return False
    except httpx.HTTPError as exc:
        log.error("Resend request failed: %s\nSubject: %s\n%s", exc, subject, text)
        return False
    finally:
        if owns:
            await client.aclose()
