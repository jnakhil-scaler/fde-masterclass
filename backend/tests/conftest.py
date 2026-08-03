import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, _with_psycopg_driver, get_db
from app.main import app

TEST_DATABASE_URL = _with_psycopg_driver(os.environ["TEST_DATABASE_URL"])

test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _override_get_db():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


# Redirect every TestClient-based request (which resolves its DB session via
# the app's get_db dependency) to the test database instead of the real one.
app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def clean_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db(clean_db):
    session = TestSessionLocal()
    yield session
    session.close()
