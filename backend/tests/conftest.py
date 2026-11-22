import os
import secrets

from cryptography.fernet import Fernet

os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": "postgresql+psycopg2://test@localhost/teledesk_test",
        "JWT_SECRET": secrets.token_urlsafe(32),
        "ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "MINIO_ACCESS_KEY": secrets.token_urlsafe(16),
        "MINIO_SECRET_KEY": secrets.token_urlsafe(32),
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import Base  # noqa: E402
import app.models  # noqa: E402,F401


@pytest.fixture
def client():
    from app.main import app

    test_client = TestClient(app)
    yield test_client
    test_client.close()


@pytest.fixture
def test_engine():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.fail("TEST_DATABASE_URL is required for DB-backed tests. Run: make test")

    url = make_url(database_url)
    if url.get_backend_name() != "postgresql" or not (
        url.database and url.database.endswith("_test")
    ):
        pytest.fail("TEST_DATABASE_URL must target a PostgreSQL database ending in _test")

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    with Session(test_engine) as session:
        yield session
