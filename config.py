"""Application configuration. All secrets come from environment variables (.env)."""
import os
import secrets
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _database_uri():
    """SQLite locally; MySQL (RDS) when DATABASE_URL or DB_HOST is set."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    host = os.getenv("DB_HOST")
    if host:
        user = quote_plus(os.getenv("DB_USER", ""))
        pwd = quote_plus(os.getenv("DB_PASSWORD", ""))
        port = os.getenv("DB_PORT", "3306")
        name = os.getenv("DB_NAME", "food_ordering")
        return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{name}?charset=utf8mb4"
    (BASE_DIR / "instance").mkdir(exist_ok=True)
    return "sqlite:///" + str(BASE_DIR / "instance" / "food_ordering.db")


APP_ENV = os.getenv("APP_ENV", "development")
_secret = os.getenv("SECRET_KEY")
if not _secret or _secret == "change-me":
    if APP_ENV == "production":
        raise RuntimeError("SECRET_KEY must be set in production (.env).")
    _secret = secrets.token_hex(32)  # dev only: sessions reset on every restart


class Config:
    APP_NAME = os.getenv("APP_NAME", "Spice Route Kitchen")
    SECRET_KEY = _secret
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8

    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB uploads
    UPLOAD_FOLDER = str(BASE_DIR / "static" / "images" / "foods")
    DISPLAY_UTC_OFFSET_MINUTES = int(os.getenv("DISPLAY_UTC_OFFSET_MINUTES", "330"))  # IST
