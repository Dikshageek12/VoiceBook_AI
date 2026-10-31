from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models import (
    ACTIVE_STATUSES, Appointment, AppointmentStatus, Doctor, DoctorSchedule, Patient, Service,
)


class BookingError(Exception):
    """A booking rule was broken. The message is written to be read aloud to a caller."""


SLOT_TAKEN = "That slot is no longer available. Please choose another time."


def _validate_slot(db: Session, doctor: Doctor, service: Service,
                   start: datetime, exclude_appointment_id: int | None = None) -> datetime:
    if doctor.department_id != service.department_id:
        raise BookingError("This doctor does not offer that service.")

    end = start + timedelta(minutes=service.duration_minutes)

    # Rule 1: the whole visit must fit inside one working window on the same day
    shifts = db.scalars(
        select(DoctorSchedule).where(
            DoctorSchedule.doctor_id == doctor.id,
            DoctorSchedule.weekday == start.weekday(),
        )
    ).all()
    within_hours = any(
        s.start_time <= start.time() and end.time() <= s.end_time and end.date() == start.date()
        for s in shifts
    )
    if not within_hours:
        raise BookingError("That time is outside the doctor's working hours.")

    # Rule 2: no overlapping active appointments for this doctor
    clash_query = select(Appointment).where(
        Appointment.doctor_id == doctor.id,
        Appointment.status.in_(ACTIVE_STATUSES),
        Appointment.start_time < end,
        Appointment.end_time > start,
    )
    if exclude_appointment_id is not None:
        clash_query = clash_query.where(Appointment.id != exclude_appointment_id)
    if db.scalars(clash_query).first() is not None:
        raise BookingError(SLOT_TAKEN)

    return end


def create_appointment(db: Session, patient_id: int, doctor_id: int,
                       service_id: int, start: datetime) -> Appointment:
    if db.get(Patient, patient_id) is None:
        raise BookingError("Unknown patient.")
    doctor = db.get(Doctor, doctor_id)
    service = db.get(Service, service_id)
    if doctor is None or service is None:
        raise BookingError("Unknown doctor or service.")

    end = _validate_slot(db, doctor, service, start)

    appt = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        service_id=service_id,
        start_time=start,
        end_time=end,
        status=AppointmentStatus.BOOKED,
    )
    db.add(appt)
    try:
        db.commit()
    except IntegrityError:
        # Another request took the same slot between our check and our insert
        db.rollback()
        raise BookingError(SLOT_TAKEN)
    db.refresh(appt)
    return appt


def reschedule_appointment(db: Session, appointment_id: int, new_start: datetime) -> Appointment:
    appt = db.get(Appointment, appointment_id)
    if appt is None or appt.status not in ACTIVE_STATUSES:
        raise BookingError("No active appointment found.")

    doctor = db.get(Doctor, appt.doctor_id)
    service = db.get(Service, appt.service_id)
    new_end = _validate_slot(db, doctor, service, new_start, exclude_appointment_id=appt.id)

    appt.start_time = new_start
    appt.end_time = new_end
    appt.status = AppointmentStatus.RESCHEDULED
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BookingError(SLOT_TAKEN)
    db.refresh(appt)
    return appt


def cancel_appointment(db: Session, appointment_id: int) -> Appointment:
    appt = db.get(Appointment, appointment_id)
    if appt is None or appt.status not in ACTIVE_STATUSES:
        raise BookingError("No active appointment found.")
    appt.status = AppointmentStatus.CANCELLED
    db.commit()
    db.refresh(appt)
    return appt