import datetime as dt
import logging
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import get_settings
from app.content import (
    featured_projects,
    get_content,
    get_post,
    get_project,
    project_types,
)
from app.emailer import (
    build_contact_text,
    build_interview_text,
    build_subscribe_text,
    send_form_email,
    utc_now_str,
)
from app.forms import (
    CONTACT_KINDS,
    INTERVIEW_FORMATS,
    ContactForm,
    InterviewForm,
    SubscribeForm,
    is_honeypot_tripped,
    verify_ts,
)
from app.ratelimit import RateLimiter, client_key

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _dateline() -> str:
    d = dt.date.today()
    return f"{d.day} {d.strftime('%B %Y')}"


def create_app() -> FastAPI:
    # Without this, nothing installs a root handler under uvicorn and every
    # INFO record is dropped — including the dry-run copy of each submission,
    # which is the only record of a message when Resend is not configured.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    settings = get_settings()
    app = FastAPI(title="PuneetBehl.com", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.content = get_content()
    app.state.ts_signer = URLSafeTimedSerializer(settings.secret_key, salt="form-ts")
    app.state.rl = RateLimiter(settings.rate_limit_max, settings.rate_limit_window)

    hosts = [h.strip() for h in settings.trusted_hosts.split(",") if h.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts or ["*"])
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    templates.env.globals["content"] = app.state.content
    templates.env.globals["now_dateline"] = _dateline

    def render(
        request: Request,
        name: str,
        *,
        nav_active: str = "",
        status_code: int = 200,
        **ctx,
    ) -> HTMLResponse:
        payload = {
            "request": request,
            "site": app.state.content.site,
            "nav_active": nav_active,
            "settings": settings,
            "form_ts": app.state.ts_signer.dumps(
                str(int(dt.datetime.now(dt.timezone.utc).timestamp()))
            ),
            **ctx,
        }
        return templates.TemplateResponse(
            request=request, name=name, context=payload, status_code=status_code
        )

    app.state.render = render

    TOO_MANY = "Too many submissions. Try again shortly."

    def bot_or_limited(request: Request, endpoint: str, website: str, ts: str) -> str | None:
        """Return "limited", "bot", or None for a submission's screening verdict."""
        if not app.state.rl.check(client_key(request, endpoint)):
            return "limited"
        if is_honeypot_tripped(website):
            return "bot"
        if not verify_ts(app.state.ts_signer, ts, settings.min_fill_seconds):
            return "bot"
        return None

    def errors_from(exc: ValidationError) -> dict[str, str]:
        out: dict[str, str] = {}
        for e in exc.errors():
            loc = e["loc"][-1] if e["loc"] else "form"
            out[str(loc)] = e["msg"]
        return out

    def sender_ip(request: Request) -> str:
        return client_key(request, "").rstrip(":")

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return render(
            request,
            "home.html",
            nav_active="",
            featured=featured_projects(),
            stats=app.state.content.site.home_stats,
        )

    @app.get("/work", response_class=HTMLResponse)
    async def work(request: Request):
        return render(
            request,
            "work.html",
            nav_active="work",
            projects=app.state.content.projects,
            filters=project_types(),
        )

    @app.get("/work/{slug}", response_class=HTMLResponse)
    async def project_detail(request: Request, slug: str):
        projects = app.state.content.projects
        project = get_project(slug)
        if project is None:
            return render(request, "404.html", nav_active="", status_code=404)
        idx = projects.index(project)
        return render(
            request,
            "project.html",
            nav_active="work",
            project=project,
            next_project=projects[(idx + 1) % len(projects)],
        )

    @app.get("/agentic", response_class=HTMLResponse)
    async def agentic(request: Request):
        return render(request, "agentic.html", nav_active="agentic")

    @app.get("/services", response_class=HTMLResponse)
    async def services(request: Request):
        return render(
            request,
            "services.html",
            nav_active="services",
            packages=app.state.content.packages,
        )

    @app.get("/about", response_class=HTMLResponse)
    async def about(request: Request):
        return render(
            request,
            "about.html",
            nav_active="about",
            roles=app.state.content.roles,
            skills=app.state.content.skills,
        )

    @app.get("/writing", response_class=HTMLResponse)
    async def writing(request: Request):
        return render(
            request,
            "writing.html",
            nav_active="writing",
            posts=app.state.content.posts,
        )

    @app.get("/writing/{slug}", response_class=HTMLResponse)
    async def post_detail(request: Request, slug: str):
        post = get_post(slug)
        if post is None:
            return render(request, "404.html", nav_active="", status_code=404)
        return render(request, "post.html", nav_active="writing", post=post)

    @app.get("/contact", response_class=HTMLResponse)
    async def contact_get(request: Request):
        return render(
            request,
            "contact.html",
            nav_active="contact",
            sent=bool(request.query_params.get("sent")),
            values={},
            errors={},
            contact_kinds=CONTACT_KINDS,
        )

    @app.post("/contact")
    async def contact_post(
        request: Request,
        name: str = Form(""),
        email: str = Form(""),
        company: str = Form(""),
        kind: str = Form(""),
        msg: str = Form(""),
        website: str = Form(""),
        ts: str = Form(""),
    ):
        verdict = bot_or_limited(request, "contact", website, ts)
        if verdict == "limited":
            return PlainTextResponse(TOO_MANY, status_code=429)
        if verdict == "bot":
            # Show a bot the same success page a person gets, and send nothing.
            return RedirectResponse("/contact?sent=1", status_code=303)
        try:
            form = ContactForm(name=name, email=email, company=company, kind=kind, msg=msg)
        except ValidationError as exc:
            return render(
                request,
                "contact.html",
                nav_active="contact",
                status_code=400,
                sent=False,
                errors=errors_from(exc),
                contact_kinds=CONTACT_KINDS,
                values={"name": name, "email": email, "company": company,
                        "kind": kind, "msg": msg},
            )
        await send_form_email(
            settings,
            subject=f"New enquiry — {form.name} ({form.kind})",
            text=build_contact_text(form, ip=sender_ip(request), when=utc_now_str()),
            reply_to=form.email,
        )
        return RedirectResponse("/contact?sent=1", status_code=303)

    @app.get("/interviews", response_class=HTMLResponse)
    async def interviews_get(request: Request):
        return render(
            request,
            "interviews.html",
            nav_active="interviews",
            sent=bool(request.query_params.get("sent")),
            values={},
            errors={},
            interview_formats=INTERVIEW_FORMATS,
        )

    @app.post("/interviews")
    async def interviews_post(
        request: Request,
        name: str = Form(""),
        email: str = Form(""),
        format: str = Form(""),
        target: str = Form(""),
        slots: str = Form(""),
        website: str = Form(""),
        ts: str = Form(""),
    ):
        verdict = bot_or_limited(request, "interviews", website, ts)
        if verdict == "limited":
            return PlainTextResponse(TOO_MANY, status_code=429)
        if verdict == "bot":
            return RedirectResponse("/interviews?sent=1", status_code=303)
        try:
            form = InterviewForm(
                name=name, email=email, format=format, target=target, slots=slots
            )
        except ValidationError as exc:
            return render(
                request,
                "interviews.html",
                nav_active="interviews",
                status_code=400,
                sent=False,
                errors=errors_from(exc),
                interview_formats=INTERVIEW_FORMATS,
                values={"name": name, "email": email, "format": format,
                        "target": target, "slots": slots},
            )
        await send_form_email(
            settings,
            subject=f"Mock interview request — {form.name} ({form.format})",
            text=build_interview_text(form, ip=sender_ip(request), when=utc_now_str()),
            reply_to=form.email,
        )
        return RedirectResponse("/interviews?sent=1", status_code=303)

    @app.post("/subscribe")
    async def subscribe_post(
        request: Request,
        email: str = Form(""),
        website: str = Form(""),
        ts: str = Form(""),
        from_: str = Form("/", alias="from"),
    ):
        # Sanitise the redirect target first: every branch below returns to it,
        # including the ones that never construct a valid SubscribeForm.
        safe = SubscribeForm(email="placeholder@example.com", **{"from": from_}).from_path
        verdict = bot_or_limited(request, "subscribe", website, ts)
        if verdict == "limited":
            return PlainTextResponse(TOO_MANY, status_code=429)
        if verdict == "bot":
            return RedirectResponse(f"{safe}?subscribed=1", status_code=303)
        try:
            form = SubscribeForm(email=email, **{"from": from_})
        except ValidationError:
            # The footer has no room for an error panel; a soft signal is enough.
            return RedirectResponse(f"{safe}?subscribed=err", status_code=303)
        await send_form_email(
            settings,
            subject=f"Newsletter signup — {form.email}",
            text=build_subscribe_text(form.email, ip=sender_ip(request), when=utc_now_str()),
            reply_to=form.email,
        )
        return RedirectResponse(f"{form.from_path}?subscribed=1", status_code=303)

    @app.exception_handler(StarletteHTTPException)
    async def not_found(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return render(request, "404.html", status_code=404)
        raise exc

    return app


app = create_app()
