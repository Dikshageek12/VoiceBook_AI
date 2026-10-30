from datetime import date, datetime
import pytest
from app.models import AppointmentStatus
from app.services.availability import get_available_slots, suggest_alternatives
from app.services.booking import (
    BookingError, cancel_appointment, create_appointment, reschedule_appointment,
)

MONDAY = date(2026, 10, 19)
SATURDAY = date(2026, 10, 24)
NOW = datetime(2026, 10, 1, 8, 0)  # fixed "now" so tests don't depend on the real clock


def slots_for(db, w, day=MONDAY):
    return get_available_slots(db, w["doctor"].id, w["service"].id, day, day,
                               now=NOW, step_minutes=30)


def book(db, w, hour, minute=0):
    return create_appointment(db, w["patient"].id, w["doctor"].id, w["service"].id,
                              datetime(2026, 10, 19, hour, minute))


def test_slots_follow_schedule(db, world):
    # 09:00-12:00 with 30-minute visits and 30-minute steps: 09:00 ... 11:30 = 6 slots
    assert len(slots_for(db, world)) == 6


def test_no_slots_on_weekend(db, world):
    assert slots_for(db, world, SATURDAY) == []


def test_booked_slot_disappears(db, world):
    book(db, world, 9)
    slots = slots_for(db, world)
    assert len(slots) == 5
    assert datetime(2026, 10, 19, 9, 0) not in slots


def test_exact_double_booking_rejected(db, world):
    book(db, world, 9)
    with pytest.raises(BookingError):
        book(db, world, 9)


def test_overlapping_booking_rejected(db, world):
    # A 09:00 visit occupies 09:00-09:30, so a 09:15 visit overlaps it
    book(db, world, 9)
    with pytest.raises(BookingError):
        book(db, world, 9, 15)


def test_outside_working_hours_rejected(db, world):
    # 11:45 + 30 minutes runs past the 12:00 end of the shift
    with pytest.raises(BookingError, match="working hours"):
        book(db, world, 11, 45)


def test_wrong_department_rejected(db, world):
    with pytest.raises(BookingError, match="does not offer"):
        create_appointment(db, world["patient"].id, world["doctor"].id,
                           world["derm_service"].id, datetime(2026, 10, 19, 9, 0))


def test_cancel_frees_slot(db, world):
    appt = book(db, world, 9)
    cancel_appointment(db, appt.id)
    assert len(slots_for(db, world)) == 6


def test_cancelled_slot_can_be_rebooked(db, world):
    appt = book(db, world, 9)
    cancel_appointment(db, appt.id)
    book(db, world, 9)


def test_reschedule_moves_slot(db, world):
    appt = book(db, world, 9)
    reschedule_appointment(db, appt.id, datetime(2026, 10, 19, 10, 0))
    slots = slots_for(db, world)
    assert datetime(2026, 10, 19, 9, 0) in slots
    assert datetime(2026, 10, 19, 10, 0) not in slots


def test_rescheduled_appointment_still_blocks_its_slot(db, world):
    appt = book(db, world, 9)
    reschedule_appointment(db, appt.id, datetime(2026, 10, 19, 10, 0))
    assert appt.status == AppointmentStatus.RESCHEDULED
    with pytest.raises(BookingError):
        book(db, world, 10)


def test_cancelled_appointment_cannot_be_cancelled_again(db, world):
    appt = book(db, world, 9)
    cancel_appointment(db, appt.id)
    with pytest.raises(BookingError):
        cancel_appointment(db, appt.id)


def test_alternatives_are_nearest_open_slots(db, world):
    book(db, world, 9)
    alternatives = suggest_alternatives(db, world["doctor"].id, world["service"].id,
                                        datetime(2026, 10, 19, 9, 0), count=3, now=NOW)
    assert datetime(2026, 10, 19, 9, 0) not in alternatives
    assert alternatives[0] == datetime(2026, 10, 19, 9, 30)