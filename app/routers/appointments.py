from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.models import ACTIVE_STATUSES, AppointmentStatus
from app.schemas import AppointmentOut, AppointmentUpdate, BookingIn, PatientIn, PatientOut
from app.services.booking import cancel_appointment, create_appointment, reschedule_appointment

router = APIRouter(tags=["appointments"])


def _get_appointment_or_404(db: Session, appt_id: int) -> models.Appointment:
    appt = db.get(models.Appointment, appt_id)
    if appt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    return appt


@router.post("/patients", response_model=PatientOut)
def upsert_patient(body: PatientIn, db: Session = Depends(get_db)):
    """Return the existing patient for this phone number, or create one."""
    patient = db.scalar(select(models.Patient).where(models.Patient.phone == body.phone))
    if patient is None:
        patient = models.Patient(full_name=body.full_name, phone=body.phone)
        db.add(patient)
    elif body.full_name and not patient.full_name:
        patient.full_name = body.full_name
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/patients/by-phone", response_model=PatientOut)
def find_patient_by_phone(phone: str, db: Session = Depends(get_db)):
    """Repeat-caller lookup. The voice agent passes the caller's number here."""
    patient = db.scalar(select(models.Patient).where(models.Patient.phone == phone))
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No patient found for this number")
    return patient


@router.get("/patients/{patient_id}/appointments", response_model=list[AppointmentOut])
def list_patient_appointments(patient_id: int, db: Session = Depends(get_db)):
    """Active bookings for a patient. The agent uses this to find which one to change."""
    query = (
        select(models.Appointment)
        .where(
            models.Appointment.patient_id == patient_id,
            models.Appointment.status.in_(ACTIVE_STATUSES),
        )
        .order_by(models.Appointment.start_time)
    )
    return db.scalars(query).all()


@router.post("/appointments", response_model=AppointmentOut,
             status_code=status.HTTP_201_CREATED)
def book(body: BookingIn, db: Session = Depends(get_db)):
    # BookingError becomes a 409 in the global handler in main.py
    return create_appointment(db, body.patient_id, body.doctor_id, body.service_id, body.start_time)


@router.get("/appointments/{appt_id}", response_model=AppointmentOut)
def get_appointment(appt_id: int, db: Session = Depends(get_db)):
    return _get_appointment_or_404(db, appt_id)


@router.patch("/appointments/{appt_id}", response_model=AppointmentOut)
def update_appointment(appt_id: int, body: AppointmentUpdate, db: Session = Depends(get_db)):
    """Reschedule (send start_time) or cancel (send status='cancelled')."""
    _get_appointment_or_404(db, appt_id)
    if body.status == AppointmentStatus.CANCELLED:
        return cancel_appointment(db, appt_id)
    if body.start_time is not None:
        return reschedule_appointment(db, appt_id, body.start_time)
    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Send start_time to reschedule, or status='cancelled' to cancel",
    )