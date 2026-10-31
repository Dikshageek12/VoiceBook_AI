from datetime import date, datetime, time, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import ACTIVE_STATUSES, Appointment, Doctor, DoctorSchedule, Service


def overlaps(start: datetime, end: datetime, appointments: list[Appointment]) -> bool:
    """True if the interval [start, end) overlaps any appointment in the list."""
    return any(a.start_time < end and a.end_time > start for a in appointments)


def get_available_slots(
    db: Session,
    doctor_id: int,
    service_id: int,
    date_from: date,
    date_to: date,
    now: datetime | None = None,
    step_minutes: int = 15,
) -> list[datetime]:
    """Possible start times for a service with a doctor between two dates (inclusive)."""
    now = now or datetime.now()

    doctor = db.get(Doctor, doctor_id)
    service = db.get(Service, service_id)
    if doctor is None or service is None:
        raise ValueError("Unknown doctor or service")
    if doctor.department_id != service.department_id:
        raise ValueError("This doctor does not offer that service")

    duration = timedelta(minutes=service.duration_minutes)
    step = timedelta(minutes=step_minutes)

    window_start = datetime.combine(date_from, time.min)
    window_end = datetime.combine(date_to, time.max)

    booked = db.scalars(
        select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_(ACTIVE_STATUSES),
            Appointment.start_time < window_end,
            Appointment.end_time > window_start,
        )
    ).all()

    schedules = db.scalars(
        select(DoctorSchedule).where(DoctorSchedule.doctor_id == doctor_id)
    ).all()

    slots: list[datetime] = []
    day = date_from
    while day <= date_to:
        for shift in schedules:
            if shift.weekday != day.weekday():
                continue
            cursor = datetime.combine(day, shift.start_time)
            shift_end = datetime.combine(day, shift.end_time)
            while cursor + duration <= shift_end:
                slot_end = cursor + duration
                if cursor > now and not overlaps(cursor, slot_end, booked):
                    slots.append(cursor)
                cursor += step
        day += timedelta(days=1)

    return sorted(slots)


def suggest_alternatives(
    db: Session,
    doctor_id: int,
    service_id: int,
    requested: datetime,
    count: int = 3,
    search_days: int = 7,
    now: datetime | None = None,
) -> list[datetime]:
    """Open slots closest to the requested time. The voice agent offers these when a slot is taken."""
    day = requested.date()
    slots = get_available_slots(
        db, doctor_id, service_id, day, day + timedelta(days=search_days), now=now
    )
    return sorted(slots, key=lambda s: abs(s - requested))[:count]