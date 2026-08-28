# PuneetBehl.com Site + Contact Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Claude Design canvas file into a real server-rendered website served by FastAPI, with contact / interview / newsletter forms that email the owner via Resend, shipped as one Docker image.

**Architecture:** FastAPI + Jinja2, server-rendered HTML at real URLs. Content (projects, posts, packages, roles, site copy) lives in `content/` as YAML and Markdown, loaded into frozen pydantic models at startup. Three form endpoints validate with pydantic, screen for bots (honeypot + signed timestamp + in-memory rate limit), send one email through the Resend HTTP API, then 303-redirect to a success state. No database. A small progressive-enhancement script adds the scroll-progress bar, reveal animations, and inline form submits; everything works with JavaScript disabled.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Jinja2, python-multipart, pydantic v2, pydantic-settings, httpx, itsdangerous, markdown-it-py, python-frontmatter, PyYAML. Tests: pytest, respx.

**Spec:** `docs/superpowers/specs/2026-08-28-puneetbehl-site-and-contact-backend-design.md`

## Global Constraints

- Python 3.12. Base image `python:3.12-slim`.
- No database, no ORM, no persistent storage.
- No JS framework, no front-end build step. One hand-written `app/static/js/site.js`, loaded with `defer`.
- CSS/JS are external files under `/static`. No inline `<style>`/`<script>` in templates except the ported `templates/_plates.svg`.
- Design system file `app/static/css/styles.css` is copied verbatim from `_ds/broadsheet-20458c33-7e5f-417c-af2f-3e6f2feef7e1/styles.css` and never hand-edited.
- Source of visual truth: `Puneet Behl Site.dc.html`. Templates are ported from specific line ranges of that file (ranges given per task), applying this conversion recipe every time:
  - `{{ x }}` → `{{ x }}` (Jinja variable — usually unchanged, but resolve against the context the route passes)
  - `<sc-for list="{{ items }}" as="p">...</sc-for>` → `{% for p in items %}...{% endfor %}`
  - `<sc-if value="{{ cond }}">...</sc-if>` → `{% if cond %}...{% endif %}`
  - Delete every `onClick="{{ ... }}"` and `onSubmit="{{ ... }}"` attribute.
  - `href="#/foo"` → `href="/foo"`; `href="#/work/{{ p.slug }}"` → `href="/work/{{ p.slug }}"`.
  - Remove `hint-placeholder-*` attributes.
  - Remove initial `opacity:0` from `.reveal` usage is NOT needed — keep classes; `site.css` handles the no-JS fallback (Task 3).
- All form emails go to `puneet739@gmail.com` (config default `MAIL_TO`).
- Owner-facing copy must not be reworded. Port text verbatim from the design.
- Commit after every task with a `feat:` / `test:` / `chore:` prefixed message.
- Every route handler is `async def`. Content lookups are sync (in-memory).

---

## File Structure

```
app/
  __init__.py          # empty
  config.py            # Settings (pydantic-settings)
  content.py           # models + loaders + lookup helpers
  emailer.py           # Resend client, send_form_email()
  forms.py             # ContactForm/InterviewForm/SubscribeForm, sign_ts/verify_ts, honeypot check
  ratelimit.py         # RateLimiter dependency
  main.py              # FastAPI app, lifespan, all routes, Jinja env
  templates/
    base.html _header.html _footer.html _plates.svg _form_errors.html
    home.html work.html project.html agentic.html services.html
    about.html writing.html post.html contact.html interviews.html
  static/
    css/styles.css css/site.css
    js/site.js
    assets/*.svg  favicon.svg
content/
  site.yaml projects.yaml packages.yaml roles.yaml skills.yaml
  writing/
    agents-are-distributed-systems.md
    ecs-to-eks-what-i-would-do-differently.md
    the-eval-set-is-the-product.md
    interoperability-is-a-people-problem.md
tests/
  conftest.py test_content.py test_pages.py test_forms.py
  test_emailer.py test_ratelimit.py
pyproject.toml Dockerfile docker-compose.yml .dockerignore
.env.example .gitignore README.md
.github/workflows/ci.yml
```

---

## Task 1: Project scaffold, config, health check

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `app/__init__.py`, `app/config.py`, `app/main.py`, `tests/__init__.py`, `tests/conftest.py`, `tests/test_pages.py`

**Interfaces:**
- Produces:
  - `app.config.Settings` — pydantic-settings model; `app.config.get_settings() -> Settings` (cached).
  - `app.main.app` — the FastAPI instance.
  - `app.main.create_app() -> FastAPI` — factory used by tests.
  - Route `GET /healthz` → `200`, JSON `{"status": "ok"}`.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "puneetbehl-site"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "httpx>=0.27",
    "itsdangerous>=2.2",
    "markdown-it-py>=3.0",
    "python-frontmatter>=1.1",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.2", "respx>=0.21"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

- [ ] **Step 2: Create `.gitignore`**

```
__pycache__/
*.pyc
.env
.venv/
.pytest_cache/
*.egg-info/
```

- [ ] **Step 3: Create `.env.example`**

```
PORT=8000
SECRET_KEY=change-me-to-a-long-random-string
RESEND_API_KEY=
MAIL_TO=puneet739@gmail.com
MAIL_FROM=onboarding@resend.dev
MAIL_DRY_RUN=true
RATE_LIMIT_MAX=5
RATE_LIMIT_WINDOW=60
MIN_FILL_SECONDS=3
TURNSTILE_SITE_KEY=
TURNSTILE_SECRET=
TRUSTED_HOSTS=*
```

- [ ] **Step 4: Create `app/__init__.py` and `tests/__init__.py`** (both empty files)

- [ ] **Step 5: Create `app/config.py`**

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8000
    secret_key: str = "dev-insecure-secret-key-change-me"
    resend_api_key: str = ""
    mail_to: str = "puneet739@gmail.com"
    mail_from: str = "onboarding@resend.dev"
    mail_dry_run: bool = False
    rate_limit_max: int = 5
    rate_limit_window: int = 60
    min_fill_seconds: int = 3
    turnstile_site_key: str = ""
    turnstile_secret: str = ""
    trusted_hosts: str = "*"

    @property
    def dry_run(self) -> bool:
        return self.mail_dry_run or not self.resend_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 6: Write the failing test — `tests/conftest.py`**

```python
import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-fixed")
os.environ.setdefault("MAIL_DRY_RUN", "true")
os.environ.setdefault("MAIL_TO", "puneet739@gmail.com")
os.environ.setdefault("MAIL_FROM", "forms@example.com")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=True)
```

- [ ] **Step 7: Write the failing test — `tests/test_pages.py`**

```python
def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 8: Run it, verify it fails**

Run: `pip install -e ".[dev]" && pytest tests/test_pages.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 9: Create `app/main.py`**

```python
from fastapi import FastAPI

from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="PuneetBehl.com", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 10: Run it, verify it passes**

Run: `pytest tests/test_pages.py -v`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add pyproject.toml .gitignore .env.example app tests
git commit -m "chore: scaffold FastAPI app with config and health check"
```

---

## Task 2: Content models and loaders

**Files:**
- Create: `app/content.py`, `content/site.yaml`, `content/projects.yaml`, `content/packages.yaml`, `content/roles.yaml`, `content/skills.yaml`, `content/writing/*.md` (4 files), `tests/test_content.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - Models (all `pydantic.BaseModel`, `model_config = ConfigDict(frozen=True)`):
    - `Metric(value: str, label: str)`
    - `Project(slug, name, mono, domain, type, year, role, tint, headline, summary, problem, architecture: str; approach: list[str]; metrics: list[Metric]; stack: list[str])`
    - `Package(kicker, name, price, terms, blurb, cta: str; items: list[str])`
    - `Role(years, title, company, note: str)`
    - `Post(slug, title, excerpt, read, body_html: str; date: datetime.date)` with property `date_display -> str` = `date.strftime("%-d %B %Y")`
    - `Testimonial(quote: str, author: str)`
    - `HomeStat(value: str, label: str)`
    - `SiteConfig(tagline_role: str, availability_short: str, availability_long: str, email: str, phone: str, linkedin: str, github: str, location: str, testimonial: Testimonial, home_stats: list[HomeStat], footer_blurb: str, credentials: str)`
  - `Content` dataclass/object with attributes: `site: SiteConfig`, `projects: list[Project]`, `packages: list[Package]`, `roles: list[Role]`, `skills: list[str]`, `posts: list[Post]`.
  - Module-level functions:
    - `load_content(root: Path = CONTENT_DIR) -> Content` — parses everything, raises on any missing file / validation error.
    - `get_content() -> Content` — cached singleton (module global, populated on first call).
    - `get_project(slug: str) -> Project | None`
    - `get_post(slug: str) -> Post | None`
    - `featured_projects() -> list[Project]` — returns `[projects[0], projects[2], projects[1], projects[4]]`.
    - `project_types() -> list[str]` — `["All"] + distinct .type in first-seen order`.
  - `CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"`

- [ ] **Step 1: Create `content/projects.yaml`**

Port all 8 objects from `Puneet Behl Site.dc.html` lines 645–716 (`const PROJECTS`). One YAML list entry per object. Keys map 1:1. `approach` is a list; `metrics` is a list of `{value, label}`; `stack` is a list. Copy every string **verbatim** including em-dashes and apostrophes. Order preserved: loaderhouse, chartwell, relayd, northgate-rails, kubestat, tenderfoot, specflow, anchor-cli.

Example shape for the first entry:

