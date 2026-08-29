import time

import httpx
import respx

from app.forms import CONTACT_KINDS, INTERVIEW_FORMATS, sign_ts


def _ts(app, age=10):
    """A signed timestamp old enough to clear MIN_FILL_SECONDS (default 3)."""
    return sign_ts(app.state.ts_signer, now=int(time.time()) - age)


def _good_payload(app):
    return {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "company": "Analytical Engines",
        "kind": CONTACT_KINDS[0],
        "msg": "I need an architecture sprint for an agent platform.",
        "website": "",
        "ts": _ts(app),
    }


# --- contact ---------------------------------------------------------------

def test_contact_get(client):
    r = client.get("/contact")
    assert r.status_code == 200
    assert "Project enquiry" in r.text
    assert 'name="website"' in r.text  # honeypot present
    assert 'name="ts"' in r.text


def test_contact_dropdown_lists_every_service(client):
    # The "What do you need?" options are rendered from packages.yaml.
    body = client.get("/contact").text
    for name in (
        "Architecture Sprint",
        "Build and Ship",
        "Fractional Architect",
        "Interview Prep",
        "30-Minute Discussion",
        "Something else",
    ):
        assert f">{name}</option>" in body


def test_contact_get_sent_panel(client):
    r = client.get("/contact?sent=1")
    assert r.status_code == 200
    assert "Thank you" in r.text
    assert "Project enquiry" not in r.text


def test_contact_post_valid_sends_and_redirects(client, app):
    with respx.mock:
        route = respx.post("https://api.resend.com/emails").mock(
            return_value=httpx.Response(200, json={"id": "x"})
        )
        r = client.post("/contact", data=_good_payload(app), follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/contact?sent=1"
    # dry-run is ON in tests -> Resend NOT actually called
    assert not route.called


def test_contact_post_missing_field_400(client, app):
    payload = _good_payload(app)
    del payload["msg"]
    r = client.post("/contact", data=payload, follow_redirects=False)
    assert r.status_code == 400
    assert "check the highlighted" in r.text.lower()
    assert "Ada Lovelace" in r.text  # value refilled


def test_contact_post_bad_email_400(client, app):
    payload = _good_payload(app)
    payload["email"] = "nope"
    r = client.post("/contact", data=payload, follow_redirects=False)
    assert r.status_code == 400


def test_contact_post_bad_kind_400(client, app):
    payload = _good_payload(app)
    payload["kind"] = "Tarot reading"
    r = client.post("/contact", data=payload, follow_redirects=False)
    assert r.status_code == 400


def test_contact_post_honeypot_silent_success(client, app):
    payload = _good_payload(app)
    payload["website"] = "I am a bot"
    r = client.post("/contact", data=payload, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/contact?sent=1"


def test_contact_post_too_fast_silent_success(client, app):
    payload = _good_payload(app)
    payload["ts"] = sign_ts(app.state.ts_signer, now=int(time.time()))  # 0s old
    r = client.post("/contact", data=payload, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/contact?sent=1"


def test_contact_post_forged_ts_silent_success(client, app):
    payload = _good_payload(app)
    payload["ts"] = "not-a-real-token"
    r = client.post("/contact", data=payload, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/contact?sent=1"


def test_contact_post_rate_limited(client, app):
    # env default RATE_LIMIT_MAX=5
    last = None
    for _ in range(7):
        last = client.post("/contact", data=_good_payload(app), follow_redirects=False)
    assert last.status_code == 429


def test_contact_send_failure_still_redirects(client, app, monkeypatch):
    async def _fail(*a, **kw):
        return False

    monkeypatch.setattr("app.main.send_form_email", _fail)
    r = client.post("/contact", data=_good_payload(app), follow_redirects=False)
    assert r.status_code == 303


# --- interviews ------------------------------------------------------------

def _iv_payload(app):
    return {
        "name": "Grace Hopper", "email": "grace@example.com",
        "format": INTERVIEW_FORMATS[0], "target": "Staff backend, fintech",
        "slots": "Tue/Thu after 8pm IST, Sat morning",
        "website": "", "ts": _ts(app),
    }


def test_interviews_get(client):
    r = client.get("/interviews")
    assert r.status_code == 200
    assert "Book a mock interview" in r.text
    assert 'action="/interviews"' in r.text


def test_interviews_get_sent(client):
    assert "Request received" in client.get("/interviews?sent=1").text


def test_interviews_post_valid(client, app):
    r = client.post("/interviews", data=_iv_payload(app), follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/interviews?sent=1"


def test_interviews_post_bad_format_400(client, app):
    p = _iv_payload(app)
    p["format"] = "Tarot reading · 90 min"
    assert client.post("/interviews", data=p, follow_redirects=False).status_code == 400


def test_interviews_post_missing_slots_400(client, app):
    p = _iv_payload(app)
    p["slots"] = ""
    r = client.post("/interviews", data=p, follow_redirects=False)
    assert r.status_code == 400
    assert "Grace Hopper" in r.text  # value refilled


def test_interviews_post_honeypot(client, app):
    p = _iv_payload(app)
    p["website"] = "bot"
    r = client.post("/interviews", data=p, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/interviews?sent=1"


def test_interviews_post_rate_limited(client, app):
    last = None
    for _ in range(7):
        last = client.post("/interviews", data=_iv_payload(app), follow_redirects=False)
    assert last.status_code == 429


# --- newsletter ------------------------------------------------------------

def _sub_payload(app, **kw):
    p = {"email": "reader@example.com", "from": "/writing", "website": "",
         "ts": _ts(app)}
    p.update(kw)
    return p


def test_subscribe_valid_redirects_back(client, app):
    r = client.post("/subscribe", data=_sub_payload(app), follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/writing?subscribed=1"


def test_subscribe_shows_panel(client):
    body = client.get("/writing?subscribed=1").text
    assert "Subscribed" in body


def test_subscribe_bad_email(client, app):
    r = client.post("/subscribe", data=_sub_payload(app, email="nope"),
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/writing?subscribed=err"


def test_subscribe_external_from_is_neutralised(client, app):
    r = client.post("/subscribe", data=_sub_payload(app, **{"from": "https://evil.com"}),
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/?subscribed=1"


def test_subscribe_honeypot(client, app):
    r = client.post("/subscribe", data=_sub_payload(app, website="bot"),
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].endswith("subscribed=1")


def test_subscribe_honeypot_keeps_safe_path(client, app):
    r = client.post("/subscribe",
                    data=_sub_payload(app, website="bot", **{"from": "https://evil.com"}),
                    follow_redirects=False)
    assert r.headers["location"] == "/?subscribed=1"


def test_subscribe_rate_limited(client, app):
    last = None
    for _ in range(7):
        last = client.post("/subscribe", data=_sub_payload(app), follow_redirects=False)
    assert last.status_code == 429
