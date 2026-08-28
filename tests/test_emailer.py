import json

import httpx
import respx

from app.config import Settings
from app.emailer import (
    build_contact_text,
    build_interview_text,
    build_subscribe_text,
    send_form_email,
    utc_now_str,
)
from app.forms import CONTACT_KINDS, INTERVIEW_FORMATS, ContactForm, InterviewForm


def _settings(**kw):
    base = dict(secret_key="x", resend_api_key="re_test", mail_to="owner@example.com",
                mail_from="forms@example.com", mail_dry_run=False)
    base.update(kw)
    return Settings(**base)


async def test_dry_run_skips_http():
    s = _settings(mail_dry_run=True)
    with respx.mock:
        route = respx.post("https://api.resend.com/emails")
        ok = await send_form_email(s, subject="s", text="t", reply_to=None)
    assert ok is True
    assert not route.called


async def test_sends_payload():
    s = _settings()
    with respx.mock:
        route = respx.post("https://api.resend.com/emails").mock(
            return_value=httpx.Response(200, json={"id": "abc"})
        )
        ok = await send_form_email(s, subject="New enquiry", text="body",
                                   reply_to="ada@example.com")
    assert ok is True
    sent = route.calls.last.request
    assert sent.headers["authorization"] == "Bearer re_test"
    payload = json.loads(sent.content)
    assert payload["to"] == ["owner@example.com"]
    assert payload["from"] == "forms@example.com"
    assert payload["reply_to"] == "ada@example.com"
    assert payload["subject"] == "New enquiry"


async def test_omits_reply_to_when_none():
    s = _settings()
    with respx.mock:
        route = respx.post("https://api.resend.com/emails").mock(
            return_value=httpx.Response(200, json={"id": "abc"})
        )
        await send_form_email(s, subject="s", text="t", reply_to=None)
    assert "reply_to" not in json.loads(route.calls.last.request.content)


async def test_non_2xx_returns_false():
    s = _settings()
    with respx.mock:
        respx.post("https://api.resend.com/emails").mock(
            return_value=httpx.Response(422, json={"error": "bad"})
        )
        ok = await send_form_email(s, subject="s", text="t", reply_to=None)
    assert ok is False


async def test_transport_error_returns_false():
    s = _settings()
    with respx.mock:
        respx.post("https://api.resend.com/emails").mock(
            side_effect=httpx.ConnectError("boom")
        )
        ok = await send_form_email(s, subject="s", text="t", reply_to=None)
    assert ok is False


async def test_reuses_supplied_client():
    s = _settings()
    async with httpx.AsyncClient(timeout=10) as client:
        with respx.mock:
            respx.post("https://api.resend.com/emails").mock(
                return_value=httpx.Response(200, json={"id": "abc"})
            )
            ok = await send_form_email(s, subject="s", text="t", reply_to=None,
                                       client=client)
        assert ok is True
        assert not client.is_closed


def test_build_contact_text_has_all_fields():
    f = ContactForm(name="Ada", email="ada@example.com", company="Acme",
                    kind=CONTACT_KINDS[0], msg="Need help")
    txt = build_contact_text(f, ip="1.2.3.4", when="2026-08-28 10:00 UTC")
    for piece in ["Ada", "ada@example.com", "Acme", CONTACT_KINDS[0], "Need help", "1.2.3.4"]:
        assert piece in txt


def test_build_interview_text_has_all_fields():
    f = InterviewForm(name="Grace", email="grace@example.com",
                      format=INTERVIEW_FORMATS[0], target="", slots="Tue 8pm IST")
    txt = build_interview_text(f, ip="5.6.7.8", when="2026-08-28 10:00 UTC")
    for piece in ["Grace", "grace@example.com", INTERVIEW_FORMATS[0], "Tue 8pm IST", "5.6.7.8"]:
        assert piece in txt
    assert "—" in txt  # empty target renders as a dash


def test_build_subscribe_text():
    txt = build_subscribe_text("reader@example.com", ip="9.9.9.9",
                               when="2026-08-28 10:00 UTC")
    assert "reader@example.com" in txt
    assert "9.9.9.9" in txt


def test_utc_now_str_shape():
    assert utc_now_str().endswith(" UTC")
    assert len(utc_now_str()) == len("2026-08-28 14:03 UTC")
