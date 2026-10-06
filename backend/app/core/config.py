"""Application configuration loaded from environment variables with sensible defaults."""
from __future__ import annotations

import os
from pathlib import Path


class Settings:
    """Typed settings object. All values read at import time from environment."""

    # Database
    database_url: str
    # Data root for the evidence engine
    data_root: Path
    # Application
    app_title: str = "TRACEIQ"
    app_version: str = "0.1.0"
    debug: bool = False

    def __init__(self) -> None:
        self.database_url = os.environ.get(
            "DATABASE_URL", "sqlite:///./traceiq.db"
        )
        data_root_env = os.environ.get("DATA_ROOT", "")
        if data_root_env:
            self.data_root = Path(data_root_env)
        else:
            # Default: repo-relative data/generated
            self.data_root = Path(__file__).resolve().parents[3] / "data" / "generated"
        self.debug = os.environ.get("DEBUG", "").lower() in {"1", "true", "yes"}


settings = Settings()
