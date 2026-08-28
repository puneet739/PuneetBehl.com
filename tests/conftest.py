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
