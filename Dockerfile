# syntax=docker/dockerfile:1

# ---- builder: resolve and install dependencies into an isolated venv ----
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /src

# The project is installed from source, so the package must exist before
# `pip install .` runs (setuptools packages = ["app"] in pyproject.toml).
COPY pyproject.toml ./
COPY app ./app
COPY content ./content

RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install .

# pip/setuptools are build-time only; dropping them keeps ~15 MB and one class
# of tooling out of the runtime image.
RUN rm -rf /opt/venv/lib/python3.12/site-packages/pip \
           /opt/venv/lib/python3.12/site-packages/pip-* \
           /opt/venv/lib/python3.12/site-packages/setuptools \
           /opt/venv/lib/python3.12/site-packages/setuptools-* \
           /opt/venv/lib/python3.12/site-packages/pkg_resources \
           /opt/venv/lib/python3.12/site-packages/wheel \
           /opt/venv/lib/python3.12/site-packages/wheel-* \
           /opt/venv/bin/pip /opt/venv/bin/pip3 /opt/venv/bin/pip3.12

# ---- runtime: venv + source only, no build residue ----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# PYTHONPATH=/app makes this copied tree authoritative over the site-packages
# copy, so app.content's CONTENT_DIR (app/../content) resolves to /app/content.
COPY app ./app
COPY content ./content

RUN useradd --uid 1001 --no-create-home --shell /usr/sbin/nologin appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT','8000'), timeout=2).status == 200 else 1)"

# Shell form so $PORT is expanded; exec so uvicorn is PID 1 and gets SIGTERM.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
