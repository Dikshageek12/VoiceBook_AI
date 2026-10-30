from datetime import time
from sqlalchemy import select
from app.database import SessionLocal
from app import models

# Fake data for development only
CATALOG = {
    "Cardiology": {
        "services": [("Cardiology consultation", 20), ("ECG review", 15), ("Echocardiogram", 45)],
        "doctors": ["Dr. Demo Cardio-1", "Dr. Demo Cardio-2"],
    },
    "Orthopedics": {
        "services": [("Orthopedic consultation", 20), ("Fracture follow-up", 15)],
        "doctors": ["Dr. Demo Ortho-1", "Dr. Demo Ortho-2"],
    },
    "Dermatology": {
        "services": [("Skin consultation", 15), ("Minor procedure", 30)],
        "doctors": ["Dr. Demo Derm-1"],
    },
    "Pediatrics": {
        "services": [("Child consultation", 20), ("Vaccination visit", 10)],
        "doctors": ["Dr. Demo Peds-1", "Dr. Demo Peds-2"],
    },
    "General Medicine": {
        "services": [("General consultation", 15), ("Health checkup", 30)],
        "doctors": ["Dr. Demo GM-1", "Dr. Demo GM-2", "Dr. Demo GM-3"],
    },
}


def seed():
    db = SessionLocal()
    try:
        if db.scalar(select(models.Department.id).limit(1)):
            print("Database already seeded. Delete voicebook.db and run alembic upgrade head to reseed.")
            return

        for dept_name, info in CATALOG.items():
            dept = models.Department(name=dept_name)
            db.add(dept)
            db.flush()

            for svc_name, minutes in info["services"]:
                db.add(models.Service(name=svc_name, duration_minutes=minutes,
                                      department_id=dept.id))

            for doc_name in info["doctors"]:
                doc = models.Doctor(name=doc_name, department_id=dept.id)
                db.add(doc)
                db.flush()
                # Monday to Saturday: morning and afternoon shifts
                for weekday in range(6):
                    db.add(models.DoctorSchedule(doctor_id=doc.id, weekday=weekday,
                                                 start_time=time(9, 0), end_time=time(13, 0)))
                    db.add(models.DoctorSchedule(doctor_id=doc.id, weekday=weekday,
                                                 start_time=time(14, 0), end_time=time(17, 0)))

        db.commit()
        print("Seeded hospital data.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()