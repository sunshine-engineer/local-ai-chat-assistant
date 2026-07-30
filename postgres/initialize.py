from postgres.db import engine
from postgres.models import Base

Base.metadata.create_all(bind=engine)
print("Database initialized successfully!")