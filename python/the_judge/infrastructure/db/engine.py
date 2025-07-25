# infrastructure/db/engine.py
from pathlib import Path

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker

from the_judge.settings import get_settings

# Global engine instance
_engine: Engine = None
_session_factory: sessionmaker = None


def get_engine() -> Engine:
    """Get or create SQLAlchemy engine."""
    global _engine
    if _engine is None:
        config = get_settings()
        database_url = config.database_url
        
        # Create database directory if using SQLite
        if database_url.startswith('sqlite'):
            # Extract path from sqlite:///path/to/db.db
            db_path = database_url.replace('sqlite:///', '')
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        _engine = create_engine(
            database_url,
            echo=getattr(config, 'debug', False),  # Use debug flag for SQL logging
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create SQLAlchemy session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine())
    return _session_factory


def initialize_database():
    """Initialize database - create tables if they don't exist."""
    from .orm import metadata, start_mappers
    
    # Initialize mappers first
    start_mappers()
    
    # Create tables if they don't exist
    engine = get_engine()
    metadata.create_all(engine)
    
    print(f"Database initialized at: {get_settings().database_url}")


def create_tables():
    """Create all database tables."""
    initialize_database()  # Use the new function


def drop_tables():
    """Drop all database tables (for testing/development)."""
    from .orm import metadata
    
    engine = get_engine()
    metadata.drop_all(engine)
