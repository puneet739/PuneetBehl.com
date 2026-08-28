# PuneetBehl.com — Deployable Site + Contact Backend

**Date:** 2026-08-28
**Status:** Approved for planning

## Problem

The repository contains `Puneet Behl Site.dc.html`, a Claude Design *canvas*
file. It is not a website: it renders only inside the design editor. Its
template syntax (`{{ }}`, `<sc-if>`, `<sc-for>`) and its `onClick` / `onSubmit`
handlers are editor constructs. `support.js` is the editor's React-based
runtime. All three forms in the design (contact enquiry, mock-interview
booking, newsletter signup) are non-functional — submitting only flips local
component state to show a "thank you" panel.

Two things are needed:

1. Turn the design into a real, deployable website — faithful to the visual
   design — served by a Python backend.
2. Make all three forms actually deliver submissions to the owner by email.

The whole thing must ship as a single Docker image the owner can deploy to a
host of their choosing later.

## Goals

- A server-rendered site reproducing all 10 views of the design at real,
  crawlable URLs.
- Contact, interview-booking, and newsletter forms that each send an email to
  `puneet739@gmail.com` via the Resend API.
- Forms work without JavaScript; JavaScript enhances them.
- One stateless, 12-factor Docker image. No database.
- Content (copy, project list, posts) lives in editable data files, not in code.
- Automated tests for every route and every form path.

## Non-goals (YAGNI)

- No CMS, admin UI, or content editing through the browser.
- No database or persistent storage of any kind.
- No user accounts or authentication.
- No newsletter list management / double opt-in — the newsletter form just
  emails the owner the submitted address.
- No analytics, tag managers, or third-party trackers.
- No JavaScript framework or front-end build step.
- No CAPTCHA in the first version (a hook is left for Cloudflare Turnstile).

## Source material inventory

From `Puneet Behl Site.dc.html` and `_ds/broadsheet-*/`:

| Asset | Disposition |
| --- | --- |
| `_ds/broadsheet-*/styles.css` | Keep verbatim as `app/static/css/styles.css`. Design-system tokens and component classes (`.btn`, `.input`, `.field`, `.tag`, `.g-*`). |
| Inline `<style>` block in the `.dc.html` `<head>` | Extract to `app/static/css/site.css` (animations, `.frame`, `.reveal`, `.dot-screen`, `#progress`, responsive `@media` rules). |
| `_ds/broadsheet-*/_ds_bundle.js` → `print-plates.js` | Port the SVG separation-filter markup it injects into a static `templates/_plates.svg` partial included once in `base.html`. Drives the CMYK numerals and plate portrait. Cosmetic; if it proves fiddly it can be dropped without blocking. |
| `support.js`, `_ds_bundle.js`, `_adherence.oxlintrc.json`, `_ds_manifest.json`, `readme.md` | Not used at runtime. Leave in repo; do not ship in the image. |
| `assets/*.svg` (10 files: project artwork + `interview-scorecard.svg` + `portrait-plate.svg`) | Copy to `app/static/assets/`. |
| `screenshots/`, `uploads/`, `Portfolio Wireframes.dc.html` | Not part of the site. Leave in repo, exclude from image. |
| `PROJECTS` array (8 entries) | → `content/projects.yaml` |
| `POSTS` array (4 entries, full body paragraphs) | → `content/writing/<slug>.md` with front matter |
| `PACKAGES` array (3 entries) | → `content/packages.yaml` |
| `ROLES` array (6 entries) | → `content/roles.yaml` |
| `SKILLS` array (30 strings) | → `content/skills.yaml` |
| `FILTERS` array | Derived from the distinct `type` values in `projects.yaml`; not a separate file. |
| Header/footer, dateline, "2 slots · Oct 2026" copy, hero text, section copy | → `content/site.yaml` for the values that recur or may change; static template text otherwise. |

## Views and routes

All `GET`, server-rendered HTML. Slugs are the existing ones from the design.

