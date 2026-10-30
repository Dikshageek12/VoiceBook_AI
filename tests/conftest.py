from datetime import time
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import models
from app.database import Base


@pytest.fixture
def db():
    """A fresh in-memory database for every test. Your voicebook.db is never touched."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def world(db):
    """A minimal hospital: one cardiology doctor, one 30-minute service, Monday to Friday 09:00-12:00."""
    cardio = models.Department(name="Cardiology")
    derm = models.Department(name="Dermatology")
    db.add_all([cardio, derm])
    db.flush()

    doctor = models.Doctor(name="Dr. Test Cardio", department_id=cardio.id)
    db.add(doctor)
    db.flush()

    service = models.Service(name="Consultation", duration_minutes=30, department_id=cardio.id)
    derm_service = models.Service(name="Skin check", duration_minutes=30, department_id=derm.id)
    patient = models.Patient(full_name="Test Patient", phone="+910000000000")
    db.add_all([service, derm_service, patient])
    db.flush()

    for weekday in range(5):
        db.add(models.DoctorSchedule(doctor_id=doctor.id, weekday=weekday,
                                     start_time=time(9, 0), end_time=time(12, 0)))
    db.commit()
    return {"doctor": doctor, "service": service, "derm_service": derm_service, "patient": patient}