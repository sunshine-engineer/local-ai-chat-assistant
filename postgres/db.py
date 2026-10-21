import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

# Compose sets DB_HOST; local development defaults to SQLite.
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    DATABASE_URL = URL.create(
        'postgresql+psycopg2', username=os.getenv('DB_USER', 'chatbot'),
        password=os.getenv('DB_PASSWORD', 'chatbot'), host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', '5432')), database=os.getenv('DB_NAME', 'chatbot'),
    ) if os.getenv('DB_HOST') else 'sqlite:///assistant.db'
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
