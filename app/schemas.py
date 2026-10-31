from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    department_id: int


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    duration_minutes: int
    department_id: int


class AvailabilityOut(BaseModel):
    doctor_id: int
    service_id: int
    slots: list[str]


class PatientIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str = Field(pattern=r"^\+?[0-9]{7,15}$")


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str | None
    phone: str


class BookingIn(BaseModel):
    patient_id: int
    doctor_id: int
    service_id: int
    start_time: datetime  # naive local clinic time, e.g. "2026-10-19T09:00:00"


class AppointmentUpdate(BaseModel):
    """Send start_time to reschedule, or status='cancelled' to cancel."""
    start_time: datetime | None = None
    status: Literal["cancelled"] | None = None


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int
    doctor_id: int
    service_id: int
    start_time: datetime
    end_time: datetime
    status: str