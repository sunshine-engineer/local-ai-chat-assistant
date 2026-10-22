"""SQLAlchemy chat-database configuration and session factory.

File: postgres/db.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from assistant.config import setting

# Compose sets DB_HOST; local development defaults to SQLite.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = (
        URL.create(
            "postgresql+psycopg2",
            username=setting("database", "user", "DB_USER"),
            password=setting("database", "password", "DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=setting("database", "port", "DB_PORT"),
            database=setting("database", "name", "DB_NAME"),
        )
        if os.getenv("DB_HOST")
        else "sqlite:///assistant.db"
    )
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
