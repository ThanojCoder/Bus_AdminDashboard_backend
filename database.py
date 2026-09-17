import os
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Support Railway, Supabase, Neon, Render environment variables
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")

if DATABASE_URL:
    # Providers like Railway, Supabase, Heroku often use postgres:// which SQLAlchemy 2.0 rejects
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
else:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "busBooking_db")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_SSLMODE = os.getenv("DB_SSLMODE", "")

    encoded_password = urllib.parse.quote_plus(DB_PASSWORD) if DB_PASSWORD else ""
    auth_part = f"{DB_USER}:{encoded_password}@" if encoded_password else (f"{DB_USER}@" if DB_USER else "")
    query_part = f"?sslmode={DB_SSLMODE}" if DB_SSLMODE else ""
    SQLALCHEMY_DATABASE_URL = f"postgresql://{auth_part}{DB_HOST}:{DB_PORT}/{DB_NAME}{query_part}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
