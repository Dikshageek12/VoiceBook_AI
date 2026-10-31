from datetime import datetime, time
from sqlalchemy import String, Integer, ForeignKey, DateTime, Time, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AppointmentStatus:
    BOOKED = "booked"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


# Statuses that occupy a slot. Cancelled and completed appointments free it.
ACTIVE_STATUSES = (AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    doctors: Mapped[list["Doctor"]] = relationship(back_populates="department")
    services: Mapped[list["Service"]] = relationship(back_populates="department")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))

    department: Mapped[Department] = relationship(back_populates="doctors")
    schedules: Mapped[list["DoctorSchedule"]] = relationship(back_populates="doctor")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))

    department: Mapped[Department] = relationship(back_populates="services")


class DoctorSchedule(Base):
    """One working window for a doctor on one weekday. A doctor can have several."""
    __tablename__ = "doctor_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    weekday: Mapped[int] = mapped_column(Integer)  # 0 = Monday ... 6 = Sunday
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)

    doctor: Mapped[Doctor] = relationship(back_populates="schedules")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)  # captured during the call
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default=AppointmentStatus.BOOKED)

    __table_args__ = (
        # Database-level guard: a doctor cannot have two active bookings at the same start time.
        Index(
            "uq_active_doctor_start",
            "doctor_id",
            "start_time",
            unique=True,
            sqlite_where=text("status IN ('booked', 'rescheduled')"),
            postgresql_where=text("status IN ('booked', 'rescheduled')"),
        ),
    )


class CallLog(Base):
    """One row per phone call. The table is created in Phase 1 and filled in Phase 2."""
    __tablename__ = "call_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_call_id: Mapped[str] = mapped_column(String(64), unique=True)  # Twilio CallSid
    caller_phone: Mapped[str] = mapped_column(String(20), index=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)  # booked | rescheduled | cancelled | handed_off