# Docker Local Dev Setup — Design

Date: 2026-08-28

## Goal

Make the project Docker-ready for **local development**. The project is a
FastAPI personal site (`app.main:app`) that serves HTML/static content loaded
from `content/`.

## Context

`Dockerfile`, `docker-compose.yml`, and `.dockerignore` already exist in the
repo as untracked files from a prior session. They appear designed for local
dev: multi-stage build, non-root runtime user, healthcheck, optional `.env`,
and a read-only `content/` bind mount. Their correctness is **unverified**.

## Scope

- Verify the existing Docker artifacts work without modification where possible.
- Fix only what is broken or clearly wrong for the local dev goal.
- Commit the three Docker files.
- Success criteria: `docker compose up` works from a clean checkout with no
  `.env` present, and the site serves at `http://localhost:8000` (or
  `$HOST_PORT`).

## Approach

1. **Static review** — Compare the Docker files against how the app runs:
   - Entrypoint: `app.main:app` (uvicorn).
   - `PYTHONPATH=/app` + `COPY app ./app` so `app.content.CONTENT_DIR`
     (`app/../content`) resolves to `/app/content`.
   - `Settings` loads `.env` from the working directory; in dev the compose
     env_file is optional and `TRUSTED_HOSTS` defaults to `*`.
2. **Build** — `docker build` the runtime target; fix build failures.
3. **Run & exercise** — `docker compose up -d`, then verify:
   - `/healthz` returns 200 (direct + compose healthcheck).
   - `/` renders the home page with content (proves content mount + cache load).
   - Static assets serve from `/static`.
   - Env vars flow from env / `.env` into `Settings`.
   - Clean startup in container logs.
4. **Teardown** — Stop and remove containers/network.
5. **Report** — What worked, what didn't, and the exact fixes made.
6. **Commit** — Add the three files with a message matching repo convention
   (lowercase `chore:`/`fix:` style seen in `git log`).

## Out of Scope

- Production hardening or registry publishing.
- Contact/form backend (separate branch work).
- Extra DX tooling (Makefile, justfile, etc.).

## Verification Plan

| Check | Expected |
|-------|----------|
| `docker build` | Image builds, runtime target lean, no build residue in `/opt/venv` |
| `docker compose up -d` | Container starts, healthcheck goes healthy |
| `curl :8000/healthz` | `{"status":"ok"}`, HTTP 200 |
| `curl :8000/` | HTML, content-driven sections rendered |
| `curl :8000/static/...` | 200 for a static asset |
| No `.env` file | App still boots (optional env_file) |

## Risks

- Compose env_file `required: false` is a newer compose feature; confirmed
  compose v2.5+ supports it (local: Compose v5.3.1 — supported).
- `featured_projects()` indexes `projects` at fixed positions
  (`p[0],p[2],p[1],p[4]`); if `content/projects.yaml` ever has fewer than 5
  entries the home view raises. Verify content count is sufficient at runtime.