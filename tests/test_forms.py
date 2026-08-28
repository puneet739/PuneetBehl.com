import time

import pytest
from itsdangerous import URLSafeTimedSerializer
from pydantic import ValidationError

from app.forms import (
    CONTACT_KINDS,
    ContactForm,
    InterviewForm,
    SubscribeForm,
    is_honeypot_tripped,
    sign_ts,
    verify_ts,
)

SIGNER = URLSafeTimedSerializer("test-secret-key-fixed", salt="form-ts")


def test_contact_form_valid():
    f = ContactForm(name="  Ada  ", email="ada@example.com", company="",
                    kind=CONTACT_KINDS[0], msg="Hello there")
    assert f.name == "Ada"
    assert f.email == "ada@example.com"


def test_contact_form_rejects_bad_kind():
    with pytest.raises(ValidationError):
        ContactForm(name="Ada", email="ada@example.com", kind="nonsense", msg="hi")


def test_contact_form_rejects_bad_email():
    with pytest.raises(ValidationError):
        ContactForm(name="Ada", email="not-an-email", kind=CONTACT_KINDS[0], msg="hi")


def test_contact_form_rejects_oversized_msg():
    with pytest.raises(ValidationError):
        ContactForm(name="Ada", email="ada@example.com", kind=CONTACT_KINDS[0],
                    msg="x" * 5001)


def test_contact_form_requires_msg():
    with pytest.raises(ValidationError):
        ContactForm(name="Ada", email="ada@example.com", kind=CONTACT_KINDS[0], msg="   ")


def test_interview_form_valid():
    f = InterviewForm(name="Ada", email="ada@example.com",
                      format="System design · 60 min", target="", slots="Tue 8pm IST")
    assert f.slots == "Tue 8pm IST"


def test_interview_form_rejects_bad_format():
    with pytest.raises(ValidationError):
        InterviewForm(name="Ada", email="ada@example.com",
                      format="Tarot reading · 90 min", slots="Tue 8pm IST")


def test_subscribe_form_sanitizes_from():
    assert SubscribeForm(email="a@b.com", **{"from": "https://evil.com"}).from_path == "/"
    assert SubscribeForm(email="a@b.com", **{"from": "//evil.com"}).from_path == "/"
    assert SubscribeForm(email="a@b.com", **{"from": "/writing"}).from_path == "/writing"


def test_subscribe_form_rejects_control_chars_and_backslash():
    assert SubscribeForm(email="a@b.com", **{"from": "/writ\ning"}).from_path == "/"
    assert SubscribeForm(email="a@b.com", **{"from": "/writ\\ing"}).from_path == "/"
    assert SubscribeForm(email="a@b.com", **{"from": 42}).from_path == "/"


def test_honeypot():
    assert is_honeypot_tripped("bot") is True
    assert is_honeypot_tripped("") is False
    assert is_honeypot_tripped(None) is False


def test_ts_roundtrip_too_fast():
    tok = sign_ts(SIGNER, now=int(time.time()))
    assert verify_ts(SIGNER, tok, min_seconds=3) is False  # just signed -> too fast


def test_ts_roundtrip_ok():
    tok = sign_ts(SIGNER, now=int(time.time()) - 10)
    assert verify_ts(SIGNER, tok, min_seconds=3) is True


def test_ts_tampered():
    assert verify_ts(SIGNER, "garbage", min_seconds=3) is False


def test_ts_too_old():
    tok = sign_ts(SIGNER, now=int(time.time()) - 99999)
    assert verify_ts(SIGNER, tok, min_seconds=3, max_age=7200) is False
