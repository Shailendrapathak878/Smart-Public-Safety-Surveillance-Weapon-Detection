import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, SecurityEvent
from database.repository import Repository
from core.detection_types import ValidatedThreat, Detection, BoundingBox

@pytest.fixture
def db_session():
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_create_security_event(db_session):
    repo = Repository(db_session)
    
    weapon = Detection(0, "gun", 0.9, BoundingBox(0,0,10,10))
    human = Detection(0, "person", 0.9, BoundingBox(0,0,10,10))
    threat = ValidatedThreat(weapon, human, 1.0)
    
    event = repo.create_security_event(threat, "TestCamera", "/fake/path.jpg")
    
    assert event.id is not None
    assert event.weapon_type == "gun"
    assert event.camera_source == "TestCamera"
    assert event.status == "NEW"

    # Test retrieval
    events = repo.get_recent_events()
    assert len(events) == 1
    assert events[0].id == event.id
