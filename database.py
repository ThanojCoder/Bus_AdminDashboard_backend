import os
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


def get_clean_database_url() -> str:
    raw_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("DATABASE_PUBLIC_URL")
        or os.getenv("POSTGRES_URL")
    )
    if raw_url:
        candidate = raw_url.strip().strip("'\"")
        # Standardize prefix for SQLAlchemy 2.0
        if candidate.startswith("postgres://"):
            candidate = candidate.replace("postgres://", "postgresql://", 1)

        # Check for unexpanded Railway template variables like ${{Postgres.DATABASE_URL}}
        if "${{" in candidate or "}}" in candidate:
            print(
                f"[DB Warning] DATABASE_URL contains unresolved Railway template: '{candidate}'"
            )
            print(
                "[DB Tip] Please copy the full postgresql:// URL from your Postgres Variables tab and paste it directly into DATABASE_URL."
            )
        else:
            try:
                u = make_url(candidate)
                if u.host:
                    print(
                        f"[DB Info] Successfully loaded DATABASE_URL -> Host: {u.host}, Port: {u.port}, DB: {u.database}"
                    )
                    return candidate
                else:
                    print(
                        f"[DB Warning] DATABASE_URL '{candidate}' is missing a hostname! Check for missing credentials or empty templates."
                    )
            except Exception as e:
                print(f"[DB Warning] Could not parse DATABASE_URL '{candidate}': {e}")

    # Fallback to individual connection parameters or Railway's PG* variables
    db_host = os.getenv("PGHOST") or os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("PGPORT") or os.getenv("DB_PORT", "5432")
    db_name = os.getenv("PGDATABASE") or os.getenv("DB_NAME", "busBooking_db")
    db_user = os.getenv("PGUSER") or os.getenv("DB_USER", "postgres")
    db_password = os.getenv("PGPASSWORD") or os.getenv("DB_PASSWORD", "")
    db_sslmode = os.getenv("DB_SSLMODE", "")

    try:
        int(str(db_port))
    except Exception:
        db_port = "5432"

    print(
        f"[DB Info] Using fallback connection parameters -> Host: {db_host}:{db_port}, DB: {db_name}"
    )
    encoded_password = urllib.parse.quote_plus(db_password) if db_password else ""
    auth_part = (
        f"{db_user}:{encoded_password}@"
        if encoded_password
        else (f"{db_user}@" if db_user else "")
    )
    query_part = f"?sslmode={db_sslmode}" if db_sslmode else ""
    return f"postgresql://{auth_part}{db_host}:{db_port}/{db_name}{query_part}"


SQLALCHEMY_DATABASE_URL = get_clean_database_url()

try:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
    )
except Exception as e:
    print(f"[DB Critical Error] Failed to create engine with URL: {e}")
    # Fallback in-memory engine so Uvicorn does not crash on import
    engine = create_engine("sqlite:///:memory:")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
