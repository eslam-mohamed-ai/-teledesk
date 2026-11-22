from sqlalchemy.orm import configure_mappers

from app.models import Company

from .factories import create_company, create_user


def test_user_company_relationship_is_bidirectional(db_session):
    configure_mappers()
    assert Company.users.property.back_populates == "company"
    company = create_company(db_session)
    user = create_user(db_session, company)
    db_session.commit()

    assert user.company is company
    assert company.users == [user]
