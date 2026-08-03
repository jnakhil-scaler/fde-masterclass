import pytest
from app.db import Base, engine, SessionLocal


@pytest.fixture
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(clean_db):
    session = SessionLocal()
    yield session
    session.close()
