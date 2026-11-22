from uuid import uuid4

from app.routes import health


def test_healthz_is_live_and_echoes_valid_request_id(client):
    request_id = str(uuid4())

    response = client.get(
        "/healthz",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == request_id


def test_readyz_reports_all_dependencies(monkeypatch, client):
    monkeypatch.setattr(health, "_check_database", lambda: None)
    monkeypatch.setattr(health, "_check_redis", lambda: None)
    monkeypatch.setattr(health, "_check_storage", lambda: None)

    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {
            "database": "ok",
            "redis": "ok",
            "storage": "ok",
        },
    }


def test_readyz_returns_unavailable_without_leaking_exception(
    monkeypatch,
    client,
):
    def unavailable():
        raise RuntimeError("password=do-not-return")

    monkeypatch.setattr(health, "_check_database", unavailable)
    monkeypatch.setattr(health, "_check_redis", lambda: None)
    monkeypatch.setattr(health, "_check_storage", lambda: None)

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "unavailable"
    assert "do-not-return" not in response.text