| Route | View | Notes |
| --- | --- | --- |
| `/` | Home | Hero, 4 stat numerals, 4 featured projects (`projects[0,2,1,4]` order from design), agentic teaser, testimonial, CTA. |
| `/work` | Work index | All 8 projects as cards. Type filter (`All` + distinct types) done client-side with a `<noscript>`-safe "all shown" default; no server round-trip. |
| `/work/{slug}` | Project detail | Problem, approach list, architecture prose, metrics, stack tags, next-project link. 404 for unknown slug. |
| `/agentic` | Agentic AI | Static content page. |
| `/services` | Services | 3 packages from `packages.yaml`. |
| `/about` | About | Bio, 6 roles from `roles.yaml`, skills tags. |
| `/writing` | Writing index | 4 posts from `content/writing/`, sorted by date descending. |
| `/writing/{slug}` | Post detail | Rendered Markdown body. 404 for unknown slug. |
| `/contact` | Contact | Enquiry form. `?sent=1` renders the success panel instead of the form. |
| `/interviews` | Mock interviews | Content + booking form. `?sent=1` success panel. |
| `/healthz` | Health check | `200 {"status":"ok"}`. Not in nav. Used by container `HEALTHCHECK`. |

Navigation, footer, the sticky header, and the newsletter form in the footer
appear on every view via `base.html`.

### Removed behaviours from the design

- Hash routing (`#/work/...`) is replaced by real paths.
- The scroll-progress bar (`#progress`) and `IntersectionObserver` reveal
  animations are reimplemented in `app/static/js/site.js` as progressive
  enhancement. With JS off, all content is visible (no `opacity:0` initial
  state applied).

## Forms

Three forms. Each is a real HTML `form` with `method="post"`. All three send
one email to the owner and have no other side effect.

### Endpoints

| Endpoint | Form model | Success redirect |
| --- | --- | --- |
| `POST /contact` | `ContactForm` | `303 → /contact?sent=1` |
| `POST /interviews` | `InterviewForm` | `303 → /interviews?sent=1` |
| `POST /subscribe` | `SubscribeForm` | `303 → /{referring path}?subscribed=1` (footer form posts from any page; use a hidden `from` field, default `/`) |

On validation failure: re-render the originating page with a `400` status, the
submitted values refilled, and an error summary near the form. (Keep it simple —
one generic "Please check the highlighted fields" plus per-field messages from
pydantic.)

### Form models (`app/forms.py`)

`ContactForm`:
- `name` — required, 1–100 chars
- `email` — required, valid email, ≤200 chars
- `company` — optional, ≤100 chars
- `kind` — required, must be one of the 5 design options
- `msg` — required, 1–5000 chars
- `website` — honeypot, must be empty (see anti-abuse)
- `ts` — hidden timestamp, used for min-fill-time check

`InterviewForm`:
- `name` — required, 1–100
- `email` — required, valid email
- `format` — required, one of the 4 design options
- `target` — optional, ≤200
- `slots` — required, 1–2000
- `website` honeypot, `ts` timestamp

`SubscribeForm`:
- `email` — required, valid email
- `from` — hidden, path to redirect back to; validated to be a local path
  (starts with `/`, no `//` or scheme)
- `website` honeypot, `ts` timestamp

All string fields are `.strip()`-ed and length-capped before validation so an
oversized body is rejected cheaply.

### Email (`app/emailer.py`)

- Transport: Resend HTTP API, `POST https://api.resend.com/emails`, `Authorization: Bearer $RESEND_API_KEY`, JSON body.
- Async via `httpx.AsyncClient`, one shared client on app state, 10s timeout.
- Payload per form:
  - `from`: `settings.mail_from`
  - `to`: `[settings.mail_to]`
  - `reply_to`: the submitter's email (so the owner replies directly)
  - `subject`:
    - contact → `New enquiry — {name} ({kind})`
    - interview → `Mock interview request — {name} ({format})`
    - subscribe → `Newsletter signup — {email}`
  - `text`: plain-text block listing every submitted field, one per line, plus
    a footer line with submission time (UTC) and source IP.
- On Resend non-2xx or network error: log the error with the full submission
  payload at `ERROR` level (so nothing is lost), and still show the user the
  success panel. Rationale: the submitter can do nothing about a Resend outage;
  the owner has the data in logs. This trade-off is intentional and documented
  in the README.
- A `MAIL_DRY_RUN=true` setting skips the HTTP call and logs the payload — used
  by tests and local dev without a key.

### Anti-abuse

- **Honeypot**: hidden `website` field, off-screen via CSS, `autocomplete="off"`,
  `tabindex="-1"`. Non-empty → silently return the success redirect without
  sending. (Do not reveal the check.)
