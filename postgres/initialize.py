"""Command-line initialization of missing chat database tables.

File: postgres/initialize.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""


def main():
    """Create missing chat database tables without deleting existing records."""
    from postgres.db import engine
    from postgres.models import Base

    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")


if __name__ == "__main__":
    main()
