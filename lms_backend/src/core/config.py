from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    # SECURITY NOTE: Must be set in .env by orchestrator
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 60 * 24  # 24h

    # SQLite database file path. This must point at the db file created by lms_database.
    # Default filename matches lms_database/init_db.py (DB_NAME = "myapp.db").
    sqlite_db_path: str = os.getenv("SQLITE_DB_PATH", "myapp.db")

    # CORS
    cors_allow_origins: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cors_allow_origins",
            (
                os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
                if os.getenv("CORS_ALLOW_ORIGINS")
                else ["*"]
            ),
        )


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Load and return settings from environment variables."""
    secret = os.getenv("JWT_SECRET_KEY", "")
    if not secret:
        # Intentionally raise early so the container fails fast with a clear message.
        raise RuntimeError(
            "Missing required env var JWT_SECRET_KEY. "
            "Ask orchestrator/user to set it in the backend .env."
        )

    algo = os.getenv("JWT_ALGORITHM", "HS256")
    exp_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", "1440"))

    return Settings(
        jwt_secret_key=secret,
        jwt_algorithm=algo,
        access_token_expires_minutes=exp_minutes,
    )
