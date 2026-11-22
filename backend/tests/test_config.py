import secrets

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.config import Settings


def _production_settings(**overrides):
    values = {
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql+psycopg2://app@db/teledesk",
        "JWT_SECRET": secrets.token_urlsafe(32),
        "ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "MINIO_ACCESS_KEY": secrets.token_urlsafe(16),
        "MINIO_SECRET_KEY": secrets.token_urlsafe(32),
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        ("JWT_SECRET", "change-me", "JWT_SECRET"),
        ("ENCRYPTION_KEY", "", "ENCRYPTION_KEY"),
        (
            "DATABASE_URL",
            "postgresql+psycopg2://teledesk@localhost:5432/teledesk",
            "DATABASE_URL",
        ),
        ("MINIO_ACCESS_KEY", "minioadmin", "storage credentials"),
    ],
)
def test_production_rejects_development_defaults(
    field,
    value,
    expected_error,
):
    with pytest.raises(ValidationError, match=expected_error):
        _production_settings(**{field: value})


def test_production_accepts_explicit_secure_configuration():
    settings = _production_settings()
    assert settings.APP_ENV == "production"
