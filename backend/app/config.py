"""
App settings in one place.

All values come from environment variables:
  - In Docker, docker-compose.yml passes them in from the project's .env file.
  - When running locally (`uv run fastapi dev`), load_dotenv() reads the same
    project-root .env file. Real environment variables always win.

There are deliberately NO default passwords or secret keys here: if one is
missing, the app stops at startup with a clear message instead of silently
running with a known, public value.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
load_dotenv(BASE_DIR.parent / ".env")              # project-root .env (local runs)


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Environment variable {name} is not set. "
            "Copy .env.example to .env in the project root and fill it in."
        )
    return value


# ---------- Database ----------
# Built from the same POSTGRES_* variables the Postgres container uses.
# POSTGRES_HOST is "localhost" for local runs and "db" (the service name)
# inside Docker - docker-compose.yml sets that. DATABASE_URL overrides it all.
DATABASE_URL = os.getenv("DATABASE_URL") or (
    "postgresql+psycopg://"
    f"{_required('POSTGRES_USER')}:{_required('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}"
    f"/{_required('POSTGRES_DB')}"
)
# Set SQL_ECHO=true to print every SQL query SQLAlchemy runs (great for learning)
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"

# ---------- JWT ----------
# HS256 wants a key of at least 32 bytes. Generate one with:
#   python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = _required("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# ---------- CORS ----------
# Which frontends are allowed to call this API from the browser.
# Comma-separated. Vite's dev server runs on port 5173 by default.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
