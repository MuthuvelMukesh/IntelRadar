from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Create SQLite database engine
# check_same_thread=False is needed for SQLite usage with Telegram bot threads
DB_URL = "sqlite:///news_bot.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Generator for database sessions (useful for dependency injection if needed)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
