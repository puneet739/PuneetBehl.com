import datetime as dt
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer
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

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _dateline() -> str:
    d = dt.date.today()
    return f"{d.day} {d.strftime('%B %Y')}"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="PuneetBehl.com", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.content = get_content()
    app.state.ts_signer = URLSafeTimedSerializer(settings.secret_key, salt="form-ts")

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

    @app.exception_handler(StarletteHTTPException)
    async def not_found(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return render(request, "404.html", status_code=404)
        raise exc

    return app


app = create_app()
