import datetime as dt
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import get_settings
from app.content import get_content

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
        return render(request, "home.html", nav_active="")

    return app


app = create_app()
