from contextlib import contextmanager
from typing import Generator
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from app.core.config import get_config
# DATABASE CONNECTION
def get_connector(schema="ccplatform"):
    """Database connection credentials."""
    config = get_config(key=schema)
    connect_url = sqlalchemy.engine.URL.create(
        drivername="mysql+mysqlconnector",
        username=config["userName"],
        password=config["password"],
        host=config["host"],
        port=config["port"],
        database=config["schema"],
    )
    return connect_url
# SQLALCHEMY ENGINE
engine = sqlalchemy.create_engine(
    get_connector(),
    pool_size=10,
    max_overflow=2,
    pool_recycle=300,
    pool_pre_ping=True,
    pool_use_lifo=True,
)
# SESSION
Session = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
# SESSION SCOPE
@contextmanager
def session_scope() -> Generator:
    """Provide a transactional scope around a series of operations."""
    session = None
    try:
        session = Session()
        yield session
    finally:
        if session:
            session.close()
# QUERY RESULT FORMATTER
def receive_query(query):
    """Result dict formatter."""
    return [
        row._asdict()
        for row in query
    ]
# CREATE DATABASE TABLES
from app.db.models import Base
Base.metadata.create_all(
    bind=engine
)