from sqlalchemy.orm import Session

from app.deps import hash_password
from app.models import Company, User


def create_company(db: Session, **overrides) -> Company:
    values = {"name": "Test company", **overrides}
    company = Company(**values)
    db.add(company)
    db.flush()
    return company


def create_user(
    db: Session,
    company: Company,
    *,
    email: str = "customer@example.test",
    password: str = "test-password",
    **overrides,
) -> User:
    values = {
        "company_id": company.id,
        "name": "Test user",
        "email": email,
        "password_hash": hash_password(password),
        **overrides,
    }
    user = User(**values)
    db.add(user)
    db.flush()
    return user
