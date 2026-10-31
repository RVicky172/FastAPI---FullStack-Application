"""
App settings in one place.

Values come from environment variables. For local development, copy
`.env.example` to `.env` - load_dotenv() reads it into the environment.
Real environment variables always win over the .env file.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# SQLAlchemy connection string:  dialect+driver://user:password@host:port/dbname
# Default = the Postgres container from docker-compose, reached from your machine.
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://todo:todo@localhost:5432/todo"
)
# Set SQL_ECHO=true to print every SQL query SQLAlchemy runs (great for learning)
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"

# JWT settings. NEVER commit a real secret - set SECRET_KEY in .env.
# HS256 wants a key of at least 32 bytes. Generate one with:
#   python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-key-change-me-in-production-0123456789")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Which frontends are allowed to call this API from the browser (CORS).
# Comma-separated in .env. Vite's dev server runs on port 5173 by default.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
