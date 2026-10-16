from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def migrate_security_events():
    """Add alert metadata to existing SQLite databases without deleting data."""
    if "sqlite" not in settings.DATABASE_URL:
        return

    inspector = inspect(engine)
    if "security_events" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("security_events")}
    additions = {
        "iow": "FLOAT",
        "alert_state": "VARCHAR DEFAULT 'INACTIVE'",
        "alarm_state": "VARCHAR DEFAULT 'INACTIVE'",
        "acknowledged_at": "DATETIME",
        "acknowledged_by": "VARCHAR",
        "reviewed_at": "DATETIME",
        "reviewed_by": "VARCHAR",
    }

    with engine.begin() as connection:
        for name, sql_type in additions.items():
            if name not in existing_columns:
                connection.execute(text(f"ALTER TABLE security_events ADD COLUMN {name} {sql_type}"))
        if "alert_state" not in existing_columns:
            connection.execute(text("UPDATE security_events SET alert_state = 'INACTIVE' WHERE alert_state IS NULL"))
        if "alarm_state" not in existing_columns:
            connection.execute(text("UPDATE security_events SET alarm_state = 'INACTIVE' WHERE alarm_state IS NULL"))

migrate_security_events()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
