def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_openapi_disabled(client):
    assert client.get("/openapi.json").status_code == 404