- **Min-fill-time**: hidden `ts` field set to render time (epoch seconds,
  signed with `SECRET_KEY` via `itsdangerous` to prevent forgery). Submissions
  faster than 3 seconds are treated as bot traffic — silent success, no send.
- **Rate limit**: in-memory fixed-window counter keyed by client IP + endpoint,
  default 5 requests / 60 seconds. Over limit → `429` with a plain message.
  Implemented as a small dependency in `app/ratelimit.py`; no external package.
  Acceptable that it resets on restart and is per-process (single-container
  deployment).
- **Turnstile hook**: `forms.py` has a `verify_turnstile(token)` function that
  is a no-op returning `True` when `TURNSTILE_SECRET` is unset. Templates
  include the widget only when `settings.turnstile_site_key` is set. Not
  configured by default.

## Content loading (`app/content.py`)

- Runs once at import / app startup. Parses:
  - `content/projects.yaml` → `list[Project]` (pydantic models), order preserved.
  - `content/packages.yaml` → `list[Package]`
  - `content/roles.yaml` → `list[Role]`
  - `content/skills.yaml` → `list[str]`
  - `content/site.yaml` → `SiteConfig` (nav labels, availability blurb,
    testimonial, hero copy, contact details, social links)
  - `content/writing/*.md` → `list[Post]`, front matter (`title`, `date`,
    `read`, `excerpt`, `slug` defaulting to filename) parsed with
    `python-frontmatter`, body rendered to HTML with `markdown-it-py`. Sorted
    by `date` desc.
- Invalid or missing content raises at startup (fail fast, not per request).
- Exposes helpers: `get_project(slug)`, `get_post(slug)`, `featured_projects()`,
  `project_types()`.
- Models are frozen; templates receive plain attribute access.

## Configuration (`app/config.py`)

