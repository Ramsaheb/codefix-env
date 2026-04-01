import os
from dataclasses import dataclass


def _read_int(name: str, default: int, minimum: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default

    return max(value, minimum)


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    log_level: str
    default_task: str
    max_sessions: int
    session_ttl_seconds: int


def load_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "CodeFixEnv"),
        app_version=os.getenv("APP_VERSION", "1.0.0"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        default_task=os.getenv("DEFAULT_TASK", "easy").strip() or "easy",
        max_sessions=_read_int("MAX_SESSIONS", default=1000, minimum=1),
        session_ttl_seconds=_read_int("SESSION_TTL_SECONDS", default=3600, minimum=60),
    )