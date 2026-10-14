"""
Configuration settings for YAFR application.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "table.db"


class Config:
    """Base application configuration."""

    SECRET_KEY = os.environ.get("YAFR_SECRET_KEY", "yafr-dev-secret-key-change-in-prod")
    DEBUG = os.environ.get("YAFR_DEBUG", "True").lower() in ("true", "1", "yes")
    HOST = os.environ.get("YAFR_HOST", "127.0.0.1")
    PORT = int(os.environ.get("YAFR_PORT", 5000))

    # SQLite Database File Location - Defaults to data/table.db
    DATABASE_PATH = os.environ.get("YAFR_DATABASE_PATH", str(DEFAULT_DB_PATH))

    # UI Configurations (Defaults loaded from or synced with configurationentry in database)
    DEFAULT_DISPLAY_STYLE = "style-dark"  # "style-light" or "style-dark"
    DEFAULT_DISPLAY_TYPE = "gallery"  # "standard", "gallery", "search-engine", "content-centric", "links-only"

    # Default limits
    MAX_SEARCH_HISTORY = 300
    MAX_VISIT_HISTORY = 5000
    LINKS_PER_PAGE = 25
