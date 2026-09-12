import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ADR-152: the environment is the interface — the application reads os.environ and
# never learns how the value got there. The fallback is the docker-compose dev
# database, so a local checkout runs with no configuration.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://newsletter_user:newsletter_password@localhost:5432/newsletter",
)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()