```yaml
- slug: loaderhouse
  name: Loaderhouse
  mono: LH
  domain: loaderhouse.com
  type: Website
  year: "2026"
  role: Architect and lead engineer
  tint: var(--color-accent)
  headline: 3.1M loads matched a year
  summary: >-
    A freight load board for mid-size Indian carriers — public marketplace,
    broker console and a matching service that ranks loads against a truck's
    route, capacity and return leg.
  problem: >-
    Loaderhouse was running on a PHP monolith where every search hit the primary
    database. Peak-hour searches took eleven seconds, brokers were losing loads
    to the phone, and the team could not ship a mobile client on top of it.
  approach:
    - Rebuilt search as a read-optimised projection in Postgres with Redis-backed geo indexes, taking p95 search latency from 11s to 240ms.
    - Split the matching engine into its own service with a scored ranking model over route overlap, capacity and historical acceptance.
    - Introduced an event log so the broker console, notifications and analytics all read the same stream instead of polling.
    - Shipped a public marketing site and SEO-indexable load pages that now bring in a third of new carrier signups.
  architecture: >-
    Next.js front end on CloudFront, Spring Boot services on ECS Fargate behind
    an ALB, Postgres with read replicas, Redis for geo and session, and an
    SNS/SQS fan-out for notification and analytics consumers. Terraform for
    everything; deploys are trunk-based through GitHub Actions.
  metrics:
    - {value: "240ms", label: "p95 search latency, down from 11s"}
    - {value: "12,400", label: "active carriers on the platform"}
    - {value: "3.1M", label: "loads matched in the last year"}
  stack: [Next.js, Spring Boot, Postgres, Redis, ECS Fargate, Terraform]
```

- [ ] **Step 2: Create `content/packages.yaml`**

Port the 3 objects from lines 754–765 (`const PACKAGES`). Keys: `kicker, name, price, terms, blurb, items (list), cta`.

- [ ] **Step 3: Create `content/roles.yaml`**

Port the 6 objects from lines 766–773 (`const ROLES`). Keys: `years, title, company, note`.

- [ ] **Step 4: Create `content/skills.yaml`**

```yaml
- Java
- Spring Boot
# ... all 30 strings from line 775, in order
```

- [ ] **Step 5: Create `content/site.yaml`**

Fill from header/footer/hero/contact copy in the design. Values:

```yaml
tagline_role: "Technical Architect · Bengaluru"
availability_short: "2 slots · Oct 2026"
availability_long: "Two slots open from October 2026"
email: "puneet739@gmail.com"
phone: "+91 97116 16135"
linkedin: "https://linkedin.com/in/puneetbehl"
github: "https://github.com/puneetbehl"
location: "Bengaluru, India · UTC+5:30"
footer_blurb: >-
  Freelance technical architect. Distributed systems, AWS and Kubernetes,
  agentic AI. Bengaluru, working worldwide.
credentials: "AWS Certified Solutions Architect · CKAD · Certified ScrumMaster"
testimonial:
  quote: >-
    Puneet arrived with a diagram and left us with a running platform. Six
    months in, the payments core has not had a Sev-1.
  author: "Ravi Menon — VP Engineering, Northgate Financial"
home_stats:
  - {value: "50M+", label: "Requests per day on the platforms I architected"}
  - {value: "99.99%", label: "Sustained uptime, fault-tolerant by design"}
  - {value: "60%", label: "Cycle-time reduction from AI, spec-driven delivery"}
  - {value: "35", label: "Engineers across 7 teams on that workflow"}
```

- [ ] **Step 6: Create the 4 Markdown posts in `content/writing/`**

For each object in `const POSTS` (lines 719–752), create `<slug>.md`:

```markdown
---
title: "Your agent is a distributed system wearing a prompt"
date: 2026-08-12
read: "8 min read"
excerpt: >-
  Every hard problem teams hit with agents in production is a problem
  distributed systems solved twenty years ago — and mostly forgot to tell the
  AI crowd about.
---

<paragraph 1 from the body array>

<paragraph 2>

...
```

`date` is the ISO form of the design's `date` string (`12 August 2026` → `2026-08-12`, `26 June 2026` → `2026-06-26`, `02 May 2026` → `2026-05-02`, `18 March 2026` → `2026-03-18`). Each element of the `body` array becomes one Markdown paragraph separated by a blank line. Copy text verbatim.

- [ ] **Step 7: Write the failing test — `tests/test_content.py`**

```python
import datetime as dt

import pytest

from app.content import (
    get_content,
    get_post,
    get_project,
    featured_projects,
    load_content,
    project_types,
)


@pytest.fixture(scope="module")
def content():
    return get_content()


def test_counts(content):
    assert len(content.projects) == 8
    assert len(content.packages) == 3
    assert len(content.roles) == 6
    assert len(content.posts) == 4
    assert len(content.skills) == 30


def test_project_order_and_fields(content):
    assert content.projects[0].slug == "loaderhouse"
    p = content.projects[0]
    assert p.metrics[0].value == "240ms"
    assert len(p.approach) == 4
    assert "Postgres" in p.stack


def test_get_project(content):
    assert get_project("chartwell").name == "Chartwell Summary"
    assert get_project("nope") is None


def test_posts_sorted_desc(content):
    dates = [p.date for p in content.posts]
    assert dates == sorted(dates, reverse=True)
    assert content.posts[0].slug == "agents-are-distributed-systems"


def test_post_renders_html(content):
    post = get_post("the-eval-set-is-the-product")
    assert post is not None
    assert "<p>" in post.body_html
    assert post.date_display == "2 May 2026"


def test_get_post_missing():
    assert get_post("nope") is None


def test_featured_order(content):
    slugs = [p.slug for p in featured_projects()]
    assert slugs == ["loaderhouse", "relayd", "chartwell", "kubestat"]


def test_project_types(content):
    types = project_types()
    assert types[0] == "All"
    assert "Website" in types and "Agentic AI" in types


def test_load_content_raises_on_missing(tmp_path):
    with pytest.raises(Exception):
        load_content(tmp_path)
```

- [ ] **Step 8: Run it, verify it fails**

Run: `pytest tests/test_content.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.content'`.

- [ ] **Step 9: Create `app/content.py`**

```python
from __future__ import annotations

import datetime as dt
from pathlib import Path

import frontmatter
import yaml
from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
_md = MarkdownIt("commonmark", {"typographer": True}).enable(["replacements", "smartquotes"])


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class Metric(_Frozen):
    value: str
    label: str


class Project(_Frozen):
    slug: str
    name: str
    mono: str
    domain: str
    type: str
    year: str
    role: str
    tint: str
    headline: str
    summary: str
    problem: str
    architecture: str
    approach: list[str]
    metrics: list[Metric]
    stack: list[str]


class Package(_Frozen):
    kicker: str
    name: str
    price: str
    terms: str
    blurb: str
    cta: str
    items: list[str]


class Role(_Frozen):
    years: str
    title: str
    company: str
    note: str


class Post(_Frozen):
    slug: str
    title: str
    excerpt: str
    read: str
    date: dt.date
    body_html: str

    @property
    def date_display(self) -> str:
        d = self.date
        return f"{d.day} {d.strftime('%B %Y')}"


class Testimonial(_Frozen):
    quote: str
    author: str


class HomeStat(_Frozen):
    value: str
    label: str


class SiteConfig(_Frozen):
    tagline_role: str
    availability_short: str
    availability_long: str
    email: str
    phone: str
    linkedin: str
    github: str
    location: str
    footer_blurb: str
    credentials: str
    testimonial: Testimonial
    home_stats: list[HomeStat]


class Content(_Frozen):
    site: SiteConfig
    projects: list[Project]
    packages: list[Package]
    roles: list[Role]
    skills: list[str]
    posts: list[Post]


def _read_yaml(path: Path):
    with path.open() as fh:
        return yaml.safe_load(fh)


def load_content(root: Path = CONTENT_DIR) -> Content:
    root = Path(root)
    site = SiteConfig(**_read_yaml(root / "site.yaml"))
    projects = [Project(**p) for p in _read_yaml(root / "projects.yaml")]
    packages = [Package(**p) for p in _read_yaml(root / "packages.yaml")]
    roles = [Role(**r) for r in _read_yaml(root / "roles.yaml")]
    skills = list(_read_yaml(root / "skills.yaml"))

    posts: list[Post] = []
    writing_dir = root / "writing"
    md_files = sorted(writing_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"no posts in {writing_dir}")
    for md_path in md_files:
        fm = frontmatter.load(md_path)
        d = fm["date"]
        if isinstance(d, str):
            d = dt.date.fromisoformat(d)
        posts.append(
            Post(
                slug=fm.get("slug", md_path.stem),
                title=fm["title"],
                excerpt=fm["excerpt"],
                read=fm["read"],
                date=d,
                body_html=_md.render(fm.content),
            )
        )
    posts.sort(key=lambda p: p.date, reverse=True)

    return Content(
        site=site,
        projects=projects,
        packages=packages,
        roles=roles,
        skills=skills,
        posts=posts,
    )


_content: Content | None = None


def get_content() -> Content:
    global _content
    if _content is None:
        _content = load_content()
    return _content


def get_project(slug: str) -> Project | None:
    return next((p for p in get_content().projects if p.slug == slug), None)


def get_post(slug: str) -> Post | None:
    return next((p for p in get_content().posts if p.slug == slug), None)


def featured_projects() -> list[Project]:
    p = get_content().projects
    return [p[0], p[2], p[1], p[4]]


def project_types() -> list[str]:
    seen: list[str] = []
    for pr in get_content().projects:
        if pr.type not in seen:
            seen.append(pr.type)
    return ["All"] + seen
```

- [ ] **Step 10: Run it, verify it passes**

Run: `pytest tests/test_content.py -v`
Expected: PASS. Fix any YAML that fails validation (usually a stray unquoted `:` in a string — wrap in quotes or use `>-`).

- [ ] **Step 11: Commit**

```bash
git add app/content.py content tests/test_content.py
git commit -m "feat: content models and YAML/Markdown loaders"
```

---

## Task 3: Base template, static assets, header and footer

