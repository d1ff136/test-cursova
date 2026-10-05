"""Налаштування підключення до PostgreSQL через SQLAlchemy."""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Завантажуємо змінні з файлу .env
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://mmr_user:mmr_password@localhost:5432/mmr_db",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: сесія БД на час обробки запиту."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