`pydantic-settings` `Settings`, read from environment / `.env`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8000` | Listen port. |
| `SECRET_KEY` | *(required)* | Signs the `ts` form field. |
| `RESEND_API_KEY` | `""` | Resend key. Empty ⇒ implies `MAIL_DRY_RUN`. |
| `MAIL_TO` | `puneet739@gmail.com` | Recipient of all form emails. |
| `MAIL_FROM` | `forms@puneetbehl.com` | Verified Resend sender. Use `onboarding@resend.dev` until the domain is verified. |
| `MAIL_DRY_RUN` | `false` | Skip the Resend call, log instead. |
| `RATE_LIMIT_MAX` | `5` | Requests per window per IP per endpoint. |
| `RATE_LIMIT_WINDOW` | `60` | Window seconds. |
| `MIN_FILL_SECONDS` | `3` | Faster submissions are treated as bots. |
| `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET` | `""` | Optional CAPTCHA. |
| `TRUSTED_HOSTS` | `*` | `TrustedHostMiddleware` value for production. |

`.env.example` documents all of these.

## Project structure

```
app/
  __init__.py
  main.py            # FastAPI app, middleware, route table, lifespan
  config.py
  content.py
  emailer.py
  forms.py
  ratelimit.py
  templates/
    base.html
    _header.html
    _footer.html
    _plates.svg
    _form_errors.html
    home.html
    work.html
    project.html
    agentic.html
    services.html
    about.html
    writing.html
    post.html
    contact.html
    interviews.html
  static/
    css/styles.css   # from _ds, verbatim
    css/site.css      # extracted inline styles
    js/site.js        # scroll progress, reveal, ajax form enhancement
    assets/*.svg
    favicon.svg
content/
  site.yaml
  projects.yaml
  packages.yaml
  roles.yaml
  skills.yaml
  writing/
    agents-are-distributed-systems.md
    ecs-to-eks-what-i-would-do-differently.md
    the-eval-set-is-the-product.md
    interoperability-is-a-people-problem.md
tests/
  conftest.py
  test_pages.py
  test_forms.py
  test_content.py
  test_ratelimit.py
pyproject.toml
Dockerfile
docker-compose.yml
.dockerignore
.env.example
.gitignore
README.md
```

## Rendering approach

- FastAPI with `Jinja2Templates`. One `base.html` with blocks: `title`,
  `meta`, `main`, `scripts`.
- Per-view `<meta>`: title, description, `og:title`/`og:description`/`og:type`,
  canonical URL. Project and post pages derive these from their content.
- `app/static` served by `StaticFiles` at `/static`. `Cache-Control` headers
  for static assets (1 day) via a small middleware or `StaticFiles` default.
- No inline `<style>`/`<script>` beyond the ported `_plates.svg`; CSS and JS are
  external files under `/static`.
- `site.js` is loaded with `defer`. It: (1) drives `#progress`, (2) adds the
  `.in` class on scroll via `IntersectionObserver`, (3) intercepts the three
  form submits, POSTs via `fetch`, and swaps in the success panel without a
  full navigation — falling back to normal submission on any error or if JS is
  absent. Respects `prefers-reduced-motion`.

## Docker

- Base `python:3.12-slim`.
- Non-root `app` user; `WORKDIR /app`.
- Install deps from `pyproject.toml` (via `pip install .` or `uv`), copy `app/`
  and `content/` only (`.dockerignore` excludes `_ds/`, `*.dc.html`, `support.js`,
  `screenshots/`, `uploads/`, `tests/`, `docs/`, `.git/`).
- `EXPOSE 8000`; `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`
  with `PORT` honored via shell form or an entrypoint.
- `HEALTHCHECK` curling `http://localhost:8000/healthz`.
- `docker-compose.yml`: builds the image, maps `8000:8000`, `env_file: .env`,
  mounts `./content` for live copy edits in dev only.
- Image target size: < 200 MB.

Deployment is host-agnostic. README gives brief notes for Fly.io, Render, and
`docker run` on a VPS behind a reverse proxy. TLS and domain are the host's
responsibility.

## Testing (TDD)

Framework: `pytest`, Starlette `TestClient`. `MAIL_DRY_RUN=true` and a fixed
`SECRET_KEY` in `conftest.py`. Resend HTTP calls are intercepted with `respx`,
with hard assertions on the request payload.

- `test_content.py`: all YAML and Markdown parse; counts match (8 projects, 4
  posts, 3 packages, 6 roles); every project has the required fields; `get_project`
  / `get_post` return `None` for unknown slugs; posts sorted by date desc.
- `test_pages.py`: each of the 10 routes returns `200` and contains a known
  string from its content. `/work/loaderhouse` shows the p95 latency metric.
  `/writing/the-eval-set-is-the-product` renders body prose. Unknown project /
  post slug returns `404`. `/healthz` returns the ok JSON. Every page includes
  the nav and footer. Response has no `{{` (no unrendered template vars).
- `test_forms.py`, per form:
  - Valid submission → `303` to the `?sent=1` URL, Resend called once with
    `to == [MAIL_TO]`, correct `subject`, `reply_to == submitter email`, and
    every submitted field present in `text`.
  - Missing required field → `400`, page re-rendered with the error partial,
    Resend not called.
  - Bad email → `400`.
  - Honeypot filled → success redirect, Resend **not** called.
  - `ts` older than now but faster than `MIN_FILL_SECONDS` → success redirect,
    not sent. Tampered/unsigned `ts` → treated as bot, not sent.
  - Oversized `msg` (> 5000) → `400`.
  - `SubscribeForm` `from` field with an external URL → rejected / coerced to `/`.
  - Resend returns 500 → user still gets `303` success; an `ERROR` log line
    contains the payload.
- `test_ratelimit.py`: 5 rapid POSTs pass, 6th returns `429`; a different IP is
  unaffected; window reset allows sending again.

CI: `.github/workflows/ci.yml` runs `pytest` and then `docker build` on push
and PR. Included in the plan.

## Rollout

1. `git init` (done) and scaffold.
2. Build content files from the design's data arrays — verbatim copy.
3. Build templates view-by-view against `styles.css` + `site.css`; eyeball each
   against the `.dc.html` rendered in the editor.
4. Wire forms + Resend with `MAIL_DRY_RUN` locally.
5. Owner creates a Resend account, verifies `puneetbehl.com` (or uses the
   onboarding sender), sets `RESEND_API_KEY` and `SECRET_KEY` in the deploy
   environment.
6. `docker build`, deploy to the chosen host, point DNS, enable TLS at the host.

## Open questions / owner actions

- Resend account + domain verification for `MAIL_FROM` (until then,
  `onboarding@resend.dev`).
- Confirm the domain is `puneetbehl.com` and it's available to point at the
  deployed container.
- Portrait: the design uses a generated plate SVG with a caption "Swap in a
  photograph any time." Ship as-is; real photo is a later content change.
