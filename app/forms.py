from __future__ import annotations

import time

from itsdangerous import BadData, URLSafeTimedSerializer
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.content import contact_kinds

# The single source of truth is content/packages.yaml; contact_kinds() reads
# the package names from there and appends the "Something else" catch-all.
CONTACT_KINDS: tuple[str, ...] = contact_kinds()

INTERVIEW_FORMATS: tuple[str, ...] = (
    "System design · 60 min",
    "Backend and Java · 60 min",
    "Engineering manager · 45 min",
    "Resume and levelling · 30 min",
)


class ContactForm(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=200)
    company: str = Field(default="", max_length=100)
    kind: str
    msg: str = Field(min_length=1, max_length=5000)

    @field_validator("name", "company", "msg", mode="before")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("kind")
    @classmethod
    def _known_kind(cls, v: str) -> str:
        if v not in CONTACT_KINDS:
            raise ValueError("pick one of the listed options")
        return v


class InterviewForm(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=200)
    format: str
    target: str = Field(default="", max_length=200)
    slots: str = Field(min_length=1, max_length=2000)

    @field_validator("name", "target", "slots", mode="before")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("format")
    @classmethod
    def _known_format(cls, v: str) -> str:
        if v not in INTERVIEW_FORMATS:
            raise ValueError("pick one of the listed formats")
        return v


class SubscribeForm(BaseModel):
    email: EmailStr = Field(max_length=200)
    from_path: str = Field(default="/", alias="from")

    @field_validator("from_path", mode="before")
    @classmethod
    def _safe_path(cls, v: object) -> str:
        # Anything that is not a plain, local, single-slash path becomes "/", so
        # the redirect after subscribing can never be pointed off-site.
        if not isinstance(v, str):
            return "/"
        v = v.strip()
        if (
            not v.startswith("/")
            or v.startswith("//")
            or "\\" in v
            or any(c < " " for c in v)
        ):
            return "/"
        return v


def is_honeypot_tripped(website: str | None) -> bool:
    return bool(website and website.strip())


def sign_ts(signer: URLSafeTimedSerializer, now: int | None = None) -> str:
    return signer.dumps(str(now if now is not None else int(time.time())))


def verify_ts(
    signer: URLSafeTimedSerializer,
    token: str,
    min_seconds: int,
    max_age: int = 7200,
) -> bool:
    """True when the token is ours, un-tampered, and neither too fresh nor stale.

    A form filled in under `min_seconds` was almost certainly filled by a script,
    not a person.
    """
    try:
        raw = signer.loads(token, max_age=max_age)
        issued = int(raw)
    except (BadData, ValueError, TypeError):
        return False
    age = int(time.time()) - issued
    return min_seconds <= age <= max_age
