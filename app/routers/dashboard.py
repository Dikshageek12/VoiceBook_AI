from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.models import ACTIVE_STATUSES

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    calls = db.scalar(select(func.count()).select_from(models.CallLog))
    active = db.scalar(
        select(func.count()).select_from(models.Appointment)
        .where(models.Appointment.status.in_(ACTIVE_STATUSES))
    )
    cancelled = db.scalar(
        select(func.count()).select_from(models.Appointment)
        .where(models.Appointment.status == "cancelled")
    )
    patients = db.scalar(select(func.count()).select_from(models.Patient))
    return {"calls": calls, "active_appointments": active,
            "cancelled": cancelled, "patients": patients}


@router.get("/dashboard/appointments")
def dashboard_appointments(db: Session = Depends(get_db)):
    query = (
        select(models.Appointment, models.Patient, models.Doctor, models.Service)
        .join(models.Patient, models.Appointment.patient_id == models.Patient.id)
        .join(models.Doctor, models.Appointment.doctor_id == models.Doctor.id)
        .join(models.Service, models.Appointment.service_id == models.Service.id)
        .where(models.Appointment.status.in_(ACTIVE_STATUSES))
        .order_by(models.Appointment.start_time)
    )
    return [
        {
            "appointment_id": a.id,
            "patient": p.full_name or "(no name)",
            "phone": p.phone,
            "doctor": d.name,
            "service": s.name,
            "start_time": a.start_time.isoformat(timespec="minutes"),
            "status": a.status,
        }
        for a, p, d, s in db.execute(query).all()
    ]
