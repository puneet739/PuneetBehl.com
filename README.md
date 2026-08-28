# PuneetBehl.com

The source for **puneetbehl.com** — a server-rendered portfolio site built with
FastAPI and Jinja2.

There is no database, no JavaScript framework, and no front-end build step. All
content (projects, packages, roles, skills, site copy, and posts) lives in
`content/` as YAML and Markdown, is loaded into frozen pydantic models once at
startup, and is rendered into HTML at real URLs. One hand-written
`app/static/js/site.js` adds progressive enhancement; every page works with
JavaScript disabled.

---

## Table of contents

- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Running the site](#running-the-site)
- [Running with Docker](#running-with-docker)
- [Configuration](#configuration)
- [Running the tests](#running-the-tests)
- [Project layout](#project-layout)
- [Editing content](#editing-content)
- [Routes](#routes)
- [Troubleshooting](#troubleshooting)

---

## Requirements

| Tool | Version | Notes |
|------|---------|-------|
| Python | **3.12 or newer** | Required by `pyproject.toml`. The macOS system Python (3.9) will not work. |
| pip or [uv](https://docs.astral.sh/uv/) | any recent | Either works; `uv` is faster. |
| Docker + Docker Compose | optional | Only if you want to run the containerised build. |
| Git | any | To clone the repository. |

Check your Python version before starting:

```bash
python3 --version   # must print 3.12.x or newer
```

If it does not, install Python 3.12+ first (`brew install python@3.12` on
macOS, `pyenv install 3.12` anywhere, or your distro's package manager) and use
that interpreter in the commands below.

---

## Quick start

The fastest path — `dev.sh` creates the virtualenv, installs dependencies,
seeds `.env`, and starts the server:

```bash
git clone <repository-url> PuneetBehl.com
cd PuneetBehl.com
./dev.sh
```

Open <http://127.0.0.1:8000>. That is all most people need; the manual steps
below do the same thing by hand.

### Manual setup

```bash
# 1. Clone and enter the project
git clone <repository-url> PuneetBehl.com
cd PuneetBehl.com

# 2. Create a virtual environment with Python 3.12+
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install the project and its dev dependencies (editable install)
pip install --upgrade pip
pip install -e ".[dev]"

# 4. Create your local environment file
cp .env.example .env

# 5. Run the development server
uvicorn app.main:app --reload --port 8000
```

Open <http://127.0.0.1:8000> in a browser.

### Using `uv` instead of pip

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
uv run uvicorn app.main:app --reload --port 8000
```

---

## Running the site

### With `dev.sh` (recommended)

```bash
./dev.sh                  # http://127.0.0.1:8000, auto-reload on
./dev.sh --port 9000      # a different port
./dev.sh --host 0.0.0.0   # reachable from other devices on your network
./dev.sh --no-reload      # disable auto-reload
./dev.sh --help           # usage
```

The script is idempotent and safe to re-run: it only creates the virtualenv,
installs dependencies (when `pyproject.toml` is newer than the last install),
or copies `.env.example` to `.env` if those are actually missing. It `cd`s to
the repository root itself, so you can call it from anywhere, and it fails with
a readable message — rather than a bind traceback — if the port is already
taken.

### By hand

Always run commands from the **repository root** — `app/config.py` loads `.env`
relative to the current working directory, and `app/content.py` resolves
`content/` relative to the package.

**Development (auto-reload on file changes):**

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Production-style (no reload, behind a proxy):**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips='*'
```

**Different port:**

```bash
uvicorn app.main:app --reload --port 9000
```

> Note: `--reload` restarts on Python file changes, and Jinja re-reads
> templates on every request — but **content is cached at startup**. After
> editing anything under `content/`, restart the server to see the change.

Health check endpoint: <http://127.0.0.1:8000/healthz> → `{"status":"ok"}`

To stop the server, press `Ctrl+C`.

---

## Running with Docker

The `Dockerfile` is a two-stage build: dependencies are installed into an
isolated venv in the builder stage, and only the venv plus the source tree are
copied into the slim runtime image (no pip, no setuptools).

**With Compose (recommended):**

```bash
cp .env.example .env          # optional — Compose runs without it
docker compose up --build
```

The site is served at <http://127.0.0.1:8000>.

Change the host port without touching any file:

```bash
HOST_PORT=9000 docker compose up --build
```

Stop and clean up:

```bash
docker compose down
```

Compose mounts `./content` into the container read-only, so you can edit
content without rebuilding the image — but because content is cached at
startup you must restart the service to pick edits up:

```bash
docker compose restart web
```

> Remove that `volumes:` mount from `docker-compose.yml` for a real production
> deployment; the image already contains its own copy of `content/`.

**Plain Docker (no Compose):**

```bash
docker build -t puneetbehl-site:local --target runtime .
docker run --rm -p 8000:8000 --env-file .env puneetbehl-site:local
```

The image defines a `HEALTHCHECK` that polls `/healthz`, and the container
listens on `$PORT` (default `8000`) as a non-root `appuser`.

---

## Configuration

Configuration is read from environment variables, or from a `.env` file in the
repository root, via `pydantic-settings` (`app/config.py`). Start by copying the
example file:

```bash
cp .env.example .env
```

| Variable | Default | What it does |
|----------|---------|--------------|
| `PORT` | `8000` | Port the app is served on (used by Docker; pass `--port` to uvicorn directly in dev). |
| `SECRET_KEY` | `dev-insecure-secret-key-change-me` | Signs the timestamped form tokens. **Set a long random value in production.** |
| `TRUSTED_HOSTS` | `*` | Comma-separated allowlist for `TrustedHostMiddleware`. Set to your real domains in production, e.g. `puneetbehl.com,www.puneetbehl.com`. |
| `RESEND_API_KEY` | *(empty)* | API key for [Resend](https://resend.com), used to deliver form emails. Empty ⇒ dry-run. |
| `MAIL_TO` | `puneet739@gmail.com` | Recipient of form submissions. |
| `MAIL_FROM` | `onboarding@resend.dev` | Sender address for form submissions. |
| `MAIL_DRY_RUN` | `false` | `true` ⇒ never actually send email. Dry-run is also forced whenever `RESEND_API_KEY` is empty. |
| `RATE_LIMIT_MAX` | `5` | Max form submissions allowed per window, per client. |
| `RATE_LIMIT_WINDOW` | `60` | Rate-limit window in seconds. |
| `MIN_FILL_SECONDS` | `3` | Minimum time a form must be open before submission is accepted (bot screen). |
| `TURNSTILE_SITE_KEY` | *(empty)* | Cloudflare Turnstile site key. Empty ⇒ the widget is disabled. |
| `TURNSTILE_SECRET` | *(empty)* | Cloudflare Turnstile secret. Empty ⇒ verification is skipped. |

`.env` is git-ignored — never commit real keys.

Generate a production `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> **Status:** the mail, rate-limit, Turnstile, and form settings above are
> already wired into `Settings` and ship in `.env.example`, but the form
> endpoints themselves (`/contact`, `/interviews`) are still being built on the
> `feat/site-and-contact-backend` branch. Everything currently served is
> read-only `GET` routes — see [Routes](#routes).

---

## Running the tests

The suite is `pytest` against an in-process `TestClient`, so no server needs to
be running.

```bash
source .venv/bin/activate
pytest
```

`pyproject.toml` already sets `testpaths = ["tests"]`, quiet output, and
`asyncio_mode = "auto"`, so a bare `pytest` from the repository root is enough.

Useful variations:

```bash
pytest -v                       # verbose, one line per test
pytest tests/test_writing.py    # a single file
pytest -k "about"               # tests matching a name
pytest -x                       # stop at the first failure
```

`tests/conftest.py` sets safe defaults (`SECRET_KEY`, `MAIL_DRY_RUN=true`,
`MAIL_FROM`) with `os.environ.setdefault`, so the tests never send email — but
note that a `.env` value can still be picked up if you set something unusual
there.

---

## Project layout

```
.
├── app/                       # the FastAPI application
│   ├── main.py                # create_app(), all routes, Jinja environment
│   ├── config.py              # Settings (pydantic-settings, reads .env)
│   ├── content.py             # content models + YAML/Markdown loaders
│   ├── templates/             # Jinja2 templates (base, header/footer, pages)
│   └── static/
│       ├── css/styles.css     # design-system CSS — generated, never hand-edit
│       ├── css/site.css       # site-specific CSS
│       ├── js/site.js         # progressive enhancement only
│       └── assets/            # project SVG plates
├── content/                   # all site copy — edit this, not the templates
│   ├── site.yaml              # tagline, contact details, footer, stats
│   ├── projects.yaml          # case studies
│   ├── packages.yaml          # service packages / pricing
│   ├── roles.yaml             # work history
│   ├── skills.yaml            # skill list
│   └── writing/*.md           # blog posts (front matter + Markdown)
├── tests/                     # pytest suite
├── docs/superpowers/          # design spec and implementation plan
├── dev.sh                     # one-command local dev server (setup + launch)
├── Dockerfile                 # two-stage build (builder → runtime)
├── docker-compose.yml         # local container run
├── pyproject.toml             # dependencies, packaging, pytest config
└── .env.example               # template for your local .env
```

The `.dc.html` files at the repository root (`Puneet Behl Site.dc.html`,
`Portfolio Wireframes.dc.html`) and `_ds/` are the Claude Design source of
visual truth that the templates were ported from. They are reference material —
the running site does not read them.

---

## Editing content

You should rarely need to touch a template to change what the site says.

**Structured content** — edit the YAML files in `content/`. They are validated
against frozen pydantic models in `app/content.py`, so a missing or misspelled
key raises a clear error at startup rather than rendering a blank page.

**Blog posts** — add a Markdown file to `content/writing/`. Posts are sorted
newest-first by `date`, and the filename stem is the URL slug unless a `slug`
key overrides it. Required front matter:

```markdown
---
slug: the-eval-set-is-the-product
title: "The eval set is the product"
date: 2026-05-02
read: "6 min read"
excerpt: >-
  One or two sentences shown on the writing index.
---

Post body in CommonMark. Typographic replacements and smart quotes are on.
```

At least one post must exist — `load_content()` raises `FileNotFoundError` if
`content/writing/` has no Markdown files.

**After any content edit, restart the server.** Content is loaded once into
`app.state.content` at startup and cached; `--reload` only restarts on *Python*
file changes, so a YAML or Markdown edit alone will not be picked up.

---

## Routes

| Path | Description |
|------|-------------|
| `GET /` | Home — featured projects and headline stats |
| `GET /work` | Work index with type filters |
| `GET /work/{slug}` | Project case study |
| `GET /agentic` | Agentic AI page |
| `GET /services` | Service packages |
| `GET /about` | Bio, roles, skills |
| `GET /writing` | Post index |
| `GET /writing/{slug}` | Post detail |
| `GET /healthz` | Liveness probe → `{"status":"ok"}` |
| *anything else* | Custom 404 page |

The interactive API docs (`/docs`, `/redoc`, `/openapi.json`) are deliberately
disabled — this is a website, not an API.

---

## Troubleshooting

**`ERROR: Package 'puneetbehl-site' requires a different Python`**
Your interpreter is older than 3.12. Recreate the venv with
`python3.12 -m venv .venv`.

**`ModuleNotFoundError: No module named 'app'`**
You are not in the repository root, or the venv is not activated. Run
`source .venv/bin/activate` from the project root, and confirm the editable
install with `pip install -e ".[dev]"`.

**`FileNotFoundError: no posts in .../content/writing`**
`content/writing/` contains no `.md` files. Add at least one post.

**`Invalid host header` / 400 responses**
`TRUSTED_HOSTS` does not include the hostname you are using. Set
`TRUSTED_HOSTS=*` for local development.

**Content edits are not showing up**
Restart the server (or `docker compose restart web`). Content is cached at
startup by design.

**`Address already in use`**
Something else holds port 8000. Use another port
(`uvicorn app.main:app --reload --port 9000`, or `HOST_PORT=9000 docker compose
up`), or find the offender with `lsof -i :8000`.

**Docker build fails on `pip install .`**
The build copies `pyproject.toml`, `app/`, and `content/` before installing.
If you added a new top-level package directory, add it to both the `COPY` lines
in the `Dockerfile` and `[tool.setuptools] packages` in `pyproject.toml`.