**Files:**
- Create: `app/templates/base.html`, `app/templates/_header.html`, `app/templates/_footer.html`, `app/templates/_plates.svg`, `app/static/css/site.css`, `app/static/js/site.js` (stub), `app/static/favicon.svg`
- Copy: `_ds/broadsheet-20458c33-7e5f-417c-af2f-3e6f2feef7e1/styles.css` → `app/static/css/styles.css`; `assets/*.svg` → `app/static/assets/`
- Modify: `app/main.py` (mount static, add Jinja env + `render()` helper, `TrustedHostMiddleware`)
- Create: `tests/test_pages.py` additions

**Interfaces:**
- Consumes: `app.content.get_content`.
- Produces:
  - `app.main.templates` — `jinja2.Environment` (via `fastapi.templating.Jinja2Templates`) with `templates` dir, `autoescape` on.
  - `app.main.render(request, name, **ctx) -> HTMLResponse` — injects `site`, `nav_active`, `settings` into every context.
  - Static mounted at `/static` (dir `app/static`).
  - `GET /` returns `200` with header + footer markup present (temporary body until Task 4 — render `base.html` with an empty `main` block, or point `/` at a placeholder; Task 4 replaces it).
  - Jinja globals: `content` (the `Content` object), `now_dateline` (callable → `"28 August 2026"` style string using `datetime.date.today()`).

- [ ] **Step 1: Copy static files**

```bash
mkdir -p app/static/css app/static/assets
cp "_ds/broadsheet-20458c33-7e5f-417c-af2f-3e6f2feef7e1/styles.css" app/static/css/styles.css
cp assets/*.svg app/static/assets/
```

- [ ] **Step 2: Create `app/static/css/site.css`**

Copy the CSS rules from inside the `<style>...</style>` block in `Puneet Behl Site.dc.html` (lines 13–66) verbatim. Then append this no-JS fallback so content is visible without `site.js`:

```css
/* no-JS fallback: reveal animations only apply once site.js adds .in */
.reveal { opacity: 1; }
.js .reveal:not(.in) { opacity: 0; }
```

And in `site.js` (Task 14) the first line will be `document.documentElement.classList.add('js')`. For this task, `site.js` is a one-line stub:

```js
document.documentElement.classList.add('js');
```

- [ ] **Step 3: Create `app/templates/_plates.svg`**

Port the SVG filter markup that `_ds/broadsheet-*/_ds_bundle.js` (`print-plates.js`) injects. Read that file; it builds an inline `<svg>` containing `<filter>` elements `#sep-c #sep-m #sep-y #sep-k #sep-all`. Reproduce that `<svg style="position:absolute;width:0;height:0" aria-hidden="true">...</svg>` as a static partial. If the bundle's exact output is hard to extract, create the file with just `<svg style="position:absolute;width:0;height:0" aria-hidden="true"></svg>` and leave a `<!-- TODO: port print-plate filters -->` — the CMYK numerals degrade to plain text, which is acceptable per spec.

