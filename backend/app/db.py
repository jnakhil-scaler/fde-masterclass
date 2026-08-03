import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()


def _with_psycopg_driver(url: str) -> str:
    """Providers (Railway, Neon, etc.) hand out plain postgresql:// URLs, which
    SQLAlchemy defaults to psycopg2 for. We install psycopg3, so normalize the
    scheme rather than relying on every .env to be hand-edited correctly."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _with_psycopg_driver(
    os.environ.get("DATABASE_URL", "postgresql+psycopg://localhost/gupta_traders")
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