- [ ] **Step 4: Create `app/templates/base.html`**

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}Puneet Behl — Technical Architect{% endblock %}</title>
<meta name="description" content="{% block description %}Freelance technical architect. Distributed systems, AWS and Kubernetes, agentic AI.{% endblock %}">
<link rel="canonical" href="{{ request.url.scheme }}://{{ request.url.netloc }}{{ request.url.path }}">
<meta property="og:title" content="{{ self.title() }}">
<meta property="og:description" content="{{ self.description() }}">
<meta property="og:type" content="{% block og_type %}website{% endblock %}">
<link rel="icon" href="/static/favicon.svg">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,400;0,600;1,400&display=swap">
<link rel="stylesheet" href="/static/css/styles.css">
<link rel="stylesheet" href="/static/css/site.css">
</head>
<body>
{% include "_plates.svg" %}
<div style="max-width:1120px;margin:0 auto;padding:0 clamp(16px,3vw,24px) 0">
<div id="progress"></div>
{% include "_header.html" %}
{% block main %}{% endblock %}
{% include "_footer.html" %}
</div>
<script src="/static/js/site.js" defer></script>
</body>
</html>
```

- [ ] **Step 5: Create `app/templates/_header.html`**

Port lines 73–95 of the design (the `<header>`). Apply the conversion recipe. Nav links become real paths. Active-link colour: replace `style="...color:{{ workColor }}"` with `style="...color:{% if nav_active == 'work' %}var(--color-accent){% else %}var(--color-text){% endif %}"` and the same for each nav item (`agentic`, `services`, `about`, `interviews`, `writing`, `contact`). Use `site.tagline_role`, `now_dateline()`, `site.availability_short`.

- [ ] **Step 6: Create `app/templates/_footer.html`**

Port lines 599–637. Apply recipe. Use `content.projects`? No — footer nav is static links. Use `site.footer_blurb`, `site.availability_long`, `site.linkedin`, `site.github`, `site.email`, `site.phone`, `site.credentials`. The newsletter `<form>`: convert to `<form method="post" action="/subscribe">`, add `{% if request.query_params.get('subscribed') %}` around the "Subscribed —" panel vs the form (mirroring the design's `subbed`/`notSubbed` split). Add hidden fields: `<input type="hidden" name="from" value="{{ request.url.path }}">`, the honeypot `<input type="text" name="website" tabindex="-1" autocomplete="off" class="hp">`, and `<input type="hidden" name="ts" value="{{ form_ts }}">`. `form_ts` comes from a Jinja global added in Step 8. Add `.hp { position:absolute; left:-9999px; width:1px; height:1px; overflow:hidden; }` to `site.css`.

- [ ] **Step 7: Write the failing test — add to `tests/test_pages.py`**

```python
def test_home_has_chrome(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.text
    assert "PUNEET BEHL" in body
    assert 'href="/work"' in body
    assert 'href="/contact"' in body
    assert "© 2026 Puneet Behl" in body
    assert "{{" not in body  # no unrendered vars


def test_static_css_served(client):
    r = client.get("/static/css/styles.css")
    assert r.status_code == 200
    assert "--color-accent" in r.text
```

- [ ] **Step 8: Modify `app/main.py`**

```python
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

    def render(request: Request, name: str, *, nav_active: str = "", status_code: int = 200, **ctx) -> HTMLResponse:
        payload = {
            "request": request,
            "site": app.state.content.site,
            "nav_active": nav_active,
            "settings": settings,
            "form_ts": app.state.ts_signer.dumps(str(int(dt.datetime.now(dt.timezone.utc).timestamp()))),
            **ctx,
        }
        return templates.TemplateResponse(name, payload, status_code=status_code)

    app.state.render = render

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return render(request, "home.html", nav_active="")

    return app


app = create_app()
```

- [ ] **Step 9: Create a minimal `app/templates/home.html`** (replaced in Task 4)

```html
{% extends "base.html" %}
{% block main %}<main style="padding:64px 0"><h1>Home</h1></main>{% endblock %}
```

- [ ] **Step 10: Run tests, verify pass**

Run: `pytest tests/test_pages.py -v`
Expected: PASS (`test_healthz`, `test_home_has_chrome`, `test_static_css_served`).

- [ ] **Step 11: Commit**

```bash
git add app tests/test_pages.py
git commit -m "feat: base template, static assets, header and footer"
```

---

## Task 4: Home view

**Files:**
- Modify: `app/templates/home.html` (full port)
- Test: `tests/test_pages.py` additions

**Interfaces:**
- Consumes: `render`, `featured_projects()`, `site.home_stats`, `site.testimonial`.
- Produces: `GET /` full home page.

- [ ] **Step 1: Write the failing test**

```python
def test_home_content(client):
    body = client.get("/").text
    assert "I design distributed systems that stay up" in body
    assert "50M+" in body
    assert "Selected work" in body
    # featured projects present with real links
    assert 'href="/work/loaderhouse"' in body
    assert 'href="/work/kubestat"' in body
    assert "Ravi Menon" in body
    assert 'href="/contact"' in body
```

- [ ] **Step 2: Run it, verify it fails**

Run: `pytest tests/test_pages.py::test_home_content -v`
Expected: FAIL (placeholder home has none of this text).

- [ ] **Step 3: Port `app/templates/home.html`**

Port lines 96–178 of `Puneet Behl Site.dc.html` (the `<sc-if value="{{ isHome }}">` block, i.e. everything from `<main style="padding:64px 0 0">` to its closing `</main>`). Wrap in:

```html
{% extends "base.html" %}
{% block main %}
  ... ported <main> ...
{% endblock %}
```

Conversions specific to this file:
- `<sc-for list="{{ featured }}" as="p" ...>` → `{% for p in featured %}` … `{% endfor %}`.
- Inside the loop: `{{ p.href }}` → `/work/{{ p.slug }}`; `art-{{ p.slug }}` stays; `{{ p.artAlt }}` → `{{ p.name }} — {{ p.summary.split('—')[0].strip() }}`; `{{ p.type }}`, `{{ p.name }}`, `{{ p.domain }}`, `{{ p.summary }}`, `{{ p.headline }}` stay.
- The 4 stat numerals block (`.cmyk-num` spans): replace the 4 hard-coded groups with `{% for s in stats %}<div>...<span class="paper">{{ s.value }}</span>...<p ...>{{ s.label }}</p></div>{% endfor %}` keeping the 4 `plate plate-c/m/y` spans each echoing `{{ s.value }}`.
- Testimonial `blockquote`: replace the quoted text with `{{ site.testimonial.quote }}` and the `footer` with `{{ site.testimonial.author }}`.
- Delete all `onClick`.

- [ ] **Step 4: Update the `/` route** in `app/main.py` to pass context:

```python
    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        from app.content import featured_projects
        return render(
            request, "home.html", nav_active="",
            featured=featured_projects(),
            stats=app.state.content.site.home_stats,
        )
```

- [ ] **Step 5: Run tests, verify pass**

Run: `pytest tests/test_pages.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/templates/home.html app/main.py tests/test_pages.py
git commit -m "feat: home view"
```

---

## Task 5: Work index and project detail views

**Files:**
- Create: `app/templates/work.html`, `app/templates/project.html`
- Modify: `app/main.py` (routes `/work`, `/work/{slug}`)
- Test: `tests/test_pages.py` additions

**Interfaces:**
- Consumes: `get_content().projects`, `get_project(slug)`, `project_types()`.
- Produces:
  - `GET /work` → `200`, all 8 projects.
  - `GET /work/{slug}` → `200` for known slug; `404` (rendered HTML page, not JSON) for unknown.

- [ ] **Step 1: Write the failing tests**

```python
def test_work_index(client):
    body = client.get("/work").text
    assert client.get("/work").status_code == 200
    for slug in ["loaderhouse", "chartwell", "relayd", "northgate-rails",
                 "kubestat", "tenderfoot", "specflow", "anchor-cli"]:
        assert f'href="/work/{slug}"' in body
    assert "Agentic AI" in body  # a filter label


def test_project_detail(client):
    r = client.get("/work/northgate-rails")
    assert r.status_code == 200
    assert "Northgate Rails" in r.text
    assert "50M+" in r.text
    assert "append-only" in r.text  # from problem/approach text


def test_project_detail_unknown_is_404(client):
    r = client.get("/work/does-not-exist")
    assert r.status_code == 404
    assert "text/html" in r.headers["content-type"]
```

- [ ] **Step 2: Run, verify fail** — `pytest tests/test_pages.py -k "work or project" -v` → FAIL (404 JSON / missing templates).

- [ ] **Step 3: Port `app/templates/work.html`**

Port lines 181–210 (`<sc-if value="{{ isWork }}">`). Conversions:
- `<sc-for list="{{ filters }}" as="f">` → `{% for f in filters %}`. Each filter is now a plain string; render `<button type="button" class="filter-btn" data-filter="{{ f }}">{{ f }}</button>` (styling handled by `site.css` + `site.js` in Task 14; for now the buttons are inert and all projects show).
- `<sc-for list="{{ shown }}" as="p">` → `{% for p in projects %}` (server always renders all; JS filters client-side later). Add `data-type="{{ p.type }}"` to each card's outer element.
- `{{ p.href }}` → `/work/{{ p.slug }}`; keep `{{ p.name }}`, `{{ p.domain }}`, `{{ p.summary }}`, `{{ p.type }}`, `art-{{ p.slug }}`.
- Inner `<sc-for list="{{ p.stack }}" as="s">` → `{% for s in p.stack %}`.
- Delete `onClick`.

Add to `site.css`: `.filter-btn{cursor:pointer} .js .work-card.hide{display:none}`.

- [ ] **Step 4: Port `app/templates/project.html`**

Port lines 213–270 (`<sc-if value="{{ isProject }}">`). Conversions:
- `{{ project.name }}`, `{{ project.domain }}`, `{{ project.year }}`, `{{ project.role }}`, `{{ project.problem }}`, `{{ project.architecture }}` stay (context key `project`).
- `<sc-for list="{{ project.metrics }}" as="m">` → `{% for m in project.metrics %}` with `{{ m.value }}` / `{{ m.label }}`.
- `<sc-for list="{{ project.approach }}" as="a">` → `{% for a in project.approach %}<li ...>{{ a }}</li>{% endfor %}`.
- `<sc-for list="{{ project.stack }}" as="s">` (appears twice) → `{% for s in project.stack %}`.
- "Next" link: `{{ nextProject.href }}` → `/work/{{ next_project.slug }}`, `{{ nextProject.name }}` → `{{ next_project.name }}` (context key `next_project`).
- `art-{{ project.slug }}` stays.
- Delete `onClick`.

- [ ] **Step 5: Add routes to `app/main.py`**

```python
    from fastapi import HTTPException
    from app.content import get_project, project_types

    @app.get("/work", response_class=HTMLResponse)
    async def work(request: Request):
        return render(request, "work.html", nav_active="work",
                      projects=app.state.content.projects, filters=project_types())

    @app.get("/work/{slug}", response_class=HTMLResponse)
    async def project_detail(request: Request, slug: str):
        projects = app.state.content.projects
        idx = next((i for i, p in enumerate(projects) if p.slug == slug), None)
        if idx is None:
            return render(request, "404.html", nav_active="", status_code=404)
        return render(request, "project.html", nav_active="work",
                      project=projects[idx],
                      next_project=projects[(idx + 1) % len(projects)])
```

- [ ] **Step 6: Create `app/templates/404.html`**

```html
{% extends "base.html" %}
{% block title %}Not found — Puneet Behl{% endblock %}
{% block main %}
<main style="padding:80px 0 120px">
  <h1 style="font-size:46px;margin:0 0 16px">Not found</h1>
  <p style="font-size:18px;color:var(--color-neutral-700)">That page doesn’t exist. <a href="/">Back to home</a>.</p>
</main>
{% endblock %}
```

Also add a catch-all 404 handler so unknown top-level paths render this page:

```python
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def not_found(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return render(request, "404.html", status_code=404)
        raise exc
```

- [ ] **Step 7: Run tests, verify pass** — `pytest tests/test_pages.py -v` → PASS.

- [ ] **Step 8: Commit**

```bash
git add app tests/test_pages.py
git commit -m "feat: work index and project detail views"
```

---

## Task 6: Agentic, Services, About views

**Files:**
- Create: `app/templates/agentic.html`, `app/templates/services.html`, `app/templates/about.html`
- Modify: `app/main.py` (routes `/agentic`, `/services`, `/about`)
- Test: `tests/test_pages.py` additions

**Interfaces:**
- Consumes: `get_content().packages`, `.roles`, `.skills`.
- Produces: `GET /agentic`, `GET /services`, `GET /about` → `200`.

- [ ] **Step 1: Write the failing tests**

```python
def test_agentic(client):
    r = client.get("/agentic")
    assert r.status_code == 200
    assert "Agents that survive production" in r.text


def test_services(client):
    body = client.get("/services").text
    assert "Architecture Sprint" in body
    assert "Build and Ship" in body
    assert "Fractional Architect" in body
    assert "$6,500" in body


def test_about(client):
    body = client.get("/about").text
    assert "AthenaHealth" in body
    assert "Spring Boot" in body  # a skill tag
    assert body.count("<li") >= 6 or "Technical Architect / Engineering Manager" in body
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Port `app/templates/agentic.html`** — lines 273–337. Mostly static; no `sc-for`/`sc-if` inside except none. Delete `onClick`. Wrap in `{% extends %}`/`{% block main %}`.

- [ ] **Step 4: Port `app/templates/services.html`** — lines 340–378. `<sc-for list="{{ packages }}" as="s">` → `{% for s in packages %}`; inner `<sc-for list="{{ s.items }}" as="i">` → `{% for i in s.items %}`. Fields `{{ s.kicker }} {{ s.name }} {{ s.price }} {{ s.terms }} {{ s.blurb }} {{ s.cta }}`.

- [ ] **Step 5: Port `app/templates/about.html`** — lines 381–425. `<sc-for list="{{ roles }}" as="r">` → `{% for r in roles %}` with `{{ r.years }} {{ r.title }} {{ r.company }} {{ r.note }}`; `<sc-for list="{{ skills }}" as="s">` → `{% for s in skills %}<span class="tag tag-neutral">{{ s }}</span>{% endfor %}`.

- [ ] **Step 6: Add routes**

```python
    @app.get("/agentic", response_class=HTMLResponse)
    async def agentic(request: Request):
        return render(request, "agentic.html", nav_active="agentic")

    @app.get("/services", response_class=HTMLResponse)
    async def services(request: Request):
        return render(request, "services.html", nav_active="services",
                      packages=app.state.content.packages)

    @app.get("/about", response_class=HTMLResponse)
    async def about(request: Request):
        return render(request, "about.html", nav_active="about",
                      roles=app.state.content.roles, skills=app.state.content.skills)
```

- [ ] **Step 7: Run tests, verify pass.**

- [ ] **Step 8: Commit**

```bash
git add app tests/test_pages.py
git commit -m "feat: agentic, services, about views"
```

---

## Task 7: Writing index and post detail views

**Files:**
- Create: `app/templates/writing.html`, `app/templates/post.html`
- Modify: `app/main.py` (routes `/writing`, `/writing/{slug}`)
- Test: `tests/test_pages.py` additions

**Interfaces:**
- Consumes: `get_content().posts`, `get_post(slug)`.
- Produces: `GET /writing` → `200` list newest-first; `GET /writing/{slug}` → `200` known / `404` unknown.

- [ ] **Step 1: Write the failing tests**

```python
def test_writing_index(client):
    body = client.get("/writing").text
    assert client.get("/writing").status_code == 200
    assert 'href="/writing/agents-are-distributed-systems"' in body
    # newest first
    assert body.index("agents-are-distributed-systems") < body.index("interoperability-is-a-people-problem")


def test_post_detail(client):
    r = client.get("/writing/the-eval-set-is-the-product")
    assert r.status_code == 200
    assert "The eval set is the product" in r.text
    assert "<p>" in r.text
    assert "2 May 2026" in r.text


def test_post_unknown_404(client):
    assert client.get("/writing/nope").status_code == 404
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Port `app/templates/writing.html`** — lines 428–444. `<sc-for list="{{ posts }}" as="p">` → `{% for p in posts %}`. Link `{{ p.href }}` → `/writing/{{ p.slug }}`. Fields `{{ p.date }}` → `{{ p.date_display }}`, `{{ p.read }}`, `{{ p.title }}`, `{{ p.excerpt }}`.

- [ ] **Step 4: Port `app/templates/post.html`** — lines 447–460. Replace `<sc-for list="{{ post.body }}" as="para"><p ...>{{ para }}</p></sc-for>` with `<div class="post-body">{{ post.body_html | safe }}</div>`. `{{ post.title }}`, `{{ post.date }}` → `{{ post.date_display }}`, `{{ post.read }}`. Set `{% block title %}{{ post.title }} — Puneet Behl{% endblock %}`, `{% block description %}{{ post.excerpt }}{% endblock %}`, `{% block og_type %}article{% endblock %}`. Add `.post-body p{margin:0 0 22px}` to `site.css` if the ported markup relied on inline styles.

- [ ] **Step 5: Add routes**

```python
    from app.content import get_post

    @app.get("/writing", response_class=HTMLResponse)
    async def writing(request: Request):
        return render(request, "writing.html", nav_active="writing",
                      posts=app.state.content.posts)

    @app.get("/writing/{slug}", response_class=HTMLResponse)
    async def post_detail(request: Request, slug: str):
        post = get_post(slug)
        if post is None:
            return render(request, "404.html", status_code=404)
        return render(request, "post.html", nav_active="writing", post=post)
```

- [ ] **Step 6: Run tests, verify pass.**

- [ ] **Step 7: Commit**

```bash
git add app tests/test_pages.py
git commit -m "feat: writing index and post detail views"
```

---

## Task 8: Form models, signed timestamp, honeypot

**Files:**
- Create: `app/forms.py`, `tests/test_forms.py`
- Modify: `app/main.py` (expose `ts_signer` helpers if needed — already on `app.state`)

**Interfaces:**
- Consumes: `app.config.get_settings`.
- Produces:
  - `CONTACT_KINDS: tuple[str, ...]` = the 5 design options (verbatim, line 495–499):
    `("Agentic architecture sprint", "Build and ship an agentic product", "Fractional architect / advisory", "Cloud or Kubernetes migration", "Something else")`
  - `INTERVIEW_FORMATS: tuple[str, ...]` = the 4 design options (line 582–585):
    `("System design · 60 min", "Backend and Java · 60 min", "Engineering manager · 45 min", "Resume and levelling · 30 min")`
  - `class ContactForm(BaseModel)`: `name: str` (1–100, stripped), `email: EmailStr` (≤200), `company: str = ""` (≤100), `kind: str` (must be in `CONTACT_KINDS`), `msg: str` (1–5000, stripped).
  - `class InterviewForm(BaseModel)`: `name` (1–100), `email: EmailStr`, `format: str` (in `INTERVIEW_FORMATS`), `target: str = ""` (≤200), `slots: str` (1–2000).
  - `class SubscribeForm(BaseModel)`: `email: EmailStr`, `from_path: str` — aliased from field name `from`; validator forces it to a safe local path (`/`-prefixed, no `//`, no scheme, no control chars) else `"/"`.
  - `def is_honeypot_tripped(website: str | None) -> bool` — `True` if `website` is truthy after strip.
  - `def sign_ts(signer, now: int | None = None) -> str`
  - `def verify_ts(signer, token: str, min_seconds: int, max_age: int = 7200) -> bool` — `True` when the token is valid, un-tampered, and its age ≥ `min_seconds` and ≤ `max_age`. Any exception → `False`.
  - `def form_error_response(...)` is NOT here — templates handle re-render; this module is pure.
- Note: `EmailStr` requires `pydantic[email]` — add `"pydantic[email]>=2.7"` to `pyproject.toml` dependencies (replace the bare `pydantic` line) and reinstall.

- [ ] **Step 1: Add `email-validator` support** — edit `pyproject.toml`: change `"pydantic>=2.7"` to `"pydantic[email]>=2.7"`. Run `pip install -e ".[dev]"`.

- [ ] **Step 2: Write the failing test — `tests/test_forms.py`**

```python
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


def test_subscribe_form_sanitizes_from():
    assert SubscribeForm(email="a@b.com", **{"from": "https://evil.com"}).from_path == "/"
    assert SubscribeForm(email="a@b.com", **{"from": "//evil.com"}).from_path == "/"
    assert SubscribeForm(email="a@b.com", **{"from": "/writing"}).from_path == "/writing"


def test_honeypot():
    assert is_honeypot_tripped("bot") is True
    assert is_honeypot_tripped("") is False
    assert is_honeypot_tripped(None) is False


def test_ts_roundtrip_too_fast():
    tok = sign_ts(SIGNER, now=int(time.time()))
    assert verify_ts(SIGNER, tok, min_seconds=3) is False  # just signed → too fast


def test_ts_roundtrip_ok():
    tok = sign_ts(SIGNER, now=int(time.time()) - 10)
    assert verify_ts(SIGNER, tok, min_seconds=3) is True


def test_ts_tampered():
    assert verify_ts(SIGNER, "garbage", min_seconds=3) is False


def test_ts_too_old():
    tok = sign_ts(SIGNER, now=int(time.time()) - 99999)
    assert verify_ts(SIGNER, tok, min_seconds=3, max_age=7200) is False
```

- [ ] **Step 3: Run, verify fail** — `pytest tests/test_forms.py -v` → `ModuleNotFoundError`.

- [ ] **Step 4: Create `app/forms.py`**

```python
from __future__ import annotations

import time

from itsdangerous import BadData, URLSafeTimedSerializer
from pydantic import BaseModel, EmailStr, Field, field_validator

CONTACT_KINDS: tuple[str, ...] = (
    "Agentic architecture sprint",
    "Build and ship an agentic product",
    "Fractional architect / advisory",
    "Cloud or Kubernetes migration",
    "Something else",
)

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
            raise ValueError("unknown kind")
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
            raise ValueError("unknown format")
        return v


class SubscribeForm(BaseModel):
    email: EmailStr = Field(max_length=200)
    from_path: str = Field(default="/", alias="from")

    @field_validator("from_path", mode="before")
    @classmethod
    def _safe_path(cls, v: str) -> str:
        if not isinstance(v, str):
            return "/"
        v = v.strip()
        if not v.startswith("/") or v.startswith("//") or "\\" in v or any(c < " " for c in v):
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
    try:
        raw = signer.loads(token, max_age=max_age)
        issued = int(raw)
    except (BadData, ValueError, TypeError):
        return False
    age = int(time.time()) - issued
    return min_seconds <= age <= max_age
```

- [ ] **Step 5: Run, verify pass** — `pytest tests/test_forms.py -v` → PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml app/forms.py tests/test_forms.py
git commit -m "feat: form models, signed timestamp, honeypot check"
```

---

## Task 9: In-memory rate limiter

**Files:**
- Create: `app/ratelimit.py`, `tests/test_ratelimit.py`

**Interfaces:**
- Produces:
  - `class RateLimiter`: `__init__(self, max_hits: int, window_seconds: int, *, clock=time.monotonic)`; `check(key: str) -> bool` — returns `True` if allowed (and records the hit), `False` if over the limit. Fixed-window. Thread-unsafe is fine (single worker); use a plain dict `{key: [timestamps]}` pruned on each call.
  - `def client_key(request, endpoint: str) -> str` → `f"{request.client.host}:{endpoint}"` (falls back to `"unknown"` host).

- [ ] **Step 1: Write the failing test — `tests/test_ratelimit.py`**

```python
from app.ratelimit import RateLimiter


def test_allows_up_to_max():
    clock = [1000.0]
    rl = RateLimiter(max_hits=3, window_seconds=60, clock=lambda: clock[0])
    assert [rl.check("a") for _ in range(3)] == [True, True, True]
    assert rl.check("a") is False


def test_separate_keys_independent():
    clock = [1000.0]
    rl = RateLimiter(max_hits=1, window_seconds=60, clock=lambda: clock[0])
    assert rl.check("a") is True
    assert rl.check("b") is True
    assert rl.check("a") is False


def test_window_resets():
    clock = [1000.0]
    rl = RateLimiter(max_hits=1, window_seconds=60, clock=lambda: clock[0])
    assert rl.check("a") is True
    assert rl.check("a") is False
    clock[0] += 61
    assert rl.check("a") is True
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Create `app/ratelimit.py`**

```python
from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, max_hits: int, window_seconds: int, *, clock=time.monotonic):
        self.max_hits = max_hits
        self.window = window_seconds
        self.clock = clock
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        now = self.clock()
        cutoff = now - self.window
        hits = [t for t in self._hits[key] if t > cutoff]
        if len(hits) >= self.max_hits:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True


def client_key(request, endpoint: str) -> str:
    host = getattr(getattr(request, "client", None), "host", None) or "unknown"
    return f"{host}:{endpoint}"
```

- [ ] **Step 4: Run, verify pass.**

- [ ] **Step 5: Commit**

```bash
git add app/ratelimit.py tests/test_ratelimit.py
git commit -m "feat: in-memory fixed-window rate limiter"
```

---

## Task 10: Resend emailer

**Files:**
- Create: `app/emailer.py`, `tests/test_emailer.py`

**Interfaces:**
- Consumes: `app.config.Settings`.
- Produces:
  - `async def send_form_email(settings, *, subject: str, text: str, reply_to: str | None, client: httpx.AsyncClient | None = None) -> bool`
    - When `settings.dry_run` is `True`: log the payload at `INFO`, return `True`, make no HTTP call.
    - Else `POST https://api.resend.com/emails` with JSON `{"from": settings.mail_from, "to": [settings.mail_to], "subject": subject, "text": text, "reply_to": reply_to}` (omit `reply_to` key if `None`), header `Authorization: Bearer {settings.resend_api_key}`, timeout 10s.
    - On 2xx → return `True`. On non-2xx or `httpx` exception → log `ERROR` with subject+text, return `False`.
  - `def build_contact_text(form, *, ip: str, when: str) -> str` — plain text, one `Label: value` per line for name/email/company/kind/msg, blank line, then `Submitted {when} from {ip}`.
  - `def build_interview_text(form, *, ip, when) -> str` — same shape for name/email/format/target/slots.
  - `def build_subscribe_text(email, *, ip, when) -> str`.
  - `def utc_now_str() -> str` → `"2026-08-28 14:03 UTC"`.

- [ ] **Step 1: Write the failing test — `tests/test_emailer.py`**

```python
import httpx
import pytest
import respx

from app.config import Settings
from app.emailer import build_contact_text, send_form_email
from app.forms import CONTACT_KINDS, ContactForm


def _settings(**kw):
    base = dict(secret_key="x", resend_api_key="re_test", mail_to="owner@example.com",
                mail_from="forms@example.com", mail_dry_run=False)
    base.update(kw)
    return Settings(**base)


@pytest.mark.anyio
async def test_dry_run_skips_http():
    s = _settings(mail_dry_run=True)
    with respx.mock:
        route = respx.post("https://api.resend.com/emails")
        ok = await send_form_email(s, subject="s", text="t", reply_to=None)
    assert ok is True
    assert not route.called


@pytest.mark.anyio
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
    import json
    payload = json.loads(sent.content)
    assert payload["to"] == ["owner@example.com"]
    assert payload["from"] == "forms@example.com"
    assert payload["reply_to"] == "ada@example.com"
    assert payload["subject"] == "New enquiry"


@pytest.mark.anyio
async def test_non_2xx_returns_false():
    s = _settings()
    with respx.mock:
        respx.post("https://api.resend.com/emails").mock(
            return_value=httpx.Response(422, json={"error": "bad"})
        )
        ok = await send_form_email(s, subject="s", text="t", reply_to=None)
    assert ok is False


def test_build_contact_text_has_all_fields():
    f = ContactForm(name="Ada", email="ada@example.com", company="Acme",
                    kind=CONTACT_KINDS[0], msg="Need help")
    txt = build_contact_text(f, ip="1.2.3.4", when="2026-08-28 10:00 UTC")
    for piece in ["Ada", "ada@example.com", "Acme", CONTACT_KINDS[0], "Need help", "1.2.3.4"]:
        assert piece in txt
```

Add to `tests/conftest.py`:

```python
@pytest.fixture
def anyio_backend():
    return "asyncio"
```

And add `"pytest" ... "anyio>=4"` — actually add `"trio"`? No. Add `"anyio>=4"` to dev deps and mark async tests with `@pytest.mark.anyio`. Simpler: add `"pytest-asyncio>=0.23"` to dev deps and put `asyncio_mode = "auto"` under `[tool.pytest.ini_options]`. Use that; drop the `anyio_backend` fixture and the `@pytest.mark.anyio` marks (auto mode picks up `async def test_*`).

Revised: dev deps get `"pytest-asyncio>=0.23"`, ini gets `asyncio_mode = "auto"`, async tests are just `async def test_...` with no marker.

- [ ] **Step 2: Update `pyproject.toml`** dev extras and pytest ini per the note above. Reinstall.

- [ ] **Step 3: Run, verify fail.**

- [ ] **Step 4: Create `app/emailer.py`**

```python
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
```

- [ ] **Step 5: Run, verify pass.**

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml app/emailer.py tests/test_emailer.py tests/conftest.py
git commit -m "feat: Resend emailer with dry-run and text builders"
```

---

## Task 11: Contact page — GET view and POST handler

**Files:**
- Create: `app/templates/contact.html`, `app/templates/_form_errors.html`
- Modify: `app/main.py` (add shared form-POST helper, routes `GET /contact`, `POST /contact`)
- Test: `tests/test_forms.py` additions (endpoint tests) — or a new `tests/test_endpoints.py`

**Interfaces:**
- Consumes: `ContactForm`, `is_honeypot_tripped`, `verify_ts`, `RateLimiter`, `send_form_email`, `build_contact_text`, `utc_now_str`, `render`.
- Produces:
  - `GET /contact` → `200`. When `?sent=1`, render the success panel instead of the form.
  - `POST /contact` (form-encoded): valid → `303` to `/contact?sent=1`; invalid → `400` re-render with `errors` dict + submitted `values`; honeypot/too-fast → `303` to `/contact?sent=1` with no email; over rate limit → `429` plain text.
  - `app.main` gains `app.state.rl` — a single `RateLimiter(settings.rate_limit_max, settings.rate_limit_window)`.
  - Helper `_bot_or_limited(request, endpoint) -> str | None` returning `"limited"`, `"bot"`, or `None` given the request form fields — reused by Tasks 12 and 13.

- [ ] **Step 1: Write the failing tests — `tests/test_endpoints.py`**

```python
import re

import pytest
import respx
import httpx

from app.forms import CONTACT_KINDS


def _ts(app):
    # a timestamp old enough to pass MIN_FILL_SECONDS (env default 3)
    import time
    from app.forms import sign_ts
    return sign_ts(app.state.ts_signer, now=int(time.time()) - 10)


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


def test_contact_get(client):
    r = client.get("/contact")
    assert r.status_code == 200
    assert "Project enquiry" in r.text
    assert 'name="website"' in r.text  # honeypot present
    assert 'name="ts"' in r.text


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
    # dry-run is ON in tests → Resend NOT actually called
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


def test_contact_post_honeypot_silent_success(client, app):
    payload = _good_payload(app)
    payload["website"] = "I am a bot"
    r = client.post("/contact", data=payload, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/contact?sent=1"


def test_contact_post_too_fast_silent_success(client, app):
    import time
    from app.forms import sign_ts
    payload = _good_payload(app)
    payload["ts"] = sign_ts(app.state.ts_signer, now=int(time.time()))  # 0s old
    r = client.post("/contact", data=payload, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/contact?sent=1"


def test_contact_post_rate_limited(client, app):
    # env default RATE_LIMIT_MAX=5
    last = None
    for _ in range(7):
        last = client.post("/contact", data=_good_payload(app), follow_redirects=False)
    assert last.status_code == 429
```

Note: because tests share the process-wide `RateLimiter`, `test_contact_post_rate_limited` must run after the other contact POST tests or reset state. Add an autouse fixture in `conftest.py` that recreates the limiter per test:

```python
@pytest.fixture(autouse=True)
def _fresh_rate_limiter(app):
    from app.ratelimit import RateLimiter
    s = app.state.settings
    app.state.rl = RateLimiter(s.rate_limit_max, s.rate_limit_window)
    yield
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Port `app/templates/contact.html`**

Port lines 463–507. Structure:
- Wrap in `{% extends %}` / `{% block main %}`, `{% block title %}Contact — Puneet Behl{% endblock %}`.
- Left column (contact details): replace `mailto:` / `tel:` / LinkedIn / "Based in" with `site.email`, `site.phone`, `site.linkedin`, `site.location`.
- Right column: `<sc-if value="{{ sent }}">...success...</sc-if>` → `{% if sent %}...{% else %}...{% endif %}`. `sent` is passed by the route (`request.query_params.get('sent')`). Remove the "Send another" button's `onClick`; make it `<a href="/contact" class="btn btn-secondary">Send another</a>`.
- The `<form>`: `<form method="post" action="/contact" ...>` (drop `onSubmit`). Each `<input>`/`<textarea>`/`<select>`: remove `value="{{ form.x }}"` / `onChange`, replace with `value="{{ values.name }}"` etc. (`values` is a dict, empty on GET). `<textarea>...{{ values.msg }}...</textarea>`. `<select>` options: mark `{% if values.kind == 'Something else' %}selected{% endif %}` per option, or loop `{% for k in contact_kinds %}<option{% if values.kind == k %} selected{% endif %}>{{ k }}</option>{% endfor %}`.
- Add hidden fields before the submit button: honeypot `<input type="text" name="website" class="hp" tabindex="-1" autocomplete="off">` and `<input type="hidden" name="ts" value="{{ form_ts }}">`.
- Include `{% include "_form_errors.html" %}` just inside the form, above the first field.

- [ ] **Step 4: Create `app/templates/_form_errors.html`**

```html
{% if errors %}
<div class="form-errors" role="alert" style="border-left:4px solid var(--color-accent-2);padding:10px 14px;margin-bottom:8px">
  <p style="margin:0;font-size:14px">Please check the highlighted fields.</p>
  <ul style="margin:6px 0 0;padding-left:18px;font-size:13px">
    {% for field, msg in errors.items() %}<li>{{ field }}: {{ msg }}</li>{% endfor %}
  </ul>
</div>
{% endif %}
```

- [ ] **Step 5: Add form plumbing to `app/main.py`**

```python
from fastapi import Form
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import ValidationError

from app.emailer import build_contact_text, send_form_email, utc_now_str
from app.forms import ContactForm, is_honeypot_tripped, verify_ts
from app.ratelimit import RateLimiter, client_key

# in create_app(), after app.state.ts_signer:
    app.state.rl = RateLimiter(settings.rate_limit_max, settings.rate_limit_window)

    def bot_or_limited(request: Request, endpoint: str, website: str, ts: str) -> str | None:
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

    @app.get("/contact", response_class=HTMLResponse)
    async def contact_get(request: Request):
        return render(request, "contact.html", nav_active="contact",
                      sent=bool(request.query_params.get("sent")),
                      values={}, errors={})

    @app.post("/contact")
    async def contact_post(
        request: Request,
        name: str = Form(""), email: str = Form(""), company: str = Form(""),
        kind: str = Form(""), msg: str = Form(""),
        website: str = Form(""), ts: str = Form(""),
    ):
        verdict = bot_or_limited(request, "contact", website, ts)
        if verdict == "limited":
            return PlainTextResponse("Too many submissions. Try again shortly.", status_code=429)
        if verdict == "bot":
            return RedirectResponse("/contact?sent=1", status_code=303)
        try:
            form = ContactForm(name=name, email=email, company=company, kind=kind, msg=msg)
        except ValidationError as exc:
            return render(request, "contact.html", nav_active="contact", status_code=400,
                          sent=False, errors=errors_from(exc),
                          values={"name": name, "email": email, "company": company,
                                  "kind": kind, "msg": msg})
        ip = client_key(request, "").rstrip(":")
        await send_form_email(
            settings,
            subject=f"New enquiry — {form.name} ({form.kind})",
            text=build_contact_text(form, ip=ip, when=utc_now_str()),
            reply_to=form.email,
        )
        return RedirectResponse("/contact?sent=1", status_code=303)
```

Pass `contact_kinds=CONTACT_KINDS` into both contact renders if the template loops options (import `CONTACT_KINDS`).

- [ ] **Step 6: Run tests, verify pass** — `pytest tests/test_endpoints.py -v` and the full suite.

- [ ] **Step 7: Commit**

```bash
git add app tests/test_endpoints.py tests/conftest.py
git commit -m "feat: contact page view and form handler"
```

---

## Task 12: Interviews page — GET view and POST handler

**Files:**
- Create: `app/templates/interviews.html`
- Modify: `app/main.py` (routes `GET /interviews`, `POST /interviews`)
- Test: `tests/test_endpoints.py` additions

**Interfaces:**
- Consumes: same helpers as Task 11 plus `InterviewForm`, `build_interview_text`, `INTERVIEW_FORMATS`.
- Produces: `GET /interviews` (`?sent=1` → success panel); `POST /interviews` → `303 /interviews?sent=1` on success / bot, `400` on invalid, `429` limited.

- [ ] **Step 1: Write the failing tests**

```python
from app.forms import INTERVIEW_FORMATS


def _iv_payload(app):
    import time
    from app.forms import sign_ts
    return {
        "name": "Grace Hopper", "email": "grace@example.com",
        "format": INTERVIEW_FORMATS[0], "target": "Staff backend, fintech",
        "slots": "Tue/Thu after 8pm IST, Sat morning",
        "website": "", "ts": sign_ts(app.state.ts_signer, now=int(time.time()) - 10),
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
    p = _iv_payload(app); p["format"] = "Tarot reading · 90 min"
    assert client.post("/interviews", data=p, follow_redirects=False).status_code == 400


def test_interviews_post_missing_slots_400(client, app):
    p = _iv_payload(app); p["slots"] = ""
    assert client.post("/interviews", data=p, follow_redirects=False).status_code == 400


def test_interviews_post_honeypot(client, app):
    p = _iv_payload(app); p["website"] = "bot"
    r = client.post("/interviews", data=p, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/interviews?sent=1"
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Port `app/templates/interviews.html`**

Port lines 510–596. This is the largest view: intro copy, "Four formats" grid, "How a session runs", "What you get", and the `#interview-booking` section with the form. Conversions:
- All static prose ports directly.
- The booking form (`<sc-if value="{{ ivSent }}">` / `ivNotSent`): `{% if sent %}` success panel `{% else %}` form `{% endif %}`. "Book another" button → `<a href="/interviews" class="btn btn-secondary">Book another</a>`.
- `<form method="post" action="/interviews" ...>` (drop `onSubmit`).
- Inputs: drop `value="{{ iv.x }}"` / `onChange`; use `value="{{ values.name }}"`, `{{ values.target }}`, `<textarea>{{ values.slots }}</textarea>`.
- `<select id="iv-format">`: `{% for f in interview_formats %}<option{% if values.format == f %} selected{% endif %}>{{ f }}</option>{% endfor %}`.
- Hidden fields: honeypot `website`, `ts` = `{{ form_ts }}`.
- `{% include "_form_errors.html" %}` inside the form.
- `{% block title %}Mock interviews — Puneet Behl{% endblock %}`.

- [ ] **Step 4: Add routes to `app/main.py`**

```python
from app.emailer import build_interview_text
from app.forms import INTERVIEW_FORMATS, InterviewForm

    @app.get("/interviews", response_class=HTMLResponse)
    async def interviews_get(request: Request):
        return render(request, "interviews.html", nav_active="interviews",
                      sent=bool(request.query_params.get("sent")),
                      values={}, errors={}, interview_formats=INTERVIEW_FORMATS)

    @app.post("/interviews")
    async def interviews_post(
        request: Request,
        name: str = Form(""), email: str = Form(""), format: str = Form(""),
        target: str = Form(""), slots: str = Form(""),
        website: str = Form(""), ts: str = Form(""),
    ):
        verdict = bot_or_limited(request, "interviews", website, ts)
        if verdict == "limited":
            return PlainTextResponse("Too many submissions. Try again shortly.", status_code=429)
        if verdict == "bot":
            return RedirectResponse("/interviews?sent=1", status_code=303)
        try:
            form = InterviewForm(name=name, email=email, format=format,
                                 target=target, slots=slots)
        except ValidationError as exc:
            return render(request, "interviews.html", nav_active="interviews",
                          status_code=400, sent=False, errors=errors_from(exc),
                          interview_formats=INTERVIEW_FORMATS,
                          values={"name": name, "email": email, "format": format,
                                  "target": target, "slots": slots})
        ip = client_key(request, "").rstrip(":")
        await send_form_email(
            settings,
            subject=f"Mock interview request — {form.name} ({form.format})",
            text=build_interview_text(form, ip=ip, when=utc_now_str()),
            reply_to=form.email,
        )
        return RedirectResponse("/interviews?sent=1", status_code=303)
```

- [ ] **Step 5: Run tests, verify pass.**

- [ ] **Step 6: Commit**

```bash
git add app tests/test_endpoints.py
git commit -m "feat: interviews page view and booking form handler"
```

---

## Task 13: Newsletter subscribe handler

**Files:**
- Modify: `app/main.py` (route `POST /subscribe`), `app/templates/_footer.html` (already has the form from Task 3 — verify hidden fields + success branch)
- Test: `tests/test_endpoints.py` additions

**Interfaces:**
- Consumes: `SubscribeForm`, `build_subscribe_text`, helpers.
- Produces: `POST /subscribe` → `303` to `{from_path}?subscribed=1` on success / bot; `303` to `{from_path}?subscribed=err` on invalid email (footer has no room for an error panel — a soft signal is enough); `429` when limited. `GET` of any page with `?subscribed=1` shows the "Subscribed —" panel in the footer (wired in Task 3 Step 6).

- [ ] **Step 1: Write the failing tests**

```python
def _sub_payload(app, **kw):
    import time
    from app.forms import sign_ts
    p = {"email": "reader@example.com", "from": "/writing", "website": "",
         "ts": sign_ts(app.state.ts_signer, now=int(time.time()) - 10)}
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
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Verify `_footer.html`** has: `<form method="post" action="/subscribe">`, hidden `from` = `{{ request.url.path }}`, honeypot `website`, hidden `ts` = `{{ form_ts }}`, and `{% if request.query_params.get('subscribed') == '1' %}<p ...>Subscribed — one note a month, no more.</p>{% else %}<form ...>{% endif %}`. Fix if missing.

- [ ] **Step 4: Add route to `app/main.py`**

```python
from app.emailer import build_subscribe_text
from app.forms import SubscribeForm

    @app.post("/subscribe")
    async def subscribe_post(
        request: Request,
        email: str = Form(""), website: str = Form(""), ts: str = Form(""),
        from_: str = Form("/", alias="from"),
    ):
        # sanitise redirect target first, always
        try:
            safe = SubscribeForm(email="placeholder@example.com", **{"from": from_}).from_path
        except ValidationError:
            safe = "/"
        verdict = bot_or_limited(request, "subscribe", website, ts)
        if verdict == "limited":
            return PlainTextResponse("Too many submissions. Try again shortly.", status_code=429)
        if verdict == "bot":
            return RedirectResponse(f"{safe}?subscribed=1", status_code=303)
        try:
            form = SubscribeForm(email=email, **{"from": from_})
        except ValidationError:
            return RedirectResponse(f"{safe}?subscribed=err", status_code=303)
        ip = client_key(request, "").rstrip(":")
        await send_form_email(
            settings,
            subject=f"Newsletter signup — {form.email}",
            text=build_subscribe_text(form.email, ip=ip, when=utc_now_str()),
            reply_to=form.email,
        )
        return RedirectResponse(f"{form.from_path}?subscribed=1", status_code=303)
```

- [ ] **Step 5: Run tests, verify pass.**

- [ ] **Step 6: Commit**

```bash
git add app tests/test_endpoints.py
git commit -m "feat: newsletter subscribe handler"
```

---

## Task 14: Progressive-enhancement JavaScript

**Files:**
- Rewrite: `app/static/js/site.js`
- Modify: `app/static/css/site.css` (filter-active styles), `app/templates/work.html` (ensure `data-type` + `.work-card` class present)
- Test: `tests/test_pages.py` addition (asset served, no-JS still shows everything)

**Interfaces:** none (browser-only). Must be a no-op failure: any JS error must not hide content.

- [ ] **Step 1: Write the failing test**

```python
def test_site_js_served(client):
    r = client.get("/static/js/site.js")
    assert r.status_code == 200
    assert "IntersectionObserver" in r.text


def test_work_cards_have_filter_hooks(client):
    body = client.get("/work").text
    assert 'class="work-card' in body
    assert 'data-type="Agentic AI"' in body
```

- [ ] **Step 2: Run, verify fail** (stub `site.js` has no `IntersectionObserver`; `work.html` may lack the class).

- [ ] **Step 3: Rewrite `app/static/js/site.js`**

```js
(function () {
  document.documentElement.classList.add('js');

  // Scroll progress bar
  var bar = document.getElementById('progress');
  if (bar) {
    var onScroll = function () {
      var h = document.documentElement;
      var d = h.scrollHeight - h.clientHeight;
      bar.style.width = (d > 0 ? (h.scrollTop / d) * 100 : 0) + '%';
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // Reveal on scroll
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var revealables = document.querySelectorAll('main > section, main > div, main figure');
  if (reduce || !('IntersectionObserver' in window)) {
    revealables.forEach(function (el) { el.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { rootMargin: '0px 0px -6% 0px', threshold: 0.04 });
    revealables.forEach(function (el, i) {
      el.classList.add('reveal');
      el.style.animationDelay = Math.min(i, 5) * 70 + 'ms';
      io.observe(el);
    });
  }

  // Work filter
  var filterBtns = document.querySelectorAll('.filter-btn');
  var cards = document.querySelectorAll('.work-card');
  if (filterBtns.length && cards.length) {
    filterBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var f = btn.getAttribute('data-filter');
        filterBtns.forEach(function (b) { b.classList.toggle('is-active', b === btn); });
        cards.forEach(function (c) {
          var show = f === 'All' || c.getAttribute('data-type') === f;
          c.classList.toggle('hide', !show);
        });
      });
    });
  }

  // Inline form submit (progressive)
  document.querySelectorAll('form[data-ajax]').forEach(function (form) {
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var fd = new FormData(form);
      fetch(form.action, { method: 'POST', body: fd, redirect: 'follow' })
        .then(function (r) { window.location.href = r.url || form.action; })
        .catch(function () { form.submit(); });
    });
  });
})();
```

- [ ] **Step 4: Add `data-ajax` to the contact and interview `<form>` tags** in `contact.html` / `interviews.html` (not the newsletter — full nav is fine there). Ensure `work.html` cards have `class="work-card lift"` and `data-type="{{ p.type }}"`.

- [ ] **Step 5: Add to `site.css`**

```css
.filter-btn.is-active { background: var(--color-accent); color: var(--color-bg); border-color: var(--color-accent); }
```

- [ ] **Step 6: Run tests, verify pass.** Run the full suite: `pytest -v`.

- [ ] **Step 7: Commit**

```bash
git add app tests/test_pages.py
git commit -m "feat: progressive-enhancement JS (progress bar, reveal, filter, ajax forms)"
```

---

## Task 15: Docker image, compose, README

**Files:**
- Create: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `README.md`
- Modify: `app/main.py` (honor `PORT` in the uvicorn entrypoint — actually handled by CMD)

**Interfaces:** none. Deliverable: `docker build` succeeds; container serves `/healthz` and `/`.

- [ ] **Step 1: Create `.dockerignore`**

```
.git
.github
.venv
__pycache__
*.pyc
.pytest_cache
tests
docs
_ds
assets
uploads
screenshots
*.dc.html
support.js
*.md
!README.md
.env
```

(Note: `content/` and `app/` are NOT ignored. `app/static/assets/` holds the SVGs the site needs — the top-level `assets/` is the original design copy and is excluded.)

- [ ] **Step 2: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY app ./app
COPY content ./content

RUN useradd --system --uid 1001 appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz').status==200 else 1)"

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./content:/app/content:ro   # dev: edit copy without rebuilding
```

- [ ] **Step 4: Create `README.md`**

Include: what this is; local dev (`python -m venv`, `pip install -e ".[dev]"`, `cp .env.example .env`, `uvicorn app.main:app --reload`); running tests (`pytest`); the env vars table (copy from the spec); Resend setup (create account, add + verify `puneetbehl.com`, set `MAIL_FROM=forms@puneetbehl.com` and `RESEND_API_KEY`; until the domain is verified use `MAIL_FROM=onboarding@resend.dev`); `MAIL_DRY_RUN=true` logs emails instead of sending; Docker (`docker compose up --build`, or `docker build -t puneetbehl-site . && docker run -p 8000:8000 --env-file .env puneetbehl-site`); deploy notes — the image is stateless and reads config from env, set `SECRET_KEY` and `TRUSTED_HOSTS` in production, terminate TLS at the platform/reverse proxy; brief pointers for Fly.io (`fly launch`, set secrets), Render (Docker service), and a VPS (`docker run` behind nginx/Caddy). Document the deliberate choice that a Resend failure still shows the user success and logs the payload at ERROR.

- [ ] **Step 5: Build and smoke-test**

Run:
```bash
docker build -t puneetbehl-site .
docker run -d --name pbtest -p 8000:8000 -e SECRET_KEY=x -e MAIL_DRY_RUN=true puneetbehl-site
sleep 3
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8000/ | grep -q "I design distributed systems"
curl -fsS http://localhost:8000/work/loaderhouse | grep -q "Loaderhouse"
docker rm -f pbtest
```
Expected: `{"status":"ok"}` and both greps succeed.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore README.md
git commit -m "chore: containerise with Dockerfile, compose, and README"
```

---

## Task 16: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: CI
on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: pytest -q
        env:
          SECRET_KEY: ci-secret
          MAIL_DRY_RUN: "true"
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t puneetbehl-site .
```

- [ ] **Step 2: Verify locally** — `pytest -q` passes with those env vars set; `docker build` already verified in Task 15.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "chore: CI — pytest and docker build"
```

---

## Self-Review

**Spec coverage:**

| Spec section | Task(s) |
| --- | --- |
| Source-material inventory (keep styles.css, extract inline CSS, port plates, copy assets, discard editor JS) | 3 |
| 10 views at real URLs | 4 (home), 5 (work + project), 6 (agentic/services/about), 7 (writing + post), 11 (contact), 12 (interviews) |
| `/healthz` | 1 |
| 404 as HTML for unknown project/post + unknown paths | 5 |
| Content → YAML + Markdown, frozen pydantic models, fail-fast loader | 2 |
| Removed hash routing; scroll bar + reveal as progressive enhancement; no-JS shows all | 3 (fallback CSS), 14 (JS) |
| 3 form endpoints, pydantic models, field limits | 8 (models), 11/12/13 (endpoints) |
| Success = 303 redirect to `?sent=1` / `?subscribed=1` state | 11, 12, 13 |
| Validation failure = 400 re-render with refilled values + error summary | 11, 12 (13 uses soft `?subscribed=err`) |
| Email via Resend, per-form subject, reply-to = submitter, text body with all fields + time + IP | 10 (emailer), 11/12/13 (wiring) |
| `MAIL_DRY_RUN` logs instead of sending | 10 |
| Resend failure → user still sees success, payload logged ERROR | 10 (return False, log), 11/12/13 (ignore return), README (documented) — 15 |
| Honeypot + signed min-fill-time + in-memory per-IP rate limit | 8 (honeypot/ts), 9 (limiter), 11 (`bot_or_limited`), reused 12/13 |
| Turnstile hook, no-op when unset | Settings carry `turnstile_*` (Task 1); `bot_or_limited` is the insertion point; widget include is conditional on `settings.turnstile_site_key`. Explicitly deferred — no template wiring in this plan. |
| `SubscribeForm.from` restricted to local path | 8 (validator), 13 (double-applied for redirect target) |
| Config via pydantic-settings, all env vars | 1 |
| Docker: slim base, non-root, `$PORT`, healthcheck, stateless; compose; `.dockerignore`; `.env.example` | 1 (`.env.example`), 15 |
| README with local/test/deploy notes | 15 |
| Tests: every route 200 + content; each form happy/invalid/honeypot/too-fast/oversized/rate-limit; content parsing | 2, 4–7, 11–14 |
| CI (pytest + docker build) | 16 |
| Per-view `<meta>` / canonical / og | 3 (base blocks), 5/7 (project & post override title/description/og_type) |
| SEO-friendly real HTML per URL | inherent to Tasks 4–12 |

Gaps found and resolved: the Turnstile widget is intentionally not wired into templates — Settings + the `bot_or_limited` seam are in place, full integration is a follow-up (matches spec's "hook is left", "not configured by default").

**Placeholder scan:** `_plates.svg` (Task 3 Step 3) permits a documented stub with a `TODO` comment — this is explicitly sanctioned by the spec ("cosmetic; if fiddly it can be dropped") and does not block any test. No other `TODO`/`TBD`/"handle edge cases"/"add validation" placeholders. All test steps contain runnable code; all implementation steps contain full code or exact line-range port instructions with a conversion recipe.

**Type consistency:**
- `render(request, name, *, nav_active="", status_code=200, **ctx)` — defined Task 3, used with these kwargs throughout.
- `bot_or_limited(request, endpoint, website, ts) -> "limited" | "bot" | None` — defined Task 11, reused verbatim in 12 and 13.
- `errors_from(ValidationError) -> dict[str,str]` — defined Task 11, reused in 12.
- `client_key(request, endpoint) -> str` — defined Task 9; `client_key(request, "").rstrip(":")` used as the IP string in 11/12/13 (consistent).
- `send_form_email(settings, *, subject, text, reply_to, client=None) -> bool` — defined Task 10, called with keyword args in 11/12/13.
- `build_contact_text` / `build_interview_text` / `build_subscribe_text` signatures `(form|email, *, ip, when)` — defined Task 10, matched in callers.
- `SubscribeForm(email=..., **{"from": ...}).from_path` — alias `from` set Task 8, used Task 13.
- `sign_ts(signer, now=None)` / `verify_ts(signer, token, min_seconds, max_age=7200)` — defined Task 8, used in tests and `bot_or_limited`.
- Content model attribute names (`p.slug`, `p.stack`, `m.value`, `post.body_html`, `post.date_display`, `s.items`, `r.note`) — defined Task 2, referenced by the template port instructions in Tasks 4–7, 11, 12.
- `RateLimiter(max_hits, window_seconds, *, clock=time.monotonic).check(key) -> bool` — defined Task 9; constructed in Task 11 as `RateLimiter(settings.rate_limit_max, settings.rate_limit_window)` and in the `conftest.py` autouse fixture.

One correction applied inline: Task 10's tests originally used `@pytest.mark.anyio`; switched to `pytest-asyncio` with `asyncio_mode = "auto"` (dev dep + ini change folded into Task 10 Step 2) so `async def test_*` runs with no marker and no extra fixture.
